# Design — Code-Coverage Skill: Vitest-First Auto-Migration from Jest

**Date:** 2026-05-28
**Author:** mario.mazzacuv@siae.it (synthesis of 3 blind agent designs)
**Skill target:** `skills/code-coverage/`
**Status:** awaiting user approval at GATE

## Contesto

L'utente ha riportato un bug nella skill `code-coverage` (SKILL.md Phase 2 decision tree, righe 60-66):

> Se trova i jest ma la versione di VITEST non è incompatibile, deve sempre fare i vitest e sostituire i jest con i vitest e sistemare tutto il resto.

### Bug diagnosi

Il decision tree corrente ha bias **presence-based** invece di **incompat-based**:

1. `jest.config.{ts,js,mjs,cjs}` esiste → jest (`jest-config-present`) **← BUG: false positive**
2. `scripts.test` menziona `jest` AND `vitest` non in devDeps → jest (`jest-script-no-vitest`) **← BUG**
3. `constraints.json` lista CJS incompatibility → jest (`cjs-constraint`) **← ORPHAN: file inesistente**
4. `constraints.json` lista legacy-jest → jest (`legacy-constraint`) **← ORPHAN**
5. Else → vitest (`vitest-first-default`)

Le rule 1+2 firano sulla SOLA presenza di artefatti Jest, contraddicendo Principle 4 ("Vitest-first for JS/TS"). Rule 3+4 sono dead code (constraints.json non esiste nel repo).

Lo stesso bug è duplicato in `scripts/validate_env.py:117-151` (`_detect_required_framework`).

## Decisione

**Invertire il bias**: Vitest è il default ASSOLUTO per JS/TS. Jest è selezionato SOLO se firma una incompatibilità tecnica reale. Quando Jest è rilevato come **legacy artifact** (config presente, script lo usa, deps presenti) ma nessuna incompatibilità reale fira → la skill **migra il progetto a Vitest** in modo atomico (snapshot + verify + rollback).

## Approcci valutati (3 blind agent paralleli)

Pattern multi-blind-agent gap-finding dalla memoria (vedi `feedback_multi_blind_agent_consensus`):

| Dimensione | AGENT-1 | AGENT-2 | AGENT-3 | Scelto |
|---|---|---|---|---|
| Modello signal | 10 (I9 monorepo Jest<27) | 10 (H3 resolver, H9 doMock+require) | 8 (skip monorepo + globalSetup) | **Union AGENT-1+2 = 10 signal** |
| Rollback safety | snapshot + .OLD.bak | **snapshot + lockfile.bak + dirty-tree REFUSE** | snapshot solo | **AGENT-2** |
| Smoke test | 1 file, 60s | **full `vitest run`, 120s** | nessuno | **AGENT-2** |
| Phase 1 integration | invoke in Phase 2 | **parallel in phase1-discover.sh** | invoke in Phase 2 | **AGENT-2** |
| validate_env.py update | sì | **sì (delega a jest-compat.json)** | NO (manca) | **AGENT-2** |
| strategy.json schema | `migration_needed: true` | **`migrate: true` (bool)** | reason-only | **AGENT-2** |
| Vitest config template | template literal | regex+best-effort | **placeholder + globals:true** | **AGENT-3** |
| Token transforms | 18 mappings | 19 mappings | 14 mappings | **Union = 21 mappings** |

**Approccio scelto**: ibrido **base AGENT-2** (rollback safety + parallel discovery + validate_env update) + **I9 di AGENT-1** + **template di AGENT-3** + **union token transforms**.

### Trade-off chiave

| Pro | Contro | Mitigazione |
|---|---|---|
| Vitest-first allineato a Principle 4 | Migrazione automatica può rompere repo legacy | Snapshot + verify + rollback + dirty-tree refuse |
| Closed list signal = deterministic | Servono nuovi signal in futuro per casi non noti | Asset JSON versionato + ADD-only |
| Phase 4b atomica | Smoke test 120s = lento su monorepo grandi | Per-workspace isolamento; opt-out via env |
| Codemod regex con word-boundary | Possibili miss su template literals con `jest.fn` | Verify gate cattura; manual review flag |

**SP stimati**: 8 SP (Umano, ~2 giorni) / 5 SP (Augmented con questi agent paralleli + sintesi)

## Architettura

### File creati (4)
1. `assets/vitest-jest-compat.json` — closed list 10 signal + token map + config map **[drafted durante synth blind agent — da validare/finalizzare, NON ricreare]**
2. `scripts/detect_jest_incompat.py` — signal evaluator (~280 LOC)
3. `scripts/migrate_jest_to_vitest.py` — migration engine (~450 LOC)
4. `references/phase-4b-migration.md` — lazy-loaded reference

