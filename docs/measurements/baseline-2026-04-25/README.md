# Baseline DevForge — 2026-04-25

Baseline telemetria pre-PR #1 anti-dilution per misurare lift post-implementazione.

## Cosa è committato

- `README.md` — questo file
- `baseline-metrics.json` — metriche aggregate derivate (session-scoped)
- `baseline-metrics-tasks.json` — metriche proxy task-scoped (generato da `lib/measure-task-baseline.sh` in T13)

## Cosa NON è committato

`devforge-state-snapshot/` — raw snapshot di 230 sessioni / 3489 eventi / 36MB.

**Motivi**:
- Contiene dati utente (email, token counts, cost estimates)
- Pesante in git history (7691 file)
- Rigenerabile da `~/.claude/devforge-state/` finché snapshot live

**Dove vive il raw snapshot**:
Locale in `docs/measurements/baseline-2026-04-25/devforge-state-snapshot/` (git-ignored via `.gitignore` locale).
Per rigenerare metriche da raw:

```bash
python3 <<'PY'
# vedi snippet in lib/adoption-analyzer.py (PR #3)
PY
```

## Key metrics (dal baseline-metrics.json)

| Skill | Adoption session-scoped (commit sessions) |
|---|---|
| siae-git-workflow | 62.4% |
| siae-brainstorming | 37.6% |
| siae-tdd | 37.6% |
| siae-writing-plans | 21.8% |
| siae-security | 13.9% |
| siae-retrospective | 7.9% |
| siae-finishing-branch | 5.9% |
| siae-verification | **3.0%** |
| siae-blind-review | **0.0%** |

## Target post-PR-2

Adoption per-task ≥ 80% su 5 skill core (brainstorming, tdd, git-workflow, verification, blind-review).
