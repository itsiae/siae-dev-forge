# Task 09 — Patch SKILL.md (Phase 2 + Phase 4b + Principle 1 + HARD READ POLICY) + remove orphan constraints.json

**Status:** `[PENDING]`
**Depends on:** task-08
**Estimate:** 15 min
**Files:**
- `skills/code-coverage/SKILL.md` (multiple PATCHes)

## Goal

Aggiornare SKILL.md per riflettere:
1. Nuovo decision tree Phase 2 (3 rule, no constraints.json)
2. Nuovo Phase 4b (migrazione condizionale)
3. Principle 1 aggiornato (jest.config.* deletion + test file token rewrite in scope)
4. HARD READ POLICY include `references/phase-4b-migration.md` come conditional

## Steps

### A. Replace Phase 2 (lines 57-74)

Trovare il blocco:
```
### Phase 2 — Strategy
...
1. `jest.config.{ts,js,mjs,cjs}` exists → `jest` (reason `jest-config-present`).
2. Else `package.json.scripts.test` mentions `jest` AND `vitest` not in devDeps → `jest` (reason `jest-script-no-vitest`).
3. Else `constraints.json` lists CJS incompatibility → `jest` (reason `cjs-constraint`).
4. Else `constraints.json` lists legacy-jest → `jest` (reason `legacy-constraint`).
5. Else → `vitest` (reason `vitest-first-default`).
```

Sostituirlo con:

```markdown
### Phase 2 — Strategy

Single source: `assets/stack-matrix.json` + `assets/vitest-jest-compat.json`. Output: `framework_by_workspace` (in-memory + `.code-coverage/strategy.json`), plus `[phase2] workspace=<path> stack=<lang> framework=<fw> reason=...` in `decisions.log`.

**Vitest-first decision tree (JS/TS per workspace) — Migration-aware:**

The mere presence of `jest.config.*` or `jest` in `scripts.test` is NOT an incompatibility — it's the current setup. The skill MIGRATES Jest→Vitest unless a real technical incompatibility signal (I1..I10 in `assets/vitest-jest-compat.json`) fires.

Phase 1 has already produced `.code-coverage/jest-compat.json` via `scripts/detect_jest_incompat.py`. Phase 2 reads it and applies (first match wins):

| Compat decision | framework | migrate | reason |
|---|---|---|---|
| `jest-forced` (I10) | `jest` | `false` | `force-jest-override:<reason>` |
| `jest-incompat` (any I1..I9) | `jest` | `false` | `hard-incompat:<comma-joined-signals>` |
| `vitest-migrate` (jest artifacts + no signal) | `vitest` | `true` | `jest-legacy-migrating-to-vitest` (triggers Phase 4b) |
| `vitest-default` (no jest at all) | `vitest` | `false` | `vitest-first-default` |

**Opt-out**: `CC_DISABLE_JEST_MIGRATION=1` or `CC_KEEP_JEST=1` env vars, OR `.code-coverage/overrides.json` with `{"force_jest": true, "force_jest_reason": "<reason>"}`. Both surface as signal I10.

Other stacks (Python/Java/Kotlin/Go/Rust/C#/Flutter) → direct lookup in `assets/stack-matrix.json`. No heuristics beyond the matrix.

**Lambda variant (JS/TS):** if `stack.json.is_lambda == true`, files matching `priority-rules.json.lambda_handler_globs` (default `*handler.ts`, `*lambda.ts`) → template `vitest-lambda-handler`; others → standard `vitest`.

**Monorepo:** iterate `stack.json.workspaces[]`, apply tree per workspace. Workspaces with `framework == "unknown"` are logged as `skipped reason=unsupported-language` and listed in Block 4. Each workspace is decided INDEPENDENTLY — a monorepo can have a mix of `vitest` (migrating or fresh) and `jest` (kept due to incompat) workspaces.

**Gate:** if ALL workspaces resolve to `unknown` → emit Block 4 + END.
```

### B. Insert new Phase 4b (after Phase 4 Vitest config generation, before "Blocking Check Handler")

Trovare in Phase 4 il paragrafo `**Vitest config generation:** only if vitest.config.ts ABSENT...`. Dopo questo paragrafo, PRIMA di `**Blocking Check Handler:**`, inserire:

