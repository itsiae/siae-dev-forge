---
task: 15
title: Version bump 1.47.0 + PR open
size: S
depends: [01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13, 14]
---

# Task 15 — Version bump + PR open

Chiusura PR #2. Bump version, commit finale, push, `gh pr create` verso main.

## Steps

### 1. Version bump

Aggiornare:
- `plugin.json` (se esistente) → `"version": "1.47.0"`
- `VERSION` file root (se esistente) → `1.47.0`
- `package.json` (se rilevante)

### 2. CHANGELOG (se esistente)

```markdown
## v1.47.0 — 2026-04-25 (Anti-Dilution PR #2)

**Task-Scoped Enforcement + Scope Cleanup**

- ADR-001: task_id-based enforcement + evidence copy-forward
- ADR-005: file-taxonomy centralizzata, .tf/.hcl coperti, .sh deny-by-default
- ADR-006: rimossi 3 escape hatches
- ADR-007: prereq map autogenerata (39 entry)
- ADR-008: nuovi gate pr-blind-review + plan-gate-write + evidence-stop + coverage-force

Rollback: `DEVFORGE_USE_SESSION_SCOPE=1`. Vedi hooks/ENV_VARS.md.
```

### 3. Finishing branch checklist (via skill `siae-finishing-branch`)

- [ ] Tutti i test PASS (run `tests/pr2-task-scope/run-all.sh`)
- [ ] Nessuna regression su PR #1 test (51/51)
- [ ] Nessuna regression su baseline (161 PASS)
- [ ] `git status` pulito (no file modificati non committati)
- [ ] Commit messages conventional
- [ ] PR #215 linkata come base

### 4. Push + PR

```bash
git push -u origin feat/anti-dilution-pr2-task-scope

gh pr create \
  --base main \
  --title "feat(anti-dilution): v1.47 task-scope + scope cleanup (PR #2/3)" \
  --body-file docs/plans/anti-dilution-pr2-task-scope/pr-body.md
```

### 5. PR body template

Creare `docs/plans/anti-dilution-pr2-task-scope/pr-body.md` con:
- Summary + link design doc
- Changes per ADR
- Acceptance criteria (checklist)
- Test results
- Rollback instructions
- Risk section
- Metriche before/after

Riutilizzare pattern del body di PR #215 (vedi `gh pr view 215 --json body`).

## Acceptance

- [ ] Version 1.47.0 committed
- [ ] CHANGELOG updated (se esistente)
- [ ] Branch pushed
- [ ] PR aperta verso main
- [ ] PR body completo con deliverables + rollback + metriche
- [ ] PR linkata a design doc + baseline metrics
- [ ] Review request a reviewer designato (skill `siae-requesting-review`)

## Out of scope

- Merge PR → umano (require review approval)
- Post-merge monitoring → gestito da siae-retrospective + PR #3 dashboard
