# Superpowers Improvements — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Portare 5 improvement dal progetto Superpowers in siae-dev-forge
**Architettura:** Patch a skill esistenti (7 file) + 2 nuove skill + 1 patch hook
**Stack:** Markdown (skill), Bash (hook)
**SP:** 5 SP-Umano / 2 SP-Augmented
**Design doc:** `docs/plans/2026-03-22-superpowers-improvements-design.md`

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | Context-First Rule in 4 skill | `task-01-context-awareness.md` | [DONE] |
| 2 | Option Zero Gate in brainstorming | `task-02-option-zero.md` | [DONE] |
| 3 | Checkbox Sync in 3 skill | `task-03-checkbox-sync.md` | [DONE] |
| 4 | Nuova skill siae-blind-review | `task-04-blind-review.md` | [DONE] |
| 5 | Patch finishing-branch per blind-review | `task-05-finishing-branch-gate.md` | [DONE] |
| 6 | Nuova skill siae-retrospective | `task-06-retrospective.md` | [DONE] |
| 7 | Patch stop-gate hook per retrospective | `task-07-stop-gate-retro.md` | [DONE] |
| 8 | Aggiorna catalogo using-devforge | `task-08-catalog-update.md` | [DONE] |

## Dipendenze

- Task 1, 2, 3 sono indipendenti (patch a skill diverse)
- Task 5 dipende da Task 4 (finishing-branch referenzia blind-review)
- Task 7 dipende da Task 6 (stop-gate referenzia retrospective)
- Task 8 dipende da Task 4 e 6 (catalogo referenzia le nuove skill)
