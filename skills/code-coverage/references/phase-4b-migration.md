# Phase 4b — Jest → Vitest Migration Reference

> **HARD READ POLICY**: Loaded ONLY if `strategy.json` contains workspace with `migrate=true`. NOT summed into base context budget.

## Token transform table

Driven by `assets/vitest-jest-compat.json.api_migration_map.rewrites` (21 entries). Word-boundary regex applied:

| Jest API | Vitest API | Behavior |
|---|---|---|
| `jest.fn(` | `vi.fn(` | Direct rewrite |
| `jest.mock(` | `vi.mock(` | Direct rewrite (hoisted same as in Jest) |
| `jest.unmock(` | `vi.unmock(` | Direct rewrite |
| `jest.doMock(` | `vi.doMock(` | Direct rewrite |
| `jest.dontMock(` | `vi.doUnmock(` | Direct rewrite (note: renamed) |
| `jest.spyOn(` | `vi.spyOn(` | Direct rewrite |
| `jest.clearAllMocks(` | `vi.clearAllMocks(` | Direct rewrite |
| `jest.resetAllMocks(` | `vi.resetAllMocks(` | Direct rewrite |
| `jest.restoreAllMocks(` | `vi.restoreAllMocks(` | Direct rewrite |
| `jest.useFakeTimers(` | `vi.useFakeTimers(` | Direct rewrite |
| `jest.useRealTimers(` | `vi.useRealTimers(` | Direct rewrite |
| `jest.advanceTimersByTime(` | `vi.advanceTimersByTime(` | Direct rewrite |
| `jest.advanceTimersByTimeAsync(` | `vi.advanceTimersByTimeAsync(` | Direct rewrite |
| `jest.runAllTimers(` | `vi.runAllTimers(` | Direct rewrite |
| `jest.runOnlyPendingTimers(` | `vi.runOnlyPendingTimers(` | Direct rewrite |
| `jest.setSystemTime(` | `vi.setSystemTime(` | Direct rewrite |
| `jest.resetModules(` | `vi.resetModules(` | Direct rewrite |
| `jest.isolateModules(` | `vi.isolateModules(` | **Rewritten + flagged manual review** (ESM vs CJS semantics differ) |
| `jest.mocked(` | `vi.mocked(` | Direct rewrite |
| `jest.requireActual(` | — | **NO rewrite, flagged only** (Vitest equivalent is async; manual conversion required) |
| `jest.requireMock(` | — | **NO rewrite, flagged only** (same async caveat) |

## Edge cases requiring manual review

1. **`jest.requireActual('./x')` / `jest.requireMock('./x')`**: sync → async transition. `vi.importActual` is async; calling test must be `async` with `await`. Codemod LEAVES the original `jest.*` call and emits a `migration-report.json.files[].manual_review[]` entry with file:line for human action.

2. **`jest.isolateModules(cb)`**: Vitest has `vi.isolateModules(cb)` but execution semantics differ around top-level imports (Vitest is ESM-first). Rewritten automatically BUT also flagged.

3. **`jest.setTimeout(N)`**: file-level config not directly portable. Codemod leaves it; recommend `vi.setConfig({ testTimeout: N })` inside `beforeAll`, OR set `test.testTimeout` in `vitest.config.ts`.

4. **Types `jest.Mock<T>` / `jest.MockedFunction<T>` / `jest.SpyInstance`**: codemod does NOT auto-transform. Suggest manual: `import type { Mock, MockedFunction, MockInstance } from 'vitest';` then drop the `jest.` prefix.

5. **`@testing-library/jest-dom`**: auto-rewritten to `@testing-library/jest-dom/vitest` import path. Both `'@testing-library/jest-dom'` and `'@testing-library/jest-dom/extend-expect'` are handled.

## Config keys without Vitest equivalent (manual review)

Driven by `api_migration_map.config_keys_manual_review`:

- **`setupFilesAfterEach`**: NO Vitest equivalent. Jest runs these AFTER EACH test. Vitest's `setupFiles` runs PRE-FILE (once). Manual port: move logic into per-test `afterEach()` hooks inside the test files OR add to `setupFiles` with awareness of semantic difference.
- **`globalSetup` / `globalTeardown`**: Vitest has equivalents (`test.globalSetup`) but signature differs (Jest receives `(globalConfig, projectConfig)`, Vitest receives `(project?: VitestProject)`). Manual port required.
- **`snapshotResolver`**: Vitest uses a different snapshot strategy. Manual port.
- **`testResultsProcessor`**: Vitest uses reporters. Manual port to custom reporter.

These flagged keys appear in `migration-report.json.workspaces[].unmapped_keys[]`.

## Lockfile rollback matrix (per package manager)

Snapshot e ripristino simmetrici. Detection PM da lockfile presence (priority order: pnpm > yarn-berry > yarn > bun > npm).

