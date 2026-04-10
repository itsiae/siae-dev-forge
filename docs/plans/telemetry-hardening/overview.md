# Telemetry Hardening — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Fix chirurgici alla telemetria DevForge: pr_merged idempotente, JSON escaping completo, session_conflict event type, cleanup skill-start stale.
**Architettura:** Modifiche puntuali ai 6 hook bash esistenti. Nessun nuovo file. Pattern unico per escaping (devforge_sanitize_json_str già in lib/logger.sh).
**Stack:** Bash
**SP:** 3 SP-Umano / 1 SP-Augmented
**Design doc:** `docs/plans/2026-04-10-telemetry-hardening-design.md`

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | pr_merged idempotente | `task-01-pr-merged-idempotent.md` | [DONE] |
| 2 | JSON escaping (11 call in 6 hook) | `task-02-json-escaping.md` | [DONE] |
| 3 | session_conflict event type + cleanup skill-start | `task-03-session-start-fixes.md` | [DONE] |

## Dipendenze

- Tutti i task sono indipendenti (toccano punti diversi dei file)
- Task 2 e 3 modificano entrambi `hooks/session-start` ma in punti distinti
