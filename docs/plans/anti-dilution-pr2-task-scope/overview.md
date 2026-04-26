---
title: PR #2 — Anti-Dilution Task-Scope + Scope Cleanup
date: 2026-04-25
status: in_progress
branch: feat/anti-dilution-pr2-task-scope
base: feat/anti-dilution-pr1-foundation
design_doc: docs/plans/2026-04-25-anti-dilution-enforcement-design.md
pr1_ref: https://github.com/itsiae/siae-dev-forge/pull/215
---

# PR #2 — Task-Scope + Scope Cleanup (v1.47)

Secondo dei 3 stadi del design anti-dilution. ADR-001, ADR-005, ADR-006,
ADR-007, ADR-008 attivati. Medium risk — cutover fasato dual-write.

## Scope

8 deliverable dal design doc (sezione "PR #2 — v1.47"):

1. `lib/task-id.sh` — computazione task_id (ADR-001)
2. 8 gate migrati a task-scoped (tdd, brainstorming, stop, pre-commit, plan, plan-gate-write, pr-blind-review, sub-skill)
3. `lib/file-taxonomy.sh` — classificazione estensioni (ADR-005)
4. Rimozione 3 escape hatches: stop-gate 2-block, brainstorming W2_DEFAULT=0, pre-commit regex substring (ADR-006)
5. `lib/generate-prereq-map.sh` → `lib/prereq-map.generated` 39 entry (ADR-007)
6. Nuovo `hooks/pr-blind-review-gate` (ADR-008)
7. `hooks/plan-gate` esteso a Write `docs/plans/*-design.md` (ADR-008)
8. `hooks/stop-gate` → `evidence-stop-gate` + `coverage-force-run` rewrite (ADR-008)

Extra-scope assorbito da PR #215 auto-review: 5 MAJOR + 1 CRITICAL (task 1).

## Strategia branch

Stacked su `feat/anti-dilution-pr1-foundation` per non bloccarci sul merge
di PR #215. Al merge di #215 rebase su main. Rollback per-gate via env var
(vedi task 12).

## Criteri accettazione globali (dal design)

- [ ] Dual-write phase funzionante (legacy + task-scoped coesistono)
- [ ] Shadow-check senza divergenza >10% su test suite
- [ ] Rollback testato via scenario DEVFORGE_USE_SESSION_SCOPE=1
- [ ] Tutti i nuovi gate testati con positive + negative case
- [ ] Zero regression su 51 test PR #1 + 168 baseline
- [ ] Adoption per-task misurata post-deploy vs `baseline-metrics-tasks.json`
- [ ] Abuse tracking per ogni bypass env var: soglia ≥5/giorno, log `bypass_abuse_suspected`

## Env vars introdotte

| Env var | Default | Scopo |
|---|---|---|
| `DEVFORGE_USE_SESSION_SCOPE` | 0 | Rollback globale: ripristina session-scoped enforcement |
| `DEVFORGE_FORCE_STOP` | 0 | Escape esplicito stop-gate (sostituisce 2-block auto-escape) |
| `DEVFORGE_BASH_TDD` | 0 | Opt-in TDD per .sh/.bash (deny-by-default) |
| `DEVFORGE_SKIP_BLIND_REVIEW` | 0 | Bypass pr-blind-review-gate (tracked) |

## Task list

Vedi `task-XX-*.md` per dettaglio. Ordine sequenziale consigliato:

1. [Task 1 — Fix 5 MAJOR + 1 CRITICAL PR #215](task-01-fix-pr215-majors.md)
2. [Task 2 — lib/task-id.sh](task-02-task-id.md)
3. [Task 3 — lib/file-taxonomy.sh](task-03-file-taxonomy.md)
4. [Task 4 — lib/generate-prereq-map.sh](task-04-prereq-map-autogen.md)
5. [Task 5 — Dual-write tdd-gate](task-05-tdd-gate-dual-write.md)
6. [Task 6 — brainstorming-gate + W2 cleanup](task-06-brainstorming-gate-dual-write.md)
7. [Task 7 — evidence-stop-gate](task-07-evidence-stop-gate.md)
8. [Task 8 — pre-commit parser + coverage-force-run](task-08-pre-commit-parser.md)
9. [Task 9 — sub-skill-gate autogen](task-09-sub-skill-gate-autogen.md)
10. [Task 10 — pr-blind-review-gate](task-10-pr-blind-review-gate.md)
11. [Task 11 — plan-gate-write](task-11-plan-gate-write.md)
12. [Task 12 — hooks.json + rollback docs](task-12-hooks-json-rollback.md)
13. [Task 13 — regression suite](task-13-regression-suite.md)
14. [Task 14 — README update PR #1 + #2](task-14-readme-update.md)
15. [Task 15 — version bump + PR open](task-15-version-bump-pr.md)

## Rischi

| Rischio | Probabilità | Impatto | Mitigazione |
|---|---|---|---|
| task_id cambia mid-task → gate reset | Media | Alto | Evidence copy-forward in task-id.sh (stesso branch + design revision) |
| Dual-write divergenza | Bassa | Medio | Shadow-log 1 giorno + test divergenza <10% |
| Rimozione W2_DEFAULT rompe sessioni headless | Media | Basso | DEVFORGE_USE_SESSION_SCOPE=1 + DEVFORGE_ENFORCEMENT_OFF=1 preservati |
| Pre-commit parser nuovo falsi negativi | Bassa | Medio | Test suite comprehensive: 'git log commit', echo, in-string commands |
| 39 prereq-map rompe skill legittime | Media | Alto | Generated + fallback hardcoded + test ogni skill post-gen |
