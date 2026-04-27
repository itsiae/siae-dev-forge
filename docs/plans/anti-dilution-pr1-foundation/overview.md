# PR #1 Anti-Dilution Foundation + Compression — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Implementare ADR-002 (evidence contract) + ADR-003 (SKILL.md compression) + ADR-004 (prompt injection budget) per v1.46 DevForge, preservando 168 PASS baseline test.
**Architettura:** 3 layer indipendenti (lib/evidence-check.sh, centralizations+compression, hook fusion) con TDD per ogni layer.
**Stack:** Bash hooks, Python 3 (adoption-analyzer + token-collector), Node (skills-core), Markdown skills.
**SP:** 5 SP-Umano / 3 SP-Augmented
**Design doc:** `docs/plans/2026-04-25-anti-dilution-enforcement-design.md` (status: approved)
**Target version:** 1.46.0
**Baseline da proteggere:** 168 PASS / 6 FAIL / 1 SKIP (test suite pre-change)

---

## Indice Task

| # | Task | File | Stato | Exec |
|---|------|------|-------|------|
| 1 | Creare 4 centralizations in lib/*.md | `task-01-centralizations.md` | [PENDING] | subagent |
| 2 | Implementare lib/evidence-check.sh (TDD) | `task-02-evidence-check.md` | [PENDING] | in-session |
| 3 | Comprimere skills/using-devforge/SKILL.md (139→90) | `task-03-compress-using-devforge.md` | [PENDING] | subagent |
| 4 | Comprimere skills/siae-brainstorming/SKILL.md (652→220) | `task-04-compress-brainstorming.md` | [PENDING] | subagent |
| 5 | Comprimere skills/siae-tdd/SKILL.md (578→180) | `task-05-compress-tdd.md` | [PENDING] | subagent |
| 6 | Comprimere skills/siae-git-workflow/SKILL.md (744→220) | `task-06-compress-git-workflow.md` | [PENDING] | subagent |
| 7 | Comprimere skills/siae-verification/SKILL.md (345→180) | `task-07-compress-verification.md` | [PENDING] | subagent |
| 8 | Comprimere skills/siae-blind-review/SKILL.md (178→110) | `task-08-compress-blind-review.md` | [PENDING] | subagent |
| 9 | Aggiungere frontmatter validates_via su 5 skill core | `task-09-validates-via-frontmatter.md` | [PENDING] | in-session |
| 10 | Creare tests/compression-regression/ (TDD) | `task-10-regression-test.md` | [PENDING] | in-session |
| 11 | Implementare hooks/devforge-context (TDD) | `task-11-devforge-context-hook.md` | [PENDING] | in-session |
| 12 | Rimuovere 3 hook fusi + aggiornare hooks.json | `task-12-hooks-json-migration.md` | [PENDING] | in-session |
| 13 | Implementare lib/measure-task-baseline.sh | `task-13-measure-task-baseline.md` | [PENDING] | in-session |
| 14 | Version bump + CHANGELOG + PR | `task-14-version-bump-pr.md` | [PENDING] | in-session |
| 15 | In-session testability protocol (meta) | `task-15-in-session-testability.md` | [PENDING] | in-session |

## Dipendenze

```
T01 ──┬─→ T03, T04, T05, T06, T07, T08 (6 task compression parallelizzabili)
T02 ──┘
T03…T08 ─→ T10 (regression test dopo compression)
T09 (indipendente, tocca solo frontmatter top delle skill)
T11 ──→ T12 (new hook prima di registrarlo)
T13 (indipendente)
Tutti ─→ T14 (version bump finale dopo tutti)
```

## Execution strategy

**Fase A — Foundation (sequenziale in-session)**:
- T01 → T02 → T10 (regression test SCRITTO prima delle compression, red state atteso)
- T09 (frontmatter validates_via)
- T11 → T12 (devforge-context hook)
- T13 (measure-task-baseline)

**Fase B — Compression (parallel-safe via subagent)**:
- T03…T08 dispatched in parallel come subagent indipendenti
- Ogni subagent riceve: skill path + target line count + K/M/D classification dal design doc + regola "K intoccabili"
- Dopo ogni compression: run T10 regression test per quella skill → se red, subagent iterates

**Fase C — Release (in-session)**:
- T14: run baseline test completo, confronto con 168/6/1, version bump, PR creation

**Stima durata (SP-Augmented)**:
- Fase A: ~60min (TDD sequenziale)
- Fase B: ~30min (6 subagent paralleli, longest path ~20min)
- Fase C: ~15min

## Criteri accettazione globali PR #1

- [ ] Tutti gli eval sets esistenti passano (baseline 168 PASS / 6 FAIL / 1 SKIP preservato o migliorato)
- [ ] SKILL.md backbone totale ≤1000 righe (wc -l deterministico verificato)
- [ ] Evento telemetry `prompt_injection_size` + `prompt_injection_emitted` con `tier` emesso
- [ ] `baseline-metrics-tasks.json` generato da snapshot via proxy branch+design-doc
- [ ] `lib/evidence-check.sh` testato con positive+negative case su tutte e 5 skill
- [ ] Hook `devforge-context` sostituisce funzionalmente i 3 hook fusi (diff-based reinject attivo, tier-based tag, budget 500 token)
- [ ] `.claude-plugin/plugin.json` bumped a 1.46.0
- [ ] PR aperta con body-file (no heredoc per tua memory "feedback_pr_body_via_file")
- [ ] siae-git-workflow invocata prima dei commit
- [ ] siae-verification invocata prima del completion claim

## Vincoli duri

- Scope `itsiae/*` **mantenuto** hardcoded (scelta utente 2026-04-25)
- PR #2 (task-scope) e PR #3 (observability) **NON** in scope
- TDD-first: test scritto e fallente prima dell'implementazione per T02, T10, T11, T13
- Tests/hooks/ esistente non deve rompersi (unit test protetti)
- Nessuna modifica a comportamento gate attuale (solo cosa considerano evidence)

## Testability protocol (in-session)

**Vincolo**: siamo dentro una sessione Claude Code. Non possiamo aprire una "sessione fresca" per osservare il modello reagire all'injection. Strategy:

- **T02, T09, T10, T11, T13**: step verifica **determinstici** in bash (wc, grep, node, python3) — eseguibili qui
- **T15**: eval set proxy — `evals/anti-dilution-pr1/*.sh` che simulano input controllato e verificano output del hook
- **Post-merge**: dogfooding capture (T15) — `docs/measurements/dogfooding-capture.sh` in sessione nuova per before/after reale
- **Improvement misurabile in-session**:
  - Riduzione righe SKILL.md (wc -l verificato)
  - Riduzione bytes injection (output devforge-context)
  - Presenza/assenza EXTREMELY_IMPORTANT in default output
  - Dedup hash-based (2 invocazioni = 2° <20 bytes)
  - `baseline-metrics-tasks.json` generato con adoption proxy task-scoped

Ogni task include un blocco "Step verifica" con comandi deterministici. Esecuzione in questa sessione via Bash tool.

## Rollback plan

Se PR #1 introduce regressioni:
- `git revert` del merge commit
- Baseline telemetry in `docs/measurements/baseline-2026-04-25/` intatto per analisi forensica
- Tutti i deliverables sono additivi o sostituiscono funzionalmente (0 breaking)
