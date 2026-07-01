# DevForge — Convenzioni SIAE + fix di flusso — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: usa `siae-subagent-development` (stessa sessione)
> o `siae-executing-plans` (sessione separata) per implementare task per task.

**Goal:** Implementare i 6 requisiti di `requirements-devforge.md` — convenzioni SIAE come contesto versionato (REQ-01/02/06) e fix comportamentali di diff PR (REQ-03), brainstorming proporzionato (REQ-04), apertura PR programmatica (REQ-05).
**Architettura:** 3 file canonici versionati iniettati da `hooks/session-start` con fallback esplicito + byte-budget; 2 helper bash condivisi (`pr-base-resolver.sh`, `diff-truncate.sh`) che rimpiazzano gli hardcode `origin/main`; euristica complessità in `lib/file-taxonomy.sh` + short-circuit nel `brainstorming-gate`; fix flusso PR (timeout `review-evidence`, linguaggio `pr-gate`, idempotenza, programmatic-first).
**Stack:** bash hooks, markdown skills, python/js lib, test bash+pytest.
**SP:** 18 umano / 7 AI-augmented.
**Design doc:** `docs/plans/2026-07-01-devforge-siae-conventions-and-flow/design.md`

---

## Indice Task

| # | Task | File | Cluster | Stato |
|---|------|------|---------|-------|
| 1 | File canonici (environments/plan-deploy/multirepo) + guard test | `task-01-canonical-reference-files.md` | A contesto | [PENDING] |
| 2 | Injection session-start (fallback esplicito + byte-budget) | `task-02-session-start-injection.md` | A contesto | [PENDING] |
| 3 | Repoint onboarding + factory-configs alla fonte canonica | `task-03-repoint-onboarding.md` | A contesto | [PENDING] |
| 4 | `lib/pr-base-resolver.sh` + unit test | `task-04-pr-base-resolver.md` | B diff | [PENDING] |
| 5 | `lib/diff-truncate.sh` + `DEVFORGE_MAX_DIFF_LINES` + unit test | `task-05-diff-truncate.md` | B diff | [PENDING] |
| 6 | Wire resolver nei siti bash (no heredoc) + regression non-main | `task-06-wire-resolver-bash.md` | B diff | [PENDING] |
| 7 | Riscrivi heredoc iniettati agli agent (base dinamica + truncation) | `task-07-rewrite-agent-heredocs.md` | B diff | [PENDING] |
| 8 | `devforge_change_is_trivial()` in file-taxonomy + unit test | `task-08-file-taxonomy-trivial.md` | C brainstorm | [PENDING] |
| 9 | brainstorming-gate short-circuit trivial + flag + reset counter | `task-09-brainstorming-gate-complexity.md` | C brainstorm | [PENDING] |
| 10 | Riconcilia "zero eccezioni" (skill/catalog/cases/ENV_VARS/memory) | `task-10-reconcile-zero-eccezioni.md` | C brainstorm | [PENDING] |
| 11 | Fix timeout review-evidence + idempotenza PR + README gate | `task-11-pr-make-possible.md` | D PR | [PENDING] |
| 12 | Programmatic-first + linguaggio onesto + no-review advisory | `task-12-pr-programmatic-first.md` | D PR | [PENDING] |
| 13 | Hook convention-injector (moment-injection ibrida) | `task-13-convention-injector.md` | A contesto | [PENDING] |

## Dipendenze

- **A**: Task 2 dipende da Task 1 (i file devono esistere); Task 3 dipende da Task 1; **Task 13 dipende da Task 1 + Task 2** (moment-injection ibrida, decisione utente 2ª AskUserQuestion).
- **B**: Task 6 dipende da Task 4 + Task 5; Task 7 dipende da Task 4 + Task 5.
- **C**: Task 9 dipende da Task 8; Task 10 indipendente (allineamento testo/memory).
- **D**: Task 12 dipende da Task 7 (condivide `hooks/pr-gate:205-266`) + Task 11; Task 11 indipendente.
- Cross-cluster: nessuna dipendenza tra A/B/C/D — i 4 cluster sono parallelizzabili tra loro (esecuzione in worktree isolati per evitare race git).

## Note di esecuzione
- Ogni task è TDD: test fallente → implementazione → verde → commit.
- Coordinamento `hooks/pr-gate:205-266`: Task 7 (base dinamica) prima, Task 12 (linguaggio advisory + no-review) dopo, sullo stesso blocco.
- Zero regressioni: girare suite esistente + delta vs baseline (memory: no-regression directive).
