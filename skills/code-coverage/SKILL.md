---
name: code-coverage
description: >
  Enterprise test generation agent invoked via /code-coverage. Analyzes a repository,
  infers tech stack, and generates deterministic unit tests targeting >=70% coverage.
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

## HARD READ POLICY (CONTEXT BUDGET)

DO NOT read `references/phase-*.md` before reaching the corresponding phase.
Combined refs after A3 inline = phase-3-sizing.md (~150 LOC) + phase-5-generation.md (~250 LOC) + phase-7-repair.md (~120 LOC) ≈ 520 LOC / ~6 KB.
Reading any ref out-of-phase is a context budget violation. Each ref MUST be read AT phase entry, never as preamble.

## GLOBAL EXECUTION PRINCIPLES (7)

1. **Autonomous execution.** Invocation = blanket approval for read/write/install in `.code-coverage/`, test dirs, `vitest.config.ts`/`jest.config.ts` if absent, and `devDependencies`. Never modify production source. Decisions → `.code-coverage/decisions.log`. ZERO prompts.
2. **Context-safety over completeness.** Batch sizes per tier (T1=3, T2=2, T3=1, T4=1 — `assets/priority-rules.json.ordering_constants`). LARGE/VERY_LARGE → persist `batch-plan.json`, resume cross-session. Batch tool calls (Write) MUST execute parallel in same assistant turn — see Phase 5 batch rule.
3. **Determinism over creativity.** `assets/stack-matrix.json` is the single source of truth for framework selection.
4. **Vitest-first for JS/TS** (decision tree inlined in Phase 2 below). Deviate to Jest only on documented constraints.
5. **Coverage targets per-priority; global floor 70%.** P1>=80%, P2>=70%, P3>=60%, global>=70% (`assets/priority-rules.json.min_coverage_pct`). P1 at 75% = FAIL. Repair max 3 iter; best-effort if exhausted.
6. **Progressive disclosure.** Load `references/phase-N.md` only on entry to phase N. Phase-1/6 are bash libs (`lib/phase{1,6}-*.sh`); Phase-2/4 are inlined here; Phase-3/5/7 are refs.
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
Gates: `stack.json.pre_existing_coverage_pct >= user_target_line` → Block 8 (coverage already sufficient) + END; `env.json.required_framework == "unknown"` → Block 4 + END.

### Phase 2 — Strategy

Single source: `assets/stack-matrix.json`. Output: `framework_by_workspace` (in-memory + `.code-coverage/strategy.json`), plus `[phase2] workspace=<path> stack=<lang> framework=<fw> reason=...` in `decisions.log`.

**Vitest-first decision tree (JS/TS per workspace):**
1. `jest.config.{ts,js,mjs,cjs}` exists → `jest` (reason `jest-config-present`).
2. Else `package.json.scripts.test` mentions `jest` AND `vitest` not in devDeps → `jest` (reason `jest-script-no-vitest`).
3. Else `constraints.json` lists CJS incompatibility → `jest` (reason `cjs-constraint`).
4. Else `constraints.json` lists legacy-jest → `jest` (reason `legacy-constraint`).
5. Else → `vitest` (reason `vitest-first-default`).

