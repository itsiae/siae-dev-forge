---
task: 05
title: tdd-gate — dual-write task-scoped migration (ADR-001)
size: M
blocks: [13]
depends: [02, 03]
---

# Task 5 — tdd-gate dual-write cutover

Migrazione `hooks/tdd-gate` da session-scoped a task-scoped. Dual-write:
mantiene session-skills legacy, aggiunge task-skills. Check read-path con
fallback rollback via `DEVFORGE_USE_SESSION_SCOPE=1`.

## Flusso nuovo

```
input: file_path
  ↓
1. scope gate: itsiae/* (unchanged)
  ↓
2. file classification: devforge_file_requires_tdd "$file_path"
   (task 3 replaces PROD_EXTENSIONS regex)
  ↓
3. TASK_ID=$(devforge_compute_task_id)
  ↓
4. Check path:
   if DEVFORGE_USE_SESSION_SCOPE=1:
     → legacy: grep siae-tdd in .devforge-session-skills
   else:
     → task-scoped: devforge_task_skill_validated "$TASK_ID" siae-tdd
       AND evidence ok: tdd_red_green_observed
   ↓
5. Decision:
   - validated → allow
   - invoked but not validated (INIT/RED phase) → block con PHASE message (attuale)
   - not invoked → block con HARD GATE message
```

## Integrazioni

- Load `lib/task-id.sh` + `lib/file-taxonomy.sh` + `lib/evidence-check.sh`
- Rimuovere regex hardcoded `PROD_EXTENSIONS` + `EXCLUDED_PATHS`
- Dual-write al bottom (quando permesso):
  - scrivi sia session-skills che task-skills

## Dual-write logic

Il gate non scrive skills_invoked (è `post-skill` hook che lo fa). Ma il
gate DEVE leggere entrambi (session + task) in fase dual-write.

Lo scope dual-write per questo task è **lettura**:
- Se task-scoped check fallisce, fallback soft a session-scoped (log divergenza)
- Se rollback env var: solo session-scoped

Lo scope dual-write per `post-skill` hook: scrive entrambi (session-skills
legacy + task-skills/$task_id/skills_invoked). Modifiche a `post-skill`
trattate come parte di questo task per coerenza.

## Edge case

- **TASK_ID vuoto** (non-itsiae repo): gate early-exit come oggi
- **TASK_ID transition mid-session** (branch change): `devforge_task_id_transition`
  chiamato da post-skill al momento del write → se same branch + design revised,
  copy-forward validated skills
- **Design doc non esistente**: task_id = sha256(branch||0), comunque valido

## Acceptance

- [ ] `hooks/tdd-gate` usa `lib/task-id.sh` + `lib/file-taxonomy.sh` + `lib/evidence-check.sh`
- [ ] `hooks/post-skill` dual-write session + task skills_invoked
- [ ] `DEVFORGE_USE_SESSION_SCOPE=1` ripristina comportamento legacy
- [ ] Regex hardcoded rimossi
- [ ] Test `tests/hooks/test_tdd_gate_task_scope.sh`:
  - [ ] same branch, design doc revised → task_id change + evidence carry
  - [ ] new branch → block
  - [ ] .sh senza DEVFORGE_BASH_TDD → no-gate
  - [ ] .sh con DEVFORGE_BASH_TDD=1 → gate attivo
  - [ ] rollback env var → session-scope behavior
  - [ ] regression: tutti i 10 test esistenti continuano a PASS
- [ ] Shadow-check log su `devforge_log`: se session-scope=allow ma task-scope=block (o viceversa) → emit `gate_divergence` event con campo `expected` e `actual`

## Out of scope

- Measurement post-deploy → task 13 (regression) + post-merge analytics
