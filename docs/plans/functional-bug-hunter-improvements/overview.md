# Plan — functional-bug-hunter v1.2.0 improvements

**Design doc**: `docs/plans/2026-05-21-functional-bug-hunter-improvements-design.md`
**Audit source**: `audit-reports/functional-bug-hunter-audit-2026-05-21.md`
**Skill target**: `skills/siae-functional-bug-hunter/`
**Branch**: `feat/siae-functional-bug-hunter`

## Goal

Chiudere 10 gap identificati nell'audit (Anthropic best practice +
capability codification + token efficiency + recall improvement) portando
la skill da score medio 6.75/10 a ~8.5/10.

## Task list

| # | Task | Stato | Effort | Dipendenze |
|---|------|-------|-------:|------------|
| 01 | Compress description ≤1024 char + move stack list to body | [COMPLETED] | 15min | – |
| 02 | Add "When to use" + "Supported stacks" sections | [COMPLETED] | 10min | 01 |
| 03 | Extract Phase 0..8 narrative → `references/pipeline_internals.md` | [COMPLETED] | 1h | – |
| 04 | Dedup hallucination guard → `references/hallucination_guard.md` | [COMPLETED] | 20min | – |
| 05 | Create `references/README.md` load-matrix | [COMPLETED] | 30min | 03, 04 |
| 06 | Implement `scripts/path_feasibility.py` + smoke test | [PENDING] | 3h | – |
| 07 | Add mode dispatcher to `scripts/run_lock.py` + smoke test | [PENDING] | 3h | – |
| 08 | Register `commands/siae-functional-bug-hunter.md` | [PENDING] | 30min | – |
| 09 | Add BP-024 + BP-025 in `references/stacks/typescript-javascript.md` | [PENDING] | 2h | – |
| 10 | Add BP-026 + BP-027 in `references/stacks/data-platform.md` | [PENDING] | 2h | – |
| 11 | Validation + CHANGELOG + version bump 1.1.0 → 1.2.0 | [PENDING] | 30min | tutti |

## Execution mode

Implementer in-session (controller-subagent pattern non necessario: task
atomici eseguiti sequenzialmente dal main agent). T1-T5 già eseguiti
prima della formalizzazione brainstorming/plan (workflow `feat/*` post-fact
ratification).

## Acceptance criteria

Vedi design doc § "Criteri di accettazione" (10 punti).

## Out of scope

Vedi design doc § "Out of scope (v1.2.0)" — split `bug_patterns.md`,
`@file:` imports, BP-028/029, pytest suite formale, Riverpod recall.
