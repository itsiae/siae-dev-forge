# Code-Coverage Skill — Optimization v2 (Plan)

**Date:** 2026-05-21
**Branch:** feat/code-coverage-optimize-v2
**Source:** 3 expert audits (best-practice, runtime, full-stack) consolidated

## Goal

Reduce iterations / wall-time / token spend of `/code-coverage` without losing efficacy
(>=70% global, P1>=80%, P2>=70%, P3>=60%, zero user prompt, determinism).

## Target metrics (expected)

- LARGE repo run: from ~280-400k tok → ~180-220k tok (-35%)
- Round-trips: from 12-18 → 7-9
- Wall-time Phase 5 (T1=3 batch): from ~10 sequential turns → ~3 parallel turns

## Fix split across 3 parallel agents (disjoint file scope)

### Agent A — SKILL.md + references (no overlap with B/C)

| ID | Fix | Where | Severity |
|----|-----|-------|----------|
| A1 | `description` frontmatter trim (9 stack → concise) | `SKILL.md:3-10` | HIGH (token persist) |
| A2 | Hard READ POLICY anti-eager-load on references | `SKILL.md` add new block | HIGH |
| A3 | Inline `phase-2-strategy.md` + `phase-4-environment.md` content (<150 LOC each) into SKILL.md; delete the two refs | `SKILL.md` + delete refs | HIGH (cache prefix stability) |
| A4 | Explicit parallel-Write directive for batch generation | `references/phase-5-generation.md` + `SKILL.md` Principle 2 | HIGH |
| A5 | Note Phase 5b trigger moved to phase1-discover.sh (decision opaque to LLM) | `SKILL.md:60-64` | MEDIUM |

### Agent B — Python scripts (no overlap with A/C)

| ID | Fix | Where | Severity |
|----|-----|-------|----------|
| B1 | `parse_coverage.py --view repair` flag (returns aggregates only) | `scripts/parse_coverage.py` add CLI arg | HIGH |
| B2 | Fix glob→regex unanchored in `assign_priority_and_threshold` (use `last_2_segments` anchor like estimate_size.py) | `scripts/parse_coverage.py:395-451` | HIGH (breaking, version bump) |
| B3 | `parse_go_cover` correct line% from `coverage.out` (weighted by numStmt) | `scripts/parse_coverage.py:154-176` | MEDIUM (breaking, no longer over-reports) |
| B4 | `detect_monorepo` Maven reactor (`<modules>`) + Gradle (`settings.gradle[.kts]` include()) | `scripts/detect_stack.py:362-379` | HIGH (unblocks Java repos) |

### Agent C — templates + categorize + phase1 + cache (no overlap with A/B)

| ID | Fix | Where | Severity |
|----|-----|-------|----------|
| C1 | Template import variants: split `vitest.template.ts`, `junit5.template.java`, `pytest.template.py` into NO_DEPS / SINGLE_DEP / MULTI_DEPS (3 files each) OR add conditional placeholder removal logic | `templates/*.template.*`, `lib/template-cache.sh` (selector logic) | HIGH (broken syntax on single-export SUTs) |
| C2 | `categorize_failure.py` normalize uses first 3 non-empty lines (not just line-1) | `scripts/categorize_failure.py:43-55` | MEDIUM |
| C3 | Move Phase 5b probe decision INSIDE `phase1-discover.sh` (idempotent: skip if coverage-report.json exists; trigger only if test_files_count > 0 AND module_coverage == []) | `lib/phase1-discover.sh`, `lib/phase6-coverage.sh` | MEDIUM |
| C4 | `decisions.log` truncate on `init_workdir` if previous run completed (archive to .archive); emit `discovery-summary.json` (~2k tok) consumable by LLM | `lib/cache-helper.sh` | LOW |

## Out of scope for this PR

- Sub-agent dispatch for VERY_LARGE (RT-F6) — conditional optimization, deferred.
- Missing frameworks (Mocha, TestNG, Bun, Clover XML, lcov BRDA) — separate PR.
- Phase 7 reduce to 2 iter (FS-6) — needs empirical validation first.
- Bazel `MODULE.bazel` / `WORKSPACE` monorepo detection (B4 follow-up) — deferred: Maven + Gradle cover the dominant SIAE Java repos (10+ multi-module). Bazel is rare in the org footprint; add when first Bazel repo lands.

## Risk + mitigation

- **B2 (glob anchor)** + **B3 (parse_go_cover)** are BREAKING: priority assignment + go coverage% will change. Mitigation: bump `priority-rules.json.version`, document in CHANGELOG as "coverage report semantics fix".
- **A3 (inline ref)** loses progressive disclosure of medium-sized refs. Mitigation: SKILL.md grows ~150 LOC but cache prefix stable; gate `if SKILL.md > 350 LOC → split again`.
- **C1 (template variants)** refactors `template-cache.sh` case statement. Mitigation: existing tests `scripts/tests/*` must pass; smoke test on this repo.

## Verification protocol

1. `pytest skills/code-coverage/scripts/tests/` — all green
2. Smoke: `bash skills/code-coverage/lib/phase1-discover.sh /tmp/test-repo` — produces stack.json + size.json + env.json (+ discovery-summary.json with C4)
3. Manual: load SKILL.md and count tokens (≤ original)
4. `git status --porcelain` pre-commit MUST show only files within each agent's claimed scope
