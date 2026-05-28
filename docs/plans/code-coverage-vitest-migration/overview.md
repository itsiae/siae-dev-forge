# Plan — code-coverage Vitest-First Auto-Migration

**Design ref:** [docs/plans/2026-05-28-code-coverage-vitest-migration-design.md](../2026-05-28-code-coverage-vitest-migration-design.md)
**Branch:** `feat/code-coverage-vitest-migration`
**SP estimate:** 8 Umano / 5 Augmented
**Tasks:** 12

## Goal

Fix the bug in `skills/code-coverage/` Phase 2 decision tree where Jest is wrongly preferred over Vitest by presence (jest.config.* or jest in scripts) rather than by real incompatibility. After this plan: Vitest is the absolute default; Jest is selected only when one of 10 deterministic incompatibility signals (I1..I10) fires; legacy Jest projects auto-migrate to Vitest with snapshot + rollback safety.

## Acceptance gate

Plan complete when ALL 12 tasks marked [COMPLETED] AND:
- `pytest skills/code-coverage/scripts/tests/` is green (existing 26 + new ≥30 tests)
- Branch `feat/code-coverage-vitest-migration` opens PR to `main`
- Spec-reviewer iter 2 PASS already validates design (no further iterations needed)

## Task index

| # | Task | Status | Touches |
|---|---|---|---|
| 01 | Validate vitest-jest-compat.json structure + sanity smoke | `[PENDING]` | `assets/vitest-jest-compat.json`, new test |
| 02 | TDD red: detect_jest_incompat signals I1-I5 | `[PENDING]` | new `scripts/tests/test_detect_jest_incompat.py` |
| 03 | TDD red+green: detect_jest_incompat signals I6-I10 + decision + monorepo | `[PENDING]` | `scripts/tests/test_detect_jest_incompat.py`, new `scripts/detect_jest_incompat.py` |
| 04 | TDD red+green: migrate codemod + idempotency + no-rewrite tokens | `[PENDING]` | new `scripts/tests/test_migrate_jest_to_vitest.py`, partial `scripts/migrate_jest_to_vitest.py` |
| 05 | TDD red+green: migrate jest config translation + package.json rewrite + setup rename | `[PENDING]` | `scripts/tests/test_migrate_jest_to_vitest.py`, `scripts/migrate_jest_to_vitest.py` |
| 06 | TDD red+green: migrate snapshot + dirty-tree refuse + opt-out + per-PM install/rollback + smoke verify | `[PENDING]` | `scripts/tests/test_migrate_jest_to_vitest.py`, `scripts/migrate_jest_to_vitest.py` |
| 07 | Patch validate_env.py + regression test | `[PENDING]` | `scripts/validate_env.py`, `scripts/tests/test_validate_env_ext.py` |
| 08 | Patch lib/phase1-discover.sh + lib/state-schema.json | `[PENDING]` | `lib/phase1-discover.sh`, `lib/state-schema.json` |
| 09 | Patch SKILL.md (Phase 2 + Phase 4b + Principle 1 + HARD READ POLICY) + remove orphan constraints.json refs | `[PENDING]` | `SKILL.md` |
| 10 | Create references/phase-4b-migration.md | `[PENDING]` | new `references/phase-4b-migration.md`, `references/index.md` |
| 11 | Integration: test_phase2_decision_tree archetypal (5 fixtures) | `[PENDING]` | new `scripts/tests/test_phase2_decision_tree.py` |
| 12 | Run full pytest + per-layer commits + open PR | `[PENDING]` | git operations |

## Quality regole (from siae-writing-plans memory)

- Ogni task standalone (eseguibile da subagent con fresh context)
- TDD: test before impl (RED → GREEN cycle)
- File path concreti, no `[...]` o `vedi sopra`
- Snippet codice completi nei task dove necessario
- Acceptance criteria verificabili in <2 min

## Out of scope

- Vitest 2.x/3.x targeting
- Babel preset translation
- CI YAML changes
- LSP/AST codemod

## REQUIRED SUB-SKILL

```
REQUIRED SUB-SKILL: siae-tdd
```
Per ogni task con prefisso "TDD red" o "TDD green" — applica ciclo Red-Green-Refactor.

```
REQUIRED SUB-SKILL: siae-executing-plans
```
Per execution batch in sessione separata (alternativa a subagent stessa sessione).
