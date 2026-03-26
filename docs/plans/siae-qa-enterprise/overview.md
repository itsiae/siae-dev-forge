# siae-qa Enterprise Upgrade — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Portare `siae-qa` a enterprise-grade su 4 dimensioni: determinismo, coverage, output strutturato, metriche.
**Design doc:** `docs/plans/2026-03-26-siae-qa-enterprise-upgrade-design.md`
**SP:** 13 SP-Umano / 5 SP-Augmented
**Branch:** `feat/siae-qa-enterprise-upgrade`

---

## File target

```
skills/siae-qa/SKILL.md                    ← modificato da task A2, A3, A4, B2, C1, C2, C3, C4
skills/siae-qa/reference/question-trees.md ← modificato da task A2, B1, B3, B4, C1
skills/siae-qa/XRAY-TEMPLATES.md           ← modificato da task A1, A4, B3, B4, C3
skills/siae-qa/reference/code-scan.md      ← NUOVO (task B2)
```

---

## Indice Task

| # | Task | File | Cluster | Stato |
|---|------|------|---------|-------|
| 01 | Allineamento segnali inferenza | `task-01-signal-alignment.md` | A | [DONE] |
| 02 | Skip-criteria espliciti per ogni domanda | `task-02-skip-criteria.md` | A | [DONE] |
| 03 | Cardinalità minima matrice scenari | `task-03-min-cardinality.md` | A | [DONE] |
| 04 | Regole granularità step | `task-04-step-granularity.md` | A | [DONE] |
| 05 | Domanda L4 performance/SLA (tutti i tipi) | `task-05-performance-questions.md` | B | [DONE] |
| 06 | Phase 0-bis Code Scan | `task-06-code-scan.md` | B | [DONE] |
| 07 | Split Integration → REST + Event | `task-07-integration-split.md` | B | [DONE] |
| 08 | 5 nuovi tipi applicativi | `task-08-new-types.md` | B | [DONE] |
| 09 | Ordinamento per flusso utente (Fase 4c) | `task-09-flow-ordering.md` | C | [DONE] |
| 10 | Primary Type + Secondary Tags | `task-10-composite-types.md` | C | [DONE] |
| 11 | Schema classificazione 5 campi enterprise | `task-11-enterprise-schema.md` | C | [DONE] |
| 12 | Release Readiness Score | `task-12-release-readiness.md` | C | [DONE] |

---

## Dipendenze

- Task 01 è indipendente (quick fix, nessuna dipendenza)
- Task 02, 03, 04 sono indipendenti tra loro e da 01
- Task 05, 06, 07, 08 sono indipendenti tra loro; 07 precede 08 (i nuovi tipi usano la struttura di Integration split)
- Task 09, 10, 11, 12 sono indipendenti tra loro
- Cluster B (05-08) può iniziare in parallelo con Cluster A (01-04)
- Cluster C (09-12) può iniziare in parallelo con A e B

## Esecuzione suggerita (subagents paralleli)

```
Wave 1 (parallela):  01 + 02 + 03 + 04 + 05 + 09 + 11 + 12
Wave 2 (dopo 07):    06 + 07 + 10
Wave 3 (dopo 07):    08
```
