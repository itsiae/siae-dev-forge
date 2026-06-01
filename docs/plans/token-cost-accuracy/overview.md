# Piano — Accuratezza calcolo costi token

**Design:** `docs/plans/2026-06-01-token-cost-accuracy-design.md` (APPROVATO)
**Branch:** `fix/token-cost-accuracy`
**Stima:** 2 SP (AI-augmented)
**Esecuzione:** TDD (Red-Green-Refactor) per ogni task

## Goal

Correggere il calcolo costi token: `cache_write_1h` deve essere prezzato 2× input
(non 1.25×). Single source of truth per i prezzi. Tasso EUR configurabile. Tracciare
token totali e modello prevalente nella telemetria.

## Indice task

| # | Task | File | Stato |
|---|------|------|-------|
| 01 | Pricing differenziato cache 5m/1h | `task-01-pricing-differentiated.md` | [PENDING] |
| 02 | Tasso EUR via env var + doc | `task-02-eur-rate-envvar.md` | [PENDING] |
| 03 | Retrocompat snapshot legacy | `task-03-legacy-snapshot-compat.md` | [PENDING] |
| 04 | Dedup tool: delega al core | `task-04-tool-delegates-core.md` | [PENDING] |
| 05 | Modello prevalente + token in telemetria | `task-05-model-prevalent-telemetry.md` | [PENDING] |

## Dipendenze

- Task 02, 03, 04, 05 dipendono da Task 01 (la tabella prezzi nuova è prerequisito).
- Task 04 dipende anche da Task 02 (il tool eredita la conversione EUR dal core).
- Task 05 dipende da Task 01+02 (accumula per modello usando lo snapshot, EUR a runtime).
- Ordine: 01 → 02 → 03 → 04 → 05.

## Criteri di accettazione globali

Vedi design doc, sezione "Criteri di accettazione" (AC1-AC9).
Test suite finale: 14 casi in `tests/test_token_collector.py`, tutti verdi.
