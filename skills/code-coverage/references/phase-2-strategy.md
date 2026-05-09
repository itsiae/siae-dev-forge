# Phase 2 — Test Strategy

## Purpose
Map the detected stack to the optimal test framework. Produce a deterministic
framework selection for every module group in the target repository.
**Always consult `assets/stack-matrix.json` — do not select frameworks from memory.**

---

## Decision Algorithm

```
FOR each module group in repo:
  language = detect primary language of group
  SWITCH language:
    CASE javascript / typescript:
      // Conditions evaluated in order — first match wins
      IF jest_config_file present (jest.config.ts|js|mjs|cjs):
        framework = jest  // condition (a): explicit Jest config
      ELSE IF package.json scripts.test contains "jest" AND vitest NOT in devDependencies:
        framework = jest  // condition (b): existing Jest runner, no migration started
      ELSE:
        framework = vitest  // DEFAULT — always prefer Vitest
    // Conditions (c) and (d) require .code-coverage/constraints.json — check before running
    // the algorithm above. If constraints.json documents CJS incompatibility or legacy reason,
    // skip the algorithm and set framework = jest directly.
    CASE python:
      framework = pytest
    CASE java:
      framework = junit5 + mockito
    CASE kotlin:
      framework = junit5 + mockk
    CASE dart / flutter:
      framework = flutter_test
    CASE pyspark (python with pyspark dep):
      framework = pytest + chispa
    CASE go:
      framework = testing (stdlib) + testify
    CASE rust:
      framework = cargo test
    CASE csharp:
      framework = xunit + moq
    CASE ruby:
      framework = rspec
    CASE php:
      framework = phpunit
    DEFAULT:
      // Do NOT block the entire workflow.
      // Skip the affected language group; log it under 'unsupported_groups' in Block 4.
      // Continue with supported groups.
      ADD group to unsupported_groups
      EMIT warning: "Language group '<group>' uses an unsupported framework. Skipped — see Block 4 unsupported_groups."
```

---

## Vitest vs Jest Decision Tree

```
Step 0 — Check .code-coverage/constraints.json (if file exists):
  IF documents CJS-incompatibility OR legacy constraint → Use Jest (conditions c/d). STOP.

Step 1 — Does repo have jest.config.{ts,js,mjs,cjs}?
  YES → Use Jest (condition a: explicit config). STOP.

Step 2 — Does package.json scripts.test contain "jest" (not "vitest")?
  NO  → Use Vitest (DEFAULT). STOP.
  YES → Does vitest appear anywhere in devDependencies?
    YES → Use Vitest (user has started migration, condition b not met). STOP.
    NO  → Use Jest (condition b: existing Jest runner, no migration). STOP.
```

**Vitest is default for ALL of: React, Next.js, Vue, Nuxt, Angular, Svelte,
Remix, Astro, Express, NestJS, Fastify, Koa, Hapi, Lambda, SST, SAM, CDK.**

> **Implementation note**: This decision tree is the executable form of SKILL.md Global Execution Principle 4. The two are equivalent — no conflict exists. Do not re-evaluate the Vitest-first rule from memory; always execute this tree.

---

## Framework Capability Matrix

| Stack | Framework | Mocking | Async | ESM | Coverage Tool |
|-------|-----------|---------|-------|-----|---------------|
| FE / Node / Serverless | **Vitest** | `vi.mock`, `vi.fn`, `vi.spyOn` | native | native | `@vitest/coverage-v8` |
| FE / Node (legacy) | Jest | `jest.mock`, `jest.fn`, `jest.spyOn` | `jest.useFakeTimers` | partial | `@jest/coverage` |
| Python | pytest | `pytest-mock` / `unittest.mock` | `pytest-asyncio` | — | `pytest-cov` |
| PySpark | pytest + chispa | `unittest.mock` | — | — | `pytest-cov` |
| Java | JUnit 5 + Mockito | `@Mock`, `@InjectMocks`, `when().thenReturn()` | `CompletableFuture` | — | JaCoCo |
| Kotlin | JUnit 5 + MockK | `mockk()`, `every {}`, `coEvery {}` | `runTest` | — | Kover |
| Flutter | flutter_test | `mocktail` / `mockito` | `async` / `pump()` | — | `flutter test --coverage` |
| Go | testing + testify | `mock` interfaces | `t.Helper()` | — | `go test -cover` |
| Rust | cargo test | trait objects / `mockall` | `tokio::test` | — | `cargo-tarpaulin` |
| C# | xUnit + Moq | `Mock<T>`, `Setup()` | `async Task` | — | Coverlet |
| Ruby | RSpec | `allow().to receive()`, `double()` | `async` | — | SimpleCov |
| PHP | PHPUnit | `createMock()`, `getMockBuilder()` | — | — | xdebug/pcov |

---

## Output: Strategy Table

Produce this table before proceeding to Phase 3:

```
┌─────────────────────────────────────────────────────────────────┐
│ TEST STRATEGY REPORT                                            │
├────────────────┬──────────────┬──────────────────┬─────────────┤
│ Module Group   │ Language     │ Framework        │ Deviation?  │
├────────────────┼──────────────┼──────────────────┼─────────────┤
│ src/services/  │ TypeScript   │ Vitest           │ No          │
│ src/utils/     │ TypeScript   │ Vitest           │ No          │
│ lambda/        │ TypeScript   │ Vitest           │ No          │
│ scripts/       │ Python 3.11  │ pytest           │ No          │
└────────────────┴──────────────┴──────────────────┴─────────────┘
```

If any deviation from default occurred, append a **Deviation Log**:

```
DEVIATION LOG:
- Module: <group>  Reason: <jest config found: jest.config.ts>
  Framework selected: jest  Default would have been: vitest
```

---

## Monorepo Handling

For monorepos, apply framework detection **per workspace**, not globally.
A monorepo may have:
- `packages/ui/` → React → Vitest
- `packages/api/` → NestJS → Vitest
- `services/data/` → Python → pytest

Produce one strategy row per workspace. Group workspaces with identical
framework + language to reduce table length when more than 10 workspaces.
