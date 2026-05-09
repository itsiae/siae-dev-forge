# Phase 4 — Environment Validation

## Purpose
Verify that the runtime, package manager, and test framework dependencies
are available before attempting test generation or execution.
**Run `scripts/validate_env.py <repo_path>` to obtain the environment report.**

---

## Checks Performed

`validate_env.py` checks in this order:

### 1. Runtime Availability
| Runtime | Command | Min Version |
|---------|---------|-------------|
| Node.js | `node --version` | 18.x |
| Python | `python3 --version` (Linux/macOS) / `python --version` (Windows) | 3.10 |
| Java | `java -version` | 17 |
| Kotlin | `kotlinc -version` | 1.9 |
| Go | `go version` | 1.21 |
| Rust | `cargo --version` | 1.70 |
| .NET | `dotnet --version` | 8.0 |
| Flutter | `flutter --version` | 3.0 |
| Ruby | `ruby --version` | 3.1 |
| PHP | `php --version` | 8.1 |

### 2. Package Manager Availability
| Tool | Command |
|------|---------|
| npm | `npm --version` |
| yarn | `yarn --version` |
| pnpm | `pnpm --version` |
| bun | `bun --version` |
| pip | `pip3 --version` (Linux/macOS) / `pip --version` (Windows) |
| poetry | `poetry --version` |
| pipenv | `pipenv --version` |
| maven | `mvn --version` |
| gradle | `./gradlew --version` (Linux/macOS) / `gradlew.bat --version` (Windows) |
| cargo | `cargo --version` |
| bundler | `bundle --version` |
| composer | `composer --version` |

### 3. Test Framework Installation
Checks whether the test framework declared in Phase 2 is already installed
in the target repo (e.g., `node_modules/vitest` exists, `pytest` importable, etc.).

### 4. Pre-Existing Coverage Pass (Automatic)

If `existing_test_frameworks` (from Phase 1) is non-empty AND `pre_existing_coverage_pct == 0`, automatically run a coverage measurement on the existing tests using the appropriate framework's coverage command:

```bash
# Example for Vitest:
npx vitest run --coverage > .code-coverage/pre-existing-coverage.txt 2>&1 && tail -n 100 .code-coverage/pre-existing-coverage.txt
# For other frameworks, apply the same redirect pattern.
```

Parse the result to extract the global coverage percentage.

If the measured coverage ≥ 70%:
- **Skip Phase 5 entirely.** Proceed directly to Block 8 reporting.
- Set Block 8 `Status` = `TARGET_ALREADY_MET` for all modules.
- Populate Block 9 with suggestions for specific uncovered modules identified in the report.

If the measured coverage < 70%:
- Record the measured value as `pre_existing_coverage_pct` and continue to Phase 5 as planned.

---

## Install Commands by Package Manager

Present these to the user and **wait for approval** before executing.

### Vitest (JS/TS)
```bash
# npm
npm install --save-dev vitest @vitest/coverage-v8

# yarn
yarn add --dev vitest @vitest/coverage-v8

# pnpm
pnpm add -D vitest @vitest/coverage-v8

# bun
bun add -d vitest @vitest/coverage-v8
```

### Jest (JS/TS — fallback only)
```bash
# npm
npm install --save-dev jest @types/jest ts-jest @jest/coverage

# yarn
yarn add --dev jest @types/jest ts-jest

# pnpm
pnpm add -D jest @types/jest ts-jest
```

### pytest (Python)
```bash
pip install pytest pytest-cov pytest-asyncio pytest-mock
# or with pyproject.toml:
pip install -e ".[test]"
# or with poetry:
poetry add --group dev pytest pytest-cov pytest-asyncio pytest-mock
```

### pytest + chispa (PySpark)
```bash
pip install pytest pytest-cov chispa pyspark
```

### JUnit 5 + Mockito (Java/Maven)
Add to `pom.xml`:
```xml
<dependency>
  <groupId>org.junit.jupiter</groupId>
  <artifactId>junit-jupiter</artifactId>
  <version>5.11.0</version>
  <scope>test</scope>
</dependency>
<dependency>
  <groupId>org.mockito</groupId>
  <artifactId>mockito-junit-jupiter</artifactId>
  <version>5.12.0</version>
  <scope>test</scope>
</dependency>
```

### JUnit 5 + MockK (Kotlin/Gradle)
Add to `build.gradle.kts`:
```kotlin
testImplementation("org.junit.jupiter:junit-jupiter:5.11.0")
testImplementation("io.mockk:mockk:1.13.12")
testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.8.0")
```

