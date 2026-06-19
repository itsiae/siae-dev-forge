# Piano — Attribution Source Completeness

**Design:** [design.md](design.md) · **Escalation non-code:** [ESCALATION.md](ESCALATION.md)
**Data:** 2026-06-19 · **Stima:** Umano 3 SP / Augmented 1 SP

## Goal

Portare `auth_email` a ~100% alla fonte lato produttore DevForge tramite:
- **Metodo A** — lazy resolution resiliente nel logger (gap 1, mitiga 2/4)
- **Metodo B** — eventi osservabilità su dominio esterno / identità irrisolta (misura gap 3/4)

## Vincoli

- **Path critico**: `devforge_log`/`devforge_log_timed` attraversati da ogni evento → no-regression obbligatoria.
- **TDD**: test RED prima dell'implementazione per ogni ciclo.
- **Best-effort**: nessun evento deve mai abortire un hook (`set -e` safe).

## Task

| # | Task | Tipo | AC | Stato |
|---|------|------|----|-------|
| 01 | [Test lazy auth resolution (RED)](task-01-test-lazy-auth.md) | test | AC1,AC2,AC3,AC6,AC7 | [PENDING] |
| 02 | [Implementa _devforge_ensure_auth + wiring (GREEN)](task-02-impl-lazy-auth.md) | impl | AC1,AC2,AC3,AC6,AC7 | [PENDING] |
| 03 | [Test osservabilità identità (RED)](task-03-test-observability.md) | test | AC4,AC5,AC8 | [PENDING] |
| 04 | [Implementa emit in session-start startup (GREEN)](task-04-impl-observability.md) | impl | AC4,AC5,AC8 | [PENDING] |
| 05 | [Doc ENV_VARS + no-regression suite](task-05-doc-and-regression.md) | doc/verify | AC6 | [PENDING] |

## Ordine

01→02 (lazy resolution: RED poi GREEN) → 03→04 (osservabilità: RED poi GREEN) → 05 (doc + regression finale).
I cicli 01-02 e 03-04 sono indipendenti tra loro; 05 chiude.
