# Superpowers Review System — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Portare document review system e GATE scaling da obra/superpowers PR #334 e #522
**Architettura:** 2 nuovi reviewer prompt + patch a 3 skill esistenti
**Stack:** Markdown (skill files)
**SP:** 3 SP-Umano / 1 SP-Augmented
**Design doc:** `docs/plans/2026-03-30-superpowers-review-system-design.md`

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | Spec reviewer prompt per brainstorming | `task-01-spec-reviewer-prompt.md` | [DONE] |
| 2 | Potenzia Step 6b in brainstorming con review automatica | `task-02-brainstorming-step6b.md` | [DONE] |
| 3 | Plan reviewer prompt per writing-plans | `task-03-plan-reviewer-prompt.md` | [DONE] |
| 4 | Aggiungi Step 3c Plan Review in writing-plans | `task-04-writing-plans-step3c.md` | [DONE] |
| 5 | GATE scaling + orchestrator boundary in subagent-development | `task-05-subagent-gate-scaling.md` | [DONE] |

## Dipendenze

- Task 1 e 3 sono indipendenti (nuovi file, nessun conflitto)
- Task 2 dipende da Task 1 (brainstorming SKILL.md referenzia spec-reviewer-prompt.md)
- Task 4 dipende da Task 3 (writing-plans SKILL.md referenzia plan-reviewer-prompt.md)
- Task 5 e' indipendente (modifica solo subagent-development)
