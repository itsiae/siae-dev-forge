# dev-analytics-v2-robust — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: `siae-subagent-development` per implementare task-per-task.

**Goal:** Upgrade skill siae-dev-analytics v1 → v2 con branch tracking totale, AI Impact narrative dual-window, 68 KPI, Excel UX pro 8-sheet, robustness policy zero-silent-failure.

**Architettura:** Estensione skill esistente `skills/siae-dev-analytics/`. Nuovi moduli: `collect_anthropic_api`, `compute_ai_impact`, `compute_branches`, `compute_reviews`, `seasonality`, `export_charts`, `export_glossary`, `validators`. Refactor major di `export_excel.py`.

**Stack:** Python 3.10+, pandas, openpyxl (+chart), pydantic, pyyaml, boto3 (opt), anthropic SDK (opt), hypothesis, mutmut, typeguard, pytz. `gh api graphql`.

**SP:** 35 SP-Umano / 14 SP-Augmented.

**Design doc:** [`../2026-04-15-dev-analytics-v2-robust-design.md`](../2026-04-15-dev-analytics-v2-robust-design.md)

**Test target:** 75 → 272 test (+197), mutation score ≥85% su core, logging coverage 100%, property-based su math.

---

## Indice Task

| # | Task | File | Stato | SP-Aug | Test nuovi |
|---|------|------|-------|:------:|:----------:|
| 1 | Scaffold nuovi moduli + requirements + SKILL.md v2 | `task-01-scaffold-v2.md` | [DONE] | 0.5 | 2 |
| 2 | F0 — AWS profile + Anthropic API client + CLI override | `task-02-sources-always-on.md` | [DONE] | 1.5 | 17 |
| 3 | F1 — PR states (OPEN/DRAFT/CLOSED/REOPENED) + 6 KPI | `task-03-pr-states.md` | [DONE] | 1 | 19 |
| 4 | F1b — Branch tracking + 8 KPI + compute_branches | `task-04-branch-tracking.md` | [DONE] | 1 | 13 |
| 5 | F2 — Review activity + co-authored + 5 KPI + compute_reviews | `task-05-review-activity.md` | [DONE] | 1 | 11 |
| 6 | F3 — Seasonality IT + complexity KPI + stale branches | `task-06-seasonality-complexity.md` | [DONE] | 1 | 8 |
| 7 | F4a-c — Cost/Value/Delivery KPI (15) | `task-07-roi-kpi-extended.md` | [DONE] | 2 | 22 |
| 8 | F4b — AI Impact: dual-window + attribution + 5 KPI + compute_ai_impact | `task-08-ai-impact.md` | [DONE] | 2 | 12 |
| 9 | F4d — DevForge adoption + correlation (3 KPI) | `task-09-devforge-adoption.md` | [DONE] | 1 | 5 |
| 10 | F4e — ROI v2 index + validators.py Pydantic models | `task-10-roi-v2-validators.md` | [DONE] | 1 | 15 |
| 11 | F5a — Excel glossary sheet + kpi-glossary-data.yaml | `task-11-excel-glossary.md` | [DONE] | 1 | 5 |
| 12 | F5b — Excel charts + tooltip + conditional formatting pro + 8-sheet refactor | `task-12-excel-ux-pro.md` | [DONE] | 2 | 14 |
| 13 | F6 — Robustness: property-based + AST audit + mutation testing + integration | `task-13-robustness-gates.md` | [DONE] | 1 | 54 |

**Totale test nuovi:** 197 → suite finale **272 test**.

---

## Dipendenze (DAG)

```
task-01 (scaffold) ── blocca tutto ──→
   ├─→ task-02 (F0 sources) ─────────────┐
   ├─→ task-03 (PR states) ───────────┐  │
   ├─→ task-04 (branches) ──────────┐ │  │
   ├─→ task-05 (reviews) ─────────┐ │ │  │
   ├─→ task-06 (seasonality) ───┐ │ │ │  │
   └─→ task-10 (validators) ───┐│ │ │ │  │
                               ││ │ │ │  │
                               ▼▼ ▼ ▼ ▼  ▼
                               task-07 (ROI KPI) ──→ task-11 (glossary) ──┐
                               task-08 (AI Impact) ─────────────────────→ │
                               task-09 (adoption) ──────────────────────→ task-12 (Excel UX)
                                                                          │
                                                                          ▼
                                                                   task-13 (robustness gates)
```

## Wave parallelization (via siae-subagent-development)

```
Wave 1 (seriale):        task-01
Wave 2 (5 parallel):     task-02 | task-03 | task-04 | task-05 | task-10
Wave 3 (2 parallel):     task-06 | task-09
Wave 4 (seriale):        task-07 → task-08
Wave 5 (seriale):        task-11 → task-12
Wave 6 (seriale):        task-13 (gates finali)
```

**Tempo stimato totale con parallelismo:** ~180 min Claude Code (vs ~400 min seriale).

---

## Criteri macro di accettazione (AC-MACRO-1..7)

- **AC-MACRO-1** Suite pytest **272/272 pass**, 0 skip non-intentional
- **AC-MACRO-2** Mutation score ≥ 85% su `compute_kpis.py`, `compute_ai_impact.py`, `autodetect_sources.py` (via mutmut)
- **AC-MACRO-3** Logging coverage 100% (AST audit test pass: ogni branch if/else/except ha log.* call)
- **AC-MACRO-4** Error messages actionable 100% (AST audit test pass: ogni RuntimeError ≥20 char + verbo azione)
- **AC-MACRO-5** Smoke test `itsiae/sport-gestione-licenze-service` produce Excel 8-sheet valido
- **AC-MACRO-6** Property-based tests green ≥1000 iterations per funzione math (z_score, roi_v2, health_score, correlation)
- **AC-MACRO-7** Coverage line ≥85% overall, ≥90% su moduli core (`compute_*.py`, `validators.py`)

## Testing finale (post-Task 13)

```bash
# Full suite
cd skills/siae-dev-analytics
PYTHONPATH=scripts python3 -m pytest tests/ -v --cov=scripts --cov-report=term

# Mutation
mutmut run --paths-to-mutate scripts/compute_kpis.py
mutmut run --paths-to-mutate scripts/compute_ai_impact.py
mutmut run --paths-to-mutate scripts/autodetect_sources.py
mutmut results

# Smoke test
PYTHONPATH=scripts python3 scripts/run_analytics.py run --config /tmp/sport-licenze-analytics.yml
```

Output atteso: `272 passed`, mutation ≥85%, Excel 8-sheet prodotto.
