# Phase 1 — Stack Discovery

## Purpose
Inspect the target repository and produce a deterministic JSON description of its tech stack,
without reading any source code. Detection is purely file-system and manifest-based.

---

## Detection File Inventory

Run `scripts/detect_stack.py <repo_path>` which inspects the following files.
**Do not read arbitrary source files during this phase.**

### JavaScript / TypeScript
| File | Signal |
|------|--------|
| `package.json` | Primary — languages, frameworks, test frameworks via deps |
| `package-lock.json` | Confirms npm usage |
| `yarn.lock` | Confirms yarn usage |
| `pnpm-lock.yaml` | Confirms pnpm usage |
| `bun.lockb` | Confirms bun usage |
| `tsconfig.json` | Confirms TypeScript |
| `vite.config.ts` / `vite.config.js` | Build tool = Vite |
| `next.config.js` / `next.config.ts` | Framework = Next.js |
| `nuxt.config.ts` | Framework = Nuxt |
| `svelte.config.js` | Framework = Svelte |
| `astro.config.mjs` | Framework = Astro |
| `angular.json` | Framework = Angular |
| `vitest.config.ts` | Existing test framework = vitest |
| `jest.config.ts` / `jest.config.js` | Existing test framework = jest |

### Serverless
| File | Signal |
|------|--------|
| `serverless.yml` / `serverless.ts` | Serverless Framework |
| `template.yaml` | AWS SAM |
| `cdk.json` | AWS CDK |
| `sst.config.ts` | SST |
| `function.json` | Azure Functions |

### Python
| File | Signal |
|------|--------|
| `requirements.txt` | pip; check content for framework names |
| `pyproject.toml` | pip/poetry/pdm; check `[tool.pytest.ini_options]` |
| `setup.py` / `setup.cfg` | Legacy pip |
| `Pipfile` | pipenv |
| `poetry.lock` | poetry |
| `conftest.py` | Confirms pytest in use |
| `pytest.ini` | Confirms pytest in use |

### Java / Kotlin
| File | Signal |
|------|--------|
| `pom.xml` | Maven; scan for `junit-jupiter`, `mockito`, Spring deps |
| `build.gradle` / `build.gradle.kts` | Gradle; scan for same |
| `.java` extension present | Language = Java |
| `.kt` / `.kts` extension present | Language = Kotlin |

### Other Languages
| File | Signal |
|------|--------|
| `pubspec.yaml` | Dart / Flutter |
| `go.mod` | Go |
| `Cargo.toml` | Rust |
| `*.csproj` / `*.sln` | C# / .NET |
| `global.json` | .NET SDK version |
| `Gemfile` | Ruby |
| `composer.json` | PHP |

### Monorepo Indicators
| File | Signal |
|------|--------|
| `turbo.json` | Turborepo |
| `nx.json` | Nx |
| `lerna.json` | Lerna |
| `pnpm-workspace.yaml` | pnpm workspace |
| `rush.json` | Rush |
| `package.json` with `"workspaces"` field | npm/yarn workspace |
| `packages/` or `apps/` directory with ≥2 child `package.json` | Monorepo pattern |

### CI/CD
| File/Path | Signal |
|-----------|--------|
| `.github/workflows/` | GitHub Actions |
| `.gitlab-ci.yml` | GitLab CI |
| `Jenkinsfile` | Jenkins |
| `.circleci/config.yml` | CircleCI |
| `azure-pipelines.yml` | Azure DevOps |
| `bitbucket-pipelines.yml` | Bitbucket |
| `.travis.yml` | Travis CI |
| `buildspec.yml` | AWS CodeBuild |

---

## Walk Exclusions

When walking the file tree, always skip these directories to avoid false positives and performance issues:

```
node_modules/  .git/       dist/       build/      out/
target/        .terraform/ vendor/     coverage/   __pycache__/
.venv/         venv/       .next/      .nuxt/      .svelte-kit/
```

Max walk depth: **6 levels** from repo root.

---

## Output Contract

`detect_stack.py` must produce a JSON object with exactly these keys:

