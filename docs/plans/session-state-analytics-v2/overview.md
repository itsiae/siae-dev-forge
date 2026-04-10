# Session State Isolation + Analytics V2 — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Isolare lo state per sessione, pinnare l'identità, rendere l'upload affidabile (outbox+retry+ack), introdurre schema v2 con event_id, e integrare token/cost con dedupe multi-model.
**Architettura:** State in `~/.claude/devforge-state/<sid>/`, logger refactored con dual write (sessione + globale), outbox-based upload, schema v2 backward compatible.
**Stack:** Bash, Python 3
**SP:** 8 SP-Umano / 5 SP-Augmented
**Design doc:** `docs/plans/2026-04-10-session-state-analytics-v2-design.md`

---

## Indice Task

### Fase 1 — PR2: Session State Isolation

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | Logger refactor: state per-sessione + identity pinning | `task-01-logger-refactor.md` | [PENDING] |
| 2 | Session-start: init dir sessione + cleanup | `task-02-session-start-init.md` | [PENDING] |
| 3 | Telemetry upload: outbox model | `task-03-outbox-upload.md` | [PENDING] |
| 4 | Stop-gate: flush + upload finale | `task-04-stop-gate-flush.md` | [PENDING] |
| 5 | Post-commit-review: upload post-evento | `task-05-post-commit-upload.md` | [PENDING] |
| 6 | Context + statusline: read da session dir | `task-06-context-statusline.md` | [PENDING] |

### Fase 2 — PR3: Analytics V2

| # | Task | File | Stato |
|---|------|------|-------|
| 7 | Logger schema v2: event_id + canonical fields | `task-07-schema-v2.md` | [PENDING] |
| 8 | Token collector: session dir + dedupe alignment | `task-08-token-collector-v2.md` | [PENDING] |
| 9 | Lambda dedup: idempotenza su event_id | `task-09-lambda-dedup.md` | [PENDING] |
| 10 | Enrich session_end + commit_created con token stats | `task-10-token-enrichment.md` | [PENDING] |
| 11 | Statusline + context: token, costo, telemetry status | `task-11-token-display.md` | [PENDING] |

## Dipendenze

### Fase 1 (PR2)
- Task 1 (logger) PRIMA di tutti gli altri — è la fondazione
- Task 2 (session-start) dipende da Task 1
- Task 3 (outbox) dipende da Task 1
- Task 4, 5, 6 dipendono da Task 1 e 2
- Task 4 e 5 dipendono da Task 3 (usano il nuovo upload)

### Fase 2 (PR3)
- Task 7 (schema v2) dipende da Task 1 (logger PR2)
- Task 8 (token collector) dipende da Task 2 (session dir)
- Task 9 (Lambda) indipendente (infra)
- Task 10, 11 dipendono da Task 7 e 8

### Ordine di esecuzione
```
Task 1 → Task 2 + Task 3 (paralleli) → Task 4 + 5 + 6 (paralleli)
→ [PR2 completa] →
Task 7 + Task 9 (paralleli) → Task 8 → Task 10 + 11 (paralleli)
```
