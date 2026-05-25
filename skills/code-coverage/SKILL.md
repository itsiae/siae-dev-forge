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
Gates: `stack.json.pre_existing_coverage_pct >= 70` → Block 8 + END; `env.json.required_framework == "unknown"` → Block 4 + END.

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

## Multi-module Maven repos (SIAE legacy)

`detect_stack.py` cerca automaticamente un pom aggregator (`<packaging>pom</packaging>` + `<modules>` non vuoto) fino a 4 livelli di profondità (override via `CC_POM_MAXDEPTH`).

Quando rilevato, `stack.json` contiene:
```json
{
  "manifest_root": "pae-deposito-musica",
  "maven_aggregator": {
    "manifest_root": "pae-deposito-musica",
    "aggregator_pom": "pae-deposito-musica/pom.xml",
    "modules": ["mod-a", "mod-b"],
    "selection_reason": "packaging-pom-with-modules"
  }
}
```

`select_command.py` inietta `-f <aggregator_pom>` nel `cov_cmd` Maven. Phase 6 esegue da repo root con il pom aggregator esplicito.

**Selection priority:**
1. Pom con `<packaging>pom</packaging>` + `<modules>` non vuoto (aggregator vero). PIU' SHALLOW vince.
2. Fallback: pom con `jacoco-maven-plugin` + `junit-jupiter` deps. PIU' SHALLOW vince.
3. None se nessun pom matcha.

**Override manuale:** se la detection sbaglia (es. aggregator > maxdepth=4), creare `.code-coverage/overrides.json`:
```json
{
  "manifest_root": "custom/path",
  "aggregator_pom": "custom/path/pom.xml"
}
```

## Maven placeholder handling (Task 02)

Pom SIAE usano ``${appVersion}``, ``${revision}`` iniettati dalla pipeline CI/CD ma non definiti nel pom. Phase 4 scansiona i pom, rileva i placeholder non risolti, e popola ``env.json.maven_placeholders``:

```json
{
  "maven_placeholders": {
    "appVersion": "1.0.0-SNAPSHOT",
    "revision": "1.0.0-SNAPSHOT"
  }
}
```

`select_command.py` propaga ``-D<token>=<value>`` nel mvn cmd Phase 6. Default = ``1.0.0-SNAPSHOT`` (override via ``overrides.json.maven_placeholders``).

**Esclusi:** built-in Maven (``${project.version}``, ``${pom.basedir}``, ...) e placeholder definiti localmente nel ``<properties>`` del pom.

**Override esempio:**
```json
{
  "maven_placeholders": {
    "appVersion": "2.0.0-RELEASE",
    "revision": "1.2.3"
  }
}
```

## Jacoco-skipped modules (Task 06)

Moduli SIAE legacy hanno spesso ``<jacoco.skip>true</jacoco.skip>`` per design (es. ``siae-pae-bollettino-service`` è aggregator senza source Java). Phase 4 detecta queste proprietà e popola ``env.json.skipped_modules``.

Phase 8 (reporting) DEVE filtrare ``skipped_modules`` dal calcolo bundle coverage:

```python
skipped = set(env_json.get("skipped_modules", []))
covered_modules = [m for m in all_modules if m not in skipped]
# bundle coverage = aggregate(covered_modules) — esclude i SKIPPED
```

I moduli SKIPPED compaiono nel report finale in sezione "Moduli skipped" con ragione ``jacoco.skip=true by-design`` — non contano come FAIL.

## Assertion library — NO auto-add deps (Task 04)

Phase 4 (validate_env.py) rileva la libreria di assertion presente nel pom Java:

- ``assertj-core`` in deps → ``env.json.assertion_lib = "assertj"`` → template
  ``junit5.template.java`` (AssertJ style: ``assertThat(x).isEqualTo(y)``)
- Solo JUnit5 vanilla (no AssertJ) → ``env.json.assertion_lib = "junit5_vanilla"``
  → template ``junit5-vanilla.template.java`` (``assertEquals(expected, actual)``)

**Principle 1 enforcement:** la skill NON modifica autonomamente il pom per
aggiungere AssertJ. È responsabilità dell'utente decidere l'upgrade. Il template
vanilla è funzionalmente equivalente per le assertion comuni.

**Detection scope:** scansiona aggregator pom + tutti i moduli figli (path
letti da ``stack.json.maven_aggregator.modules`` quando rilevato in Task 01).
AssertJ presente in UN qualsiasi modulo → template AssertJ globale.

## SUPPORTING FILES

See `references/index.md` for the full map of lib/, scripts/, assets/, templates/, and references/.
