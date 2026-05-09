# Phase 7 — Repair Loop

## Purpose
For each failing test or module below coverage threshold, apply a deterministic
diagnostic + fix cycle. Iterate until coverage ≥70% or the loop limit is reached.

---

## Failure Categories

Every test failure maps to exactly one category. Categorize BEFORE applying any fix.

### Category 1: Dependency Issue
**Symptoms:**
- `Cannot find module 'X'`
- `ModuleNotFoundError: No module named 'X'`
- `Package or classfile 'X' not found`
- `error[E0433]: failed to resolve`
- Missing peer dependency warnings at test startup

**Fix Strategy — decision tree (evaluate in order, stop at first match):**

1. Does the error message contain `"Dynamic require of"`?
   **YES →** Cause: CJS-only package in ESM context.
   Fix: add the package to `test.deps.inline: ['package-name']` in `vitest.config.ts`. Document in `.code-coverage/constraints.json`.

2. Does the import path start with `@/`, `~/`, or a custom alias (not starting with `./`, `../`, or a bare package name)?
   **YES →** Cause: unresolved path alias.
   Fix: read `tsconfig.json` → `compilerOptions.paths` → add matching `resolve.alias` entries to `vitest.config.ts`.

3. Check `package.json` / `requirements.txt` / `pom.xml` for the missing dependency.
   - If missing: add to the install commands list and present to user for approval.
   - If the import path is wrong: run `grep -r "export.*FunctionName" src/` to find the correct path.
   - If the dependency is an AWS SDK mock: add `aws-sdk-client-mock` to dev dependencies.

4. Re-run tests after applying the fix.

### Category 2: Import Issue
**Symptoms:**
- `SyntaxError: The requested module 'X' does not provide an export named 'Y'`
- `ImportError: cannot import name 'Y' from 'X'`
- `error TS2305: Module 'X' has no exported member 'Y'`
- Named import resolves to `undefined`

**Fix Strategy:**
1. Read the source file being imported to find the correct export name.
2. Check for: named vs default export mismatch, barrel file re-exports, `index.ts` indirection.
3. Update the import statement in the test file.
4. For TypeScript: check `tsconfig.json` `paths` aliases — may require Vitest `resolve.alias` config.

### Category 3: Runtime Issue
**Symptoms:**
- Test times out (async test never resolves)
- `TypeError: X is not a function`
- `ReferenceError: X is not defined`
- Unexpected exception not caught by the test
- Environment-specific code (browser API in Node environment)

**Fix Strategy:**
1. Check for unresolved promises: add `await` to the Act step, or use `resolves/rejects` matchers.
2. Check environment: Vitest defaults to `node` — if DOM APIs needed, set `environment: 'jsdom'` in vitest.config.ts.
3. For `X is not a function`: verify the mock returns the right type (object vs function).
4. For environment-specific globals (`window`, `document`, `localStorage`): add `globals: true` to vitest config or mock them explicitly.

### Category 4: Mock Issue
**Symptoms:**
- `Mock not called` / `Expected to have been called`
- Mock returns `undefined` when a value was expected
- `Cannot spy on a non-function value`
- Original function called instead of mock (mock not hoisted)
- `vi.mock` / `jest.mock` factory not taking effect

**Fix Strategy:**
1. **Hoisting**: `vi.mock(...)` calls must be at the top of the test file (Vitest auto-hoists, but factory must be a callback, not a variable reference).
2. **Return value**: ensure mock returns the correct shape. Use `mockResolvedValue` for async, `mockReturnValue` for sync.
3. **Spy cleanup**: add `vi.clearAllMocks()` in `beforeEach` to prevent test pollution.
4. **Deep mocks**: for chained calls like `client.method().submethod()`, use `vi.fn().mockReturnThis()` for chain or mock each level separately.
5. **Module factory**: for default exports, use `{ default: vi.fn().mockReturnValue(...) }`.

### Category 5: Assertion Issue
**Symptoms:**
- `Expected X to equal Y` (value mismatch)
- Snapshot mismatch
- Type mismatch (`object` vs `string`)
- Off-by-one on numeric assertions
- Async assertion not awaited (`expect(...).resolves.toBe` not awaited)

