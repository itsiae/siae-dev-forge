# siae-qa — TC Audit Gate (Fase 4c)

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Aggiungere un gate di quality review (Fase 4c) tra la generazione TC e l'export, con approccio distrust che verifica la tracciabilità AC→TC e la completezza del test set.
**Architettura:** Modifiche pure a file Markdown della skill. Fase 4c inserita in `SKILL.md` tra Fase 4b e Fase 5. Template audit gate aggiunto in `XRAY-TEMPLATES.md` con voce checklist.
**Stack:** Markdown / DevForge skill DSL
**SP:** 3 SP-Umano / 1 SP-Augmented
**Design doc:** `docs/plans/2026-03-30-siae-qa-tc-audit-gate-design.md`

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | Fase 4c TC Audit Gate in SKILL.md | `task-01-fase-4c-skill-md.md` | [DONE] |
| 2 | Template TC Audit Gate in XRAY-TEMPLATES.md | `task-02-template-audit-xray.md` | [PENDING] |

## Dipendenze

- Task 1 e Task 2 sono indipendenti (file diversi) — possono essere parallelizzati
- Task 2 dipende logicamente da Task 1 per coerenza dei contenuti — eseguire in sequenza

## Ordine di esecuzione suggerito

```
Task 1 → Task 2  (sequenziale — stesso branch, verifiche finali insieme)
```
