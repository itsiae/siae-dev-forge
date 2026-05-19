---
name: code-coverage
description: >
  Enterprise test generation agent invoked via /code-coverage. Analyzes a repository,
  infers the tech stack (JavaScript/TypeScript via Vitest or Jest, React/Vue/Angular
  components, Python pytest + PySpark/chispa, Java JUnit5 with JaCoCo, Kotlin JUnit5
  with Kover/MockK, Go testing, Rust cargo with tarpaulin or llvm-cov, C# xUnit with
  coverlet, Flutter/Dart flutter_test, Ruby RSpec, PHP PHPUnit), defines the optimal
  unit testing strategy, and generates deterministic tests targeting >=70% coverage.
  Zero user runtime interactions.
---

# Enterprise Test Generation Agent

**Activates ONLY when the user explicitly types `/code-coverage`. Do not self-activate.**

## INPUT MODE — Deterministic, autonomous

- No args → use `$(pwd)`. Absolute local path → use it. GitHub URL → auto-clone:
  ```bash
  AUTO_CLONE_DIR=$(mktemp -d); trap 'rm -rf "$AUTO_CLONE_DIR"' EXIT
  git clone --depth 1 --branch "${BRANCH:-main}" "$GITHUB_URL" "$AUTO_CLONE_DIR"
  ```
- Malformed URL OR missing path → single error + STOP. NEVER ask user.

## GLOBAL EXECUTION PRINCIPLES (7)

1. **Autonomous execution.** Invocation = blanket approval for read/write/install in `.code-coverage/`, test dirs, `vitest.config.ts`/`jest.config.ts` if absent, and `devDependencies`. Never modify production source. Decisions → `.code-coverage/decisions.log`. ZERO prompts.
2. **Context-safety over completeness.** Batch sizes per tier (T1=3, T2=2, T3=1, T4=1 — `assets/priority-rules.json.ordering_constants`). LARGE/VERY_LARGE → persist `batch-plan.json`, resume cross-session.
3. **Determinism over creativity.** `assets/stack-matrix.json` is the single source of truth for framework selection.
4. **Vitest-first for JS/TS** (decision tree in `references/phase-2-strategy.md`). Deviate to Jest only on documented constraints.
5. **Coverage targets per-priority; global floor 70%.** P1>=80%, P2>=70%, P3>=60%, global>=70% (`assets/priority-rules.json.min_coverage_pct`). P1 at 75% = FAIL. Repair max 3 iter; best-effort if exhausted.
6. **Progressive disclosure.** Load `references/phase-N.md` only on entry to phase N. Phase-1/6 are bash libs (`lib/phase{1,6}-*.sh`); Phase-2/3/4/5/7 are refs.
7. **State persistence + cache.** Outputs in `.code-coverage/`. `stack.json`/`size.json`/`env.json` cached vs manifest mtime. Templates cached via `lib/template-cache.sh`. Schema: `lib/state-schema.json`.

## WORKFLOW

### Phase 0 — Init
```bash
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 required" >&2; exit 1; }
source skills/code-coverage/lib/cache-helper.sh
init_workdir "<repo>"
```

### Phase 1 — Discovery
```bash
bash skills/code-coverage/lib/phase1-discover.sh "<repo>"
```
Gates: `stack.json.pre_existing_coverage_pct >= 70` → Block 8 + END; `env.json.required_framework == "unknown"` → Block 4 + END.

### Phase 2 — Strategy
See `references/phase-2-strategy.md`. Output: `framework_by_workspace` logged.

### Phase 3 — Sizing (REF if LARGE/VERY_LARGE)
If `size.json.class IN ("LARGE","VERY_LARGE")` → emit phased-mode notice, run `python3 skills/code-coverage/scripts/plan_batches.py <repo> > <repo>/.code-coverage/batch-plan.json`, load `references/phase-3-sizing.md`.

### Phase 4 — Environment
Load `references/phase-4-environment.md`. Auto-install via `validate_env.py install_commands` + `assets/install-snippets.json`. Snapshot lockfile pre-install (`.code-coverage/lockfile.bak`); rollback on non-zero exit.

### Phase 5b — Coverage Probe (conditional)
**Trigger:** `stack.existing_test_frameworks != []` AND `stack.module_coverage == []`.
```bash
bash skills/code-coverage/lib/phase6-coverage.sh "<repo>"   # PROBE — populates coverage-report.json so D1 fires TIER-FIRST in Phase 5.
```

### Phase 5 — Generation
Load `references/phase-5-generation.md`. **Step 0 hard gate (PRESERVE_EXISTING)** + `bash lib/placeholder-check.sh <file>` before every write. Template hard-cache via `lib/template-cache.sh`. Ordering (D1 conditional TIER-FIRST vs P-TIER) + P1 floor enforcement in the ref. Lazy-load `assets/few-shot-e2e.md` (first batch) and `assets/anti-patterns.md` (on any fail).

### Phase 6 — Coverage
```bash
bash skills/code-coverage/lib/phase6-coverage.sh "<repo>"
```
If all P1>=80%, P2>=70%, P3>=60%, global>=70% → SKIP Phase 7 → OUTPUT.

### Phase 7 — Repair
See `references/phase-7-repair.md` (categorize → group → systemic-fix vs per-file → progress guard → autonomous early-abort). Max 3 iter, max 1 full coverage run/iter.

## OUTPUT — Conditional Blocks

Always emit Block 1 (Repository Summary: path, languages, size class, monorepo), Block 5 (Generated Test Files table: Path | Module | Tier | Priority | Coverage gain), Block 8 (Coverage Report Summary: Module | Lines% | Branch% | Threshold | Status; + Stalled Files if Phase 7 non-convergent).

Conditional (programmatic, NEVER prompt):
- Block 4 (`unsupported_groups`): only if non-empty.
- Block 6 (`Dependency Install Commands`): only if `validate_env.py.install_commands` non-empty.
- Block 9 (`Next Actions`): if any module sub-threshold OR follow-up batch active OR PRESERVE_EXISTING entries OR manual tests suggested.

## SUPPORTING FILES

See `references/index.md` for the full map of lib/, scripts/, assets/, templates/, and references/.
