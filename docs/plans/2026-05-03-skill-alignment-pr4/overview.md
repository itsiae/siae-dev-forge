# PR-4 Backbone Hardening — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development` per implementare questo piano task per task.

**Goal:** Eliminare backbone leakage SIAE-specific + ridurre instruction bloat in 5 skill backbone via progressive disclosure + riscrivere description in pattern Anthropic "Use when X".

**Architettura:** Edit testuali + extract reference file. Zero hook nuovi, zero behavioural change deterministico. Solo modifiche al contenuto delle skill.

**Stack:** Markdown skill content, frontmatter YAML, bash per validation.

**SP:** 8 SP-Augmented (era 2; aumentato dopo baseline 5 skill bloat misurate).

**Design doc:** `../2026-05-03-skill-alignment-design.md` (sezioni 3.1, 3.2, 3.3).

**Vincolo critico:** **NO-REGRESSION** — ogni skill toccata deve mantenere accuracy di attivazione pre-PR. Baseline misurata in Task 01.

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | Baseline measurement (line count + leakage grep + skill-activation snapshot) | `task-01-baseline.md` | [DONE] |
| 2 | Strip leakage `siae-service-logic-map` line 10 | `task-02-strip-leakage-service-logic-map.md` | [DONE] |
| 3 | Strip leakage `siae-microservices-map` line 6 | `task-03-strip-leakage-microservices-map.md` | [DONE] |
| 4 | Strip leakage `siae-git-workflow` PRODUZIONE/CERTIFICAZIONE | `task-04-strip-leakage-git-workflow.md` | [DONE] |
| 5 | Refactor `siae-debugging` (progressive disclosure + description rewrite) | `task-05-refactor-debugging.md` | [PENDING] |
| 6 | Refactor `siae-finishing-branch` (PD + DR) | `task-06-refactor-finishing-branch.md` | [PENDING] |
| 7 | Refactor `siae-writing-plans` (PD + DR) | `task-07-refactor-writing-plans.md` | [PENDING] |
| 8 | Refactor `siae-executing-plans` (PD + DR) | `task-08-refactor-executing-plans.md` | [PENDING] |
| 9 | Refactor `siae-brainstorming` (PD + DR) | `task-09-refactor-brainstorming.md` | [PENDING] |
| 10 | Description rewrite `siae-tdd` (no PD, già <200) | `task-10-rewrite-tdd-description.md` | [PENDING] |
| 11 | Description rewrite `siae-verification` (no PD) | `task-11-rewrite-verification-description.md` | [PENDING] |
| 12 | Description rewrite `using-devforge` (no PD) | `task-12-rewrite-using-devforge-description.md` | [PENDING] |
| 13 | Final validation (line count + grep + accuracy diff vs baseline) | `task-13-validation.md` | [PENDING] |

## Dipendenze

- Task 01 deve precedere tutti gli altri (baseline immutabile)
- Task 02-04 indipendenti tra loro (3 file diversi)
- Task 05-09 indipendenti tra loro (5 skill diverse)
- Task 10-12 indipendenti tra loro
- Task 13 dipende da Task 01-12 tutti DONE

## Criteri accettazione PR

- 0 match grep `sport-\*\|pop-\*\|pae-\*\|PRODUZIONE\|CERTIFICAZIONE` in 8 backbone
- 8/8 skill backbone <200 righe
- 8/8 description backbone in pattern "Use when X. ..."
- Tutti reference file linkati esistono e sono raggiungibili
- 0 cross-reference rotte: tutte `REQUIRED SUB-SKILL: siae-X` puntano a file esistenti
- Skill activation accuracy post ≥ baseline (no-regression principle)
