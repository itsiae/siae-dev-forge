# Supporting Files Index

Quick map di tutti i file della skill `code-coverage`. Una entry per ciascuno
script/asset/lib/template citato in `SKILL.md`.

## References (phase docs, lazy-loaded)

| Path | Phase | Purpose |
|------|-------|---------|
| `references/phase-3-sizing.md` | 3 | Batch plan resume protocol per LARGE/VERY_LARGE |
| `references/phase-5-generation.md` | 5 | Pre-write gate, ordering tree, AAA pattern, batch ceilings, few-shot trigger |
| `references/phase-7-repair.md` | 7 | Categorize → group → fix → progress guard → early-abort |

> Phase 2 (Strategy) and Phase 4 (Environment) are inlined in `SKILL.md` — small enough that a ref round-trip was net-negative.

## Lib (bash helpers)

| Path | Purpose |
|------|---------|
| `lib/cache-helper.sh` | Bash utils: cache mtime check, ensure_gitignore, init_workdir, log_decision |
| `lib/phase1-discover.sh` | Parallel discovery runner (stack/size/env), fail-fast |
| `lib/phase6-coverage.sh` | Coverage run + parse, hardened (no eval, no jq) |
| `lib/placeholder-check.sh` | Hard gate `{{X}}` placeholder pre-write |
| `lib/template-cache.sh` | Hard-cache template per framework in `.code-coverage/_templates/` |
| `lib/state-schema.json` | Schema documenting all `.code-coverage/*` files |

## Assets (single sources of truth)

| Path | Purpose |
|------|---------|
| `assets/stack-matrix.json` | **Single source**: stack → framework + coverage_command + report_format |
| `assets/priority-rules.json` | P1/P2/P3 + ordering_constants + skip patterns + lambda globs |
| `assets/install-snippets.json` | **Single source**: install commands per framework |
| `assets/repair-strategies.json` | **Single source**: error patterns → category + fix steps |
| `assets/few-shot-e2e.md` | Lazy-load: T1 example with grep + AAA test (Phase 5 first batch) |
| `assets/anti-patterns.md` | Lazy-load: 3 BAD/GOOD pairs (Phase 5/7 fail >= 1) |

## Scripts (Python)

| Path | Purpose |
|------|---------|
| `scripts/detect_stack.py` | Stack detection JSON (+ test_infrastructure, module_coverage, coverage_exclude) |
| `scripts/estimate_size.py` | Size + file_list + priority_score JSON |
| `scripts/validate_env.py` | Env + framework_check + install_commands JSON |
| `scripts/parse_coverage.py` | Coverage report parsing per 8 framework |
| `scripts/categorize_failure.py` | Failure categorization Cat 1-6 + normalize() |
| `scripts/plan_batches.py` | Batch plan ordering (tier-first conditional) |
| `scripts/select_command.py` | Risolve framework→stack + selezione build-system/OS → cov_cmd/report_path/format |

## Templates

| Path | Purpose |
|------|---------|
| `templates/*.template.*` | Test skeletons per framework (with rationale paragraph) |
