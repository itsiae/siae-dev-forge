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
Conditional refs (loaded ONLY if trigger fires — NOT in base budget):
- `references/phase-4b-migration.md` (~140 LOC): loaded SOLO se `strategy.json` contiene workspace con `migrate=true`.
- `references/java-siae-quirks.md` (~variable): loaded SOLO se Java/Maven detected (vedi Phase 4 loader).

Reading any ref out-of-phase is a context budget violation. Each ref MUST be read AT phase entry, never as preamble.

## GLOBAL EXECUTION PRINCIPLES (7)

1. **Autonomous execution.** Invocation = blanket approval for read/write/install in `.code-coverage/`, test dirs, `vitest.config.ts` (create if absent), `jest.config.*` (delete during Phase 4b migration with snapshot), `package.json` `scripts`/`devDependencies` keys only, and existing `*.{test,spec}.*` files for Jest→Vitest token transforms during Phase 4b. Never modify production source. Decisions → `.code-coverage/decisions.log`. ZERO prompts.
2. **Context-safety over completeness.** Batch sizes per tier (T1=3, T2=2, T3=1, T4=1 — `assets/priority-rules.json.ordering_constants`). LARGE/VERY_LARGE → persist `batch-plan.json`, resume cross-session. Batch tool calls (Write) MUST execute parallel in same assistant turn — see Phase 5 batch rule.
LARGE/VERY_LARGE con pending_batches >= 2, oppure MEDIUM con loc > 15000 e pending_batches >= 3
→ parallel multi-agent dispatch (fino a 4 subagent Sonnet, ognuno owner di batch disgiunti).
Trigger e protocollo in `references/phase-5-parallel.md`. Il coordinatore non legge i sorgenti: li leggono i subagent.
3. **Determinism over creativity.** `assets/stack-matrix.json` is the single source of truth for framework selection.
4. **Vitest-first for JS/TS, with auto-migration from Jest.** When the project uses Jest but Vitest is compatible (closed list of incompatibility signals I1..I10 in `assets/vitest-jest-compat.json`), Phase 4b migrates `jest.config.*`, `package.json` scripts/devDeps, and test files (codemod) to Vitest. Jest is retained ONLY when ≥1 signal in I1..I9 fires, or I10 user opt-out is active.
5. **Coverage targets line E branch separati.** Global floor 70% line. Branch target
   = `user-choice.json.target_branch` (può essere alzato da soglia CI, vedi Phase 2.5).
   Per file con `coverage_mode == branch-priority` (branch-heavy o branch lontana dal
   target) usa il template branch-matrix: la line non basta, conta la branch matrix.
   P1 floor ≥ 80% / P2 ≥ 70% / P3 ≥ 60% enforced (vedi phase-5-generation.md).
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
Gates:
- `stack.json.pre_existing_coverage_pct >= 70` (preset full-bundle default) → Block 8 "coverage already sufficient" + END. This is the early fast-exit before the user picks a target — uses the most ambitious preset as the gate so a project with very high pre-existing coverage skips the workflow without prompting.
- `env.json.required_framework == "unknown"` → Block 4 + END.

The chosen-target gate (`>= user_target_line`) is applied later in Phase 2.5 once the sentinel handshake has populated `user-choice.json` (see Phase 2.5 below).

### Phase 2 — Strategy

Single source: `assets/stack-matrix.json` + `assets/vitest-jest-compat.json`. Output: `framework_by_workspace` (in-memory + `.code-coverage/strategy.json`), plus `[phase2] workspace=<path> stack=<lang> framework=<fw> reason=... migrate=<bool>` in `decisions.log`.

**Vitest-first decision tree (JS/TS per workspace) — Migration-aware (v2):**

The mere presence of `jest.config.*` or `jest` in `scripts.test` is NOT an incompatibility — it's the current setup. The skill MIGRATES Jest→Vitest unless a real technical incompatibility signal (I1..I10 in `assets/vitest-jest-compat.json`) fires.

Phase 1 has already produced `.code-coverage/jest-compat.json` via `scripts/detect_jest_incompat.py`. Phase 2 reads it and emits per-workspace decision:

| `jest-compat.json` decision | framework | migrate | reason emitted |
|---|---|---|---|
| `jest-forced` (I10) | `jest` | `false` | `force-jest-override:<reason>` |
| `jest-incompat` (any I1..I9) | `jest` | `false` | `hard-incompat:<comma-joined-signals>` |
| `vitest-migrate` (jest artifacts + no signal) | `vitest` | `true` | `jest-legacy-migrating-to-vitest` (triggers Phase 4b) |
| `vitest-default` (no jest at all) | `vitest` | `false` | `vitest-first-default` |

