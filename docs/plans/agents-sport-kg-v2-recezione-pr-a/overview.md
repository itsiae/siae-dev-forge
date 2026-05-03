# PR-A — Recezione sport-kg v2 in mcp-impact-analyst + qa-investigator

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Estendere i 2 agent SIAE-specific più hot-path (mcp-impact-analyst, qa-investigator) per recepire envelope D1, enum status v2, e 9 tool MCP nuovi di sport-kg v2.

**Architettura:** Modifica testuale a 2 file markdown agent (`agents/mcp-impact-analyst.md`, `agents/qa-investigator.md`). Estensione `ToolSearch select` Step 0 esistente + sezioni testuali pipeline + output format.

**Stack:** Markdown agent prompts (no codice). Smoke test manuale via dispatch Agent + `mcp__sport-kg__*` live.

**SP:** 3 SP-Umano / 2 SP-Augmented

**Design doc:** `docs/plans/2026-05-03-agents-sport-kg-v2-recezione-design.md` (commit `dea5240`)

**Branch:** `feat/agents-sport-kg-v2-recezione`

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | Baseline pre-modifica (snapshot 2 dispatch) | `task-01-baseline-snapshot.md` | [DONE] |
| 2 | mcp-impact-analyst: estensione bulk loading Step 0 | `task-02-mia-bulk-loading.md` | [DONE] |
| 3 | mcp-impact-analyst: Stage 3 5° check + sezioni nodi | `task-03-mia-stage3-nodes.md` | [DONE] |
| 4 | mcp-impact-analyst: output card envelope D1 + enum v2 | `task-04-mia-output-envelope.md` | [DONE] |
| 5 | qa-investigator: estensione bulk loading Step 0 | `task-05-qa-bulk-loading.md` | [DONE] |
| 6 | qa-investigator: Stage 1 nuove righe domanda-tipo | `task-06-qa-stage1-rows.md` | [DONE] |
| 7 | qa-investigator: Stage 2 alternate_hypotheses | `task-07-qa-stage2-hypotheses.md` | [DONE] |
| 8 | qa-investigator: enum status v2 + mapping legacy | `task-08-qa-enum-mapping.md` | [DONE] |
| 9 | Smoke test Test 1 + Test 2 + diff baseline | `task-09-smoke-test.md` | [DONE-PARTIAL] (MCP degraded, AC-2 deferred — vedi diff-pr-a-validation.md) |

## Dipendenze

- Task 1 deve essere completato PRIMA di tutti gli altri (baseline snapshot)
- Task 2-4 (mcp-impact-analyst) sono sequenziali: 2 → 3 → 4 sullo stesso file
- Task 5-8 (qa-investigator) sono sequenziali: 5 → 6 → 7 → 8 sullo stesso file
- Task 2-4 e Task 5-8 sono indipendenti tra loro (file diversi)
- Task 9 dipende da TUTTI i precedenti (smoke test finale)

## Criteri di Accettazione (dal design § 10)

- [ ] AC-1: 2 agent aggiornati (`mcp-impact-analyst.md`, `qa-investigator.md`) con bulk loading select esteso + sezioni testuali aggiornate
- [ ] AC-2: smoke test Test 1 + Test 2 passano (tutti i check binari di § 9.2)
- [ ] AC-3: diff post-mod vs Snapshot 1 e 2 = solo aggiunte, zero righe legacy rimosse o modificate

## Riferimenti

- Sport-KG PR #23 (D1+D2+D3+D4+D5): https://github.com/itsiae/sport-kg/pull/23
- Onda 6 BusinessRule: PR #18
- Onda 9 who_authenticates: PR #21
- Onda 10 BatchJob: PR #17
