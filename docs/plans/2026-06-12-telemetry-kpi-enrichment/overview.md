# Piano — Arricchimento eventi telemetria KPI (branch_created + has_tests)

- **Design:** [../2026-06-12-telemetry-kpi-enrichment-design.md](../2026-06-12-telemetry-kpi-enrichment-design.md) (APPROVATO, spec-review PASS iter 2)
- **Branch:** `feat/telemetry-kpi-enrichment` (worktree `~/devforge-wt-telemetry`)
- **Metodo:** TDD obbligatorio (test-first per componente)
- **Vincolo non negoziabile:** ADDITIVO PURO — nessuna modifica a eventi/campi esistenti consumati dalla pipeline; zero-loss telemetria invariato.

## Goal

Migliorare la qualità dei KPI #3 (lead time, via nuovo evento `branch_created`) e #5
(`has_tests` robusto + `tests_files_changed`) emettendo nuovi dati telemetria raw additivi.

## Criteri di accettazione globali

1. `branch_created` emesso SOLO su creazione branch (`-b`/`-c`), `base_branch` corretto, mai su altri comandi.
2. Evento valido JSON con `branch`/`repo_remote` top-level (no duplicazione meta).
3. `has_tests` copre anche `__tests__/` e `conftest`; nessun falso negativo sui pattern pre-esistenti.
4. `tests_files_changed` int coerente col diff del commit.
5. Eventi/campi esistenti invariati (additivo); pipeline non si rompe.
6. Hook portabile bash 3.2/macOS, best-effort non bloccante.

## Task

| # | Task | Stato |
|---|------|-------|
| 01 | `hooks/branch-tracker` + entry `hooks.json` (TDD: T1,T2,T3,T3b,T3c,T3d,T4) | [PENDING] |
| 02 | `hooks/post-commit-review`: pattern has_tests + `tests_files_changed` (TDD: T5,T6,T7,T8) | [PENDING] |
| 03 | No-regression payload `commit_created` + verifica integrazione hooks.json (TDD: T9) | [PENDING] |

## Dipendenze

- task-01 indipendente (nuovo file + hooks.json).
- task-02 indipendente (modifica post-commit-review).
- task-03 dipende da task-02 (verifica il payload modificato) e da task-01 (hooks.json integro).
