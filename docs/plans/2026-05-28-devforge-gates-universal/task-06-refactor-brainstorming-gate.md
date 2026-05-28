# Task 06 — Refactor `brainstorming-gate` (riordino + commento) + 7 integration test

> **REQUIRED SUB-SKILL:** `siae-tdd`
> **Dipendenza:** task 01 (lib esistente)
> **Attenzione speciale:** riordino blocchi richiesto (scope-check attuale L65 PRIMA di PLUGIN_ROOT L71)

**Goal:** `hooks/brainstorming-gate` usa `devforge_gate_scope_active` con scope-check spostato DOPO il blocco source. Commento legacy `non-itsiae-taskable` generalizzato. 7 scenari integration PASS.

**File coinvolti:**
- Modifica: `hooks/brainstorming-gate` (riordino blocchi + sostituzione inline + cleanup commento)
- Crea: `tests/integration/brainstorming_gate.test.sh`

---

## Step 1 — Scrivi il test fallente

Crea `tests/integration/brainstorming_gate.test.sh`:

```bash
#!/usr/bin/env bash
# Integration test brainstorming-gate — 7 scenari (design §6.2)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
HOOK="${REPO_ROOT}/hooks/brainstorming-gate"

PASS=0; FAIL=0; FAIL_DETAILS=""

TMPDIR=$(mktemp -d)
cleanup() {
    rm -rf "$TMPDIR"
    rm -f "${HOME}/.claude/.devforge-gate-scope"
    rm -f "${HOME}/.claude/.devforge-session-skills"
}
trap cleanup EXIT

setup_repo() {
    local remote="$1"
    rm -rf "$TMPDIR/repo"; mkdir -p "$TMPDIR/repo/src/main"
    (cd "$TMPDIR/repo" && git init -q && [ -n "$remote" ] && git remote add origin "$remote" || true)
}

run_hook() {
    local cwd="$1" file_path="$2"
    (cd "$cwd" && echo "{\"tool_input\":{\"file_path\":\"$file_path\",\"new_string\":\"x\"}}" | bash "$HOOK" 2>/dev/null)
}

assert_passes() {
    local n="$1" desc="$2" output="$3"
    if echo "$output" | grep -q '"decision"[[:space:]]*:[[:space:]]*"block"'; then
        FAIL=$((FAIL + 1)); FAIL_DETAILS="${FAIL_DETAILS}\n  [FAIL] ${n} ${desc}"
    else
        PASS=$((PASS + 1)); printf "  [PASS] %s %s\n" "$n" "$desc"
    fi
}
assert_blocks() {
    local n="$1" desc="$2" output="$3"
    if echo "$output" | grep -q '"decision"[[:space:]]*:[[:space:]]*"block"'; then
        PASS=$((PASS + 1)); printf "  [PASS] %s %s\n" "$n" "$desc"
    else
        FAIL=$((FAIL + 1)); FAIL_DETAILS="${FAIL_DETAILS}\n  [FAIL] ${n} ${desc}: ${output}"
    fi
}

mark_validated() { mkdir -p "${HOME}/.claude"; echo "siae-brainstorming" >> "${HOME}/.claude/.devforge-session-skills"; }
clear_validated() { rm -f "${HOME}/.claude/.devforge-session-skills"; }

PROD_FILE="$TMPDIR/repo/src/main/foo.java"

clear_validated; mark_validated; setup_repo "git@github.com:itsiae/foo.git"; unset DEVFORGE_GATE_SCOPE
assert_passes A "universal + itsiae + validated" "$(run_hook "$TMPDIR/repo" "$PROD_FILE")"

clear_validated; setup_repo "git@github.com:itsiae/foo.git"
assert_blocks B "universal + itsiae + not validated" "$(run_hook "$TMPDIR/repo" "$PROD_FILE")"

clear_validated; mark_validated; setup_repo "git@github.com:acme/foo.git"
assert_passes C "universal + acme + validated" "$(run_hook "$TMPDIR/repo" "$PROD_FILE")"

clear_validated; setup_repo "git@github.com:acme/foo.git"
assert_blocks D "universal + acme + not validated (NEW)" "$(run_hook "$TMPDIR/repo" "$PROD_FILE")"

clear_validated; setup_repo ""
assert_blocks E "universal + no remote + not validated" "$(run_hook "$TMPDIR/repo" "$PROD_FILE")"

clear_validated; setup_repo "git@github.com:itsiae/foo.git"; export DEVFORGE_GATE_SCOPE=itsiae
assert_blocks F "itsiae scope + itsiae + not validated" "$(run_hook "$TMPDIR/repo" "$PROD_FILE")"

clear_validated; setup_repo "git@github.com:acme/foo.git"; export DEVFORGE_GATE_SCOPE=itsiae
assert_passes G "itsiae scope + acme + not validated (rollback)" "$(run_hook "$TMPDIR/repo" "$PROD_FILE")"

unset DEVFORGE_GATE_SCOPE; clear_validated

echo
echo "brainstorming_gate.test.sh — PASS: $PASS / 7 — FAIL: $FAIL / 7"
[ -n "$FAIL_DETAILS" ] && echo -e "$FAIL_DETAILS"
[ "$FAIL" -eq 0 ] || exit 1
```