| PM | Lockfile snap'd | Install fwd | Rollback restore + reinstall |
|---|---|---|---|
| npm | `package-lock.json` | `npm install` | restore `package-lock.json` → `npm ci` (frozen) |
| pnpm | `pnpm-lock.yaml` | `pnpm install` | restore `pnpm-lock.yaml` → `pnpm install --frozen-lockfile` |
| yarn classic (v1) | `yarn.lock` | `yarn install` | restore `yarn.lock` → `yarn install --frozen-lockfile` |
| yarn berry (v2+) | `yarn.lock` + `.yarnrc.yml` | `yarn install` | restore both → `yarn install --immutable` |
| bun | `bun.lockb` | `bun install` | restore `bun.lockb` → `bun install --frozen-lockfile` |

Yarn berry detection: presenza `.yarnrc.yml` AND `yarn.lock` (vs yarn classic = only `yarn.lock`).

## Rollback (manual)

If migration committed but user wants to undo:

```bash
# 1. Restore files from snapshot
cp -R .code-coverage/migration-snapshot/* .

# 2. Restore lockfile + reinstall (frozen, per PM)
# npm:
cp .code-coverage/migration-snapshot/package-lock.json . && npm ci

# pnpm:
cp .code-coverage/migration-snapshot/pnpm-lock.yaml . && pnpm install --frozen-lockfile

# yarn classic:
cp .code-coverage/migration-snapshot/yarn.lock . && yarn install --frozen-lockfile

# yarn berry:
cp .code-coverage/migration-snapshot/yarn.lock . && \
  cp .code-coverage/migration-snapshot/.yarnrc.yml . && \
  yarn install --immutable

# bun:
cp .code-coverage/migration-snapshot/bun.lockb . && bun install --frozen-lockfile

# 3. Remove vitest.config.ts if auto-generated
grep -q "Generated by code-coverage skill Phase 4b" vitest.config.ts && rm vitest.config.ts
```

## Monorepo migration policy

Per-workspace atomicity + batch failure policy:

- Workspaces processati **serial** (NOT parallel) to avoid lockfile contention.
- If workspace B fails after A committed: A stays migrated. B restored. Skill emits Block 4 partial status: `Migration partial: A=ok, B=failed, manual review required`.
- Opt-in full revert: env `CC_MIGRATION_ALL_OR_NOTHING=1` → if any workspace fails, revert ALL committed workspaces in the run.

Rationale: rollback di A dopo install success means destroying lockfile changes + rebuilt `node_modules`. Trade-off: partial-success > full-revert (preserves user time).

## Mixed jest + vitest already present

If both `jest.config.*` AND `vitest.config.ts` exist BEFORE migration:

- `vitest.config.ts` is **NOT overwritten** (preserves user customization).
- `jest.config.*` is deleted only if `vitest.config.ts` is verified parseable (contains `defineConfig` + `export default`).
- Test files codemod runs regardless (normalizes any `jest.*` to `vi.*`).
- Migration report flags this as `dual-config-detected` for awareness.

## Performance characteristics

- Detection (`detect_jest_incompat.py`): <100ms per workspace cold cache.
- Migration per small project (≤50 tests): ~30s including install.
- Migration per large monorepo (10 workspaces × 200 tests): ~10min serial.
- Smoke test (`vitest run --no-coverage`): 5-60s typical.

## Failure modes & recovery

| Failure | Skill action | User action |
|---|---|---|
| Dirty working tree | Refuse migration (exit 1) | `git stash` → retry |
| `<pm> install` exits non-zero | Snapshot retained, mark `install-failed` | Investigate package.json conflicts |
| `vitest run` exits non-zero | Snapshot restored automatically | Manual debug; possibly set `CC_KEEP_JEST=1` |
| Disk full mid-write | Snapshot restored on next run | Free disk; re-run |
| Codemod false positive in string literal | None auto | Set `CC_DISABLE_JEST_MIGRATION=1` + manual fix file |
| PM binary not in PATH | `install` skipped, no smoke test | Install PM globally, re-run |

## Idempotency

Re-running `migrate_jest_to_vitest.py` after a successful migration:
- `vitest.config.ts` exists → not overwritten.
- `package.json.scripts.test` already `vitest run` → re-rewrite is identity.
- `devDependencies.jest` absent → no removal needed.
- Test files already use `vi.*` → codemod is identity (word-boundary check).
- `jest.config.*` already deleted → no rename needed.

Net result: re-run on already-migrated repo = no-op (no diff in working tree).

## State files contract

- `.code-coverage/migration-report.json`: detailed per-workspace outcome (status, pm, files, unmapped_keys, verified).
- `.code-coverage/migration-snapshot/`: rollback bundle (mirror of repo paths).
- `migration-report.json.workspaces[].manual_review[]`: explicit list of file:trigger entries for human action post-migration.
