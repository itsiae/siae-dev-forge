---
task: 09
title: sub-skill-gate — load prereq-map.generated (ADR-007)
size: S
depends: [04]
blocks: [13]
---

# Task 9 — sub-skill-gate integra prereq-map.generated

Sostituire array `PREREQ_MAP` hardcoded (7 entry) con lettura dal file
generato da Task 4.

## Change

**Attuale** (linee 37-45 di `hooks/sub-skill-gate`):

```bash
PREREQ_MAP=(
    "siae-git-workflow=siae-git-env"
    "siae-finishing-branch=siae-git-env,siae-git-workflow"
    "siae-git-worktrees=siae-git-env"
    "siae-service-logic-map=siae-microservices-map"
    "siae-writing-plans=siae-brainstorming"
    "siae-executing-plans=siae-writing-plans"
    "siae-requesting-review=siae-finishing-branch"
)
```

**Nuovo**:

```bash
PREREQ_MAP_FILE="${PLUGIN_ROOT}/lib/prereq-map.generated"
if [ ! -f "$PREREQ_MAP_FILE" ]; then
    # Fallback di emergenza: hardcoded 7 entry (solo per CI/dev broken state)
    devforge_log "sub_skill_gate" "warning" "{\"reason\":\"prereq_map_generated_missing\",\"fallback\":\"hardcoded\"}"
    PREREQ_MAP=(
        "siae-git-workflow=siae-git-env"
        "siae-finishing-branch=siae-git-env,siae-git-workflow"
        "siae-git-worktrees=siae-git-env"
        "siae-service-logic-map=siae-microservices-map"
        "siae-writing-plans=siae-brainstorming"
        "siae-executing-plans=siae-writing-plans"
        "siae-requesting-review=siae-finishing-branch"
    )
else
    # Read from generated file (newline-separated key=value)
    mapfile -t PREREQ_MAP < "$PREREQ_MAP_FILE"
fi
```

## Rollback

Se `prereq-map.generated` contiene entry sbagliate → fix script in Task 4,
re-run generator. File è committato in repo.

## Acceptance

- [ ] `hooks/sub-skill-gate` legge `lib/prereq-map.generated`
- [ ] Fallback hardcoded preserved (emergency)
- [ ] Log `prereq_map_generated_missing` se file assente
- [ ] Test `tests/hooks/test_sub_skill_gate_generated.sh`:
  - [ ] file presente + 20+ entry → skill con prereq validate bloccate correttamente
  - [ ] file assente → fallback hardcoded attivo + warning log
  - [ ] skill con >1 prereq (es. finishing-branch=git-env,git-workflow) funziona
- [ ] Zero regression su test esistenti

## Out of scope

- Task-scoped: sub-skill-gate resta session-scoped in PR #2 (prereq invocation
  è session-level, non per-task. Differente ADR.)
