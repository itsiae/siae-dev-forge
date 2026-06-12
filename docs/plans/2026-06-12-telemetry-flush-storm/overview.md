# Fix storm flusher telemetria + backlog illimitato — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development` (stessa sessione)
> o `siae-executing-plans` (sessione separata) per implementare questo piano task per task.

**Goal:** Eliminare lo storm di upload concorrenti e il backlog illimitato del flusher telemetria, in modo additivo e zero-loss.
**Architettura:** Hardening in-place del durable-outbox producer-side. Refactor della POST in funzione iniettabile, poi 4 componenti additivi (lock globale mkdir-based, cap per invocazione, dead-letter, GC per-sessione) tutti confinati in `lib/telemetry-upload.sh`.
**Stack:** Bash (POSIX-ish, portabile macOS BSD + Linux), test bash con override-injection.
**SP:** 4 (Umano) / 1 (Augmented)
**Design doc:** `docs/plans/2026-06-12-telemetry-flush-storm-design.md`

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | Refactor: estrai `_devforge_post_batch` (abilita injection nei test) | `task-01-refactor-post-batch.md` | [DONE] |
| 2 | C1 — Lock globale mkdir-based su `devforge_upload_backlog` | `task-02-global-lock.md` | [DONE] |
| 3 | C2 — Cap per invocazione (oldest-first) | `task-03-cap-per-invocation.md` | [DONE] |
| 4 | C3 — Dead-letter dopo K tentativi → `failed/` | `task-04-dead-letter.md` | [DONE] |
| 5 | C4 — GC sessioni morte (archivia, unità per-sessione) | `task-05-gc-dead-outboxes.md` | [DONE] |
| 6 | No-regression + wiring (cooldown invariato, suite verde) | `task-06-no-regression-wiring.md` | [DONE] |

## Dipendenze

- **Task 1 è prerequisito di tutti**: senza `_devforge_post_batch` iniettabile i test 2-4 farebbero rete reale.
- **Task 4 (C3) dipende da Task 2 (C1)** — WARN-3 del design: il dead-letter è race-safe SOLO sotto il lock. Mai mergiare C3 senza C1.
- **Task 2 → 3 → 4 vanno serializzati**: toccano tutti il corpo di `devforge_upload_backlog`; eseguirli in ordine evita conflitti nello stesso blocco.
- **Task 5 (C4) è indipendente** — nuova funzione `devforge_gc_dead_outboxes`, non tocca il loop di upload.
- **Task 6 è ultimo**: verifica no-regression dopo che 1-5 sono `[DONE]`.

## Criteri di accettazione globali (dal design, Sez. "Criteri di accettazione")

1. Backlog N batch + mock 200 → tutti in `acked/`, ≤cap per invocazione. (Task 3)
2. Mock 500 ripetuto → dopo K tentativi i batch finiscono in `failed/`, non più ritentati. (Task 4)
3. Lock: due upload concorrenti → solo uno processa; stale lock >120s recuperato. (Task 2)
4. GC: outbox sessione non-corrente, mtime >GC_DAYS → archiviato (per-sessione). (Task 5)
4b. Outbox recente o sessione corrente → MAI archiviato. (Task 5)
4c. Lock dir 119s → blocca; 121s → recuperato. (Task 2)
5. Cooldown 60s invariato; zero-loss invariato (nessun `rm` cieco). (Task 4, Task 6)
6. Suite telemetria esistente resta verde. (Task 6)
