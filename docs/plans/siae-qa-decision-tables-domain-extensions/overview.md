# siae-qa — Decision Tables, Domain Extensions, Coverage Metrics

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Colmare i 3 gap prioritari identificati dal panel QA nella skill `siae-qa`:
Decision Tables assenti, domain extensions mancanti (Mobile, IaC, Event-driven),
coverage metrics assenti.

**Architettura:** Modifiche pure a file Markdown della skill. Nessun codice
applicativo. Il gate 4a-bis viene inserito in `SKILL.md` tra Fase 4a e 4b.
I nuovi tipi si aggiungono a `question-trees.md` seguendo il pattern L1/L2/L3
già consolidato. Le metriche si integrano nel Riepilogo Copertura esistente
in `XRAY-TEMPLATES.md`.

**Stack:** Markdown / DevForge skill DSL
**SP:** 5 SP-Umano / 3 SP-Augmented
**Design doc:** `docs/plans/2026-03-30-siae-qa-decision-tables-domain-extensions-design.md`

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | Gate 4a-bis Decision Table in SKILL.md | `task-01-gate-4abis-skill-md.md` | [DONE] |
| 2 | Vincolo non negoziabile DT in SKILL.md | `task-02-vincolo-dt-skill-md.md` | [DONE] |
| 3 | Prefisso [DT] in XRAY-TEMPLATES.md | `task-03-prefisso-dt-xray.md` | [DONE] |
| 4 | Albero Mobile/Flutter in question-trees.md | `task-04-tree-mobile-flutter.md` | [DONE] |
| 5 | Albero IaC/Terraform in question-trees.md | `task-05-tree-iac-terraform.md` | [DONE] |
| 6 | Albero Event-driven/Async in question-trees.md | `task-06-tree-event-driven.md` | [DONE] |
| 7 | Tabella Segnali Req Typing (+3 righe) in XRAY-TEMPLATES.md | `task-07-segnali-req-typing.md` | [DONE] |
| 8 | Coverage Score nel Riepilogo Copertura in XRAY-TEMPLATES.md | `task-08-coverage-score.md` | [DONE] |
| 9 | Checklist di Verifica (+2 voci) in XRAY-TEMPLATES.md | `task-09-checklist-verifica.md` | [DONE] |

## Dipendenze

- Task 1 e 2 sono indipendenti ma entrambi su `SKILL.md` — eseguirli in sequenza
- Task 3, 7, 8, 9 sono tutti su `XRAY-TEMPLATES.md` — eseguirli in sequenza
- Task 4, 5, 6 sono tutti su `question-trees.md` — eseguirli in sequenza
- Non ci sono dipendenze tra i 3 gruppi — possono essere parallelizzati

## Ordine di esecuzione suggerito

```
Batch A (SKILL.md):      Task 1 → Task 2
Batch B (question-trees): Task 4 → Task 5 → Task 6
Batch C (XRAY-TEMPLATES): Task 3 → Task 7 → Task 8 → Task 9
```

Batch A, B, C possono partire in parallelo se si usano subagent separati.
