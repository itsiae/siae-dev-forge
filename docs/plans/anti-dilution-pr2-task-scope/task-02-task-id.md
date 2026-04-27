---
task: 02
title: lib/task-id.sh — computazione task_id (ADR-001)
size: M
blocks: [05, 06, 07, 08, 10, 11]
---

# Task 2 — `lib/task-id.sh`

Computazione deterministica `task_id` usata da tutti i gate task-scoped.
Include `devforge_task_id_transition()` per evidence copy-forward
(mitigazione rischio #1 del design doc).

## API

```bash
# devforge_compute_task_id
# stdout: 12-char hex (sha256[:12]) — o empty string se fuori scope itsiae
devforge_compute_task_id() {
    # 1. Skip se non in repo itsiae (coerente con gate scope)
    # 2. branch_name = `git branch --show-current`
    # 3. design_doc = latest docs/plans/*-design.md (o "")
    # 4. design_doc_mtime = stat del design doc (o "0")
    # 5. sha256(branch_name + "|" + design_doc + "|" + design_doc_mtime)[:12]
}

# devforge_task_id_transition OLD_ID NEW_ID
# Copy-forward evidence se same branch AND same design_doc (solo mtime revised).
# No copy se branch OR design_doc cambiati (task legittimamente nuovo).
devforge_task_id_transition() {
    local old_id="$1" new_id="$2"
    # Load metadata file from both task_id
    # Confronta: se $BRANCH == $OLD_BRANCH && $DESIGN_PATH == $OLD_DESIGN_PATH
    #   → cp -a ~/.claude/.devforge-task-skills/$OLD/* ~/.claude/.devforge-task-skills/$NEW/
    # Altrimenti no-op.
}

# devforge_task_skill_invoked TASK_ID SKILL_NAME
# Aggiunge SKILL_NAME a skills_invoked del task
devforge_task_skill_invoked() {
    local task_id="$1" skill="$2"
    local dir="${HOME}/.claude/.devforge-task-skills/${task_id}"
    mkdir -p "$dir"
    # atomic append
    touch "$dir/skills_invoked"
    grep -qxF "$skill" "$dir/skills_invoked" 2>/dev/null || echo "$skill" >> "$dir/skills_invoked"
}

# devforge_task_skill_validated TASK_ID SKILL_NAME
# Return 0 se skill_name in skills_validated del task
devforge_task_skill_validated() {
    local task_id="$1" skill="$2"
    local f="${HOME}/.claude/.devforge-task-skills/${task_id}/skills_validated"
    [ -f "$f" ] && grep -qxF "$skill" "$f"
}

# devforge_task_skill_mark_validated TASK_ID SKILL_NAME
# Mark skill as validated per task (chiamato dal gate dopo evidence check)
devforge_task_skill_mark_validated() {
    local task_id="$1" skill="$2"
    local dir="${HOME}/.claude/.devforge-task-skills/${task_id}"
    mkdir -p "$dir"
    grep -qxF "$skill" "$dir/skills_validated" 2>/dev/null || echo "$skill" >> "$dir/skills_validated"
}
```

## Layout filesystem

```
~/.claude/.devforge-task-skills/
└── <task_id>/
    ├── skills_invoked       # newline-separated
    ├── skills_validated     # newline-separated
    └── metadata             # key=value:  branch_name=..., design_doc=..., created_ns=...
```

## Edge cases

| Scenario | task_id computation | Evidence copy-forward |
|---|---|---|
| New branch, no design doc | sha256(branch\|\|0) | no (empty OLD) |
| Same branch, design doc created | sha256(branch\|path\|mtime1) | no (first) |
| Same branch, design doc revised | sha256(branch\|path\|mtime2) | **yes** (copy from mtime1 task) |
| Branch change | sha256(new_branch\|...) | no |
| Design doc path change | sha256(branch\|new_path\|...) | no |
| Not in itsiae repo | empty string | n/a — gate skip |

## Acceptance

- [ ] `lib/task-id.sh` creato con le 5 funzioni sopra
- [ ] Test `tests/lib/test_task_id.sh` ≥10 casi
  - [ ] computation stabile (stesso input → stesso output)
  - [ ] scope itsiae: non-itsiae repo → empty
  - [ ] evidence copy-forward: design revised → validated carry
  - [ ] branch change: no copy
  - [ ] both change: no copy
  - [ ] skills_invoked/skills_validated append idempotente
  - [ ] atomic write (concurrent bash test)
- [ ] Zero side effect se called fuori git repo
- [ ] Source-safe (no side effect on `source`)

## Out of scope

- Integrazione nei gate → task 5+ (dual-write)
- Rollback env var DEVFORGE_USE_SESSION_SCOPE → task 12 (hooks.json doc)
