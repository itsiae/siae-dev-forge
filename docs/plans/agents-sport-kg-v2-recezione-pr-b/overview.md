# PR-B — Recezione sport-kg v2 in doc-generator + code-reviewer

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Estendere doc-generator (HLD batch+auth+rules) e code-reviewer (Point 4 drift KG↔codice) per recepire i nuovi nodi sport-kg v2 (BatchJob, BusinessRule, ExternalSystem) e il tool `graph_consistency_check`.

**Architettura:** Modifica testuale a 2 file markdown agent (`agents/doc-generator.md`, `agents/code-reviewer.md`). Estensione `ToolSearch select` Step 0 esistente + sezioni HLD/review.

**Stack:** Markdown agent prompts (no codice). Smoke test manuale via dispatch Agent + KG live.

**SP:** 2 SP-Umano / 1 SP-Augmented

**Design doc:** `docs/plans/2026-05-03-agents-sport-kg-v2-recezione-design.md` (commit `dea5240`)

**Branch:** `feat/agents-sport-kg-v2-recezione` (può essere mergiato dopo PR-A o in parallelo come branch separato `feat/agents-sport-kg-v2-recezione-pr-b`)

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | Baseline pre-modifica (snapshot HLD + review) | `task-01-baseline-snapshot.md` | [DONE] |
| 2 | doc-generator: estensione bulk loading Step 0 | `task-02-dg-bulk-loading.md` | [DONE] |
| 3 | doc-generator: HLD swim lane Batch Schedulers + footer freshness | `task-03-dg-batch-footer.md` | [DONE] |
| 4 | doc-generator: HLD Authentication chain + Domain rules | `task-04-dg-auth-rules.md` | [DONE] |
| 5 | code-reviewer: estensione bulk loading Step 0 | `task-05-cr-bulk-loading.md` | [DONE] |
| 6 | code-reviewer: Point 4 sotto-checklist drift KG↔codice | `task-06-cr-point4-drift.md` | [DONE] |
| 7 | Smoke test Test 3 + Test 4 + diff baseline | `task-07-smoke-test.md` | [DONE-PARTIAL] (MCP degraded, AC-5 deferred — vedi diff-pr-b-validation.md; AC-6 PASS via static review) |

## Dipendenze

- Task 1 deve essere completato PRIMA di tutti gli altri (baseline snapshot)
- Task 2-4 (doc-generator) sequenziali: 2 → 3 → 4 sullo stesso file
- Task 5-6 (code-reviewer) sequenziali: 5 → 6 sullo stesso file
- Task 2-4 e Task 5-6 indipendenti tra loro (file diversi)
- Task 7 dipende da TUTTI i precedenti

## Criteri di Accettazione (dal design § 10)

- [ ] AC-4: 2 agent aggiornati (`doc-generator.md`, `code-reviewer.md`)
- [ ] AC-5: smoke test Test 3 + Test 4 passano (check binari § 9.3)
- [ ] AC-6: diff post-mod vs snapshot pre-modifica = solo aggiunte

## Riferimenti

- Sport-KG PR #23 (D3 graph_consistency_check)
- Onda 9 who_authenticates: PR #21
- Onda 10 BatchJob + ExternalSystem: PR #17
- Onda 6 BusinessRule: PR #18