### flutter_test (Flutter)
Add to `pubspec.yaml` dev_dependencies:
```yaml
dev_dependencies:
  flutter_test:
    sdk: flutter
  mocktail: ^1.0.0
```

### Go (stdlib + testify)
```bash
go get github.com/stretchr/testify@latest
```

### Rust (platform-conditional)
```bash
# Linux
cargo install cargo-tarpaulin

# macOS / Windows
cargo install cargo-llvm-cov
```

### xUnit + Moq (C#)
```bash
dotnet add package xunit
dotnet add package xunit.runner.visualstudio
dotnet add package Moq
dotnet add package coverlet.msbuild
```

---

## Output Contract

`validate_env.py` must produce:

```json
{
  "repo_path": "<path>",
  "required_framework": "vitest",
  "available": [
    {"tool": "node", "version": "20.11.0", "min_required": "18.0.0", "ok": true},
    {"tool": "pnpm", "version": "8.15.0", "min_required": null, "ok": true}
  ],
  "missing": [
    {"tool": "vitest", "location": "node_modules", "ok": false}
  ],
  "install_commands": [
    "pnpm add -D vitest @vitest/coverage-v8"
  ],
  "blocking": false
}
```

`blocking: true` means the runtime itself is missing (e.g., no Node.js) — the skill cannot proceed without manual intervention.

### Blocking Check Handler

If any check in `validate_env.py` output returns `blocking: true`, **stop the workflow immediately** with the following error message template:

```
ENVIRONMENT BLOCKER — Skill cannot proceed.

Check failed:  <tool name>
Reason:        <why it is blocking, e.g. "Node.js >= 18.0.0 required, found 16.x">
Required by:   <Phase N — framework name>

To resolve:
  <exact install or upgrade command>
  e.g. "brew install node@20" / "nvm use 20" / "sudo apt-get install nodejs"

Re-run /code-coverage after resolving the blocker.
```

Do not continue to Phase 5 or any subsequent phase until the user confirms the blocker is resolved and re-runs the skill.

---

## Vitest Config Generation

If Vitest is selected and no `vitest.config.ts` exists, run these pre-config checks first, then generate and propose the config (do not write without approval):

### Pre-Config Checks (run before generating vitest.config.ts)

1. **tsconfig.json path aliases:** Read `tsconfig.json` → `compilerOptions.paths`. If any paths are defined, each entry becomes a `resolve.alias` entry in `vitest.config.ts`.
   Example: `"@/*": ["./src/*"]` → `alias: { '@': path.resolve(__dirname, './src') }`

2. **Frontend vs Node environment:** Check the stack detected in Phase 2:
   - React, Vue, Angular, Svelte, Remix, Astro, Next.js, Nuxt → `environment: 'jsdom'`
   - Node.js, Lambda, SST, SAM, CDK, Serverless, NestJS, Express, Fastify → `environment: 'node'`

3. **Source directory:** Identify the primary source directory (`src/`, `app/`, `lib/`, or repo root). Set `coverage.include` to target that directory — without this field, v8 only measures files actually imported during tests, not all source files.

4. **testing-library setup:** If stack is React/Vue/Angular/Svelte AND `@testing-library/*` is in dependencies → prepare `setupFiles: ['./src/setupTests.ts']` and add `@testing-library/jest-dom` to the install commands.

```typescript
import { defineConfig } from 'vitest/config'
import path from 'path'

export default defineConfig({
  test: {
    globals: false,               // Keep false — use explicit imports from 'vitest' (safer with TypeScript strict)
    environment: '<node|jsdom>',  // Replace: 'jsdom' for React/Vue/Angular/Svelte; 'node' for Node.js/Lambda
    // setupFiles: ['./src/setupTests.ts'],  // Uncomment for React/Vue with @testing-library/jest-dom
  },
  resolve: {
    alias: {
      // Add entries from tsconfig.json compilerOptions.paths, e.g.:
      // '@': path.resolve(__dirname, './src'),
    },
  },
  coverage: {
    provider: 'v8',
    reporter: ['text', 'html', 'lcov'],
    include: ['src/**/*.{ts,tsx}'],  // REQUIRED — adapt to actual source directory (app/, lib/, etc.)
    exclude: [
      'node_modules/**', 'dist/**', '**/*.config.*',
      '**/__mocks__/**', '**/index.ts',
    ],
    thresholds: { lines: 70, functions: 70, branches: 70 },
  },
})
```
