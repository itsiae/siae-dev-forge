# siae-test-data — Unicità Nomi Cross-Run — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Garantire che run successive di siae-test-data producano nomi/cognomi e ragioni sociali univoche, legando il seed di generazione all'epoch time.
**Architettura:** Auto-populate `id_tag` da epoch 5 cifre in `genera_dataset()` (Python) e `main()` (JS) quando non esplicitamente fornito. Propagare `run_epoch` nel meta output. Aggiornare ragione sociale con suffisso epoch.
**Stack:** Python 3.11+, Node.js, pytest
**SP:** 3
**Design doc:** `docs/plans/2026-06-23-siae-test-data-uniqueness-design.md`

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | Auto-generate id_tag da epoch in genera_dataset() (Python) | `task-01-python-id-tag-epoch.md` | [DONE] |
| 2 | Propagare run_epoch in genera_profilo() e meta block (Python) | `task-02-python-run-epoch-meta.md` | [DONE] |
| 3 | Aggiornare ragione sociale con suffisso epoch (Python) | `task-03-python-ragione-sociale-epoch.md` | [DONE] |
| 4 | Aggiungere --id-tag al CLI main() (Python) | `task-04-python-cli-id-tag.md` | [DONE] |
| 5 | Aggiungere epoch tag ai pid in generate_profiles.js | `task-05-js-pid-epoch.md` | [DONE] |
| 6 | Aggiornare output_schema.md con generated_at_epoch | `task-06-schema-update.md` | [DONE] |
| 7 | Test cross-run uniqueness Python | `task-07-test-python-uniqueness.md` | [DONE] |
| 8 | Test cross-run uniqueness Node.js | `task-08-test-js-uniqueness.md` | [DONE] |

## Dipendenze

- Task 2 dipende da Task 1 (run_epoch viene calcolato nella stessa funzione di id_tag)
- Task 3 dipende da Task 1 (usa id_tag per il suffisso ragione sociale)
- Task 4 è indipendente (solo CLI wiring, non tocca la logica)
- Task 5 è indipendente (file JS separato)
- Task 6 è indipendente (solo documentazione)
- Task 7 dipende da Task 1+2+3
- Task 8 dipende da Task 5