```markdown
**Jest→Vitest migration (Phase 4b — conditional):** For any workspace with `strategy.json.framework_by_workspace[ws].migrate == true`:

```bash
python3 skills/code-coverage/scripts/migrate_jest_to_vitest.py "<repo>"
# Exit codes:
#   0 = migration committed + smoke-verified
#   1 = refused (dirty working tree / install failed)
#   2 = verification failed, snapshot restored
#   4 = no migrating workspaces (no-op)
```

Migration pipeline (per workspace, atomic):
1. **Dirty-tree pre-flight**: `git status` su file touched → if dirty, REFUSE + Block 4 entry
2. **Snapshot** package.json + jest.config.* + jest.setup.* + lockfile + all *.{test,spec}.* → `.code-coverage/migration-snapshot/`
3. **Translate** `jest.config.* → vitest.config.ts` (skip if exists). Keys in `config_keys_manual_review` (`setupFilesAfterEach`, `globalSetup`, `globalTeardown`, etc.) are flagged in `migration-report.json.unmapped_keys[]`, NOT rewritten.
4. **Rewrite** `package.json` (scripts: jest→vitest run; devDeps: remove jest stack, add vitest)
5. **Codemod** test files via `assets/vitest-jest-compat.json.api_migration_map.rewrites` (21 mappings). Tokens in `no_rewrite_tokens` (`jest.requireActual`, `jest.requireMock`) are flagged but NOT rewritten.
6. **Rename** `jest.setup.* → vitest.setup.*` + transform `@testing-library/jest-dom` → `/vitest`
7. **Install** per-PM (npm/pnpm/yarn/yarn-berry/bun detected from lockfile)
8. **Smoke verify**: `npx vitest run --reporter=basic --no-coverage` timeout 120s
9. **Commit** (delete jest.config.* after verify) OR **Rollback** (restore snapshot + frozen-lockfile reinstall)

Outputs: `.code-coverage/migration-report.json` + `.code-coverage/migration-snapshot/`. Manual review entries surface in Block 9.

Lazy-loaded reference: `references/phase-4b-migration.md` (loaded ONLY if any workspace has `migrate=true` — see HARD READ POLICY).
```

### C. Update Principle 1 (around line 30)

Trovare:
```
1. **Autonomous execution.** Invocation = blanket approval for read/write/install in `.code-coverage/`, test dirs, `vitest.config.ts`/`jest.config.ts` if absent, and `devDependencies`. Never modify production source. Decisions → `.code-coverage/decisions.log`. ZERO prompts.
```

Sostituire con:

```
1. **Autonomous execution.** Invocation = blanket approval for read/write/install in `.code-coverage/`, test dirs, `vitest.config.ts` (create if absent), `jest.config.*` (delete during Phase 4b migration with snapshot), `package.json` `scripts`/`devDependencies` keys only, and existing `*.{test,spec}.*` files for Jest→Vitest token transforms during Phase 4b. Never modify production source. Decisions → `.code-coverage/decisions.log`. ZERO prompts.
```

### D. Update HARD READ POLICY (lines 22-26)

Trovare:
```
Combined refs after A3 inline = phase-3-sizing.md (~150 LOC) + phase-5-generation.md (~250 LOC) + phase-7-repair.md (~120 LOC) ≈ 520 LOC / ~6 KB.
```

Append dopo questo blocco:

```markdown
Conditional refs (loaded ONLY if trigger fires — NOT in base budget):
- `references/phase-4b-migration.md` (~120 LOC): caricato SOLO se `strategy.json` contiene workspace con `migrate=true`.
- `references/java-siae-quirks.md` (~variable): caricato SOLO se Java/Maven detected (vedi Phase 4 loader).
```

### E. Update Principle 4 (around line 33-34)

Trovare:
```
4. **Vitest-first for JS/TS** (decision tree inlined in Phase 2 below). Deviate to Jest only on documented constraints.
```

Sostituire con:

```
4. **Vitest-first for JS/TS, with auto-migration from Jest.** When the project uses Jest but Vitest is compatible (closed list of incompatibility signals I1..I10 in `assets/vitest-jest-compat.json`), Phase 4b migrates `jest.config.*`, `package.json` scripts/devDeps, and test files (codemod) to Vitest. Jest is retained ONLY when ≥1 signal in I1..I9 fires, or I10 user opt-out is active.
```

### F. Verify

```bash
grep -c "constraints.json" skills/code-coverage/SKILL.md
# Expected: 0 (orphan refs removed)
```

## Acceptance

- [ ] Phase 2 section rewritten (no constraints.json refs)
- [ ] Phase 4b inserted after Phase 4 (before Blocking Check Handler)
- [ ] Principle 1 updated (scope explicit)
- [ ] Principle 4 updated (auto-migration mentioned)
- [ ] HARD READ POLICY mentions phase-4b as conditional
- [ ] `grep "constraints.json" SKILL.md` returns 0 hits
- [ ] SKILL.md still parseable (read sections 1-260 sanity)
