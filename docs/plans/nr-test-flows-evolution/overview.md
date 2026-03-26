# siae-nr-test-flows Evolution — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Evolvere la skill siae-nr-test-flows da 4.4/10 a enterprise-grade
aggiungendo Question Tree contestuale, copertura framework IT factory,
pattern meccanici P6-P10, User Journey ordering e Smoke Test set.

**Architettura:** 7 file modificati/creati nella directory `skills/siae-nr-test-flows/`.
Approccio modulare: la logica complessa viene esternalizzata in reference file
per non superare il limite token di SKILL.md.

**Stack:** Markdown + YAML (skill DevForge — no codice di produzione)

**SP:** 8 SP-Umano / 3 SP-Augmented

**Design doc:** `docs/plans/2026-03-26-nr-test-flows-evolution-design.md`

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | Crea Question Tree | `task-01-question-tree.md` | [PENDING] |
| 2 | Aggiorna SKILL.md | `task-02-skill-md.md` | [PENDING] |
| 3 | Aggiorna Framework Detection Matrix | `task-03-framework-matrix.md` | [PENDING] |
| 4 | Aggiorna Evidence Patterns P6-P10 | `task-04-evidence-patterns.md` | [PENDING] |
| 5 | Crea Journey Ordering Rules | `task-05-journey-ordering.md` | [PENDING] |
| 6 | Aggiorna Flow Map Template | `task-06-flow-map-template.md` | [PENDING] |
| 7 | Aggiorna Test List Template | `task-07-test-list-template.md` | [PENDING] |

## Dipendenze

- Task 2 dipende da Task 1 (SKILL.md referenzia question-tree.md)
- Task 2 dipende da Task 5 (SKILL.md referenzia journey-ordering-rules.md)
- Task 3, 4, 6, 7 sono indipendenti e parallelizzabili
- Task 2 va eseguito per ultimo tra quelli che dipendono da altri
