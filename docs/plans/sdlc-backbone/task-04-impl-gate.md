# Task 04: impl-gate (Sostituisce tdd-gate + plan-gate)

**Dipendenze:** Task 02 (sdlc-state.sh)
**File coinvolti:** nuovo `hooks/impl-gate`, modifica `hooks/hooks.json`, rimozione logica SDLC da `hooks/tdd-gate` e `hooks/plan-gate`

---

## Step 1 — Crea `hooks/impl-gate`

```bash
#!/usr/bin/env bash
# PreToolUse hook: BLOCCA Edit/Write su codice produzione senza fasi backbone
# ─── GATE CONTRACT ───
# Behavior:  fail-closed per codice produzione
# Requires:  SDLC state (brainstorming + plan + tdd completate)
# Reads:     ${DEVFORGE_STATE_DIR}/.devforge-sdlc-stage
# On-missing: block (regole 1+2 violate)
# ─────────────────────────────────────────────────────────────────

set -euo pipefail

HOOK_INPUT=$(cat)

# Extract file_path
if command -v jq >/dev/null 2>&1; then
    FILE_PATH=$(echo "$HOOK_INPUT" | jq -r '.file_path // .tool_input.file_path // empty' 2>/dev/null || true)
else
    FILE_PATH=$(echo "$HOOK_INPUT" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"file_path"[[:space:]]*:[[:space:]]*"//;s/"$//' || true)
fi

[ -z "$FILE_PATH" ] && echo '{}' && exit 0

# Normalize path
[[ "$FILE_PATH" != /* ]] && FILE_PATH="$(pwd)/${FILE_PATH#./}"

# Skip files outside repo
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
GIT_ROOT="$(git -C "$HOOK_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
if [ -n "$GIT_ROOT" ] && [[ "$FILE_PATH" != "$GIT_ROOT"/* ]]; then
    echo '{}' && exit 0
fi

# Only gate production code
PROD_EXTENSIONS="\.java$|\.ts$|\.tsx$|\.js$|\.jsx$|\.py$|\.vue$|\.go$|\.kt$"
if ! echo "$FILE_PATH" | grep -qE "$PROD_EXTENSIONS"; then
    echo '{}' && exit 0
fi

# Exclude test files
EXCLUDED_PATHS="test/|tests/|__tests__|spec/|Test\.(java|kt)$|\.spec\.|\.test\.|test_.*\.py$|_test\.go$|docs/|plans/|SKILL\.md|CLAUDE\.md|\.md$|evals/"
if echo "$FILE_PATH" | grep -qE "$EXCLUDED_PATHS"; then
    echo '{}' && exit 0
fi

# Check SDLC stage prerequisites
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${PLUGIN_ROOT}/lib/logger.sh"
source "${PLUGIN_ROOT}/lib/sdlc-state.sh"

# Regola 1+2: brainstorming, plan, tdd devono essere completate
PREREQS=$(sdlc_check_prerequisites "tdd")
if [ "$PREREQS" != "ok" ]; then
    MISSING="${PREREQS#missing:}"
    BASENAME=$(basename "$FILE_PATH")
    devforge_log "impl_gate" "blocked" "{\"file\":\"$BASENAME\",\"missing_stages\":\"$MISSING\"}"

    cat <<EOF
{
  "decision": "block",
  "reason": "DevForge SDLC Gate — BLOCCATO. Per modificare ${BASENAME} (codice produzione), devi completare le fasi: ${MISSING}. Segui il backbone: brainstorming → plan → tdd → poi codice."
}
EOF
    exit 0
fi

# TDD phase check: se in fase tdd, verifica state machine TDD (RED/GREEN/REFACTOR)
TDD_STATE_FILE="${DEVFORGE_STATE_DIR}/.devforge-tdd-state"
TDD_STATE=$(cat "$TDD_STATE_FILE" 2>/dev/null || echo "")
TDD_PHASE=$(echo "$TDD_STATE" | cut -d'|' -f1)
if [ "$TDD_PHASE" = "INIT" ]; then
    BASENAME=$(basename "$FILE_PATH")
    devforge_log "impl_gate" "blocked" "{\"file\":\"$BASENAME\",\"phase\":\"INIT\"}"
    cat <<EOF
{
  "decision": "block",
  "reason": "DevForge TDD Phase Gate — BLOCCATO. Hai invocato siae-tdd ma non hai ancora un test fallente. Scrivi PRIMA il test per ${BASENAME}, eseguilo (deve fallire), poi potrai scrivere codice produzione."
}
EOF
    exit 0
fi

echo '{}'
exit 0
```

## Step 2 — Registra impl-gate in hooks.json

In `hooks/hooks.json`, aggiungere `impl-gate` come hook PreToolUse per Edit e Write. Rimuovere tdd-gate e plan-gate dalla lista (o marcali come deprecati).

## Step 3 — Svuota la logica SDLC da tdd-gate e plan-gate

`tdd-gate` e `plan-gate` vengono ridotti a stub che emettono `{}` — la logica SDLC e' ora in `impl-gate`. Eventualmente possono essere rimossi del tutto se non hanno altra responsabilita'.

## Step 4 — Verifica

```bash
export DEVFORGE_STATE_DIR=$(mktemp -d)
mkdir -p "$DEVFORGE_STATE_DIR"

# Senza stage completate: deve bloccare
result=$(echo '{"file_path":"src/UserService.java"}' | bash hooks/impl-gate 2>/dev/null)
echo "$result" | grep -q '"block"' && echo "PASS: blocks without backbone" || echo "FAIL"

# Con brainstorming + plan + tdd completate: deve passare
source lib/sdlc-state.sh
sdlc_advance_stage "brainstorming"
sdlc_advance_stage "plan"
sdlc_advance_stage "execution"
sdlc_advance_stage "tdd"
result=$(echo '{"file_path":"src/UserService.java"}' | bash hooks/impl-gate 2>/dev/null)
echo "$result" | grep -q '{}' || echo "$result" | grep -q '{}' && echo "PASS: allows with backbone" || echo "FAIL"

rm -rf "$DEVFORGE_STATE_DIR"
```

## Step 5 — Commit

```bash
git add hooks/impl-gate hooks/hooks.json hooks/tdd-gate hooks/plan-gate
git commit -m "feat(backbone): add impl-gate, phase-based enforcement for prod code

- impl-gate checks SDLC stages (brainstorming+plan+tdd) before allowing prod edits
- Replaces tdd-gate and plan-gate SDLC logic
- Keeps TDD phase state machine (RED/GREEN/REFACTOR) check
- Registered in hooks.json as PreToolUse for Edit/Write

Co-Authored-By: SIAE DevForge"
```