**Opt-out (triple safety boundary)**: (1) `CC_DISABLE_JEST_MIGRATION=1` or `CC_KEEP_JEST=1` env vars; OR (2) `.code-coverage/overrides.json` with `{"force_jest": true, "force_jest_reason": "<reason>"}`; OR (3) intentionally dirty working tree on migration target files (Phase 4b refuses if `git status` shows uncommitted changes). All three opt-outs surface in `decisions.log`. Transparency principle: user can preview Phase 2 verdict by running `python3 scripts/detect_jest_incompat.py <repo>` BEFORE invoking the skill, to see which workspaces would migrate without actually triggering migration.

Other stacks (Python/Java/Kotlin/Go/Rust/C#/Flutter) → direct lookup in `assets/stack-matrix.json` for `framework`, `coverage_command`, `report_format`. No heuristics beyond the matrix.

**Lambda variant (JS/TS):** if `stack.json.is_lambda == true`, files matching `priority-rules.json.lambda_handler_globs` (default `*handler.ts`, `*lambda.ts`) → template `vitest-lambda-handler`; others → standard `vitest`.

**Monorepo:** iterate `stack.json.workspaces[]`, apply tree per workspace. Each workspace decided INDEPENDENTLY — a monorepo can have a mix of `vitest` (migrating or fresh) and `jest` (kept due to incompat) workspaces. Workspaces with `framework == "unknown"` are logged as `skipped reason=unsupported-language` and listed in Block 4.

**Gate:** if ALL workspaces resolve to `unknown` → emit Block 4 + END.

### Phase 2.5 — Target-aware coverage re-check (after sentinel handshake)

After `lib/sentinel-handshake.sh` writes `.code-coverage/user-choice.json` with the chosen `target_line`, re-evaluate the coverage gate using the actual target the user selected. The Phase 1 default gate (`>= 70`) catches projects with already maximum coverage; this Phase 2.5 gate catches projects whose existing coverage already satisfies a less ambitious custom target (e.g., user picks 45, pre-existing is 50 → skip the workflow).

```bash
# Inputs are read from JSON files; values are passed via argv to avoid shell
# interpolation in the python -c body (no injection surface even if the JSON
# values are malformed — float() raises ValueError, gate stays closed).
USER_TARGET=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['target_line'])" "$REPO/.code-coverage/user-choice.json") || exit 0
PRE_COV=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('pre_existing_coverage_pct',0))" "$REPO/.code-coverage/stack.json") || exit 0
if python3 -c "import sys; sys.exit(0 if float(sys.argv[1]) >= float(sys.argv[2]) else 1)" "$PRE_COV" "$USER_TARGET"; then
    echo "[phase2.5] pre_existing_coverage_pct=$PRE_COV >= user_target_line=$USER_TARGET → Block 8 + END"
    # NOTE: pseudo-code — replace with the actual Block 8 emitter wired in the consumer
fi
```

Snippet contract: missing/malformed `user-choice.json` or `stack.json` → silent no-op (`|| exit 0`); the workflow proceeds and Phase 1 default gate has already enforced the upper bound.

If gate fires → Block 8 "coverage already sufficient for chosen target" + END.

### Phase 3 — Sizing (REF if LARGE/VERY_LARGE)
If `size.json.class IN ("LARGE","VERY_LARGE")` → emit phased-mode notice, run `python3 skills/code-coverage/scripts/plan_batches.py --size <repo>/.code-coverage/size.json --stack <repo>/.code-coverage/stack.json --out <repo>/.code-coverage/batch-plan.json`, load `references/phase-3-sizing.md`.
Valuta il trigger parallelo (vedi references/phase-5-parallel.md "Trigger"). Logga:
"[phase3] parallel_mode=enabled agents=N" oppure "[phase3] parallel_mode=disabled reason=...".

**Prediction:** `python3 skills/code-coverage/scripts/predict_coverage.py <repo>` →
coverage-prediction.json. Includi nel messaggio pre-Phase-4: "[prediction]
branch_p7=<Y>% confidence=<C> <risk_flag>". Non-bloccante: se fallisce, Phase 3 continua.

### Phase 4 — Environment

**[Loader]** Trigger predicate (load `references/java-siae-quirks.md` once if ANY is true):

1. `stack.json.language == "java"`, OR
2. `stack.json.maven_aggregator` is present (non-null), OR
3. `find <repo> -maxdepth 3 -name pom.xml -print -quit` returns a non-empty path.

Equivalent bash check (consumer-side, exit 0 = load required):
```bash
REPO="${1:-.}"
if python3 -c "
import json, pathlib, sys
sj = pathlib.Path('$REPO/.code-coverage/stack.json')
if not sj.is_file(): sys.exit(1)
d = json.loads(sj.read_text())
sys.exit(0 if d.get('language') == 'java' or d.get('maven_aggregator') else 1)
" 2>/dev/null || find "$REPO" -maxdepth 3 -name pom.xml -print -quit | grep -q .; then
    echo "LOAD references/java-siae-quirks.md"
fi
```

If triggered, read the file once and apply all applicable quirks for the remainder of the session.

Read `.code-coverage/env.json`. For each framework with `installed: false` and non-null command in `assets/install-snippets.json`:
1. Snapshot lockfile (`package-lock.json` / `yarn.lock` / `pnpm-lock.yaml` / `poetry.lock`) → `.code-coverage/lockfile.bak`.
2. Run `install-snippets.json[<framework>].command` (or `alt_yarn`/`alt_pnpm`/`alt_poetry` matching detected PM).
3. Exit != 0 → restore lockfile, append error to `.code-coverage/install-log.txt`, emit Block 4 "framework install failed" + END.
4. Exit == 0 → log to `decisions.log` and proceed.

Frameworks with `command: null` (junit5/junit5-gradle/mockk/cargo-test/flutter_test): read `manual_manifest_edit`, apply autonomously to `pom.xml`/`build.gradle`/`Cargo.toml`/`pubspec.yaml`, then run verification (e.g., `mvn dependency:resolve`, timeout 30s).

**Vitest config generation:** only if `vitest.config.ts` ABSENT and framework=vitest. Generate skeleton with `environment` (`jsdom` for FE, `node` for backend), `coverage.provider: 'v8'`, `reporter: ['text','json-summary']`. Never overwrite existing config. Log decision.

**Jest→Vitest migration (Phase 4b — conditional):** For any workspace with `strategy.json.framework_by_workspace[ws].migrate == true`:

```bash
python3 skills/code-coverage/scripts/migrate_jest_to_vitest.py "<repo>"
# Exit codes: 0=ok | 1=refused/install-failed | 2=verification-failed (snapshot restored) | 4=noop
```

Migration pipeline (per workspace, atomic):
1. **Dirty-tree pre-flight**: `git status` su file touched → if dirty, REFUSE + Block 4 entry
2. **Snapshot** package.json + jest.config.* + jest.setup.* + lockfile + all `*.{test,spec}.*` → `.code-coverage/migration-snapshot/`
3. **Translate** `jest.config.* → vitest.config.ts` (skip if exists). Keys in `config_keys_manual_review` (`setupFilesAfterEach`, `globalSetup`, etc.) are flagged in `migration-report.json.unmapped_keys[]`, NOT rewritten
4. **Rewrite** `package.json` (scripts: jest→vitest run; devDeps: remove jest stack, add vitest+@vitest/coverage-v8+jsdom-if-FE)
5. **Codemod** test files via `assets/vitest-jest-compat.json.api_migration_map.rewrites` (21 mappings). Tokens in `no_rewrite_tokens` (`jest.requireActual`, `jest.requireMock`) flagged but NOT rewritten
6. **Rename** `jest.setup.* → vitest.setup.*` + transform `@testing-library/jest-dom` → `/vitest`
7. **Install** per-PM (npm/pnpm/yarn/yarn-berry/bun detected from lockfile)
8. **Smoke verify**: `npx vitest run --reporter=basic --no-coverage` timeout 120s
9. **Commit** (delete jest.config.* after verify) OR **Rollback** (restore snapshot + frozen-lockfile reinstall via `rollback_install_cmd_for(pm)`)

Outputs: `.code-coverage/migration-report.json` + `.code-coverage/migration-snapshot/`. **Block 9 (Next Actions) MUST include every `migration-report.json.workspaces[].files.manual_review[]` entry** verbatim with file:line, so the user can resolve `jest.requireActual`/`requireMock`/`isolateModules`/types post-migration. Missing this surfacing causes CI failures without diagnosis.

Lazy-loaded reference: `references/phase-4b-migration.md` (loaded ONLY if any workspace has `migrate=true` — see HARD READ POLICY).

**Blocking Check Handler:** if `env.json.missing` includes essential runtime (Node/Python/Java/Go/Rust/Dotnet/Flutter) → emit `ENVIRONMENT BLOCKER` block with runtime-specific install hint + STOP. Do not continue without runtime.

**TIMEOUT handling:** `env.json.available[i].reason == "TIMEOUT"` → log warning, do NOT block; treat as "available but slow"; subsequent installs use 60s timeout (JVM/Flutter default 30s per `validate_env.py`).

Output: `.code-coverage/install-log.txt`, `.code-coverage/lockfile.bak`, `decisions.log` updated.

**Phase 4 — Test helpers:** se `<repo>/<src>/__tests__/helpers/` non contiene gli helper,
copia da `templates/helpers/*.ts` (PRESERVE_EXISTING: skip se già presenti). Log in decisions.log.

**Phase 4 — ICU probe:** se un file under test ha `scan_tz_usage.py.uses_tz==true`, verifica
che il runtime Node abbia ICU full: `node -e "new Intl.DateTimeFormat('it-IT',{timeZone:'Europe/Rome'}).format(new Date())"`.
Se fallisce con RangeError → forza l'import di `mockTz` negli spec TZ-dipendenti (il mock
bypassa Intl) e logga `[phase4] ICU probe failed → mockTz forced` in decisions.log.