## Step 2 — Esegui e verifica che fallisce

```bash
bash tests/integration/brainstorming_gate.test.sh
```

Atteso: FAIL scenario D.

## Step 3 — Implementa il refactor (3 sub-edit)

### 3.1 — Riordino blocchi (CRITICO)

Stato attuale L62-75:
```bash
# Scope: itsiae/* only          ← L63
REMOTE_URL="$(git -C ...)"      ← L64
if ! echo "$REMOTE_URL" ...      ← L65
    echo '{}'                    ← L66
    exit 0                       ← L67
fi                               ← L68
...
PLUGIN_ROOT="..."                ← L71
source "${PLUGIN_ROOT}/lib/..."  ← L72-75
```

Nuovo ordine:
```bash
PLUGIN_ROOT="..."                ← prima
source "${PLUGIN_ROOT}/lib/logger.sh" 2>/dev/null || true
source "${PLUGIN_ROOT}/lib/block-explainer.sh" 2>/dev/null || true
source "${PLUGIN_ROOT}/lib/scope-check.sh" 2>/dev/null || true
if ! source "${PLUGIN_ROOT}/lib/file-taxonomy.sh" 2>/dev/null \
   || ! source "${PLUGIN_ROOT}/lib/task-id.sh" 2>/dev/null; then
    ...
fi
# Scope check: DEVFORGE_GATE_SCOPE env (default universal). Vedi lib/scope-check.sh.
REMOTE_URL="$(git -C "$FILE_GIT_ROOT" remote get-url origin 2>/dev/null || true)"
if command -v devforge_gate_scope_active >/dev/null 2>&1 \
   && ! devforge_gate_scope_active "$REMOTE_URL"; then
    echo '{}'
    exit 0
fi
```

**Operativamente:**
1. Sposta il blocco `PLUGIN_ROOT=... source ...` (attuale L71-75) PRIMA di `REMOTE_URL=...`
2. Sostituisci l'inline `grep itsiae/` con la chiamata alla lib (vedi pattern task 02)
3. Verifica che `FILE_GIT_ROOT` sia definita PRIMA del nuovo blocco scope-check (riga ~50 nel hook)

### 3.2 — Cleanup commento legacy (L153)

Stato attuale L153:
```bash
    # Rollback / non-itsiae-taskable path → legacy SID-anchored counter
```

Nuovo:
```bash
    # Rollback / no-task-id path → legacy SID-anchored counter
```

### 3.3 — Add source scope-check.sh

Aggiungi la riga `source "${PLUGIN_ROOT}/lib/scope-check.sh" 2>/dev/null || true` dopo il source di `block-explainer.sh` (L73 attuale).

## Step 4 — Esegui e verifica che passa

```bash
bash -n hooks/brainstorming-gate && bash tests/integration/brainstorming_gate.test.sh
grep -c "non-itsiae-taskable" hooks/brainstorming-gate  # atteso: 0
```

Atteso: `PASS: 7 / 7`, exit 0, grep count 0.

## Step 5 — Commit

```bash
git add hooks/brainstorming-gate tests/integration/brainstorming_gate.test.sh
git commit -m "refactor(hooks): brainstorming-gate uses scope-check lib + reorder

Moves PLUGIN_ROOT/source blocks before scope-check so the new lib is
available. Legacy 'non-itsiae-taskable' comment generalized to 'no-task-id'.
Gate active on any git repo by default. 7 integration tests PASS.

Co-Authored-By: SIAE DevForge"
```

---

## Criteri di accettazione

- [ ] `grep -c "grep.*itsiae" hooks/brainstorming-gate` = 0
- [ ] `grep -c "non-itsiae-taskable" hooks/brainstorming-gate` = 0
- [ ] `hooks/brainstorming-gate` source-a `lib/scope-check.sh`
- [ ] Ordine verificato: `PLUGIN_ROOT=` precede `source .../scope-check.sh` precede chiamata `devforge_gate_scope_active`
- [ ] `bash -n hooks/brainstorming-gate` exit 0
- [ ] `bash tests/integration/brainstorming_gate.test.sh` exit 0 con `PASS: 7 / 7`
