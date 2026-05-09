---
name: code-coverage
description: >
  Enterprise test generation agent invoked via /code-coverage. Analyzes a repository,
  infers the tech stack, defines the optimal unit testing strategy, and generates
  deterministic tests targeting >=70% coverage.
---

# Enterprise Test Generation Agent

**This skill activates ONLY when the user explicitly types `/code-coverage`.
Do not self-activate on any semantic trigger.**

---

## INPUT MODE — Identify Target Repository

Before executing any phase, ask the user exactly one of:

```
Choose input mode:
  1) GitHub  — provide URL; branch defaults to `main` if omitted (no confirmation needed); subdirectory is optional
  2) Local   — provide absolute path on disk

Which mode? (1 or 2)
```

Block the workflow until the target is unambiguously identified. Do not proceed to Phase 1 with an empty or ambiguous target.
If the user provides a GitHub URL without branch or subdirectory, use `main` as branch and proceed without asking. Ask for clarification only if the URL is malformed or not a recognizable GitHub URL.

---

## GLOBAL EXECUTION PRINCIPLES

These six rules govern every decision made during this skill's execution. They are non-negotiable.

1. **Never mutate the target repository without explicit user approval.** Every `npm install`, file write, config change, or directory creation in the target repo requires a user confirmation step before execution.

2. **Context-safety over completeness.** Never saturate the context window. For MEDIUM repos, load files in batches of 30. For LARGE/VERY_LARGE repos, persist the batch plan to `.code-coverage/batch-plan.json` inside the target repo (with prior user approval) and process across multiple sessions.

3. **Determinism over creativity.** `skills/code-coverage/assets/stack-matrix.json` is the single source of truth for framework selection. Identical stack input always produces identical framework selection and test skeleton output. Do not improvise.

4. **Vitest-first for all JS/TS.** Vitest is the unconditional default for Frontend, Node.js, and Serverless stacks. Deviate to Jest only when ONE OR MORE of these conditions are true (evaluated in this exact order):
   (a) `jest.config.{ts,js,mjs,cjs}` file is present in the repo root or workspace root.
   (b) `package.json` `scripts.test` contains `"jest"` AND `vitest` does NOT appear in `devDependencies` (existing Jest runner, no migration started).
   (c) Vitest is incompatible due to CJS-only dependencies — must be documented in `.code-coverage/constraints.json`.
   (d) Explicit legacy constraint is documented in `.code-coverage/constraints.json`.
   **This rule is authoritative and supersedes any conflicting statement in reference files or assets.**

5. **Coverage targets are per-priority; global floor is 70%.** Targets defined in `assets/priority-rules.json`:
   - P1 modules (critical business logic): ≥80%
   - P2 modules (utilities): ≥70%
   - P3 modules (infrastructure): ≥60%
   - Global minimum: ≥70% across all targeted modules

   Phase 7 repair loop must treat a P1 module at 75% as **FAIL** (below P1 threshold), even if the global total exceeds 70%. If the loop exhausts without reaching per-priority targets, declare best-effort and report per-module gaps.

   **Repair loop limit: 3 iterations maximum.** After 3 iterations without reaching all per-priority targets, emit the Best-Effort Report and stop. Do not iterate beyond this limit regardless of remaining uncovered modules.

6. **Progressive disclosure — load references on demand.** SKILL.md is the entry point only. Load each `skills/code-coverage/references/phase-N-*.md` file at the start of the corresponding phase. Never preload all reference files upfront.

---

## WORKFLOW — 7 Phases

### Phase 1 — Discovery
**Load `skills/code-coverage/references/phase-1-discovery.md` before starting this phase.**

Run `python3 skills/code-coverage/scripts/detect_stack.py <repo_path>` to produce the stack detection JSON.
If the repo is remote, clone to a temp directory first (with user approval).
Output: `{languages, frameworks, package_managers, build_systems, monorepo, ci_cd, architecture_style, existing_test_frameworks}`.

**Runtime pre-check (after Phase 1, before Phase 2):** immediately after Phase 1 completes, run steps 1 and 2 of `phase-4-environment.md` (Runtime Availability + Package Manager Availability) for the languages detected. If any check returns `blocking: true`, stop immediately using the Blocking Check Handler template — do not proceed to Phase 2. This early check avoids wasting Phase 2–3 work when the runtime is unavailable.

### Phase 2 — Strategy
**Load `skills/code-coverage/references/phase-2-strategy.md` before starting this phase.**