### Phase 5b — Coverage Probe (handled in Phase 1)

Triggered automatically by `phase1-discover.sh` when `test_files_count > 0` AND `module_coverage == []`. Produces `.code-coverage/coverage-report.json` so D1 fires TIER-FIRST in Phase 5. No LLM action required.

### Phase 5 — Generation
If parallel_mode == enabled:
  - Verifica che il tool Agent sia disponibile (altrimenti fallback sequenziale + log).
  - Load `references/phase-5-parallel.md`.
  - Esegui il Dispatch Protocol (P1-P5): assegna batch→agenti, dispatcha le Agent call
    Sonnet nello STESSO turno, attendi, join, re-queue partial/failed.
  - SKIP il loop sequenziale standard (gira dentro i subagent).
  - Procedi a Phase 6 (coordinatore).
Else:  *(solo sequential path — in parallel mode è caricato dai subagent)*
  Load `references/phase-5-generation.md`. **Step 0 hard gate (PRESERVE_EXISTING)** + `bash lib/placeholder-check.sh <file>` before every write. Template hard-cache via `lib/template-cache.sh`. Ordering (D1 conditional TIER-FIRST vs P-TIER) + P1 floor enforcement in the ref. Lazy-load `assets/few-shot-e2e.md` (first batch) and `assets/anti-patterns.md` (on any fail).

