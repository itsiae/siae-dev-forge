# Task 05: close-gate (Sostituisce stop-gate + pre-commit enforcement)

**Dipendenze:** Task 02 (sdlc-state.sh)
**File coinvolti:** nuovo `hooks/close-gate`, modifica `hooks/hooks.json`, modifica `hooks/stop-gate`, modifica `hooks/pre-commit`

---

## Step 1 — Crea `hooks/close-gate`

```bash
#!/usr/bin/env bash
# PreToolUse hook: BLOCCA chiusura (PR, push, stop) senza review + verification
# ─── GATE CONTRACT ───
# Behavior:  fail-closed per operazioni di chiusura
# Requires:  SDLC state (review + verification completate)
# Reads:     ${DEVFORGE_STATE_DIR}/.devforge-sdlc-stage
# On-missing: block (regola 3 violata)
# ─────────────────────────────────────────────────────────────────

set -euo pipefail

HOOK_INPUT=$(cat)

# Detect if this is a close operation (git push, gh pr create, stop claim)
TOOL_INPUT=$(echo "$HOOK_INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"command"[[:space:]]*:[[:space:]]*"//;s/"$//' || true)

IS_CLOSE_OP=false
if echo "$TOOL_INPUT" | grep -qE 'git push|gh pr create|gh pr merge'; then
    IS_CLOSE_OP=true
fi

if [ "$IS_CLOSE_OP" != "true" ]; then
    echo '{}'
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${PLUGIN_ROOT}/lib/logger.sh"
source "${PLUGIN_ROOT}/lib/sdlc-state.sh"

# Regola 3: review + verification devono essere completate
MISSING_STAGES=""
for stage in review verification; do
    if [ "$(sdlc_is_stage_completed "$stage")" != "yes" ]; then
        MISSING_STAGES="${MISSING_STAGES:+$MISSING_STAGES, }$stage"
    fi
done

if [ -n "$MISSING_STAGES" ]; then
    devforge_log "close_gate" "blocked" "{\"missing_stages\":\"$MISSING_STAGES\"}"
    cat <<EOF
{
  "decision": "block",
  "reason": "DevForge SDLC Gate — BLOCCATO. Per chiudere (push/PR), devi completare: ${MISSING_STAGES}. Segui il backbone: review → verification → poi finish."
}
EOF
    exit 0
fi

echo '{}'
exit 0
```

## Step 2 — Rimuovi enforcement SDLC da stop-gate e pre-commit

`stop-gate`: rimuovere la sezione che blocca per mancanza siae-verification. Mantenere la telemetria session_end.

`pre-commit`: rimuovere la sezione che blocca per mancanza siae-git-workflow. Mantenere il quality gate (secret scan, naming, etc.).

## Step 3 — Registra close-gate in hooks.json

Aggiungere come PreToolUse per Bash (per intercettare git push/gh pr create).

## Step 4 — Verifica

```bash
export DEVFORGE_STATE_DIR=$(mktemp -d)
mkdir -p "$DEVFORGE_STATE_DIR"
source lib/sdlc-state.sh

# Senza review/verification: blocca
result=$(echo '{"command":"git push origin feature/test"}' | bash hooks/close-gate 2>/dev/null)
echo "$result" | grep -q '"block"' && echo "PASS: blocks close without review+verification" || echo "FAIL"

# Con review+verification: passa
sdlc_advance_stage "review"
sdlc_advance_stage "verification"
result=$(echo '{"command":"git push origin feature/test"}' | bash hooks/close-gate 2>/dev/null)
[ "$result" = "{}" ] && echo "PASS: allows close with review+verification" || echo "FAIL"

rm -rf "$DEVFORGE_STATE_DIR"
```

## Step 5 — Commit

```bash
git add hooks/close-gate hooks/hooks.json hooks/stop-gate hooks/pre-commit
git commit -m "feat(backbone): add close-gate, enforce review+verification before close

- close-gate blocks git push/PR if review+verification stages not completed
- Removes SDLC enforcement from stop-gate (keeps telemetry)
- Removes SDLC enforcement from pre-commit (keeps quality gate)

Co-Authored-By: SIAE DevForge"
```
