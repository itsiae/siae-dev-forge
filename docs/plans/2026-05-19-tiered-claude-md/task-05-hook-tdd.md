---
task: 05
title: TDD hook session-start-tiered-advisor
status: PENDING
estimate_min: 60
type: TDD
depends_on: []
---

# Task 05 — TDD hook `session-start-tiered-advisor`

## Obiettivo

Implementare hook bash non-bloccante che rileva CLAUDE.md mancante o stale
all'avvio sessione, emette suggerimento via `additionalContext` senza
bloccare il boot.

## File da creare

1. `hooks/session-start-tiered-advisor` (~80 righe bash)
2. `tests/test_hook_session_start_tiered_advisor.py` (~120 righe pytest)
3. `tests/fixtures/hook-tiered-advisor/` con fixture:
   - `repo-with-fresh-map/` (CODEBASE_MAP.md last_mapped oggi)
   - `repo-with-stale-map/` (last_mapped 30gg fa)
   - `repo-without-map/` (no docs/CODEBASE_MAP.md)
   - `repo-with-many-commits/` (last_mapped 5gg fa + 50 commit simulati)

## Hook contract

**Input:** env vars Claude Code SessionStart hook
- `CLAUDE_PROJECT_DIR` — root del repo
- (matcher: `startup|resume`)

**Output stdout:** opzionale `additionalContext` markdown (vedi Claude Code docs)

**Exit code:** 0 SEMPRE (memory `feedback_session_start_hook_invariants`)

## Logica

```bash
#!/usr/bin/env bash
set -uo pipefail  # NON pipefail+e: hook non deve mai fallire
# Memory feedback_session_start_hook_invariants: pipefail guard + 2>/dev/null

ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$ROOT" 2>/dev/null || exit 0

MAP="docs/CODEBASE_MAP.md"

# Timeout 3s hard cap
(
  if [[ ! -f "$MAP" ]]; then
    cat <<-EOF
	{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "ℹ Nessuna codebase map in docs/CODEBASE_MAP.md. Per generarla: /forge-map (o /forge-map --tiered per gerarchia)."}}
	EOF
    exit 0
  fi

  # Parse last_mapped dal frontmatter
  LAST_MAPPED=$(awk '/^last_mapped:/ {print $2; exit}' "$MAP" 2>/dev/null)
  [[ -z "$LAST_MAPPED" ]] && exit 0

  # Calcolo età in giorni (macOS BSD date + Linux GNU date fallback)
  if NOW_TS=$(date -u +%s 2>/dev/null) && MAP_TS=$(date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "$LAST_MAPPED" +%s 2>/dev/null || date -u -d "$LAST_MAPPED" +%s 2>/dev/null); then
    AGE_DAYS=$(( (NOW_TS - MAP_TS) / 86400 ))
  else
    AGE_DAYS=0
  fi

  # Commits since last_mapped
  COMMITS=$(git -C "$ROOT" rev-list --count HEAD --since="$LAST_MAPPED" 2>/dev/null || echo 0)
  # Memory feedback_bash_grep_count_fallback: usa true non echo 0 — fix:
  COMMITS=${COMMITS:-0}

  if (( AGE_DAYS > 14 )) || (( COMMITS >= 30 )); then
    cat <<-EOF
	{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "⚠ Codebase map stale: $AGE_DAYS giorni, $COMMITS commit dall'ultimo mapping. Suggerito: /forge-map (--tiered per gerarchia)."}}
	EOF
  fi
) &
HOOK_PID=$!

# Timeout 3s
sleep 3
kill -0 $HOOK_PID 2>/dev/null && kill $HOOK_PID 2>/dev/null

wait $HOOK_PID 2>/dev/null
exit 0  # SEMPRE exit 0
```

## TDD cycle

**RED 1:** `test_hook_no_map_emits_advisory`
- Arrange: fixture `repo-without-map/`
- Act: invoke hook, capture stdout
- Assert: stdout contiene "Nessuna codebase map" + JSON valido

**RED 2:** `test_hook_fresh_map_no_output`
- Arrange: fixture `repo-with-fresh-map/`
- Act: invoke
- Assert: stdout vuoto, exit 0

**RED 3:** `test_hook_stale_map_emits_advisory`
- Arrange: fixture `repo-with-stale-map/` (last_mapped 30gg fa)
- Act: invoke
- Assert: stdout contiene "stale" + "30 giorni"

**RED 4:** `test_hook_many_commits_emits_advisory`
- Arrange: fixture `repo-with-many-commits/` (5gg + 50 commit)
- Act: invoke
- Assert: stdout contiene "50 commit"

**RED 5:** `test_hook_exits_zero_on_git_error`
- Arrange: directory NON git
- Act: invoke
- Assert: exit code 0 (anche se git fail)

**RED 6:** `test_hook_exits_zero_on_timeout`
- Arrange: mock git command che hang
- Act: invoke con timeout
- Assert: exit code 0, hook ucciso a 3s

**RED 7:** `test_hook_json_output_valid`
- Act: invoke su stale map
- Assert: stdout è JSON parsabile con campi `hookSpecificOutput.hookEventName == "SessionStart"`

## Criteri di accettazione

1. ✅ 7 test pytest PASS
2. ✅ Hook exit code 0 in TUTTI gli scenari
3. ✅ Output JSON conforme spec SessionStart Claude Code
4. ✅ Timeout 3s rispettato
5. ✅ Compatibile macOS BSD + Linux GNU date
6. ✅ Nessun output stderr a meno di errore catastrofico

## Definition of Done

- Hook + test creati
- 7/7 PASS
- Hook eseguibile (`chmod +x`)
- Commit: `feat(hooks): session-start-tiered-advisor non-blocking stale detector`