### Phase 6 — Coverage
```bash
bash skills/code-coverage/lib/phase6-coverage.sh "<repo>"
```
If all P1>=80%, P2>=70%, P3>=60%, global>=70% → SKIP Phase 7 → OUTPUT.

### Phase 7 — Repair
See `references/phase-7-repair.md` (categorize → group → systemic-fix vs per-file → progress guard → autonomous early-abort). Max iter = min(10, max(3, ceil(batch_plan.batches.length × 1.5))) — letto da
.code-coverage/batch-plan.json (fallback 3). Max 1 full coverage run/iter.
If parallel_mode == enabled: i fix per-file con >= 2 file di categorie diverse sono
dispatchati a repair-agent Sonnet in parallelo (vedi phase-5-parallel.md "Phase 7 parallel
repair"). Systemic fix e full coverage run restano sequenziali (coordinatore).

## OUTPUT — Conditional Blocks

Always emit Block 1 (Repository Summary: path, languages, size class, monorepo), Block 5 (Generated Test Files table: Path | Module | Tier | Priority | Coverage gain), Block 8 (Coverage Report Summary: Module | Lines% | Branch% | Threshold | Status; + Stalled Files if Phase 7 non-convergent).

Conditional (programmatic, NEVER prompt):
- Block 4 (`unsupported_groups`): only if non-empty.
- Block 6 (`Dependency Install Commands`): only if `validate_env.py.install_commands` non-empty.
- Block 9 (`Next Actions`): if any module sub-threshold OR follow-up batch active OR PRESERVE_EXISTING entries OR manual tests suggested.
  - Include i file di `.code-coverage/intractable.json` con la rispettiva `suggested_strategy`. Formato:
    "Intractable (manual): src/dao/X.ts → reflection per private methods; src/dao/Y.ts → requires DB fixture (skip in unit)."
    Ogni entry `files[]` in intractable.json è resa come `"<path> → <suggested_strategy>"` (reason in parentesi se utile).
  - Aggiungi anche: follow-up batch attivo (pending_batches), PRESERVE_EXISTING entries (file già presenti saltati), manual tests suggeriti.
  - Se `.code-coverage/intractable.json` è assente o `files[]` è vuoto, ometti la sezione intractable.

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