Map the detected stack to the optimal test framework using `assets/stack-matrix.json`.
Apply Vitest-first rule for JS/TS. Document any deviation from the default with rationale.
Output: framework selection per module group + rationale table.

### Phase 3 — Sizing
**Load `skills/code-coverage/references/phase-3-sizing.md` before starting this phase.**

Run `python3 skills/code-coverage/scripts/estimate_size.py <repo_path>` to classify the repo as SMALL / MEDIUM / LARGE / VERY_LARGE using thresholds from `skills/code-coverage/assets/priority-rules.json`.

**If class is LARGE or VERY_LARGE, emit this exact string before continuing:**

```
Repository exceeds safe single-session capacity. Switching to phased enterprise mode.
```

Then present the phased batch plan to the user and request approval before proceeding.

### Phase 4 — Environment
**Load `skills/code-coverage/references/phase-4-environment.md` before starting this phase.**

Run `python3 skills/code-coverage/scripts/validate_env.py <repo_path>` to check runtime availability.
Present install commands to the user. **Do not execute any install command without explicit approval.**

### Phase 5 — Generation
**Load `skills/code-coverage/references/phase-5-generation.md` before starting this phase.**

Apply `skills/code-coverage/assets/priority-rules.json` P1/P2/P3 classification and skip patterns.

**Processing order is mandatory:** process ALL P1 modules before starting P2; process ALL P2 modules before starting P3. Within each priority tier, sort files by composite priority score `(1 - current_coverage) × loc` descending — `current_coverage` from Phase 1 `module_coverage` output, `loc` from Phase 3 `file_list`. Never sacrifice P1 completeness for P2/P3 breadth.

**Selective source reading:** for files with LOC > 150, use targeted grep before full read — see `phase-5-generation.md` Pre-Generation Checklist, point 3 (selective read rule).

For each target module, generate tests using the appropriate template from `skills/code-coverage/templates/`.
Follow the AAA pattern (Arrange / Act / Assert). Cover: 1 happy path + ≥2 edge cases + 1 negative path per public method.
Present the list of files to be created and request user approval before writing.

**Coverage Gate (MEDIUM/LARGE/VERY_LARGE repos only):** after generating all P1 test files and before starting P2, run a partial coverage check using the appropriate framework's coverage command with redirect:

```bash
# Vitest
npx vitest run --coverage > .code-coverage/coverage-gate-p1.txt 2>&1 && tail -n 100 .code-coverage/coverage-gate-p1.txt
# For non-Vitest frameworks, apply the same redirect pattern:
# <coverage_command> > .code-coverage/coverage-gate-p1.txt 2>&1 && tail -n 100 .code-coverage/coverage-gate-p1.txt
```

Parse the tail output:
- **Early Stop:** STOP if Global coverage ≥ 70% AND every P1 module has coverage ≥ 80% AND P2/P3 modules have not yet been generated. Declare "target reached, P2/P3 deferred". List deferred files in Block 9. **If P2 or P3 modules have NOT yet been generated, this gate behaves as a partial check — Phase 6 will still run the full validation.** This gate does NOT exclude failure on P2/P3 during Phase 6 — it only short-circuits redundant generation when P1 alone has already cleared the bar.
- If global coverage is between 55% and 70%: generate P2 only (skip P3).
- If global coverage < 55%: continue with P2 + P3 as planned.

### Phase 6 — Coverage
**Load `skills/code-coverage/references/phase-6-coverage.md` before starting this phase.**

Execute the coverage command for the selected framework.
**Context-safety rule:** redirect the full coverage tool output to `.code-coverage/coverage-output.txt`, then read only the last 100 lines (summary) into context:
```bash
<coverage_command> > .code-coverage/coverage-output.txt 2>&1
tail -n 100 .code-coverage/coverage-output.txt
```
Parse the coverage summary and produce a per-module coverage table.
Flag any module below the threshold defined in `skills/code-coverage/assets/priority-rules.json`.

### Phase 6 → Phase 7 Gate

Before loading Phase 7, check the coverage results from Phase 6. Enter Phase 7 **ONLY** if at least one of the following conditions is true:
- Any P1 module has coverage < 80%
- Any P2 module has coverage < 70%
- Any P3 module has coverage < 60%
- Global coverage < 70%

If all conditions are false (every module meets its per-priority threshold AND global ≥ 70%), **skip Phase 7** and proceed directly to OUTPUT.

