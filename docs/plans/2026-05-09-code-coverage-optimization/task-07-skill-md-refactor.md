# Task 07 — SKILL.md Refactor (P7 + P9 + P11 + ST5)

**Goal:** Inline phase-1/2/6/7 entry-points in SKILL.md (≤220 LOC); cancellare phase-1/2/6/7 reference files; cancellare Detection File Inventory; consolidare single source of truth (Vitest-first SKILL.md only, install→`assets/install-snippets.json`, mocking→template+1 paragrafo rationale); creare `assets/few-shot-e2e.md` + `assets/anti-patterns.md` lazy-load.

**SP:** 1.5 (Augmented)
**Fix IDs covered:** P7 + P9 + P11 + ST5
**Branch:** `feat/code-coverage-opt-skill-refactor`
**Dipendenze:** task-03 (parser disponibile, Phase 6 può essere inlined), task-04 (repair logic in script, Phase 7 può essere inlined)

---

## File coinvolti

**Cancellazione**:
- `skills/code-coverage/references/phase-1-discovery.md`
- `skills/code-coverage/references/phase-2-strategy.md`
- `skills/code-coverage/references/phase-6-coverage.md` (logica già in scripts/parse_coverage.py post-PR3)
- `skills/code-coverage/references/phase-7-repair.md` (logica già in scripts/categorize_failure.py post-PR4)