**Fix Strategy:**
1. Log the actual output in the Act step and compare to expected.
2. For object assertions: use `toMatchObject` instead of `toEqual` when partial matching is acceptable.
3. For async assertions: ensure `await expect(promise).resolves.toBe(...)` is awaited.
4. If the assertion is wrong (not the code): fix the test's expected value to match the actual correct behavior.
5. For snapshot mismatches after intentional change: run `vitest --update-snapshots` (with user approval).

---

## Repair Loop Algorithm

```
max_iterations = 3
coverage_target = 70
iteration = 0
stall_tracker = {}  # map of (file, error_signature) → last_seen_iteration

WHILE (per_priority_targets_not_met AND iteration < max_iterations):
  // per_priority_targets_not_met = any P1 < 80% OR any P2 < 70% OR any P3 < 60% OR global < 70%
  iteration++
  
  FOR each failing test:
    1. Read the error output
    2. Categorize → Category 1..5
    3. Compute error_signature = normalize(error_message)  // strip line numbers, timestamps, file paths
    4. key = (file, error_signature)
       IF stall_tracker[key] == iteration - 1:  // same error in consecutive iteration
         MARK file as "stalled" — skip from further repair iterations
         CONTINUE to next failing test
       stall_tracker[key] = iteration
    5. Apply fix strategy for that category
    6. Re-run only the affected test file
  
  FOR each module below its per-priority threshold (P1: 80%, P2: 70%, P3: 60%):
    1. Identify uncovered lines (from coverage report)
    2. Determine why they are uncovered (branch condition? error path?)
    3. Add targeted test case for uncovered branch
    4. Re-run coverage for that module

  Run full coverage report
  Update coverage table

  // Early abort check — evaluated after iteration 1 only
  IF iteration == 1 AND global_coverage < 30%:
    EMIT triage table classifying each module below 30% as one of:
      - untestable-by-design (DOM-only code, no DI, framework internals)
      - missing-setup (requires integration test infrastructure not available in unit test env)
      - requires-refactoring (no injectable seam — direct instantiation of dependencies)
    ASK user: "Coverage is critically low (<30%) after first repair iteration.
               Continuing has low expected yield (2 iterations remaining).
               Options: (1) Continue repair  (2) Declare best-effort now"
    IF user chooses option 2: EXIT loop immediately

IF per_priority_targets_met:
  EMIT "Coverage targets achieved — P1: <N>% (≥80%), P2: <N>% (≥70%), P3: <N>% (≥60%), Global: <N>% (≥70%)"
ELSE:
  EMIT best-effort report (see below)
```

---

## Best-Effort Report (Loop Limit Reached)

When `max_iterations` is exhausted without reaching 70%:

```
BEST-EFFORT COVERAGE REPORT
============================
Iterations completed: 3 / 3
Final coverage: <N>% (target: 70%)

Modules still below threshold:
| Module | Cover% | Threshold | Blocker |
|--------|--------|-----------|---------|
| src/handlers/auth.ts | 54% | 80% P1 | Lines 89-112: AWS Cognito integration — requires live mock unavailable in env |

Stalled files (same error in two consecutive iterations — excluded from repair):
| File | Error Signature | Suggested Action |
|------|----------------|------------------|
| src/legacy/payment.ts | TypeError: Cannot read property 'X' of undefined | Requires refactoring — no injectable seam |

Suggested next steps:
1. Add integration test for AWS Cognito using LocalStack
2. Extract Cognito client to injectable interface for unit testability
3. Add contract test in a separate test suite
```

---

## Iteration Log

Maintain a running iteration log visible to the user:

```
[Repair] Iteration 1/3
  ✗ payment.service.test.ts: Category 4 (Mock Issue) — mock returns undefined
    Fix: added mockResolvedValue({ id: '1' }) to DynamoDB GetCommand mock
  ✗ order.handler.test.ts: Category 2 (Import Issue) — named export mismatch
    Fix: changed import { handler } to import { orderHandler }
  Coverage after iteration 1: 62% → 71% ✓ Target reached

[Repair] Done — coverage 71% ≥ 70% target
```
