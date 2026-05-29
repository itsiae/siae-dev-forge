# Task 12 — Run full pytest + per-layer commits + open PR

**Status:** `[PENDING]`
**Depends on:** task-01 through task-11
**Estimate:** 15 min
**Files:** git operations + GitHub PR

## Goal

Verifica finale: full test suite green (no regression), commits atomici per layer, PR aperta a main.

## Steps

### A. Full test suite

```bash
cd /Users/mazzacuv/Git/siae-dev-forge
python3 -m pytest skills/code-coverage/scripts/tests/ -v --tb=short 2>&1 | tee /tmp/cc-test-output.log
```

Verifica nel log:
- TUTTI i test pre-esistenti (26 file: `test_*.py`) ancora pass.
- I 4 nuovi file test (`test_vitest_jest_compat_asset.py`, `test_detect_jest_incompat.py`, `test_migrate_jest_to_vitest.py`, `test_phase2_decision_tree.py`) pass.
- Counter test totale ≥ pre-existing + 30 nuovi = ≥56 test totali nuovi/totali.

Se ci sono fail:
- Fix sul ramo (NON saltare TDD, NON marcare task completati con fail attivi).
- Re-run.

### B. Verify bash + JSON syntax

```bash
bash -n skills/code-coverage/lib/phase1-discover.sh
python3 -c "import json; json.load(open('skills/code-coverage/lib/state-schema.json'))"
python3 -c "import json; json.load(open('skills/code-coverage/assets/vitest-jest-compat.json'))"
# SKILL.md orphan refs
grep -c "constraints.json" skills/code-coverage/SKILL.md  # → 0
```

### C. Atomic commits per layer

```bash
git status --short

# Layer 1: asset
git add skills/code-coverage/assets/vitest-jest-compat.json \
        skills/code-coverage/scripts/tests/test_vitest_jest_compat_asset.py
git commit -m "$(cat <<'EOF'
feat(code-coverage): add vitest-jest-compat.json closed signal list

Closed list of 10 incompatibility signals (I1..I10) for Vitest-first
auto-migration. Anything NOT in this list is migrable.

Co-Authored-By: SIAE DevForge
EOF
)"

# Layer 2: detect script
git add skills/code-coverage/scripts/detect_jest_incompat.py \
        skills/code-coverage/scripts/tests/test_detect_jest_incompat.py
git commit -m "$(cat <<'EOF'
feat(code-coverage): add detect_jest_incompat.py signal evaluator

Per-workspace evaluator emitting jest-compat.json with decision:
vitest-default | vitest-migrate | jest-incompat | jest-forced.
Deterministic detection via closed list I1..I10.

Co-Authored-By: SIAE DevForge
EOF
)"

# Layer 3: migrate script
git add skills/code-coverage/scripts/migrate_jest_to_vitest.py \
        skills/code-coverage/scripts/tests/test_migrate_jest_to_vitest.py
git commit -m "$(cat <<'EOF'
feat(code-coverage): add migrate_jest_to_vitest.py atomic migration

Phase 4b engine: dirty-tree refuse, snapshot, jest.config translation,
package.json rewrite, codemod (21 mappings, no-rewrite tokens flagged),
per-PM install/rollback (npm/pnpm/yarn/yarn-berry/bun), smoke verify.

Co-Authored-By: SIAE DevForge
EOF
)"

# Layer 4: integration patches
git add skills/code-coverage/scripts/validate_env.py \
        skills/code-coverage/scripts/tests/test_validate_env_ext.py \
        skills/code-coverage/lib/phase1-discover.sh \
        skills/code-coverage/lib/state-schema.json \
        skills/code-coverage/scripts/tests/test_phase2_decision_tree.py
git commit -m "$(cat <<'EOF'
feat(code-coverage): wire Phase 2 decision to jest-compat.json

- validate_env._detect_required_framework: delegates to compat file
- phase1-discover.sh: runs detect_jest_incompat.py in parallel
- state-schema.json: documents migrate flag, jest-compat.json, migration-report.json
- 5 archetypal integration tests (incl. THE bug-fix regression)

Co-Authored-By: SIAE DevForge
EOF
)"

# Layer 5: docs
git add skills/code-coverage/SKILL.md \
        skills/code-coverage/references/phase-4b-migration.md \
        skills/code-coverage/references/index.md
git commit -m "$(cat <<'EOF'
docs(code-coverage): SKILL.md Phase 2 v2 + Phase 4b + remove orphan constraints.json

- Phase 2 decision tree: presence-based -> incompat-based (THE BUG FIX)
- Phase 4b: conditional Jest->Vitest migration (atomic + rollback)
- Principle 1: clarify Phase 4b file mutation scope
- Principle 4: auto-migration mentioned
- HARD READ POLICY: phase-4b conditional
- Remove orphan constraints.json refs (dead code)
- New conditional reference: references/phase-4b-migration.md

Co-Authored-By: SIAE DevForge
EOF
)"

# Layer 6: plan + design
git add docs/plans/2026-05-28-code-coverage-vitest-migration-design.md \
        docs/plans/code-coverage-vitest-migration/
git commit -m "$(cat <<'EOF'
docs(plans): add code-coverage vitest-migration design + 12-task plan

Design synthesized from 3 blind agent proposals + spec-review iter 2 PASS.
Decomposition: 12 bite-sized tasks for TDD execution.

Co-Authored-By: SIAE DevForge
EOF
)"
```