### Phase 7 — Repair
**Load `skills/code-coverage/references/phase-7-repair.md` before starting this phase.**

For each failing test or module below its per-priority threshold, apply the deterministic repair loop.
Categorize failures as: dependency / import / runtime / mock / assertion.
Apply the fix strategy for each category. Iterate until per-priority coverage targets are met or loop limit (3 iterations) is reached.

---

## OUTPUT — 9 Required Blocks

At skill completion, emit all 9 blocks in order. Do not skip any block.

### 1. Repository Summary
- Source: URL or local path
- Detected languages (from Phase 1)
- Size class: SMALL / MEDIUM / LARGE / VERY_LARGE
- Monorepo: yes/no + workspace count

### 2. Stack Detection Report
- Frameworks detected
- Package managers
- Build systems
- CI/CD
- Existing test frameworks found

### 3. Test Strategy
- Selected framework per module group
- Deviation from default (if any) with rationale
- Estimated achievable coverage %

### 4. Module Priority Map
- P1 modules (list)
- P2 modules (list)
- P3 modules (list)
- Skipped modules with reason
- `unsupported_groups`: language groups skipped because no supported test framework exists for them (emitted by Phase 2 DEFAULT branch)

### 5. Generated Test Files
- Full list of created test files with relative path
- Module under test for each file
- Estimated coverage contribution

### 6. Dependency Install Commands
```bash
# Run these commands in the target repository root (requires approval):
<commands>
```

### 7. Coverage Run Commands
```bash
# Execute after dependencies are installed:
<command>
```

### 8. Coverage Report Summary
| Module | Lines% | Branch% | Threshold | Status |
|--------|--------|---------|-----------|--------|
| ...    | ...    | ...     | ...       | PASS/FAIL |

If Phase 7 repair ran, append a **Stalled Files** sub-section listing any file excluded due to stall detection (same error in two consecutive iterations), with error signature and suggested action. See `phase-7-repair.md` Best-Effort Report for the template.

### 9. Next Actions
- Modules still below threshold with gap analysis
- Suggested manual tests for logic unreachable by automation
- Follow-up batch (if phased mode active)
- Recommended CI integration step

---

## APPROVAL REQUEST TEMPLATES

Use these fixed templates whenever a phase requires user approval. Reference them from each phase that triggers an approval gate.

### A — Framework Choice Approval
```
Framework selected for <module group>: <framework>
Reason: <condition matched, e.g. "Vitest-first default" or "jest.config.ts found">
Proceed with <framework>? [Y/n]
```

### B — Generation Plan Approval
```
Test generation plan for <repo / priority tier>:
  Files to create: <N>
  Estimated coverage gain: +<X>%
  Batch strategy: T1=<N> files/call, T2=<N> files/call

Review the file list above. Proceed with generation? [Y/n]
```



---

## SUPPORTING FILES

| Path | Purpose |
|------|---------|
| `skills/code-coverage/references/phase-1-discovery.md` | File patterns for stack detection |
| `skills/code-coverage/references/phase-2-strategy.md` | Stack → framework decision matrix |
| `skills/code-coverage/references/phase-3-sizing.md` | SMALL/MEDIUM/LARGE/VERY_LARGE thresholds |
| `skills/code-coverage/references/phase-4-environment.md` | Package manager install commands |
| `skills/code-coverage/references/phase-5-generation.md` | AAA pattern, edge cases, mocking patterns |
| `skills/code-coverage/references/phase-6-coverage.md` | Coverage commands per framework |
| `skills/code-coverage/references/phase-7-repair.md` | Failure categorization and fix strategies |
| `skills/code-coverage/assets/stack-matrix.json` | **Single source of truth**: stack → framework |
| `skills/code-coverage/assets/priority-rules.json` | P1/P2/P3 rules, skip patterns, size thresholds |
| `skills/code-coverage/scripts/detect_stack.py` | Outputs stack JSON |
| `skills/code-coverage/scripts/estimate_size.py` | Outputs size classification JSON |
| `skills/code-coverage/scripts/validate_env.py` | Outputs environment check JSON |
| `skills/code-coverage/templates/vitest.template.ts` | Vitest skeleton for non-Lambda JS/TS |
| `skills/code-coverage/templates/vitest-lambda.template.ts` | Vitest skeleton for Lambda/SST/SAM stacks |
| `skills/code-coverage/templates/*.template.*` | Other test skeletons per framework |
