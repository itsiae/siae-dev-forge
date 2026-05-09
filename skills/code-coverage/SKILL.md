---
name: code-coverage
description: >
  Enterprise test generation agent invoked via /code-coverage. Analyzes a repository,
  infers the tech stack, defines the optimal unit testing strategy, and generates
  deterministic tests targeting >=70% coverage. Zero user runtime interactions.
---

# Enterprise Test Generation Agent

**This skill activates ONLY when the user explicitly types `/code-coverage`. Do not self-activate.**

---

## INPUT MODE — Deterministic, autonomous

- No args → use `$(pwd)`.
- Local path absolute → use it.
- GitHub URL → auto-clone in `mktemp -d`. Default branch=`main` if omitted. Cleanup at session end.
- Malformed URL OR missing path → emit single error message and STOP.

NEVER ask user. Skill is fully autonomous.

---

## GLOBAL EXECUTION PRINCIPLES (7)

1. **Autonomous Execution Policy.** Invocation = blanket approval for read/write/install in: (a) `.code-coverage/` workdir, (b) test directories, (c) `vitest.config.ts`/`jest.config.ts` if absent, (d) `devDependencies` install. Never modify production source. Decisions logged to `.code-coverage/decisions.log`. ZERO user prompts.
2. **Context-safety over completeness.** Load files in batches sized per tier (T1=3, T2=2, T3=1, T4=1 — see `assets/priority-rules.json` `ordering_constants`). For LARGE/VERY_LARGE, persist `batch-plan.json` and process across sessions.
3. **Determinism over creativity.** `assets/stack-matrix.json` = single source of truth for framework selection. Identical input → identical output.
4. **Vitest-first for all JS/TS.** Vitest is unconditional default. Deviate to Jest only when (in this order): (a) `jest.config.{ts,js,mjs,cjs}` exists, (b) `package.json scripts.test` contains `"jest"` AND `vitest` not in devDeps, (c) Vitest CJS-incompatibility documented in `.code-coverage/constraints.json`, (d) explicit legacy constraint in `.code-coverage/constraints.json`. **This rule is authoritative.**
5. **Coverage targets per-priority; global floor 70%.** `assets/priority-rules.json` `min_coverage_pct`: P1≥80%, P2≥70%, P3≥60%, global≥70%. P1 at 75% = FAIL even if global > 70%. Repair loop max 3 iter; emit best-effort if exhausted.
6. **Progressive disclosure.** Load `references/phase-N.md` only when entering phase N. Phase-1/2/6/7 are inlined here. Phase-3/4/5 are separate refs.
7. **State persistence + cache.** All structured outputs in `.code-coverage/`. Files `stack.json`, `size.json`, `env.json` cached vs `package.json`/`pom.xml`/etc. mtime. Templates loaded ONCE per (framework, session). Schema: `lib/state-schema.json`.

---

## WORKFLOW

### Phase 0 (init)

```bash
source skills/code-coverage/lib/cache-helper.sh
init_workdir <repo_path>  # crea .code-coverage/, ensure_gitignore, init decisions.log
```

### Phase 1 — Discovery (INLINE)

Run in parallel (skip if cache valid via `is_cache_valid`):
```bash
python3 skills/code-coverage/scripts/detect_stack.py <repo> > <repo>/.code-coverage/stack.json &
python3 skills/code-coverage/scripts/estimate_size.py <repo> --file-list --with-coverage <repo>/.code-coverage/coverage-report.json > <repo>/.code-coverage/size.json &
python3 skills/code-coverage/scripts/validate_env.py <repo> > <repo>/.code-coverage/env.json &
wait
```

If `stack.json.pre_existing_coverage_pct >= 70` → emit Block 8 with current value + END.

If `env.json.required_framework == "unknown"` → emit "Language not supported" Block 4 + END.

### Phase 2 — Strategy (INLINE)

Read `stack.json` + `assets/stack-matrix.json`. Apply Principle 4 Vitest-first decision tree. Output: framework + rationale logged to `decisions.log`.

### Phase 3 — Sizing (REF if LARGE/VERY_LARGE)

If `size.json.class IN ("LARGE", "VERY_LARGE")`:
- emit `Repository exceeds safe single-session capacity. Switching to phased enterprise mode.`
- Run `python3 skills/code-coverage/scripts/plan_batches.py <repo> > <repo>/.code-coverage/batch-plan.json`
- Load `references/phase-3-sizing.md` for batch resume protocol.

### Phase 4 — Environment (REF)

Load `references/phase-4-environment.md`. Auto-install via `validate_env.py install_commands` + `assets/install-snippets.json`. Snapshot lockfile pre-install (`.code-coverage/lockfile.bak`); rollback if exit-code ≠ 0.

### Phase 5 — Generation (REF)

Load `references/phase-5-generation.md`. Pre-write hard gate: `bash lib/placeholder-check.sh <file>` before EVERY write.

**Ordering rule (D1 conditional):**
```python
import json
stack = json.loads(open(".code-coverage/stack.json").read())
has_module_coverage = bool(stack.get("module_coverage"))
if has_module_coverage:
    sort_key = lambda f: (TIER_ORDER[f["tier"]], -f["priority_score"])  # TIER-FIRST
else:
    sort_key = lambda f: (PRIORITY_ORDER[f["priority"]], -f["loc"])  # P-TIER FALLBACK
```
Constants in `assets/priority-rules.json.ordering_constants`. Implementazione concreta in `scripts/plan_batches.py`.