```json
{
  "repo_path": "<absolute path>",
  "languages": ["typescript", "python"],
  "frameworks": ["react", "express"],
  "package_managers": ["pnpm"],
  "build_systems": ["vite"],
  "monorepo": false,
  "ci_cd": ["github-actions"],
  "architecture_style": "frontend-spa",
  "existing_test_frameworks": ["vitest"],
  "test_infrastructure": {
    "setup_files": [],
    "global_mocks": [],
    "existing_aliases": {},
    "patterns_sample": ""
  },
  "pre_existing_coverage_pct": 0
}
```

`architecture_style` values: `frontend-spa`, `backend-api`, `microservices`,
`serverless`, `data-pipeline`, `java-microservice`, `mobile-flutter`, `unknown`.

---

## Existing Test Infrastructure Scan

After running `detect_stack.py`, perform a targeted read of existing test infrastructure. This data is consumed by Phase 5 to avoid duplicating mock factories already defined globally.

**For Vitest/Jest repos (JS/TS):**
1. If `vitest.config.ts` or `jest.config.ts` exists: read it — extract `setupFiles`, `globalSetup`, `resolve.alias`, `environment`, `globals`.
2. Check for a `__mocks__/` directory at repo root — list all mock files present.
3. Read up to 3 existing `.test.ts` files from P1 directories to extract: mock patterns in use, fixture/factory helpers, import path conventions.

**For pytest repos (Python):**
- Read up to 2 `conftest.py` files — extract fixture names, scopes, and `pytest-mock` usage patterns.

**For JUnit repos (Java/Kotlin):**
- Scan for `@TestConfiguration` classes — list shared test beans.

Produce field `"test_infrastructure"` in the discovery output JSON:
```json
{
  "setup_files": ["src/setupTests.ts"],
  "global_mocks": ["__mocks__/axios.ts", "__mocks__/db.ts"],
  "existing_aliases": { "@": "src" },
  "patterns_sample": "brief excerpt of mock pattern found in existing tests"
}
```
This field is passed to Phase 5 to reuse existing infrastructure instead of duplicating it.

---

## Coverage Pre-Check

After the test infrastructure scan, check for an existing coverage report:

1. Look for `coverage/lcov.info`, `.code-coverage/coverage-output.txt`, or `coverage-summary.json` at repo root.
2. If found: parse the file to extract per-module coverage percentages. Emit field `"pre_existing_coverage"` in the discovery JSON:
   ```json
   { "pre_existing_coverage_pct": 42.5, "module_coverage": { "src/services/payment.ts": 87.0, "src/utils/formatter.ts": 0.0 } }
   ```
3. If not found: set `"pre_existing_coverage_pct": 0`.

**This field is consumed in Phase 3**: if `pre_existing_coverage_pct ≥ 70%`, Phase 3 can declare the global target already met and skip generation.

---

## Coverage Exclusion Scan

After the Coverage Pre-Check, parse `coverage.exclude` (or equivalent) from any detected config files. This exclusion list is passed forward as a Phase 1 output consumed by Phase 5 to avoid generating tests for excluded paths.

| Config file | Exclusion field |
|-------------|----------------|
| `vitest.config.ts` / `vitest.config.js` | `coverage.exclude` array |
| `jest.config.ts` / `jest.config.js` | `coveragePathIgnorePatterns` array |
| `.nycrc` / `.nycrc.json` | `exclude` array |
| `pyproject.toml` | `[tool.coverage.run]` → `omit` list |
| `pytest.ini` / `setup.cfg` | `[coverage:run]` → `omit` list |

Produce field `"coverage_exclude"` in the discovery output JSON:
```json
{ "coverage_exclude": ["node_modules/**", "dist/**", "**/*.config.*", "src/generated/**"] }
```

If no exclusion field is found: set `"coverage_exclude": []`. Phase 5 must skip any file matching a pattern in this list.

---

## Remote Repository Handling

If the user provides a GitHub URL:
1. Extract `owner/repo` and optional `branch` and `subdir`.
2. Auto-clone in `mktemp -d` senza prompt. Cleanup automatico al termine della sessione. Path temp loggato in `.code-coverage/decisions.log`.
3. Run detection on the cloned path.
4. If `subdir` was specified, run detection on `<clone_root>/<subdir>`.

```bash
git clone --depth=1 --branch <branch> https://github.com/<owner>/<repo> <tmpdir>
```
