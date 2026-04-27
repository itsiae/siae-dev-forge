---
task: 11
title: plan-gate esteso a Write docs/plans/*-design.md (ADR-008)
size: S
depends: [02]
blocks: [12, 13]
---

# Task 11 — plan-gate esteso

Estende `hooks/plan-gate` da matcher `EnterPlanMode` a includere anche
`PreToolUse:Write` su `docs/plans/*-design.md`. Risolve bypass via Write
diretto (design doc scritto senza invocare brainstorming).

## Opzioni implementative

### Opzione A (scelta) — Hook duplicato

Creare nuovo hook `hooks/plan-gate-write` con logica analoga ma matcher Write.
Mantenere `hooks/plan-gate` invariato per backward compat.

Vantaggi: separazione netta, nessun cambio semantico su plan-gate esistente.

### Opzione B (scartata) — Estensione plan-gate con dual-matcher

Modificare `hooks/plan-gate` per leggere `HOOK_INPUT` e discriminare tra
EnterPlanMode e Write. Duplica logica di routing.

## Logica `hooks/plan-gate-write`

```bash
#!/usr/bin/env bash
set -euo pipefail
export DEVFORGE_CURRENT_HOOK="plan-gate-write"

HOOK_INPUT=$(cat)

# Extract file_path
if command -v jq >/dev/null 2>&1; then
    FILE_PATH=$(echo "$HOOK_INPUT" | jq -r '.file_path // .tool_input.file_path // empty')
fi

# Match only docs/plans/*-design.md
if ! echo "$FILE_PATH" | grep -qE "(^|/)docs/plans/[^/]+-design\.md$"; then
    echo '{}'; exit 0
fi

# Scope itsiae (consistency)
# ... (stesso pattern)

# Task-scoped check
source "${PLUGIN_ROOT}/lib/task-id.sh"
TASK_ID=$(devforge_compute_task_id)

if [ -n "$TASK_ID" ] && [ "${DEVFORGE_USE_SESSION_SCOPE:-0}" != "1" ]; then
    # Check evidence via task-skills (brainstorming invoked → validated once design doc produced)
    # NB: chicken-and-egg: il design doc è LA evidence! Quindi controlliamo invocazione, non validation.
    TASK_DIR="${HOME}/.claude/.devforge-task-skills/${TASK_ID}"
    if [ -f "$TASK_DIR/skills_invoked" ] && grep -qxF "siae-brainstorming" "$TASK_DIR/skills_invoked"; then
        echo '{}'; exit 0
    fi
else
    if grep -qF "siae-brainstorming" "${HOME}/.claude/.devforge-session-skills" 2>/dev/null; then
        echo '{}'; exit 0
    fi
fi

# BLOCK
cat <<EOF
{
  "decision": "block",
  "reason": "DevForge Plan Gate (Write) — BLOCCATO. Stai scrivendo ${FILE_PATH} ma NON hai invocato siae-brainstorming in questa sessione. Invoca siae-brainstorming prima di materializzare il design doc. Questo evita che design docs siano generati ad-hoc senza il processo di trade-off."
}
EOF
exit 0
```

## Nota chicken-and-egg

Il design doc è L'EVIDENCE di siae-brainstorming. Quindi **non** possiamo
usare `devforge_skill_validated` (richiederebbe design doc esistente). Usiamo
invece `skills_invoked` (skill chiamata ma evidence non ancora prodotta).

È coerente: `siae-brainstorming` invocato + Write design doc → gate OK, doc
scritto, evidence prodotta → validated al prossimo check.

## Integrazione hooks.json

Aggiungere matcher Write con `plan-gate-write`:

```json
{
  "matcher": "Write",
  "hooks": [
    {
      "type": "command",
      "command": "bash '${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd' plan-gate-write",
      "timeout": 5
    }
  ]
}
```

## Acceptance

- [ ] `hooks/plan-gate-write` creato
- [ ] Matcha `docs/plans/*-design.md` (non `*-plan.md`, non altri .md)
- [ ] Task-scoped invocation check (non validation — chicken-and-egg)
- [ ] Rollback session-scope
- [ ] Scope itsiae consistent
- [ ] Test `tests/hooks/test_plan_gate_write.sh`:
  - [ ] Write docs/plans/foo-design.md senza brainstorming → block
  - [ ] Write docs/plans/foo-design.md con brainstorming → allow
  - [ ] Write docs/plans/foo-plan.md → skip (no match)
  - [ ] Write src/foo.ts → skip
  - [ ] non-itsiae repo → skip
  - [ ] Edit (non Write) docs/plans/foo-design.md → skip (matcher Write only)
- [ ] Integrato in `hooks.json` (task 12)

## Out of scope

- Block su Edit: il design doc può essere modificato (revision flow normale)
- `*-plan.md`: scritti DOPO design, hanno già prerequisito via sub-skill-gate
  (`siae-writing-plans=siae-brainstorming`)