> **Nota (amendment-2 spec-review)**: `vitest-jest-compat.json` esiste già nel working tree del branch dopo lo step di synth dei 3 blind agent. Va trattato come **drafted/da validare** durante TDD, non "da creare ex novo".

### File patched (4)
1. `SKILL.md` — Phase 2 decision tree (lines 60-66), nuovo Phase 4b, Principle 1
2. `scripts/validate_env.py` — `_detect_required_framework` (lines 117-151)
3. `lib/phase1-discover.sh` — parallel compat detection
4. `lib/state-schema.json` — schema additions (migrate flag, jest-compat.json, migration-report.json)

### Test files (3)
- `scripts/tests/test_detect_jest_incompat.py` — 15+ tests, copre I1..I10
- `scripts/tests/test_migrate_jest_to_vitest.py` — 10+ tests (idempotency, dirty-tree refuse, opt-out, codemod)
- `scripts/tests/test_phase2_decision_tree.py` — 5 archetipi end-to-end

### Closed list incompatibility signals (I1..I10)

| ID | Nome | Detection |
|---|---|---|
| I1 | react-native | deps `react-native` OR `@react-native/*` OR `metro.config.*` OR jest preset `react-native`/`jest-expo` |
| I2 | vue-cli-jest-preset | jest preset `@vue/cli-plugin-unit-jest` AND no `vite`/`@vitejs/plugin-vue` |
| I3 | angular-jest-preset | jest preset `jest-preset-angular` AND no `@analogjs/vitest-angular` |
| I4 | node-lt-18 | `engines.node` o `.nvmrc` < 18.0.0 |
| I5 | custom-local-transformer | `transform:` fuori allowlist {ts-jest, babel-jest, @swc/jest, esbuild-jest} |
| I6 | custom-local-resolver | `resolver:` punta a `./...` (file locale) |
| I7 | ts-jest-ast-transformers | `astTransformers:` con contenuto |
| I8 | custom-test-environment | `testEnvironment` fuori allowlist {node, jsdom, happy-dom + jest-environment-*} |
| I9 | jest-lt-27 | `devDeps.jest` < 27.0.0 (legacy jest-jasmine2 runner) |
| I10 | force-jest-override | env `CC_DISABLE_JEST_MIGRATION=1` o `CC_KEEP_JEST=1` o `.code-coverage/overrides.json.force_jest=true` |

### Decision tree v2 (Phase 2)

```
Input: .code-coverage/jest-compat.json (workspaces[ws])

1. workspaces[ws].incompatibility_signals contiene I10
   → jest, reason="force-jest-override:<reason>", migrate=false
2. workspaces[ws].incompatibility_signals non vuoto (escluso I10)
   → jest, reason="hard-incompat:I1,I3,..", migrate=false
3. workspaces[ws].has_jest_artifacts == true
   → vitest, reason="jest-legacy-migrating-to-vitest", migrate=true  ← THE FIX
4. else
   → vitest, reason="vitest-first-default", migrate=false
```

### Phase 4b (nuova)

Trigger: any workspace con `migrate=true`.

Pipeline atomica:
1. **Pre-flight**: `git status` su file touched → se dirty, REFUSE + Block 4
2. **Snapshot**: copy `package.json`, `jest.config.*`, `jest.setup.*`, lockfile, all `*.{test,spec}.*` → `.code-coverage/migration-snapshot/<workspace_hash>/`
3. **Translate** `jest.config.* → vitest.config.ts` (skip se esiste). Per chiavi in `config_keys_manual_review` (`setupFilesAfterEach`, `globalSetup`, `globalTeardown`, `snapshotResolver`, `testResultsProcessor`) emette entry in `migration-report.json.manual_review[]` e NON le riscrive
4. **Rewrite** `package.json` (scripts: jest→vitest run; devDeps: remove jest stack, add vitest)
5. **Codemod** test files (21 mappings). Token in `no_rewrite_tokens` (`jest.requireActual`, `jest.requireMock`) NON vengono riscritti — solo flaggati in `migration-report.json.manual_review[]` con file:line. Token in `manual_review_triggers` (`jest.isolateModules`, `jest.setTimeout`, types `jest.Mock<`/`MockedFunction`/`SpyInstance`) vengono riscritti MA emettono anche entry manual_review per audit umano
6. **Rename** `jest.setup.* → vitest.setup.*` + transform `@testing-library/jest-dom`→`/vitest`
7. **Install** (per-PM matrix — vedi sezione "Lockfile rollback matrix" più sotto)
8. **Verify**: `npx vitest run --reporter=basic --no-coverage` con timeout 120s
9. **Commit** (delete jest.config.* dopo verify) OR **Rollback** (restore snapshot + reinstall lockfile-frozen)

