# Task 01 — Nuovo hook `hooks/session-end` (emit senza rm)

**Goal:** Creare `hooks/session-end` che emette l'evento `session_end` con conteggi
accumulati, idempotente via guard, **senza** cancellare i file di stato di sessione.

**File coinvolti:**
- Creazione: `hooks/session-end`
- Creazione: `tests/hooks/test_session_end_hook.sh`

**Copre AC:** AC-5, AC-6, AC-7, AC-8, AC-10.

---

## Step TDD

### Step 1 — Scrivi il test fallente

Crea `tests/hooks/test_session_end_hook.sh` (modellato su
`tests/hooks/test_evidence_stop_gate.sh`):

```bash
#!/usr/bin/env bash
# test_session_end_hook.sh — nuovo hook SessionEnd: emit session_end senza rm stato.
set -eu
PASS=0; FAIL=0
REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK="${REPO_ROOT}/hooks/session-end"

# Seed: HOME temp + counters + log file isolato. Ritorna il path di HOME.
_seed_home() {
    local th; th=$(mktemp -d)
    mkdir -p "$th/.claude"
    printf 'siae-tdd,siae-git-workflow,siae-verification\n' > "$th/.claude/.devforge-session-skills"
    printf '4\n' > "$th/.claude/.devforge-session-commits"
    printf '1000000000\n' > "$th/.claude/.devforge-session-start-ns"
    echo "$th"
}

# Invoca il hook con un payload SessionEnd su stdin (reason configurabile).
_run() {  # $1=HOME $2=reason
    printf '{"hook_event_name":"SessionEnd","reason":"%s","session_id":"t"}' "${2:-other}" \
        | HOME="$1" DEVFORGE_LOG_FILE="$1/.claude/devforge.jsonl" bash "$HOOK" 2>/dev/null || true
}

echo "=== AC-5/AC-8: emit session_end con conteggi accumulati + schema ==="
TH=$(_seed_home); _run "$TH" other
LOG="$TH/.claude/devforge.jsonl"
# Schema-presence: i campi chiave dello schema identico devono esserci (WARN-3 review).
if grep -q '"event":"session_end"' "$LOG" 2>/dev/null \
   && grep -q '"skills_used_count":3' "$LOG" 2>/dev/null \
   && grep -q '"commits_count":4' "$LOG" 2>/dev/null \
   && grep -q '"token_state_complete"' "$LOG" 2>/dev/null \
   && grep -q '"by_model"' "$LOG" 2>/dev/null \
   && grep -q '"by_tool"' "$LOG" 2>/dev/null; then
    echo "  PASS  session_end skills=3 commits=4 + schema completo"; PASS=$((PASS+1))
else
    echo "  FAIL  atteso session_end skills=3 commits=4 + campi schema; log: $(tail -1 "$LOG" 2>/dev/null)"; FAIL=$((FAIL+1))
fi
rm -rf "$TH"

echo "=== AC-6: idempotenza — seconda invocazione non riemette ==="
TH=$(_seed_home); _run "$TH" other; _run "$TH" other
N=$(grep -c '"event":"session_end"' "$TH/.claude/devforge.jsonl" 2>/dev/null || echo 0)
if [ "$N" -eq 1 ]; then
    echo "  PASS  esattamente 1 session_end"; PASS=$((PASS+1))
else
    echo "  FAIL  attesi 1 session_end, trovati $N"; FAIL=$((FAIL+1))
fi
rm -rf "$TH"

echo "=== AC-7: NESSUN rm dei file di stato ==="
TH=$(_seed_home); _run "$TH" other
if [ -f "$TH/.claude/.devforge-session-skills" ] \
   && [ -f "$TH/.claude/.devforge-session-commits" ] \
   && [ -f "$TH/.claude/.devforge-session-start-ns" ]; then
    echo "  PASS  file di stato preservati"; PASS=$((PASS+1))
else
    echo "  FAIL  file di stato cancellati (regressione del bug)"; FAIL=$((FAIL+1))
fi
rm -rf "$TH"

echo "=== AC-10: reason=resume — file preservati ==="
TH=$(_seed_home); _run "$TH" resume
if [ -f "$TH/.claude/.devforge-session-skills" ] \
   && grep -qF 'siae-git-workflow' "$TH/.claude/.devforge-session-skills"; then
    echo "  PASS  resume: ledger intatto"; PASS=$((PASS+1))
else
    echo "  FAIL  resume: ledger perso"; FAIL=$((FAIL+1))
fi
rm -rf "$TH"

echo ""
echo "RESULT: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
```

### Step 2 — Esegui e verifica che fallisce

Run: `bash tests/hooks/test_session_end_hook.sh`
Output atteso: FAIL su tutti i casi (il file `hooks/session-end` non esiste ancora →
`bash: hooks/session-end: No such file or directory`).

### Step 3 — Implementa `hooks/session-end`

Estrai la logica di `_devforge_emit_session_end` da `hooks/stop-gate:48-130`
**ESCLUDENDO** le righe 127-129 (`rm -f` dei file di stato). Struttura del nuovo hook:

```bash
#!/usr/bin/env bash
# session-end — SessionEnd hook: emette session_end con conteggi accumulati.
# NON cancella i file di stato (reset delegato a session-start). Non puo' bloccare.
# ─────────────────────────────────────────────────────────────────
# Hook:     session-end
# Evento:   SessionEnd
# Matcher:  "" (tutti i reason: clear/resume/logout/prompt_input_exit/other)
# Formato:  echo '{}' (cleanup/logging only)
# ─────────────────────────────────────────────────────────────────
set -euo pipefail
export DEVFORGE_CURRENT_HOOK="session-end"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${PLUGIN_ROOT}/lib/logger.sh"
devforge_init_session 2>/dev/null || true
source "${PLUGIN_ROOT}/lib/telemetry-upload.sh" 2>/dev/null || true

# reason (diagnostico, NON entra nello schema session_end — vedi design §3.6)
INPUT=$(cat 2>/dev/null || echo "")
REASON="other"
if command -v jq >/dev/null 2>&1 && [ -n "$INPUT" ]; then
    REASON=$(printf '%s' "$INPUT" | jq -r '.reason // "other"' 2>/dev/null || echo "other")
fi

SESSION_START_NS_FILE="${HOME}/.claude/.devforge-session-start-ns"
SESSION_COMMITS_FILE="${HOME}/.claude/.devforge-session-commits"
SESSION_SKILLS_FILE="${HOME}/.claude/.devforge-session-skills"
SESSION_END_GUARD="${HOME}/.claude/.devforge-session-end-guard"

# Guard at-most-once per segmento (clearato da session-start all'avvio successivo).
if ! mkdir "$SESSION_END_GUARD" 2>/dev/null; then
    echo '{}'; exit 0
fi

SESSION_START_NS=$(cat "$SESSION_START_NS_FILE" 2>/dev/null || echo "0")
COMMITS_COUNT=$(cat "$SESSION_COMMITS_FILE" 2>/dev/null || echo "0")
SKILLS_LIST=$(cat "$SESSION_SKILLS_FILE" 2>/dev/null || echo "")
if [ -n "$SKILLS_LIST" ]; then
    SKILLS_USED_COUNT=$(echo "$SKILLS_LIST" | tr ',' '\n' | sort -u | wc -l | tr -d ' ')
else
    SKILLS_USED_COUNT=0
fi

# Chiusura ultima skill via timestamp chaining (PORTATA da stop-gate:53-68).
SKILL_TS_FILE="${HOME}/.claude/.devforge-skill-start"
if [ -f "$SKILL_TS_FILE" ]; then
    PREV_DATA=$(cat "$SKILL_TS_FILE")
    PREV_START_NS=$(echo "$PREV_DATA" | cut -d'|' -f1)
    PREV_SKILL=$(echo "$PREV_DATA" | cut -d'|' -f2)
    PREV_PHASE=$(echo "$PREV_DATA" | cut -d'|' -f3)
    SAFE_PREV_SKILL=$(devforge_sanitize_json_str "$PREV_SKILL")
    SAFE_PREV_PHASE=$(devforge_sanitize_json_str "$PREV_PHASE")
    if [ -n "$PREV_START_NS" ] && [ -n "$PREV_SKILL" ]; then
        devforge_log_timed "skill_completed" "success" "$PREV_START_NS" \
            "{\"skill_name\":\"${SAFE_PREV_SKILL}\",\"sdlc_phase\":\"${SAFE_PREV_PHASE}\",\"outcome\":\"success\"}" || true
    fi
    rm -f "$SKILL_TS_FILE"   # consentito: skill-start NON e' stato di sessione (e' resettato da session-start)
fi

# Token snapshot + payload session_end (schema IDENTICO a stop-gate:71-105).
# [Copiare integralmente il blocco token + devforge_log_timed "session_end" ...
#  da stop-gate:71-105, invariato, incluso task_adoption + recap stderr + flush.]

devforge_upload_logs 2>/dev/null || true
echo '{}'
exit 0
```

> **Nota implementativa**: il blocco token-stats + la riga `devforge_log_timed
> "session_end"` (con tutti i campi `by_model`/`by_tool`/`token_state_complete`/...)
> + `task_adoption` + recap stderr vanno copiati **verbatim** da `hooks/stop-gate:71-125`
> per garantire schema event identico. L'UNICA differenza rispetto all'originale è
> l'assenza del blocco `rm -f` (stop-gate:127-129).

### Step 4 — Esegui e verifica che passa

Run: `bash tests/hooks/test_session_end_hook.sh`
Output atteso: `RESULT: PASS=4 FAIL=0`

### Step 5 — Commit

```bash
git add hooks/session-end tests/hooks/test_session_end_hook.sh
git commit -m "feat(hooks): nuovo SessionEnd hook emette session_end senza rm stato (task-01)"
```

---

## Criteri di accettazione

- [ ] `hooks/session-end` esiste ed è eseguibile.
- [ ] Emette esattamente 1 evento `session_end` con `skills_used_count`/`commits_count`
      accumulati dai counter (AC-5, AC-8).
- [ ] Idempotente via guard `mkdir`: seconda invocazione non riemette (AC-6).
- [ ] NON cancella `.devforge-session-skills/-commits/-start-ns` (AC-7).
- [ ] `reason=resume` → ledger intatto (AC-10).
- [ ] Schema event `session_end` identico a quello attuale (campi `by_*`,
      `token_state_complete`, ecc. — verifica diff con stop-gate:104-105).
- [ ] `bash tests/hooks/test_session_end_hook.sh` → `PASS=4 FAIL=0`.