**P1 floor enforcement**: post each iter, if `min(P1 modules lines_pct) < 80%` → force-include sub-threshold P1 files in next batch above any tier/priority order.

**Lazy-load assets** in Phase 5:
- Primo batch della session → carica `assets/few-shot-e2e.md` ONCE.
- Fail rate ≥ 1 nella session → carica `assets/anti-patterns.md` ONCE.

### Phase 6 — Coverage (INLINE)

```bash
FW=$(jq -r '.required_framework' .code-coverage/env.json)
COV_CMD=$(jq -r --arg fw "$FW" '.stacks[$fw].coverage_command // .stacks[].coverage_command' skills/code-coverage/assets/stack-matrix.json)
REPORT_PATH=$(jq -r --arg fw "$FW" '.stacks[$fw].coverage_report_path // .stacks[].coverage_report_path' skills/code-coverage/assets/stack-matrix.json)
cd <repo> && eval "$COV_CMD" 2>&1 | tee .code-coverage/coverage-stdout.log
FORMAT=$(jq -r --arg fw "$FW" '.stacks[$fw].coverage_report_format // .stacks[].coverage_report_format' skills/code-coverage/assets/stack-matrix.json)
python3 skills/code-coverage/scripts/parse_coverage.py "$FORMAT" "<repo>/$REPORT_PATH" > <repo>/.code-coverage/coverage-report.json
```

Read `coverage-report.json`. If all P1≥80%, P2≥70%, P3≥60%, global≥70% → SKIP Phase 7 → OUTPUT.

### Phase 7 — Repair (INLINE algorithm)

Budget: max 3 iter, max 1 full coverage run/iter. Categorize via `python3 scripts/categorize_failure.py < <stderr>`. Group by `error_signature`; if `count >= max(2, 30% failures)` AND categoria `systemic_eligible` → fix config-level UNA volta. Otherwise per-file scoped Edit (NO full-file regen). Re-run modified tests WITHOUT `--coverage`; full coverage UNA volta a fine iter.

Progress guard: if `Δglobal_coverage < 0.5pp AND Δfailing_count <= 0` → STOP best-effort.

Autonomous early-abort: if iter==1 AND `global_coverage < 30%` AND any `P1.lines_pct < 40%` → set `loop_max_remaining = 2` (1 retry only).

Best-effort report con tabella **Stalled Files** in OUTPUT Block 8 se max iter raggiunto.

---

## OUTPUT — Conditional Blocks

Always emit Block 1, 5, 8. Conditional (programmatic check, MAI prompt utente):
- Block 4 (`unsupported_groups`): only if non-empty array.
- Block 6 (`Dependency Install Commands`): only if `validate_env.py.install_commands` non-empty.
- Block 9 (`Next Actions`): only if any module sub-threshold OR follow-up batch active OR manual tests suggested.

### Block 1 — Repository Summary
- source path/URL, languages (from `stack.json`), size class (`size.json.class`), monorepo (`stack.json.monorepo`)

### Block 5 — Generated Test Files
| Path | Module under test | Tier | Priority | Estimated coverage gain |

### Block 8 — Coverage Report Summary
| Module | Lines% | Branch% | Threshold | Status |
+ Stalled Files sub-section if Phase 7 ran without convergence

---

## SUPPORTING FILES

| Path | Purpose |
|------|---------|
| `references/phase-3-sizing.md` | Batch plan resume protocol (LARGE/VERY_LARGE) |
| `references/phase-4-environment.md` | Auto-install policy + Blocking Check Handler |
| `references/phase-5-generation.md` | Ordering tree, AAA pattern, batch ceilings, few-shot trigger |
| `assets/stack-matrix.json` | **Single source**: stack → framework + coverage_command + report_format |
| `assets/priority-rules.json` | P1/P2/P3 + ordering_constants + skip patterns |
| `assets/install-snippets.json` | **Single source**: install commands per framework |
| `assets/repair-strategies.json` | **Single source**: error patterns → category + fix steps |
| `assets/few-shot-e2e.md` | Lazy-load: T1 example with grep + AAA test (Phase 5 first batch) |
| `assets/anti-patterns.md` | Lazy-load: 3 BAD/GOOD pairs (Phase 5/7 fail ≥1) |
| `scripts/detect_stack.py` | Stack detection JSON (+ test_infrastructure, module_coverage, coverage_exclude) |
| `scripts/estimate_size.py` | Size + file_list + priority_score JSON |
| `scripts/validate_env.py` | Env + framework_check + install_commands JSON |
| `scripts/parse_coverage.py` | Coverage report parsing per 8 framework |
| `scripts/categorize_failure.py` | Failure categorization Cat 1-6 + normalize() |
| `scripts/plan_batches.py` | Batch plan ordering (tier-first conditional) |
| `lib/cache-helper.sh` | Bash utils: cache mtime check, ensure_gitignore, init_workdir, log_decision |
| `lib/placeholder-check.sh` | Hard gate `{{X}}` placeholder pre-write |
| `lib/state-schema.json` | Schema documenting all `.code-coverage/*` files |
| `templates/*.template.*` | Test skeletons per framework (with rationale paragraph) |
