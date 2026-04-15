# siae-dev-analytics — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development` per implementare questo piano task per task.

**Goal:** Skill DevForge che misura velocità/qualità degli sviluppatori SIAE che usano Claude Code, produce report Excel con 11 KPI + ROI sintetico per reportistica management.

**Architettura:** Claude orchestratore (SKILL.md) + Python pipeline (scripts/) invocati via subprocess. `gh` CLI come unica interfaccia GitHub (no pygithub). Auto-detect fonti (GitHub obbligatorio + S3 telemetry opzionale) con graceful degrade FULL/HYBRID/GITHUB-ONLY.

**Stack:** Python 3.10+, pandas, openpyxl, pydantic, pyyaml, boto3 (opt), pytest. `gh` CLI per GitHub GraphQL.

**SP:** 20 SP-Umano / 8 SP-Augmented, 7 task.

**Design doc:** [`docs/plans/2026-04-15-siae-dev-analytics-design.md`](../2026-04-15-siae-dev-analytics-design.md)

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | Skill scaffold + SKILL.md + requirements.txt + gate 🔴 privacy | `task-01-scaffold-skill.md` | [PENDING] |
| 2 | `autodetect_sources.py` — detect GitHub/S3 + matrice mode | `task-02-autodetect-sources.md` | [PENDING] |
| 3 | `collect_github.py` — gh graphql PR/commit/review + cache | `task-03-collect-github.md` | [PENDING] |
| 4 | `compute_kpis.py` — 11 KPI + z-score + ROI Index | `task-04-compute-kpis.md` | [PENDING] |
| 5 | `export_excel.py` — 4 sheet xlsx con formatting | `task-05-export-excel.md` | [PENDING] |
| 6 | `collect_s3_telemetry.py` — optional S3 reader | `task-06-collect-s3-telemetry.md` | [PENDING] |
| 7 | `run_analytics.py` CLI + integration test + command + reference docs | `task-07-cli-and-integration.md` | [PENDING] |

## Dipendenze

```
task-01 (scaffold) ──┬─→ task-02 (autodetect) ─┬─→ task-07 (CLI + integration)
                     ├─→ task-03 (collect-gh)   ─┤
                     ├─→ task-04 (compute-kpis) ─┤
                     ├─→ task-05 (export-excel) ─┤
                     └─→ task-06 (collect-s3)   ─┘
```

- Task 1 blocca tutti (setup directory + SKILL.md)
- Task 2-6 sono **indipendenti tra loro** dopo Task 1 → parallelizzabili
- Task 7 dipende da tutti i precedenti (integration)

## Parallelizzazione raccomandata

```
Wave 1 (seriale):      Task 1
Wave 2 (parallelo 5x): Task 2 || Task 3 || Task 4 || Task 5 || Task 6
Wave 3 (seriale):      Task 7
```

## Testing finale (post-Task 7)

Dopo il completamento di Task 7:
1. `pytest skills/siae-dev-analytics/tests/ -v` → tutti i test verdi
2. Esecuzione manuale end-to-end: `/forge-analytics --config template/devforge-analytics.yml --format both`
3. Verifica Excel apribile, 4 sheet, privacy header, data sources dichiarato
4. Smoke test con dati reali: 1 repo pubblico itsiae, finestra 30gg, conferma gate 🔴

**Criterio di successo globale:** tutti i 17 AC del design doc PASSANO.