### Lockfile rollback matrix (BLOCK-1 amendment)

Snapshot e ripristino devono essere simmetrici per package manager. Detection PM da lockfile presence (priority order: pnpm > yarn > bun > npm).

| PM | Lockfile snap'd | Install fwd | Rollback restore + reinstall |
|---|---|---|---|
| npm | `package-lock.json` | `npm install` | restore `package-lock.json` → `npm ci` (frozen) |
| pnpm | `pnpm-lock.yaml` | `pnpm install` | restore `pnpm-lock.yaml` → `pnpm install --frozen-lockfile` |
| yarn classic (v1) | `yarn.lock` | `yarn install` | restore `yarn.lock` → `yarn install --frozen-lockfile` |
| yarn berry (v2+) | `yarn.lock` + `.yarnrc.yml` + `.yarn/install-state.gz` | `yarn install` | restore tutti e 3 → `yarn install --immutable` |
| bun | `bun.lockb` | `bun install` | restore `bun.lockb` → `bun install --frozen-lockfile` |

Rollback completo lascia `node_modules` consistente con lockfile pre-migration. Detection yarn berry: presenza `.yarnrc.yml` con `nodeLinker` o `.yarn/releases/`.

### Monorepo rollback policy (amendment ADR-5)

Per-workspace atomicità + **batch failure policy**:
- Ogni workspace ha snapshot dir separato (`.code-coverage/migration-snapshot/<workspace_hash>/`).
- Workspaces processati seriale (NON parallel) per evitare lockfile contention.
- Se workspace B fallisce e A è già committed: A resta migrato (NON revert), B viene ripristinato. La skill emette Block 4 "Migration partial: A=ok, B=failed, manual review required" + dettagli in `migration-report.json.workspaces[].status`.
- Rationale: rollback di A dopo install success significherebbe distruggere lockfile cambiato + `node_modules` rebuilt. Trade-off: partial-success > full-revert (tutela tempo ricostruzione utente).
- Opt-in full-revert: env `CC_MIGRATION_ALL_OR_NOTHING=1` → se any workspace fail, revert tutti i workspace già committed in questa run (richiede snapshot tar di package-lock root in monorepo).

## Criteri di accettazione

- [ ] Phase 2 emette `framework=vitest, migrate=true` quando Jest presente + nessun signal I1..I10
- [ ] Phase 2 emette `framework=jest, migrate=false` quando ANY signal I1..I10 fira
- [ ] Phase 4b non parte se working tree dirty su file target (refuse + Block 4)
- [ ] Phase 4b ripristina snapshot se smoke test fallisce (per-workspace, simmetrico per PM)
- [ ] `validate_env.py._detect_required_framework` delega a `jest-compat.json`
- [ ] `phase1-discover.sh` lancia `detect_jest_incompat.py` in parallelo
- [ ] Codemod idempotente (run 2x su stesso input = no-op)
- [ ] Opt-out via `CC_DISABLE_JEST_MIGRATION=1` o `overrides.json.force_jest`
- [ ] Token in `no_rewrite_tokens` (requireActual/requireMock) NON riscritti, solo flaggati
- [ ] Chiavi in `config_keys_manual_review` NON riscritte, solo flaggate
- [ ] Lockfile rollback matrix corretta per npm/pnpm/yarn-v1/yarn-berry/bun (test per ogni PM)
- [ ] **Test suite**: `test_detect_jest_incompat.py` ≥15 test (1 per signal + edge cases + monorepo), `test_migrate_jest_to_vitest.py` ≥10 test (idempotency + dirty-tree refuse + opt-out + codemod + lockfile rollback per PM), `test_phase2_decision_tree.py` ≥5 archetipi end-to-end → **totale ≥30 test new**
- [ ] **Zero regression**: i test esistenti in `skills/code-coverage/scripts/tests/` (26 file pre-esistenti) passano post-patch
- [ ] Orphan reference `constraints.json` rimosso da SKILL.md (Phase 2 rules 3+4)

## ADR (Architecture Decision Records)

### ADR-1: Closed list invece di heuristic detection
Una closed list di 10 signal deterministici (JSON declarativo) anziché euristica adattiva.
**Rationale:** determinismo > completezza. Ogni signal = file evidence regex/JSON match, no LLM judgment, no eval di user code.

### ADR-2: Migrazione automatica full vs partial/report-only
Migration **completa** (config + package.json + test files + setup), non report-only o partial.
**Rationale:** User ha detto "sistemare tutto il resto". Partial = due test runner coesistenti = CI rotto. Mitigazione: snapshot + verify gate.

