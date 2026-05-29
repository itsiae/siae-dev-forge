# Code-Coverage Skill Remediation — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development` (stessa sessione)
> oppure `siae-executing-plans` (sessione separata) per implementare questo piano task per task.

**Goal:** Eliminare alla radice i 12 gap del post-mortem `/code-coverage` su `accertatori-data-service` e introdurre l'esecuzione multi-agente parallela (≤4 subagent Sonnet) dei task di coverage.

**Architettura:** La skill `skills/code-coverage/` resta single-skill ma acquisisce: (1) consapevolezza del target reale (branch pct pre-esistente + soglie CI), (2) generazione branch-aware (branch-matrix + tecniche avanzate reflection/class-mock/TZ-mock + helper riusabili), (3) repair loop robusto (max_iter scalato, classificazione intractable gated, progress guard a 2 livelli, prediction), (4) orchestrazione multi-agente via Agent dispatch (coordinatore + ≤4 subagent Sonnet path-disgiunti).

**Stack:** Python 3 (script + pytest), Bash (lib/*.sh + bats-like), TypeScript (template `.ts`), Markdown (references + SKILL.md). Test runner skill: `pytest` in `skills/code-coverage/scripts/tests/`.

**SP:** ~21 task (5 workstream). I workstream sono indipendentemente committabili: WS-1→WS-4 danno il guadagno di qualità (branch coverage), WS-5 il guadagno di tempo (parallelismo).

**Design doc:** `docs/code-coverage-remediation-design.md`

---

## Indice Task

### WS-1 — Fondamenta dati (prerequisito di tutto)
| # | Task | File | Stato |
|---|------|------|-------|
| 1 | `pre_existing_branch_pct` in stack.json | `task-01-stack-branch-pct.md` | [DONE] |
| 2 | CI thresholds + working-dir single-pass | `task-02-detect-ci-thresholds.md` | [DONE] |
| 3 | effective_target nel sentinel handshake | `task-03-effective-target.md` | [DONE] |
| 4 | Fix bug workspace-key + stale jest tag | `task-04-stale-jest-fix.md` | [DONE] |

### WS-2 — Generazione branch-aware (Phase 3 + Phase 5)
| # | Task | File | Stato |
|---|------|------|-------|
| 5 | `count_branch_operators.py` | `task-05-branch-operator-counter.md` | [PENDING] |
| 6 | `classify_coverage_mode.py` | `task-06-coverage-mode.md` | [PENDING] |
| 7 | Template `vitest-branch-matrix` + dual-fixture | `task-07-branch-matrix-template.md` | [PENDING] |
| 8 | `plan_batches.py` schema + Phase 3 step 3b | `task-08-plan-batches-schema.md` | [PENDING] |

### WS-3 — Tecniche avanzate + helper library (Phase 4 + Phase 5/7)
| # | Task | File | Stato |
|---|------|------|-------|
| 9 | `scan_private_methods.py` | `task-09-scan-private-methods.md` | [PENDING] |
| 10 | `scan_class_instantiations.py` | `task-10-scan-class-instantiations.md` | [PENDING] |
| 11 | `scan_tz_usage.py` | `task-11-scan-tz-usage.md` | [PENDING] |
| 12 | Test-helper library + Phase 4 gen | `task-12-helper-library.md` | [PENDING] |
| 13 | Anti-pattern + few-shot branch-matrix | `task-13-docs-antipattern-fewshot.md` | [PENDING] |

### WS-4 — Repair loop robusto (Phase 7)
| # | Task | File | Stato |
|---|------|------|-------|
| 14 | `classify_intractable.py` | `task-14-classify-intractable.md` | [PENDING] |
| 15 | max_iter scaling + repair-strategies cat 13 | `task-15-max-iter-scaling.md` | [PENDING] |
| 16 | Two-tier guard + strategy ladder | `task-16-two-tier-guard.md` | [PENDING] |
| 17 | `predict_coverage.py` + sentinel display | `task-17-predict-coverage.md` | [PENDING] |

### WS-5 — Esecuzione multi-agente parallela
| # | Task | File | Stato |
|---|------|------|-------|
| 18 | batch-plan schema multi-agente | `task-18-batch-plan-multiagent.md` | [PENDING] |
| 19 | `references/phase-5-parallel.md` | `task-19-phase5-parallel-ref.md` | [PENDING] |
| 20 | SKILL.md hooks Phase 3/5/7 parallel | `task-20-skill-parallel-hooks.md` | [PENDING] |
| 21 | intractable.json aggregation + Block 9 | `task-21-intractable-aggregation.md` | [PENDING] |

---

## Dipendenze

- **WS-1 è prerequisito globale.** Task 1 (branch pct) abilita Task 6 (coverage-mode), Task 17 (prediction). Task 2 (CI thresholds) abilita Task 3 (effective_target).
- Task 3 dipende da Task 2. Task 4 è indipendente (bug fix isolato).
- **WS-2:** Task 6 dipende da Task 5 (legge `branch-count/*.json`) e Task 1 (branch pct). Task 7 dipende da Task 5. Task 8 dipende da Task 5+6 (popola i campi nel batch-plan).
- **WS-3:** Task 9/10/11 indipendenti tra loro. Task 12 indipendente. Task 13 dipende da Task 7 (esempio branch-matrix).
- **WS-4:** Task 14 dipende da Task 9/10/11 (riusa gli scanner). Task 15 indipendente. Task 16 dipende da Task 14. Task 17 dipende da Task 1+5.
- **WS-5:** Task 18 dipende da Task 8 (schema batch-plan). Task 19 dipende da Task 18. Task 20 dipende da Task 19. Task 21 dipende da Task 14+19.

## Ordine di esecuzione consigliato

`1 → 2 → 3 → 4` (WS-1) → `5 → 6 → 8 → 7` (WS-2) → `9 → 10 → 11 → 12 → 13` (WS-3) → `14 → 15 → 16 → 17` (WS-4) → `18 → 19 → 20 → 21` (WS-5).

## Convenzioni test

- Script Python: pytest in `skills/code-coverage/scripts/tests/test_<nome>.py`. Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_<nome>.py -v`.
- Lib bash: test stile `scripts/tests/test_*.sh` (vedi `test_sentinel_handshake.sh` esistente).
- Template `.ts` / docs `.md`: verifica strutturale (grep/placeholder-check), non pytest.