**Modifica**:
- `skills/code-coverage/SKILL.md` (REFACTOR completo, target ≤220 LOC)
- `skills/code-coverage/references/phase-3-sizing.md` (TRIM minor: rimuovi Quick Sizing references)
- `skills/code-coverage/references/phase-4-environment.md` (TRIM da 263 a ~80 LOC)
- `skills/code-coverage/references/phase-5-generation.md` (TRIM mocking patterns sezione, ~140 LOC rimosse)
- `skills/code-coverage/templates/*.template.*` (aggiungi 1 paragrafo rationale all'inizio)

**Creazione**:
- `skills/code-coverage/assets/few-shot-e2e.md` (~80 LOC: example T1 source → grep → test completo)
- `skills/code-coverage/assets/anti-patterns.md` (~50 LOC: 3 BAD/GOOD pairs)
- `skills/code-coverage/assets/install-snippets.json` (~150 LOC: install commands per framework)

---

## Step bite-sized

### Step 1 — Branch + verifica task-03 e task-04 merged

```bash
git checkout main && git pull
git checkout -b feat/code-coverage-opt-skill-refactor
test -f skills/code-coverage/scripts/parse_coverage.py && echo "task-03 merged"
test -f skills/code-coverage/scripts/categorize_failure.py && echo "task-04 merged"
```

### Step 2 — Crea `assets/install-snippets.json`

```json
{
  "vitest": {
    "command": "npm install --save-dev vitest @vitest/coverage-v8",
    "alt_yarn": "yarn add --dev vitest @vitest/coverage-v8",
    "alt_pnpm": "pnpm add -D vitest @vitest/coverage-v8",
    "manual_manifest_edit": null
  },
  "jest": {
    "command": "npm install --save-dev jest @types/jest ts-jest",
    "alt_yarn": "yarn add --dev jest @types/jest ts-jest",
    "alt_pnpm": "pnpm add -D jest @types/jest ts-jest",
    "manual_manifest_edit": null
  },
  "pytest": {
    "command": "pip install pytest pytest-cov",
    "alt_poetry": "poetry add --group=dev pytest pytest-cov",
    "manual_manifest_edit": null
  },
  "junit5": {
    "command": null,
    "manual_manifest_edit": "Aggiungi a pom.xml dependencies:\n  <dependency>\n    <groupId>org.junit.jupiter</groupId>\n    <artifactId>junit-jupiter</artifactId>\n    <version>5.10.0</version>\n    <scope>test</scope>\n  </dependency>\n  <dependency>\n    <groupId>org.mockito</groupId>\n    <artifactId>mockito-core</artifactId>\n    <version>5.5.0</version>\n    <scope>test</scope>\n  </dependency>"
  },
  "junit5-gradle": {
    "command": null,
    "manual_manifest_edit": "Aggiungi a build.gradle dependencies:\n  testImplementation 'org.junit.jupiter:junit-jupiter:5.10.0'\n  testImplementation 'org.mockito:mockito-core:5.5.0'\nE in test block: useJUnitPlatform()"
  },
  "mockk": {
    "command": null,
    "manual_manifest_edit": "Aggiungi a build.gradle.kts:\n  testImplementation(\"io.mockk:mockk:1.13.8\")"
  },
  "cargo-test": {
    "command": null,
    "manual_manifest_edit": "Aggiungi a Cargo.toml [dev-dependencies]:\n  mockall = \"0.12\""
  },
  "go-test": {
    "command": "go get -t github.com/stretchr/testify",
    "manual_manifest_edit": null
  },
  "flutter_test": {
    "command": null,
    "manual_manifest_edit": "Aggiungi a pubspec.yaml dev_dependencies:\n  flutter_test:\n    sdk: flutter\n  mocktail: ^1.0.0"
  },
  "xunit": {
    "command": "dotnet add package xunit && dotnet add package xunit.runner.visualstudio && dotnet add package coverlet.collector",
    "manual_manifest_edit": null
  }
}
```

### Step 3 — Crea `assets/few-shot-e2e.md`

```markdown
# Few-Shot End-to-End — T1 Pure Logic Example

> Lazy-load: caricato in Phase 5 ALLA PRIMA invocazione del session.

## Source file (target)

`src/utils/format-currency.ts` (LOC: 28)

```typescript
export function formatCurrency(amount: number, currency: string = "EUR"): string {
  if (amount < 0) {
    throw new Error("Negative amount not allowed");
  }
  if (amount === 0) {
    return `0.00 ${currency}`;
  }
  const formatted = amount.toFixed(2);
  return `${formatted} ${currency}`;
}

export function parseCurrency(value: string): number {
  const match = value.match(/^([\d.]+)\s+([A-Z]{3})$/);
  if (!match) {
    throw new Error("Invalid currency format");
  }
  return parseFloat(match[1]);
}
```

## Pre-Generation grep

```bash
grep -nE "^export (default|const|function|class)" src/utils/format-currency.ts
# Output:
# 1:export function formatCurrency(amount: number, currency: string = "EUR"): string {
# 13:export function parseCurrency(value: string): number {
```

→ 2 named exports, 0 dependencies → tier T1, batch_ceiling=3.

## Generated test (output)

`src/utils/format-currency.test.ts` (LOC: 56)

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { formatCurrency, parseCurrency } from './format-currency'

// Mock cleanup strategy:
// - DEFAULT: vi.clearAllMocks() in beforeEach (resetta calls/instances)
// - Aggiungi afterEach(vi.restoreAllMocks()) SOLO se il file usa vi.spyOn()

beforeEach(() => { vi.clearAllMocks() })

describe('formatCurrency', () => {
  it('formats positive amount with default EUR', () => {
    // Arrange
    const amount = 100.5
    // Act
    const result = formatCurrency(amount)
    // Assert
    expect(result).toBe('100.50 EUR')
  })

  it('formats with custom currency code', () => {
    expect(formatCurrency(50, 'USD')).toBe('50.00 USD')
  })

  it('returns zero formatted when amount is 0', () => {
    // Edge case: zero boundary
    expect(formatCurrency(0)).toBe('0.00 EUR')
    expect(formatCurrency(0, 'GBP')).toBe('0.00 GBP')
  })

  it('throws on negative amount', () => {
    // Negative path
    expect(() => formatCurrency(-1)).toThrow('Negative amount not allowed')
    expect(() => formatCurrency(-0.01)).toThrow('Negative amount not allowed')
  })
})

describe('parseCurrency', () => {
  it('parses valid currency string', () => {
    expect(parseCurrency('100.50 EUR')).toBeCloseTo(100.5)
  })

  it('parses zero amount', () => {
    expect(parseCurrency('0 EUR')).toBe(0)
  })

  it('throws on malformed input', () => {
    // Negative path: input non matching regex
    expect(() => parseCurrency('invalid')).toThrow('Invalid currency format')
    expect(() => parseCurrency('100.50')).toThrow('Invalid currency format')  // missing currency
    expect(() => parseCurrency('100 USD EUR')).toThrow('Invalid currency format')  // double currency
  })
})
```

## Coverage stimata

- Lines: 100% (tutte le righe coperte)
- Branches: 100% (3 branch: amount<0, amount==0, fallthrough; regex match/no-match)
- Functions: 2/2 = 100%

## Pattern applicati (AAA + edge cases)

| Pattern | Applicazione |
|---------|--------------|
| Happy path | `formatCurrency(100.5)` con default EUR |
| Edge case 1 | Custom currency `USD` |
| Edge case 2 | Boundary zero (input/output) |
| Negative path | Throw su negative amount + malformed regex |

## Tier classification

T1 — Pure Logic (0 imports esterni, 0 I/O, 0 framework). Batch_ceiling=3.
```

### Step 4 — Crea `assets/anti-patterns.md`

```markdown
# Anti-Patterns Gallery — 3 BAD / GOOD pairs

> Lazy-load: caricato SOLO se Phase 5 o Phase 7 hanno fail rate ≥1 nella session corrente.

## Anti-pattern 1: Weak assertions

### BAD
```typescript
it('processes input', () => {
  const result = process({ id: 1 })
  expect(result).toBeTruthy()  // ❌ Coverage hit ma zero behavioral guarantee
})
```

### GOOD
```typescript
it('processes input and returns enriched object', () => {
  const result = process({ id: 1 })
  expect(result).toEqual({
    id: 1,
    processed: true,
    timestamp: expect.any(Number)
  })
})
```

**Razionale**: `toBeTruthy()` passa anche per oggetti random/wrong-shape. Asserisci la struttura attesa.

---

## Anti-pattern 2: Self-mock (mock del SUT)

### BAD
```typescript
vi.mock('./payment-service')  // ❌ stiamo testando payment-service, non un suo client!
import { processPayment } from './payment-service'

it('processes payment', () => {
  vi.mocked(processPayment).mockResolvedValue({ status: 'OK' })
  const result = processPayment({ amount: 10 })
  expect(result).toEqual({ status: 'OK' })  // tautologia
})
```

### GOOD
```typescript
vi.mock('./database')  // ✅ mock SOLO le dependency esterne del SUT
import { processPayment } from './payment-service'
import { db } from './database'

it('processes payment and persists', async () => {
  vi.mocked(db.save).mockResolvedValue(true)
  const result = await processPayment({ amount: 10 })
  expect(result.status).toBe('OK')
  expect(db.save).toHaveBeenCalledWith(expect.objectContaining({ amount: 10 }))
})
```

**Razionale**: mockare il SUT trasforma il test in tautologia che verifica il mock, non il codice.

---

## Anti-pattern 3: Async test senza await

### BAD
```typescript
it('fetches user data', () => {
  fetchUser(1).then(user => {
    expect(user.id).toBe(1)  // ❌ test passa anche se assert fallisce dentro Promise
  })
})
```

### GOOD
```typescript
it('fetches user data', async () => {
  const user = await fetchUser(1)  // ✅ async/await garantisce wait + propaga errori
  expect(user.id).toBe(1)
})

// Alternative valida con expect.assertions:
it('fetches user data (Promise style)', () => {
  expect.assertions(1)
  return fetchUser(1).then(user => {
    expect(user.id).toBe(1)
  })
})
```

**Razionale**: `Promise` non-awaited fa terminare il test prima dell'assert. Vitest/Jest non sa che il test ha aspettative pendenti senza `expect.assertions(N)` o `await`.
```

### Step 5 — Riscrivi SKILL.md (target ≤220 LOC)

Riscrittura completa di `skills/code-coverage/SKILL.md` (vedi struttura sotto). Sostituisci INTERAMENTE il contenuto attuale con:

```markdown
---
name: code-coverage
description: >
  Enterprise test generation agent invoked via /code-coverage. Analyzes a repository,
  infers the tech stack, defines the optimal unit testing strategy, and generates
  deterministic tests targeting >=70% coverage. Zero user runtime interactions.
---

# Enterprise Test Generation Agent

**This skill activates ONLY when the user explicitly types `/code-coverage`. Do not self-activate.**

---

## INPUT MODE — Deterministic, autonomous

- No args → use `$(pwd)`.
- Local path absolute → use it.
- GitHub URL → auto-clone in `mktemp -d`. Default branch=`main` if omitted. Cleanup at session end.
- Malformed URL OR missing path → emit single error message and STOP.

NEVER ask user. Skill is fully autonomous.

---

## GLOBAL EXECUTION PRINCIPLES (7)

1. **Autonomous Execution Policy.** Invocation = blanket approval for read/write/install in: (a) `.code-coverage/` workdir, (b) test directories, (c) `vitest.config.ts`/`jest.config.ts` if absent, (d) `devDependencies` install. Never modify production source. Decisions logged to `.code-coverage/decisions.log`. ZERO user prompts.
2. **Context-safety over completeness.** Load files in batches sized per tier (T1=3, T2=2, T3=1, T4=1 — see `assets/priority-rules.json` `ordering_constants`). For LARGE/VERY_LARGE, persist `batch-plan.json` and process across sessions.
3. **Determinism over creativity.** `assets/stack-matrix.json` = single source of truth for framework selection. Identical input → identical output.
4. **Vitest-first for all JS/TS.** Vitest is unconditional default. Deviate to Jest only when (in this order): (a) `jest.config.{ts,js,mjs,cjs}` exists, (b) `package.json scripts.test` contains `"jest"` AND `vitest` not in devDeps, (c) Vitest CJS-incompatibility documented in `.code-coverage/constraints.json`, (d) explicit legacy constraint in `.code-coverage/constraints.json`. **This rule is authoritative.**
5. **Coverage targets per-priority; global floor 70%.** `assets/priority-rules.json` `min_coverage_pct`: P1≥80%, P2≥70%, P3≥60%, global≥70%. P1 at 75% = FAIL even if global > 70%. Repair loop max 3 iter; emit best-effort if exhausted.
6. **Progressive disclosure.** Load `references/phase-N.md` only when entering phase N. Phase-1/2/6/7 are inlined here. Phase-3/4/5 are separate refs.
7. **State persistence + cache.** All structured outputs in `.code-coverage/`. Files `stack.json`, `size.json`, `env.json` cached vs `package.json`/`pom.xml`/etc. mtime. Templates loaded ONCE per (framework, session). Schema: `lib/state-schema.json`.

---

## WORKFLOW

### Phase 0 (init)

```bash
source skills/code-coverage/lib/cache-helper.sh
init_workdir <repo_path>  # crea .code-coverage/, ensure_gitignore, init decisions.log
```

### Phase 1 — Discovery (INLINE)

Run in parallel (skip if cache valid):
```bash
python3 skills/code-coverage/scripts/detect_stack.py <repo> > <repo>/.code-coverage/stack.json &
python3 skills/code-coverage/scripts/estimate_size.py <repo> --file-list --with-coverage <repo>/.code-coverage/coverage-report.json > <repo>/.code-coverage/size.json &
python3 skills/code-coverage/scripts/validate_env.py <repo> > <repo>/.code-coverage/env.json &
wait
```

If `stack.json.pre_existing_coverage_pct >= 70` → emit Block 8 with current value + END.

If `env.json.framework == "unknown"` → emit "Language not supported" Block 4 + END.

### Phase 2 — Strategy (INLINE)

Read `stack.json` + `assets/stack-matrix.json`. Apply Principle 4 Vitest-first decision tree. Output: framework + rationale logged to decisions.log.

### Phase 3 — Sizing (REF if LARGE/VERY_LARGE)

If `size.json.size_class IN ("LARGE", "VERY_LARGE")`:
- emit `Repository exceeds safe single-session capacity. Switching to phased enterprise mode.`
- Run `python3 skills/code-coverage/scripts/plan_batches.py <repo> > <repo>/.code-coverage/batch-plan.json`
- Load `references/phase-3-sizing.md` for batch resume protocol.

### Phase 4 — Environment (REF)

Load `references/phase-4-environment.md`. Auto-install via `validate_env.py install_commands` field. Snapshot lockfile pre-install (`.code-coverage/lockfile.bak`); rollback if exit-code ≠ 0.

### Phase 5 — Generation (REF)

Load `references/phase-5-generation.md`. Apply ordering rule (see below). Pre-write hard gate: `bash lib/placeholder-check.sh <file>` before EVERY write.

**Ordering rule (D1 conditional)**:
```python
import json
stack = json.loads(open(".code-coverage/stack.json").read())
has_module_coverage = bool(stack.get("module_coverage"))
if has_module_coverage:
    sort_key = lambda f: (TIER_ORDER[f["tier"]], -f["priority_score"])  # TIER-FIRST
else:
    sort_key = lambda f: (PRIORITY_ORDER[f["priority"]], -f["loc"])  # P-TIER FALLBACK
```
Constants in `assets/priority-rules.json.ordering_constants`.

**P1 floor enforcement**: post each iter, if `min(P1 modules lines_pct) < 80%` → force-include sub-threshold P1 files in next batch above any tier/priority order.

### Phase 6 — Coverage (INLINE)

```bash
FW=$(jq -r '.framework' .code-coverage/stack.json)
COV_CMD=$(jq -r --arg fw "$FW" '.[$fw].coverage_command' skills/code-coverage/assets/stack-matrix.json)
REPORT_PATH=$(jq -r --arg fw "$FW" '.[$fw].coverage_report_path' skills/code-coverage/assets/stack-matrix.json)
cd <repo> && eval "$COV_CMD" 2>&1 | tee .code-coverage/coverage-stdout.log
FORMAT=$(jq -r --arg fw "$FW" '.[$fw].coverage_report_format' skills/code-coverage/assets/stack-matrix.json)
python3 skills/code-coverage/scripts/parse_coverage.py "$FORMAT" "<repo>/$REPORT_PATH" > <repo>/.code-coverage/coverage-report.json
```

Read `coverage-report.json`. If all P1≥80%, P2≥70%, P3≥60%, global≥70% → SKIP Phase 7 → OUTPUT.

### Phase 7 — Repair (INLINE algorithm)

Budget: max 3 iter, max 1 full coverage/iter. Categorize via `python3 scripts/categorize_failure.py < <stderr>`. Group by `error_signature`; if `count >= max(2, 30% failures)` AND categoria `systemic_eligible` → fix config-level UNA volta. Otherwise per-file scoped Edit (NO full-file regen). Re-run modified tests WITHOUT `--coverage`; full coverage UNA volta a fine iter.

Progress guard: if `Δglobal_coverage < 0.5pp AND Δfailing_count <= 0` → STOP best-effort.

Autonomous early-abort: if iter==1 AND `global_coverage < 30%` AND any `P1.lines_pct < 40%` → set `loop_max_remaining = 2` (1 retry only).

Best-effort report con tabella **Stalled Files** in OUTPUT Block 8 se max iter raggiunto.

---

## OUTPUT — Conditional Blocks

Always emit Block 1, 5, 8. Conditional (programmatic check):
- Block 4 (`unsupported_groups`): only if non-empty array.
- Block 6 (`Dependency Install Commands`): only if `validate_env.py.install_commands` non-empty.
- Block 9 (`Next Actions`): only if any module sub-threshold OR follow-up batch active OR manual tests suggested.

### Block 1 — Repository Summary
- source path/URL, languages (from stack.json), size class (size.json), monorepo (stack.json)

### Block 5 — Generated Test Files
| Path | Module under test | Tier | Priority | Estimated coverage gain |

### Block 8 — Coverage Report Summary
| Module | Lines% | Branch% | Threshold | Status |
+ Stalled Files sub-section if Phase 7 ran without convergence

---

## SUPPORTING FILES

| Path | Purpose |
|------|---------|
| `references/phase-3-sizing.md` | Batch plan resume protocol (LARGE/VERY_LARGE) |
| `references/phase-4-environment.md` | Auto-install policy + Blocking Check Handler |
| `references/phase-5-generation.md` | Ordering tree, AAA pattern, batch ceilings, few-shot trigger |
| `assets/stack-matrix.json` | **Single source**: stack → framework + coverage_command + report_format |
| `assets/priority-rules.json` | P1/P2/P3 + ordering_constants + skip patterns |
| `assets/install-snippets.json` | **Single source**: install commands per framework |
| `assets/repair-strategies.json` | **Single source**: error patterns → category + fix steps |
| `assets/few-shot-e2e.md` | Lazy-load: T1 example with grep + AAA test (Phase 5 first batch) |
| `assets/anti-patterns.md` | Lazy-load: 3 BAD/GOOD pairs (Phase 5/7 fail ≥1) |
| `scripts/detect_stack.py` | Stack detection JSON |
| `scripts/estimate_size.py` | Size + file_list + priority_score JSON |
| `scripts/validate_env.py` | Env + framework_check + install_commands JSON |
| `scripts/parse_coverage.py` | Coverage report parsing per 8 framework |
| `scripts/categorize_failure.py` | Failure categorization Cat 1-6 + normalize() |
| `scripts/plan_batches.py` | Batch plan ordering (tier-first conditional) |
| `lib/cache-helper.sh` | Bash utils: cache mtime check, ensure_gitignore, init_workdir |
| `lib/placeholder-check.sh` | Hard gate `\{\{X\}\}` placeholder pre-write |
| `lib/state-schema.json` | Schema documenting all `.code-coverage/*` files |
| `templates/*.template.*` | Test skeletons per framework (with rationale paragraph) |
```

(Verifica con `wc -l skills/code-coverage/SKILL.md` post-write: deve essere ≤ 220 LOC.)

### Step 6 — Cancella reference files inlined

```bash
git rm skills/code-coverage/references/phase-1-discovery.md
git rm skills/code-coverage/references/phase-2-strategy.md
git rm skills/code-coverage/references/phase-6-coverage.md
git rm skills/code-coverage/references/phase-7-repair.md
```

### Step 7 — TRIM `phase-4-environment.md` da 263 a ~80 LOC

Riscrittura completa. Nuovo contenuto:

```markdown
# Phase 4 — Environment Setup

**Goal**: garantire che runtime + framework siano installati prima di Phase 5.

## Auto-install policy

Read `.code-coverage/env.json`. For each framework with `installed: false` and non-null install command:

1. Snapshot lockfile: `cp <lockfile> .code-coverage/lockfile.bak` (lockfile = `package-lock.json` / `yarn.lock` / `pnpm-lock.yaml` / `poetry.lock`).
2. Run install command from `assets/install-snippets.json[<framework>].command`.
3. If exit-code != 0:
   - Restore lockfile from backup.
   - Append error to `.code-coverage/install-log.txt`.
   - emit Block 4 entry "framework install failed" + END Phase 4.
4. If exit-code == 0: log to `decisions.log` and proceed.

For frameworks with `command: null` (junit5/mockk/cargo-test/flutter_test):
- Read `assets/install-snippets.json[<framework>].manual_manifest_edit`.
- Apply edit autonomously to pom.xml/build.gradle/Cargo.toml/pubspec.yaml.
- Run subsequent verification (e.g., `mvn dependency:resolve`, timeout 30s).

## Vitest config generation

Solo se `vitest.config.ts` ASSENTE e framework=vitest. Generate skeleton:

```typescript
import { defineConfig } from 'vitest/config'
export default defineConfig({
  test: {
    environment: 'jsdom',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json-summary'],
      include: ['src/**/*.{ts,tsx,js,jsx}'],
      exclude: ['**/*.test.*', '**/*.spec.*', '**/node_modules/**']
    }
  }
})
```

Mai sovrascrivere config esistente.

## Blocking Check Handler

Se `env.json.runtime_check.<runtime>.available == false` (Node/Python/Java/Go/Rust missing):

```
ENVIRONMENT BLOCKER

Required runtime not available: <runtime>

Install:
  <runtime-specific install command from official docs>

Then re-run /code-coverage.
```

STOP execution. Don't continue without runtime.

## TIMEOUT handling

If `env.json.pm_check.<tool>.reason == "TIMEOUT"`:
- Log warning, do NOT block.
- Treat as "available but slow"; subsequent commands use 60s timeout.
```

### Step 8 — TRIM `phase-5-generation.md`: rimuovi mocking patterns sezione

In `phase-5-generation.md`, cancella interamente la sezione "Mocking Patterns by Framework" (righe ~107-244 originali). Aggiungi al posto un singolo paragrafo:

```markdown
## Mocking patterns

Mocking patterns sono nei template files (`skills/code-coverage/templates/<framework>.template.*`). Ogni template include 1 paragrafo di rationale "perché questo mock" all'inizio. Il template è caricato ONCE per (framework, session).

Default mock cleanup: `vi.clearAllMocks()` in `beforeEach`. Aggiungi `vi.restoreAllMocks()` in `afterEach` SOLO se il test usa `vi.spyOn()`.
```

### Step 9 — Aggiungi rationale paragrafo a ogni template

Per ogni `templates/<framework>.template.*`, aggiungi all'inizio (commentato secondo la sintassi del linguaggio):

`vitest.template.ts`:
```typescript
// ====================================================================
// VITEST TEMPLATE — Mock pattern rationale
// ====================================================================
// vi.mock(path, factory) sostituisce il modulo per TUTTI i test del file.
// Use named exports: ({ funcName: vi.fn() }) per esempio.
// Use default exports: ({ default: vi.fn() }) — la chiave 'default' è critica.
// Use namespace: ({ default: vi.fn(), helper: vi.fn() }) per misti.
// Verify export shape FIRST via grep:
//   grep -nE "^export (default|const|function|class)" <dep-source-file>
// ====================================================================
```

(Adatta sintassi commento per pytest.py / junit5.java / mockk.kt / etc.)

### Step 10 — Spec-reviewer

Lancia spec-reviewer. Verifica in particolare:
- SKILL.md ≤220 LOC (`wc -l`)
- Reference files cancellati corretti
- Nessuna duplicazione cross-file dopo refactor

### Step 11 — Commit + PR

```bash
git add skills/code-coverage/SKILL.md \
        skills/code-coverage/references/phase-3-sizing.md \
        skills/code-coverage/references/phase-4-environment.md \
        skills/code-coverage/references/phase-5-generation.md \
        skills/code-coverage/templates/ \
        skills/code-coverage/assets/few-shot-e2e.md \
        skills/code-coverage/assets/anti-patterns.md \
        skills/code-coverage/assets/install-snippets.json
# Le cancellazioni sono già staged via git rm in Step 6

git commit -m "feat(code-coverage): SKILL.md refactor + single source + few-shot (P7, P9, P11, ST5)

P11: SKILL.md inline phase-1/2/6/7 entry-points (target <=220 LOC).
     Cancellati phase-1/2/6/7 reference files (logica in scripts).
     Cancellata Detection File Inventory (era duplicato di detect_stack.py).
     phase-4-environment.md trim 263 -> ~80 LOC.
     phase-5-generation.md trim ~140 LOC mocking patterns (in template).

P9: single source of truth consolidato:
    - Vitest-first → SKILL.md Principle 4 only
    - install commands → assets/install-snippets.json (used by validate_env.py)
    - coverage commands → assets/stack-matrix.json (already)
    - mocking patterns → templates/* + 1 paragrafo rationale

P7: assets/few-shot-e2e.md (T1 example end-to-end, lazy-load Phase 5 first batch)
    + assets/anti-patterns.md (3 BAD/GOOD pairs, lazy-load if fail >=1)

ST5: SKILL.md è ora orchestrator + decision tree, non documentazione duplicata.

Refs design doc 2026-05-09-code-coverage-optimization-design.md PR7.

Co-Authored-By: SIAE DevForge"

git push -u origin feat/code-coverage-opt-skill-refactor
gh pr create --title "feat(code-coverage): SKILL.md refactor + single source + few-shot (P7, P9, P11, ST5)" --body "$(cat <<'EOF'
## Summary
- SKILL.md riscritto: ≤220 LOC, inline phase-1/2/6/7 entry-points
- Cancellati 4 reference files (phase-1/2/6/7) — logica in scripts già esistenti
- phase-4-environment.md trim 263→80 LOC (auto-install policy concise)
- phase-5-generation.md rimossa sezione Mocking Patterns (era duplicata in template)
- Single source consolidato: install→install-snippets.json, mocking→template+rationale, vitest-first→SKILL.md
- Lazy-load assets/few-shot-e2e.md + assets/anti-patterns.md

Refs: docs/plans/2026-05-09-code-coverage-optimization-design.md PR7

## Test plan
- [ ] `wc -l SKILL.md` <= 220
- [ ] Reference cancellati correttamente (phase-1/2/6/7)
- [ ] Smoke test su MEDIUM: skill invocata con SKILL.md only (refs caricati on-demand)
- [ ] Spec-reviewer PASS

Co-Authored-By: SIAE DevForge
EOF
)"
```

---

## Acceptance criteria

- [ ] `SKILL.md` ≤ 220 LOC (verificare con `wc -l skills/code-coverage/SKILL.md`)
- [ ] `references/phase-1-discovery.md` cancellato
- [ ] `references/phase-2-strategy.md` cancellato
- [ ] `references/phase-6-coverage.md` cancellato
- [ ] `references/phase-7-repair.md` cancellato
- [ ] `references/phase-4-environment.md` ≤ 100 LOC
- [ ] `references/phase-5-generation.md` non contiene più sezione "Mocking Patterns by Framework"
- [ ] `assets/install-snippets.json` esiste con 10+ framework
- [ ] `assets/few-shot-e2e.md` esiste, ~80 LOC
- [ ] `assets/anti-patterns.md` esiste, 3 BAD/GOOD pairs
- [ ] Ogni template ha paragrafo rationale all'inizio
- [ ] Smoke test MEDIUM: ZERO errori "phase-X.md not found" durante session (significa che logica inlined funziona)
- [ ] Spec-reviewer PASS

## Note operative

- Questa è la PR più impattante a livello di codice → verifica cross-reference dopo refactor (cerca string "phase-1-discovery.md", "phase-2-strategy.md", etc. con grep ovunque)
- ≤220 LOC è soft target; spec-reviewer può approvare fino a 250 LOC se rationale documentato
- I template paragraphs di rationale aggiungono ~5-10 LOC ciascuno × 11 template = ~70-100 LOC totali (compensati dalla cancellazione di phase-5 mocking section)
