# Piano — Visualizzazione attivazione plugin + durabilità telemetria

**Design:** [design.md](design.md) (approvato 2026-06-18)
**Branch:** feat/statusline-python-and-update-notice (estende PR #339)
**Goal forte:** "non possiamo avere degradazione della telemetria" → D2 elimina il no-fsync via tier perl.
**SP:** Umano ~4.5 · Augmented ~2.25

## Task

| # | Task | Stato | File |
|---|------|-------|------|
| 01 | D2 — tier perl fsync in logger.sh (elimina degradazione) | [DONE] | [task-01](task-01-perl-fsync-tier.md) |
| 02 | A+B — label versione / dev-mode (statusline) | [DONE] | [task-02](task-02-version-dev-label.md) |
| 03 | #1 — cache git per-cwd (fix bug cross-repo) | [DONE] | [task-03](task-03-git-cache-perrepo.md) |
| 04 | C — pallino 🟡 fallback telemetria (statusline) | [DONE] | [task-04](task-04-telemetry-health-dot.md) |
| 05 | Wiring test in run-all.sh + no-regression | [DONE] | [task-05](task-05-wire-tests-no-regression.md) |

## Ordine consigliato
01 (D2, il goal critico) → 02 → 03 → 04 → 05. Task 01 prima perché è il goal bloccante e tocca codice telemetria critico.

## AC globali
- **D2:** perl tier elimina no-fsync; T3b/T9b aggiornati; tier python3/node invariati.
- **A/B:** `🔨 DevForge v1.91.0` (semver) / `(dev)` (non-semver).
- **#1:** cache git keyed per-cwd, zero contaminazione cross-repo.
- **C:** `🟡` su label quando sentinel `.devforge-no-fsync-warned` presente.
- **Vincoli:** bash 3.2, `set -euo pipefail` safe, additivo, no rete.
