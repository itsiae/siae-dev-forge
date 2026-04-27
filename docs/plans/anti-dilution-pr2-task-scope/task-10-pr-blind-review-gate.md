---
task: 10
title: Nuovo hook pr-blind-review-gate (ADR-008)
size: M
depends: [02]
blocks: [12, 13]
---

# Task 10 — `hooks/pr-blind-review-gate`

Nuovo hook PreToolUse:Bash matcher `gh pr (create|edit)`. Blocca apertura
PR se siae-blind-review non validata task-scoped. Risolve gap adoption
`blind_review=0%` della baseline.

## Matcher

```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "bash '${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd' pr-blind-review-gate",
      "timeout": 10
    }
  ]
}
```

Registrato in sequenza **dopo** `pre-commit` e `pr-gate` (hook registrati
esistenti su matcher Bash). Ordine invariato se pre-commit/pr-gate exitano
con `{}`.

## Logica hook

```bash
#!/usr/bin/env bash
set -euo pipefail
export DEVFORGE_CURRENT_HOOK="pr-blind-review-gate"

HOOK_INPUT=$(cat)

# Extract command via jq/regex
if command -v jq >/dev/null 2>&1; then
    TOOL_COMMAND=$(echo "$HOOK_INPUT" | jq -r '.command // .tool_input.command // empty')
else
    TOOL_COMMAND=$(echo "$HOOK_INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"command"[[:space:]]*:[[:space:]]*"//;s/"$//')
fi

# Use token parser from lib/cmd-parser.sh (from task 8)
source "${PLUGIN_ROOT}/lib/cmd-parser.sh"
FIRST=$(_first_token "$TOOL_COMMAND")
SECOND=$(_second_token "$TOOL_COMMAND")
THIRD=$(_third_token "$TOOL_COMMAND")

# Match only `gh pr create` or `gh pr edit`
if [ "$FIRST" != "gh" ] || [ "$SECOND" != "pr" ]; then
    echo '{}'; exit 0
fi
if [ "$THIRD" != "create" ] && [ "$THIRD" != "edit" ]; then
    echo '{}'; exit 0
fi

# Scope: itsiae repo check (consistency)
GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || true)
[ -z "$GIT_ROOT" ] && { echo '{}'; exit 0; }
REMOTE_URL=$(git -C "$GIT_ROOT" remote get-url origin 2>/dev/null || true)
if ! echo "$REMOTE_URL" | grep -qE "[/:]itsiae/"; then
    echo '{}'; exit 0
fi

# Bypass
if [ "${DEVFORGE_SKIP_BLIND_REVIEW:-0}" = "1" ]; then
    # track abuse
    # ... (pattern come DEVFORGE_SKIP_GIT_GATE)
    devforge_log "pr_blind_review_bypassed" "warning" "{...}"
    echo '{}'; exit 0
fi

# Task-scoped evidence check
source "${PLUGIN_ROOT}/lib/task-id.sh"
source "${PLUGIN_ROOT}/lib/evidence-check.sh"
TASK_ID=$(devforge_compute_task_id)

if [ -n "$TASK_ID" ] && [ "${DEVFORGE_USE_SESSION_SCOPE:-0}" != "1" ]; then
    if devforge_skill_validated siae-blind-review "$TASK_ID"; then
        echo '{}'; exit 0
    fi
else
    # Fallback session-scope
    if grep -qF "siae-blind-review" "${HOME}/.claude/.devforge-session-skills" 2>/dev/null; then
        echo '{}'; exit 0
    fi
fi

# BLOCK
devforge_log "pr_blind_review_gate" "blocked" "{\"task_id\":\"${TASK_ID}\"}"
cat <<EOF
{
  "decision": "block",
  "reason": "DevForge Blind Review Gate — BLOCCATO. Stai aprendo una PR ma NON hai invocato siae-blind-review sul codice per questo task. Il blind review verifica che spec e codice siano allineati (hostile auditor mindset). Invoca siae-blind-review ora, completa il verdict, poi riprova. Bypass tracked: DEVFORGE_SKIP_BLIND_REVIEW=1 gh pr create ..."
}
EOF
exit 0
```

## Integrazione hooks.json

Aggiungere entry in `hooks.json` matcher Bash, come 3° hook (dopo pre-commit e pr-gate).

## Acceptance

- [ ] `hooks/pr-blind-review-gate` creato
- [ ] Token matching `gh pr create/edit` (no regex substring)
- [ ] Task-scoped + session rollback
- [ ] Bypass `DEVFORGE_SKIP_BLIND_REVIEW=1` + abuse tracking
- [ ] Scope `itsiae/*` consistent
- [ ] Test `tests/hooks/test_pr_blind_review_gate.sh`:
  - [ ] `gh pr create` senza blind-review → block
  - [ ] `gh pr create` con blind-review validated → allow
  - [ ] `gh pr view` → skip (no gate)
  - [ ] `gh issue create` → skip
  - [ ] `gh pr merge` → skip (fuori scope, solo create/edit)
  - [ ] non-itsiae repo → skip
  - [ ] DEVFORGE_SKIP_BLIND_REVIEW=1 → allow + abuse log
- [ ] Integrato in `hooks.json` (task 12)

## Out of scope

- `gh pr merge` check → non richiesto dal design (PR create è la fase dove
  blind review deve essere già fatto)