### D. Push + open PR

```bash
git push -u origin feat/code-coverage-vitest-migration

gh pr create --base main --title "fix(code-coverage): Vitest-first decision tree + auto-migration from Jest" --body "$(cat <<'EOF'
## Summary

- **Bug:** Phase 2 decision tree falls back to Jest on mere presence of `jest.config.*` or `jest` in test scripts, violating Principle 4 (Vitest-first). Same bug duplicated in `validate_env.py`. Orphan `constraints.json` reference in SKILL.md.
- **Fix:** Invert the bias. Vitest is the absolute default. Jest is selected ONLY when one of 10 deterministic incompatibility signals (I1..I10) fires. Legacy Jest projects auto-migrate to Vitest via new Phase 4b (atomic: snapshot → translate → codemod → install → smoke verify → commit OR rollback).
- **Safety:** dirty-tree refuse pre-flight; per-PM lockfile rollback matrix (npm/pnpm/yarn-classic/yarn-berry/bun); opt-out via `CC_DISABLE_JEST_MIGRATION=1` or `overrides.json.force_jest`.

## Design

3 blind agent paralleli proposed independent designs. Synthesized: base AGENT-2 (rollback safety + parallel discovery + validate_env delegation) + I9 monorepo signal from AGENT-1 + Vitest config template from AGENT-3 + union of 21 token transforms.

Spec-reviewer iter 2 → PASS (1 BLOCK + 4 amendments + 3 WARN from iter 1 all resolved).

See: `docs/plans/2026-05-28-code-coverage-vitest-migration-design.md`.

## Changes

- New: `assets/vitest-jest-compat.json` (closed signal list, 21 token rewrites, config key map)
- New: `scripts/detect_jest_incompat.py` (deterministic signal evaluator)
- New: `scripts/migrate_jest_to_vitest.py` (atomic Phase 4b migration engine)
- New: `references/phase-4b-migration.md` (conditional reference)
- Patch: `SKILL.md` Phase 2 + Phase 4b + Principles 1+4 + HARD READ POLICY
- Patch: `scripts/validate_env.py` (delegate to jest-compat.json)
- Patch: `lib/phase1-discover.sh` (parallel compat detection)
- Patch: `lib/state-schema.json` (schema additions: migrate, jest-compat, migration-report)
- 4 new test files, ≥30 new tests

## Test plan

- [ ] `pytest skills/code-coverage/scripts/tests/` green (existing 26 + new ≥30 = ≥56 tests)
- [ ] Archetype 2 regression test passes (legacy jest + ts-jest + jest in scripts → vitest-migrate, NOT jest)
- [ ] Archetype 3 (React Native) keeps Jest (I1 fires)
- [ ] Archetype 4 (monorepo) per-workspace decision verified
- [ ] Archetype 5 (overrides.json force_jest) → jest-forced
- [ ] Smoke test on a real project (manual, post-merge optional)

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Migration breaks real project | Snapshot + dirty-tree refuse + verify gate + rollback |
| Smoke test 120s slow CI | Opt-out env var |
| Codemod false positive on string literal | Manual review flag + verify gate catches |
| jest.requireActual sync→async | NO auto-rewrite, only flagged |
| Lockfile state inconsistency | Per-PM frozen-lockfile restore matrix |

## Out of scope

- Vitest 2.x/3.x targeting
- Babel preset translation
- CI YAML changes
- LSP/AST-based codemod

Co-Authored-By: SIAE DevForge
EOF
)"
```

## Acceptance

- [ ] Test suite green (≥56 test totali, no regression)
- [ ] Bash + JSON syntax check pass
- [ ] `grep constraints.json SKILL.md` = 0
- [ ] 6 commits atomici per layer
- [ ] PR aperta a main con summary completo + test plan + risks
- [ ] Reviewer assegnato (vedi `gh pr edit` se necessario)