### ADR-3: Dirty-tree refuse invece di force-overwrite
La skill **rifiuta** la migration se working tree contiene modifiche unstaged sui file target.
**Rationale:** preservare lavoro utente è invariante > automation. Workaround utente: `git stash`.

### ADR-4: Vitest pinned a ^1.6.0
Non `latest`, non `^2.x`.
**Rationale:** Vitest 2.x ha cambiato default (pool, deps); 1.6 è stable ecosystem. Bump = future PR.

### ADR-5: Per-workspace decisione in monorepo
Ogni workspace valuta i signal indipendentemente.
**Rationale:** monorepo con 1 workspace RN (I1) + 4 lib (compatible) → solo le lib migrano. Atomicità per workspace.

### ADR-6: Codemod regex con word-boundary
No AST parsing (no babel/ts-morph dependency).
**Rationale:** pattern `\bjest\.fn\(` con boundary check è safe per 99% casi reali; per ASTrisk si penalizza con complessità install. Manual review flag cattura edge case.

## Stato Phase 2 -> Phase 7

Workflow esistente preservato:
- Phase 1 (discovery) → ora include compat eval in parallelo
- Phase 2 (strategy) → decision tree v2
- Phase 3 (sizing) → invariato
- Phase 4 (env install) → invariato
- **Phase 4b (NEW) — migration**, condizionale su `migrate=true`
- Phase 5 (generation) → invariato (genera Vitest tests; migration ha già normalizzato esistenti)
- Phase 6 (coverage) → invariato
- Phase 7 (repair) → invariato

## Rischi e mitigazioni

| Rischio | Severity | Mitigazione |
|---|---|---|
| Migrazione rompe progetto reale | HIGH | Snapshot+verify+rollback+dirty-tree refuse |
| Smoke test 120s rallenta CI | MEDIUM | Opt-out `CC_DISABLE_JEST_MIGRATION=1` |
| Codemod miss su template literal | LOW | Manual review flag + verify gate |
| `jest.requireActual` async transformation | MEDIUM | Flag manual review esplicito |
| Orphan constraints.json rimosso = silent break su SKILL consumer | LOW | Nessun consumer noto |

## Out of scope (deferred)

- Vitest 2.x/3.x targeting (separate PR)
- Babel preset translation (esbuild copre 99%)
- CI YAML changes (utente gestisce)
- Auto bump @testing-library/* versions
- LSP/AST-based codemod (regex sufficiente)

## SKILL.md HARD READ POLICY update (amendment-5 spec-review)

SKILL.md `HARD READ POLICY (CONTEXT BUDGET)` (linee 22-26) deve essere aggiornata per documentare che `references/phase-4b-migration.md` è **conditional** (non sommato nel budget base):

```diff
-Combined refs after A3 inline = phase-3-sizing.md (~150 LOC) + phase-5-generation.md (~250 LOC) + phase-7-repair.md (~120 LOC) ≈ 520 LOC / ~6 KB.
+Combined refs after A3 inline = phase-3-sizing.md (~150 LOC) + phase-5-generation.md (~250 LOC) + phase-7-repair.md (~120 LOC) ≈ 520 LOC / ~6 KB.
+Conditional refs (loaded only if trigger fires, NOT in base budget):
+- references/phase-4b-migration.md (~120 LOC): caricato SOLO se strategy.json contiene workspace con migrate=true.
+- references/java-siae-quirks.md (~variable): caricato SOLO se Java/Maven detected (vedi Phase 4 loader).
```

Questo allinea Phase 4b al pattern di progressive disclosure esistente per `java-siae-quirks.md`.

## Amendments tracker

| Amendment | Origin | Status | Where fixed |
|---|---|---|---|
| BLOCK-1: lockfile rollback matrix per PM | spec-review | ✓ FIXED | sezione "Lockfile rollback matrix" |
| Amendment-2: vitest-jest-compat.json già drafted | spec-review | ✓ FIXED | sezione "File creati (4)" + nota |
| Amendment-3: monorepo rollback policy | spec-review | ✓ FIXED | sezione "Monorepo rollback policy" |
| Amendment-4: manual_review_triggers flag-only | spec-review | ✓ FIXED | Pipeline atomica step 5 + asset compat.json |
| Amendment-5: HARD READ POLICY phase-4b | spec-review | ✓ FIXED | questa sezione (above) |
| WARN-2: setupFilesAfterEach mapping | spec-review | ✓ FIXED | asset compat.json (MANUAL_REVIEW_NOT_EQUIVALENT) |
| WARN-3: @babel/preset-typescript spurious | spec-review | ✓ FIXED | asset compat.json I5 allowlist (rimosso) |
| WARN: criteri quantificati | spec-review | ✓ FIXED | sezione "Criteri di accettazione" (≥30 test, 26 esistenti) |