Other stacks (Python/Java/Kotlin/Go/Rust/C#/Flutter) → direct lookup in `assets/stack-matrix.json` for `framework`, `coverage_command`, `report_format`. No heuristics beyond the matrix.

**Lambda variant (JS/TS):** if `stack.json.is_lambda == true`, files matching `priority-rules.json.lambda_handler_globs` (default `*handler.ts`, `*lambda.ts`) → template `vitest-lambda-handler`; others → standard `vitest`.

**Monorepo:** iterate `stack.json.workspaces[]`, apply tree per workspace. Workspaces with `framework == "unknown"` are logged as `skipped reason=unsupported-language` and listed in Block 4.

**Gate:** if ALL workspaces resolve to `unknown` → emit Block 4 + END.

### Phase 3 — Sizing (REF if LARGE/VERY_LARGE)
If `size.json.class IN ("LARGE","VERY_LARGE")` → emit phased-mode notice, run `python3 skills/code-coverage/scripts/plan_batches.py <repo> > <repo>/.code-coverage/batch-plan.json`, load `references/phase-3-sizing.md`.

### Phase 4 — Environment

**[Loader]** If `stack.json.language == "java"` (or Maven build system detected), read `references/java-siae-quirks.md` now and apply all applicable quirks for the remainder of this session.

Read `.code-coverage/env.json`. For each framework with `installed: false` and non-null command in `assets/install-snippets.json`:
1. Snapshot lockfile (`package-lock.json` / `yarn.lock` / `pnpm-lock.yaml` / `poetry.lock`) → `.code-coverage/lockfile.bak`.
2. Run `install-snippets.json[<framework>].command` (or `alt_yarn`/`alt_pnpm`/`alt_poetry` matching detected PM).
3. Exit != 0 → restore lockfile, append error to `.code-coverage/install-log.txt`, emit Block 4 "framework install failed" + END.
4. Exit == 0 → log to `decisions.log` and proceed.

Frameworks with `command: null` (junit5/junit5-gradle/mockk/cargo-test/flutter_test): read `manual_manifest_edit`, apply autonomously to `pom.xml`/`build.gradle`/`Cargo.toml`/`pubspec.yaml`, then run verification (e.g., `mvn dependency:resolve`, timeout 30s).

**Vitest config generation:** only if `vitest.config.ts` ABSENT and framework=vitest. Generate skeleton with `environment` (`jsdom` for FE, `node` for backend), `coverage.provider: 'v8'`, `reporter: ['text','json-summary']`. Never overwrite existing config. Log decision.

**Blocking Check Handler:** if `env.json.missing` includes essential runtime (Node/Python/Java/Go/Rust/Dotnet/Flutter) → emit `ENVIRONMENT BLOCKER` block with runtime-specific install hint + STOP. Do not continue without runtime.

**TIMEOUT handling:** `env.json.available[i].reason == "TIMEOUT"` → log warning, do NOT block; treat as "available but slow"; subsequent installs use 60s timeout (JVM/Flutter default 30s per `validate_env.py`).

Output: `.code-coverage/install-log.txt`, `.code-coverage/lockfile.bak`, `decisions.log` updated.

### Phase 5b — Coverage Probe (handled in Phase 1)

Triggered automatically by `phase1-discover.sh` when `test_files_count > 0` AND `module_coverage == []`. Produces `.code-coverage/coverage-report.json` so D1 fires TIER-FIRST in Phase 5. No LLM action required.

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

## Java/Maven/SIAE quirks (progressive disclosure)

> **Java/Maven users**: stack-specific quirks loaded from
> `references/java-siae-quirks.md` at Phase 4 entry (progressive disclosure).
> Covers multi-module aggregator detection, Maven placeholders, JDK/Lombok
> compatibility matrix, Surefire includes/excludes, Jacoco-skipped modules,
> entity setter detection, Java source-level matrix, mvn invocation strategy,
> and assertion library rationale.

## Assertion library — NO auto-add deps

**Principle:** Never add assertion library deps automatically. Skill detects
``assertion_lib`` from the pom and selects the matching template (AssertJ or
JUnit5 vanilla) — it does NOT modify the pom to add AssertJ. Rationale and
detection scope are in `references/java-siae-quirks.md`.

## Coverage target — forced choice + estime (Task 10)

L'utente sceglie esplicitamente il target di coverage (40% quick-win vs 70% full) con stima upfront del wall-clock attesa basata su sizing + adjusters.

### Sizing repo (Phase 2.1)

`scripts/estimate_effort.py` classifica:

| size_class | LoC main | classi Java |
|---|---|---|
| small  | <5k | <50 |
| medium | 5k-30k | 50-300 |
| large  | >30k | >300 |

### Stime baseline (wall-clock minutes)

| size | target 40% p50 | p90 | target 70% p50 | p90 |
|---|---|---|---|---|
| small  | 10 | 20 | 25  | 45  |
| medium | 20 | 40 | 60  | 100 |
| large  | 45 | 90 | 150 | 240 |

### Adjusters moltiplicativi

| Condizione | Multiplier | Rilevazione |
|---|---|---|
| Source <10 (legacy-java) | ×1.30 | Task 07 |
| Lombok/JDK HARD-WARN | ×1.20 | Task 03 |
| Spring Boot detected | ×1.25 | Task 09 |
| AssertJ assente | ×1.05 | Task 04 |
| Cache .code-coverage valida (<7d) | ×0.85 | timestamp |

### Sentinel handshake (operativo)

Helper `lib/sentinel-handshake.sh` standardizza il consumer pattern:

```bash
# 1. estimate_effort.py emette .code-coverage/pending-user-choice.json + (opzionale exit 3)
python3 scripts/estimate_effort.py <repo>

# 2. Consumer (Claude main loop o bash chain) legge il sentinel in formato key=value
bash skills/code-coverage/lib/sentinel-handshake.sh read <repo>
# Output: type=forced_choice_coverage_target
#         option_a_target_line=40
#         option_a_p50_min=25
#         option_b_target_line=70
#         option_b_p50_min=98
#         ...

# 3. Consumer prompt user (AskUserQuestion lato LLM, o terminal lato bash) → ottiene scelta

# 4. Scrive user-choice.json con la scelta
bash skills/code-coverage/lib/sentinel-handshake.sh write <repo> 40
# Scrive user-choice.json con target_line=40, target_branch=30, p50/p90 dalla sentinel, timestamp
```

Lo script accetta target_line come intero in `[1, 95]` (invalid → exit 1). I preset `40` (quick-win) e `70` (full-bundle) usano `target_branch` fisso (30, 60); per i custom `target_branch = max(1, N - 10)`.

### Interactive prompt

```bash
bash skills/code-coverage/lib/sentinel-handshake.sh prompt <repo>
# Mostra 3 opzioni:
#   1) Quick Win   — 40% line / 30% branch
#   2) Full Bundle — 70% line / 60% branch
#   3) Custom      — enter your own line target (1–95)
# Esporta TARGET_LINE/TARGET_BRANCH e scrive user-choice.json.
```

### CLI bypass (non-interactive)

```bash
python3 scripts/estimate_effort.py <repo> --target=40   # preset quick-win
python3 scripts/estimate_effort.py <repo> --target=70   # preset full-bundle
python3 scripts/estimate_effort.py <repo> --target=55   # custom
# Scrive direttamente user-choice.json, NO sentinel
```

Utile per CI, test automation, run preferenze stabili.

## SUPPORTING FILES

See `references/index.md` for the full map of lib/, scripts/, assets/, templates/, and references/.
