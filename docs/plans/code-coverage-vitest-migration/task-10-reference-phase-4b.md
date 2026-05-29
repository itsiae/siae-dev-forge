# Task 10 — Create references/phase-4b-migration.md

**Status:** `[PENDING]`
**Depends on:** task-09
**Estimate:** 10 min
**Files:**
- `skills/code-coverage/references/phase-4b-migration.md` (NEW)
- `skills/code-coverage/references/index.md` (PATCH: add entry)

## Goal

Lazy-loaded reference per Phase 4b migration. Loaded ONLY se any workspace ha `migrate=true`. Documenta token transform table completa, edge cases (RN/Vue CLI/Angular), rollback manuale, monorepo policy.

## Steps

### A. Create `references/phase-4b-migration.md`

```markdown
# Phase 4b — Jest → Vitest Migration Reference

> **HARD READ POLICY**: Caricare SOLO se `strategy.json` contiene workspace con `migrate=true`. NON sommato nel base context budget.

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
| `jest.runAllTimers(` | `vi.runAllTimers(` | Direct rewrite |
| `jest.runOnlyPendingTimers(` | `vi.runOnlyPendingTimers(` | Direct rewrite |
| `jest.setSystemTime(` | `vi.setSystemTime(` | Direct rewrite |
| `jest.resetModules(` | `vi.resetModules(` | Direct rewrite |
| `jest.isolateModules(` | `vi.isolateModules(` | **Rewritten + flagged manual review** (semantic differences ESM vs CJS) |
| `jest.mocked(` | `vi.mocked(` | Direct rewrite |
| `jest.requireActual(` | — | **NO rewrite, flagged only** (Vitest equivalent `vi.importActual` is async; manual conversion required) |
| `jest.requireMock(` | — | **NO rewrite, flagged only** (same async caveat) |

## Edge cases requiring manual review

1. **`jest.requireActual('./x')` / `jest.requireMock('./x')`**: sync → async transition. `vi.importActual` is async; the calling test must be `async` and `await` must be added. Codemod LEAVES the original `jest.*` call and emits a `migration-report.json.files[].manual_review[]` entry with file:line for human action.

2. **`jest.isolateModules(cb)`**: Vitest has `vi.isolateModules(cb)` but execution semantics differ around top-level imports (Vitest is ESM-first; isolation semantics for CJS dynamic require may break). Rewritten automatically BUT also flagged.

3. **`jest.setTimeout(N)`**: file-level config not directly portable. Codemod leaves it; recommend `vi.setConfig({ testTimeout: N })` inside `beforeAll`, OR set `test.testTimeout` in `vitest.config.ts`.

4. **Types `jest.Mock<T>` / `jest.MockedFunction<T>` / `jest.SpyInstance`**: codemod does NOT auto-transform. Suggest manual: `import type { Mock, MockedFunction, MockInstance } from 'vitest';` then drop the `jest.` prefix.

5. **`@testing-library/jest-dom`**: auto-rewritten to `@testing-library/jest-dom/vitest` import path.

## Config keys without Vitest equivalent (manual review)

Driven by `config_keys_manual_review`:
- `setupFilesAfterEach`: NO Vitest equivalent. Jest runs these AFTER EACH test. Vitest's `setupFiles` runs PRE-FILE (once). Manual port: move logic into per-test `afterEach()` hooks inside the test files OR add to `setupFiles` with awareness of semantic difference.
- `globalSetup` / `globalTeardown`: Vitest has equivalents (`test.globalSetup`) but signature differs (Jest receives `(globalConfig, projectConfig)`, Vitest receives `(project?: VitestProject)`). Manual port required.
- `snapshotResolver`: Vitest uses a different snapshot strategy. Manual port.
- `testResultsProcessor`: Vitest uses reporters. Manual port to custom reporter.

## Rollback (manual)

If migration committed but user wants to undo:

```bash
# 1. Restore files from snapshot
cp -R .code-coverage/migration-snapshot/* .

# 2. Restore lockfile + reinstall (frozen)
# For npm:
cp .code-coverage/migration-snapshot/package-lock.json . && npm ci
# For pnpm:
cp .code-coverage/migration-snapshot/pnpm-lock.yaml . && pnpm install --frozen-lockfile
# For yarn (classic):
cp .code-coverage/migration-snapshot/yarn.lock . && yarn install --frozen-lockfile
# For yarn berry:
cp .code-coverage/migration-snapshot/yarn.lock . && cp .code-coverage/migration-snapshot/.yarnrc.yml . && yarn install --immutable
# For bun:
cp .code-coverage/migration-snapshot/bun.lockb . && bun install --frozen-lockfile

# 3. Remove vitest.config.ts if it was auto-generated
grep -q "AUTO-MIGRATED-FROM" vitest.config.ts && rm vitest.config.ts
```

## Monorepo migration policy

Per-workspace atomicity + batch failure policy:
- Workspaces processed **serially** (NOT parallel) to avoid lockfile contention.
- If workspace B fails after A committed: A stays migrated. B restored. Skill emits Block 4 with partial status.
- Opt-in full revert: env `CC_MIGRATION_ALL_OR_NOTHING=1` → if any workspace fails, revert ALL committed workspaces in the run.

## Mixed jest + vitest already present

If both `jest.config.*` AND `vitest.config.ts` exist BEFORE migration:
- `vitest.config.ts` is **NOT overwritten** (preserves user customization).
- `jest.config.*` is deleted only if `vitest.config.ts` is verified parseable.
- Test files codemod runs regardless (normalizes any `jest.*` to `vi.*`).
- Migration report flags this as `dual-config-detected` for awareness.

## Performance characteristics

- Detection (`detect_jest_incompat.py`): <100ms per workspace cold cache.
- Migration per small project (≤50 tests): ~30s including install.
- Migration per large monorepo (10 workspaces × 200 tests): ~10min.
- Smoke test (`vitest run --no-coverage`): 5-60s typical.

## Failure modes & recovery

| Failure | Skill action | User action |
|---|---|---|
| Dirty working tree | Refuse migration | `git stash` → retry |
| `npm install` exits non-zero | Snapshot restored, mark `install-failed` | Investigate package.json conflicts |
| `vitest run` exits non-zero | Snapshot restored, mark `verification-failed` | Manual debug; possibly set `CC_KEEP_JEST=1` |
| Disk full mid-write | Snapshot restored on next run | Free disk; re-run |
| Codemod over-aggressive (false positive in string literal) | None auto | Open issue; meanwhile manually fix file or set `CC_DISABLE_JEST_MIGRATION=1` |
```

### B. Update `references/index.md`

Aggiungere entry alla tabella/list dei reference:

```markdown
- `phase-4b-migration.md` — Jest→Vitest migration reference. **Conditional**: loaded ONLY if any workspace in strategy.json has `migrate=true`. Covers token transform table, edge cases, manual rollback, monorepo policy.
```

## Acceptance

- [ ] `references/phase-4b-migration.md` creato (~140 LOC)
- [ ] `references/index.md` aggiornato con entry conditional
- [ ] Token transform table copre tutte le 21 rewrites + 2 no-rewrite
- [ ] Rollback documentato per tutti i 5 PM
- [ ] Monorepo policy documentata (serial + per-workspace + opt-in full-revert)
