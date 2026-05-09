# Task 08 — Plan Batches + Template Fixes (P8 + ST3 + ST8)

**Goal:** Implementare `scripts/plan_batches.py` con ordering condizionale (D1) + selective dependency export grep deterministico (P8) + multi-dep template variants. Split `vitest-lambda.template.ts` in handler + module (ST8). Chiusura del piano: integra tutto.

**SP:** 1 (Augmented)
**Fix IDs covered:** P8 + ST3 + ST8
**Branch:** `feat/code-coverage-opt-plan-batches`
**Dipendenze:** task-04 (categorize_failure.py), task-05 (detect_stack.py emette module_coverage), task-07 (SKILL.md refactor) — è la PR finale

---

## File coinvolti

**Creazione**:
- `skills/code-coverage/scripts/plan_batches.py` (~180 LOC Python)
- `skills/code-coverage/scripts/tests/test_plan_batches.py` (~80 LOC, 2 test)
- `skills/code-coverage/scripts/tests/fixtures/plan-input/` (sample size.json + stack.json per test)
- `skills/code-coverage/templates/vitest-lambda-handler.template.ts` (~120 LOC — solo Lambda)
- `skills/code-coverage/templates/vitest-lambda-module.template.ts` (~80 LOC — solo module)

**Modifica**:
- `skills/code-coverage/templates/vitest.template.ts` (aggiungi 3 multi-dep variants)
- `skills/code-coverage/references/phase-5-generation.md` (Pre-Generation Checklist 3b: comando grep deterministico)
- `skills/code-coverage/assets/stack-matrix.json` (aggiorna `template_path` per Lambda detection)

**Cancellazione**:
- `skills/code-coverage/templates/vitest-lambda.template.ts` (sostituito da 2 file split)

---

## Step bite-sized

### Step 1 — Branch + verifica dipendenze merged

```bash
git checkout main && git pull
git checkout -b feat/code-coverage-opt-plan-batches
test -f skills/code-coverage/scripts/categorize_failure.py && echo "task-04 merged"
test -f skills/code-coverage/scripts/parse_coverage.py && echo "task-03 merged"
# Check che SKILL.md sia stata refattorizzata (≤220 LOC)
LOC=$(wc -l < skills/code-coverage/SKILL.md)
[ "$LOC" -le 220 ] && echo "task-07 merged: SKILL.md $LOC LOC OK"
# Check che detect_stack emetta module_coverage
python3 skills/code-coverage/scripts/detect_stack.py skills/code-coverage/scripts/tests/fixtures/repos/vue-app | grep -q '"module_coverage"' && echo "task-05 merged: module_coverage emitted"
```

### Step 2 — Crea fixture per test plan_batches

`skills/code-coverage/scripts/tests/fixtures/plan-input/with-coverage/size.json`:
```json
{
  "size_class": "MEDIUM",
  "file_count": 5,
  "loc_total": 500,
  "file_list": [
    {"path": "src/services/payment.ts", "loc": 200, "tier": "T2", "priority": "P1", "current_coverage": 0.0, "priority_score": 200.0},
    {"path": "src/utils/format.ts", "loc": 50, "tier": "T1", "priority": "P2", "current_coverage": 0.5, "priority_score": 25.0},
    {"path": "src/utils/parse.ts", "loc": 80, "tier": "T1", "priority": "P2", "current_coverage": 0.0, "priority_score": 80.0},
    {"path": "src/handlers/api.ts", "loc": 120, "tier": "T4", "priority": "P1", "current_coverage": 0.2, "priority_score": 96.0},
    {"path": "src/store/state.ts", "loc": 50, "tier": "T3", "priority": "P3", "current_coverage": 0.0, "priority_score": 50.0}
  ]
}
```

`skills/code-coverage/scripts/tests/fixtures/plan-input/with-coverage/stack.json`:
```json
{
  "languages": ["typescript"],
  "frameworks": ["vitest"],
  "module_coverage": [
    {"path": "src/services/payment.ts", "lines_pct": 0.0},
    {"path": "src/utils/format.ts", "lines_pct": 50.0}
  ],
  "pre_existing_coverage_pct": 14.0
}
```

`skills/code-coverage/scripts/tests/fixtures/plan-input/no-coverage/size.json`:
```json
{
  "size_class": "MEDIUM",
  "file_count": 5,
  "loc_total": 500,
  "file_list": [
    {"path": "src/services/payment.ts", "loc": 200, "tier": "T2", "priority": "P1"},
    {"path": "src/utils/format.ts", "loc": 50, "tier": "T1", "priority": "P2"},
    {"path": "src/utils/parse.ts", "loc": 80, "tier": "T1", "priority": "P2"},
    {"path": "src/handlers/api.ts", "loc": 120, "tier": "T4", "priority": "P1"},
    {"path": "src/store/state.ts", "loc": 50, "tier": "T3", "priority": "P3"}
  ]
}
```

`skills/code-coverage/scripts/tests/fixtures/plan-input/no-coverage/stack.json`:
```json
{
  "languages": ["typescript"],
  "frameworks": ["vitest"],
  "module_coverage": [],
  "pre_existing_coverage_pct": 0.0
}
```

### Step 3 — TDD: scrivi 2 test per `plan_batches.py` (RED)

Crea `skills/code-coverage/scripts/tests/test_plan_batches.py`:

```python
"""Test per plan_batches.py — verifica D1 conditional ordering."""
import json
import subprocess
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "plan-input"
SCRIPT = Path(__file__).resolve().parent.parent / "plan_batches.py"


def run_planner(fixture_dir: Path) -> dict:
    result = subprocess.run(
        [
            "python3", str(SCRIPT),
            "--size", str(fixture_dir / "size.json"),
            "--stack", str(fixture_dir / "stack.json"),
        ],
        capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)


def test_with_module_coverage_uses_tier_first():
    """D1: con module_coverage non-empty → TIER-FIRST ordering (T1 first)."""
    plan = run_planner(FIXTURES / "with-coverage")
    batches = plan["batches"]
    # Primo batch deve essere tier T1 (utils/format.ts e utils/parse.ts)
    first_batch_files = batches[0]["files"]
    first_tiers = {f["tier"] for f in first_batch_files}
    assert first_tiers == {"T1"}, f"Expected T1 first, got {first_tiers}"
    # Within T1: ordering by priority_score desc → parse.ts (80) before format.ts (25)
    paths = [f["path"] for f in first_batch_files]
    assert paths.index("src/utils/parse.ts") < paths.index("src/utils/format.ts")
    # Strategy must be tier-first
    assert plan["ordering_strategy"] == "tier-first"


def test_without_module_coverage_uses_p_tier_fallback():
    """D1: con module_coverage empty → P-TIER FALLBACK (P1 first by LOC desc)."""
    plan = run_planner(FIXTURES / "no-coverage")
    batches = plan["batches"]
    # Primo batch deve essere P1 (services/payment.ts e handlers/api.ts)
    first_batch_files = batches[0]["files"]
    first_priorities = {f["priority"] for f in first_batch_files}
    assert "P1" in first_priorities, f"Expected P1 first, got {first_priorities}"
    # P1 tiers can be T2 (payment) and T4 (handler) — both included before P2/P3
    paths = [f["path"] for f in first_batch_files]
    assert "src/services/payment.ts" in paths
    # Strategy must be p-tier
    assert plan["ordering_strategy"] == "p-tier-fallback"
```

### Step 4 — Run test in RED

```bash
cd skills/code-coverage
python3 -m pytest scripts/tests/test_plan_batches.py -v
```

Output atteso: 2 errors (FileNotFoundError plan_batches.py).

### Step 5 — GREEN: implementa `scripts/plan_batches.py`

```python
#!/usr/bin/env python3
"""plan_batches.py — produce batch plan ordinato secondo D1 conditional ordering.

Usage:
    python3 plan_batches.py --size <size.json> --stack <stack.json>
    python3 plan_batches.py --size .code-coverage/size.json --stack .code-coverage/stack.json

Output (stdout): JSON batch plan con schema:
    {
        "ordering_strategy": "tier-first" | "p-tier-fallback",
        "total_files": int,
        "batches": [
            {"id": int, "tier": str, "priority": str, "files": [...], "size": int}
        ],
        "deferred": []
    }
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
PRIORITY_RULES_PATH = SKILL_ROOT / "assets" / "priority-rules.json"


def load_priority_rules() -> dict:
    with open(PRIORITY_RULES_PATH) as f:
        return json.load(f)


def build_batches(file_list: list, ordering_strategy: str, ceilings: dict) -> list:
    """Raggruppa file_list (già ordinato) in batch rispettando il ceiling per tier.

    Ogni batch contiene SOLO file dello stesso tier (per coerenza ceiling).
    """
    batches = []
    batch_id = 1
    current_batch = []
    current_tier = None

    for f in file_list:
        f_tier = f.get("tier", "T4")
        ceiling = ceilings.get(f_tier, 1)

        # Se cambiamo tier o riempiamo il ceiling, chiudiamo il batch corrente
        if current_tier is None:
            current_tier = f_tier

        if f_tier != current_tier or len(current_batch) >= ceiling:
            if current_batch:
                batches.append({
                    "id": batch_id,
                    "tier": current_tier,
                    "priority": current_batch[0].get("priority"),
                    "files": current_batch,
                    "size": len(current_batch),
                })
                batch_id += 1
                current_batch = []
            current_tier = f_tier

        current_batch.append(f)

    # Flush ultimo batch
    if current_batch:
        batches.append({
            "id": batch_id,
            "tier": current_tier,
            "priority": current_batch[0].get("priority"),
            "files": current_batch,
            "size": len(current_batch),
        })

    return batches


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=Path, required=True, help="Path a size.json")
    parser.add_argument("--stack", type=Path, required=True, help="Path a stack.json")
    parser.add_argument("--out", type=Path, default=None, help="Output path (default: stdout)")
    args = parser.parse_args()

    # Validazione input
    if not args.size.exists():
        print(json.dumps({"error": f"size file not found: {args.size}"}), file=sys.stderr)
        return 1
    if not args.stack.exists():
        print(json.dumps({"error": f"stack file not found: {args.stack}"}), file=sys.stderr)
        return 1

    size_data = json.loads(args.size.read_text())
    stack_data = json.loads(args.stack.read_text())
    rules = load_priority_rules()

    file_list = size_data.get("file_list", [])
    if not file_list:
        result = {"ordering_strategy": "none", "total_files": 0, "batches": [], "deferred": []}
        print(json.dumps(result, indent=2))
        return 0

    ordering_constants = rules.get("ordering_constants", {})
    tier_order = ordering_constants.get("tier_order", {"T1": 0, "T2": 1, "T3": 2, "T4": 3})
    priority_order = ordering_constants.get("priority_order", {"P1": 0, "P2": 1, "P3": 2})
    ceilings = ordering_constants.get("batch_ceiling_per_tier", {"T1": 3, "T2": 2, "T3": 1, "T4": 1})

    # D1 CONDITIONAL: tier-first SE module_coverage non-empty, P-tier fallback altrimenti
    has_module_coverage = bool(stack_data.get("module_coverage"))

    if has_module_coverage:
        # TIER-FIRST: sort by tier asc, then priority_score desc
        sorted_files = sorted(
            file_list,
            key=lambda f: (
                tier_order.get(f.get("tier", "T4"), 4),
                -float(f.get("priority_score", f.get("loc", 0)))
            )
        )
        ordering_strategy = "tier-first"
    else:
        # P-TIER FALLBACK: sort by priority asc, then LOC desc (no priority_score reliable)
        sorted_files = sorted(
            file_list,
            key=lambda f: (
                priority_order.get(f.get("priority", "P3"), 3),
                -int(f.get("loc", 0))
            )
        )
        ordering_strategy = "p-tier-fallback"

    # Filtra file_list per skip patterns
    skip_patterns = rules.get("skip_patterns", [])
    import re
    def is_skipped(path: str) -> bool:
        for pattern in skip_patterns:
            regex = pattern.replace("**/", ".*/").replace("**", ".*").replace("*", "[^/]*")
            if re.search(regex, path):
                return True
        return False

    deferred = [f for f in sorted_files if is_skipped(f["path"])]
    eligible = [f for f in sorted_files if not is_skipped(f["path"])]

    # Build batches respecting ceiling
    batches = build_batches(eligible, ordering_strategy, ceilings)

    result = {
        "ordering_strategy": ordering_strategy,
        "total_files": len(eligible),
        "batches": batches,
        "deferred": deferred,
    }

    output = json.dumps(result, indent=2)
    if args.out:
        args.out.write_text(output)
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Make executable:
```bash
chmod +x skills/code-coverage/scripts/plan_batches.py
```

### Step 6 — Run test in GREEN

```bash
cd skills/code-coverage
python3 -m pytest scripts/tests/test_plan_batches.py -v
```

Output atteso:
```
test_plan_batches.py::test_with_module_coverage_uses_tier_first PASSED
test_plan_batches.py::test_without_module_coverage_uses_p_tier_fallback PASSED

2 passed in <1s>
```

### Step 7 — Coverage del nuovo script ≥70%

```bash
cd skills/code-coverage
python3 -m pytest scripts/tests/test_plan_batches.py --cov=scripts/plan_batches --cov-report=term-missing
```

Aggiungi test per skip patterns + edge case file_list vuoto se sotto 70%.

### Step 8 — Aggiorna `phase-5-generation.md` Pre-Generation Checklist 3b (P8)

Sostituisci la sezione Pre-Generation Checklist point 3 / 3b con:

```markdown
### Pre-Generation Checklist (per ogni file da generare)

1. Read source file (selective: se LOC > 150 usa grep prima del read full).
2. Identify dependencies che dovranno essere mockate.
3. **For each dependency: run grep deterministico** (P8):

   ```bash
   grep -nE "^export (default|const|function|class|interface|type)|module\.exports" <dep_path>
   ```

   Output → determina `mock_shape`:
   - `export default` only → `vi.mock(path, () => ({ default: vi.fn() }))`
   - `export const/function/class` only → `vi.mock(path, () => ({ funcName: vi.fn() }))`
   - both → `vi.mock(path, () => ({ default: vi.fn(), funcName: vi.fn() }))`
   - `module.exports = ...` (CJS) → `vi.mock(path, () => ({ default: vi.fn() }))`

   Cache result per `(dep_path, session)` per evitare re-grep su batch successivi.

4. Apply template variant from `templates/<framework>.template.*` based on dep count:
   - 0 deps (T1 pure logic) → use `# VARIANT_NO_DEPS` block, delete other variants
   - 1-2 deps → use `# VARIANT_SINGLE_DEP` or `# VARIANT_TWO_DEPS`
   - 3+ deps → use `# VARIANT_MULTI_DEPS`

5. **Hard gate placeholder check** (P6): `bash skills/code-coverage/lib/placeholder-check.sh <file>` BEFORE writing. Exit 1 → fail loudly.

6. Persist file list in `.code-coverage/generation-plan.txt` then write.
```

### Step 9 — Aggiungi multi-dep variants a `vitest.template.ts`

Aggiungi al file `skills/code-coverage/templates/vitest.template.ts` 3 sezioni nuove dopo l'header:

```typescript
// ====================================================================
// VITEST TEMPLATE — Variants
// Selezionare UNA variante in base al numero di dependencies.
// Cancellare le altre prima di scrivere il test file.
// ====================================================================

// ====================================================================
// VARIANT_NO_DEPS — T1 Pure Logic (0 dependencies, no mock needed)
// ====================================================================
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { {{SUT_FUNCTIONS}} } from '{{SUT_PATH}}'

beforeEach(() => { vi.clearAllMocks() })

describe('{{SUT_NAME}}', () => {
  // Tests here — no mocks
})

// ====================================================================
// VARIANT_SINGLE_DEP — 1 dependency (mock factory single shape)
// ====================================================================
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { {{SUT_FUNCTIONS}} } from '{{SUT_PATH}}'
import { {{DEP_NAMED_EXPORT}} } from '{{DEP_IMPORT_PATH}}'

vi.mock('{{DEP_IMPORT_PATH}}', () => ({
  {{DEP_NAMED_EXPORT}}: vi.fn(),
}))

beforeEach(() => { vi.clearAllMocks() })

describe('{{SUT_NAME}}', () => {
  // Tests here — single dep mocked
})

// ====================================================================
// VARIANT_TWO_DEPS — 2 dependencies (mixed named/default exports)
// ====================================================================
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { {{SUT_FUNCTIONS}} } from '{{SUT_PATH}}'
import {{DEP1_DEFAULT_OR_NAMED}} from '{{DEP1_IMPORT_PATH}}'
import { {{DEP2_NAMED}} } from '{{DEP2_IMPORT_PATH}}'

vi.mock('{{DEP1_IMPORT_PATH}}', () => ({
  default: vi.fn(),  // se DEP1 è default export
  // OR named: { {{DEP1_NAMED}}: vi.fn() }
}))
vi.mock('{{DEP2_IMPORT_PATH}}', () => ({
  {{DEP2_NAMED}}: vi.fn(),
}))

beforeEach(() => { vi.clearAllMocks() })

describe('{{SUT_NAME}}', () => {
  // Tests here — 2 deps mocked
})

// ====================================================================
// VARIANT_MULTI_DEPS — 3+ dependencies (T3/T4 service heavy)
// ====================================================================
// Per più di 2 dep, usa fixture helper o factory pattern:
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { {{SUT_FUNCTIONS}} } from '{{SUT_PATH}}'

// Repeat per ogni dep (auto-generated):
vi.mock('{{DEP1_IMPORT_PATH}}', () => ({ {{DEP1_EXPORTS}} }))
vi.mock('{{DEP2_IMPORT_PATH}}', () => ({ {{DEP2_EXPORTS}} }))
vi.mock('{{DEP3_IMPORT_PATH}}', () => ({ {{DEP3_EXPORTS}} }))

beforeEach(() => { vi.clearAllMocks() })

describe('{{SUT_NAME}}', () => {
  // Tests here — multi-dep
})
```

### Step 10 — Split `vitest-lambda.template.ts` (ST8)

Crea `skills/code-coverage/templates/vitest-lambda-handler.template.ts` (per Lambda handler files):

```typescript
// ====================================================================
// VITEST LAMBDA HANDLER TEMPLATE
// Per file: src/handlers/*.ts che esportano Lambda handler (APIGatewayProxyHandler, SQSHandler, etc.)
// ====================================================================
import { describe, it, expect, beforeEach, vi } from 'vitest'
import type { APIGatewayProxyEvent, Context } from 'aws-lambda'
import { handler } from './{{HANDLER_FILE_NAME}}'

vi.mock('aws-sdk')  // o specifico SDK Lambda usa
{{ADDITIONAL_MOCKS}}

const MOCK_CONTEXT: Context = {
  callbackWaitsForEmptyEventLoop: false,
  functionName: 'test',
  functionVersion: '$LATEST',
  invokedFunctionArn: 'arn:aws:lambda:eu-west-1:000:function:test',
  memoryLimitInMB: '128',
  awsRequestId: 'test-id',
  logGroupName: '/aws/lambda/test',
  logStreamName: '2026/01/01/[$LATEST]00000',
  getRemainingTimeInMillis: () => 1000,
  done: () => {},
  fail: () => {},
  succeed: () => {},
}

beforeEach(() => { vi.clearAllMocks() })

describe('{{HANDLER_NAME}} Lambda handler', () => {
  it('returns 200 on valid input', async () => {
    const event = { body: JSON.stringify({ valid: true }) } as APIGatewayProxyEvent
    const result = await handler(event, MOCK_CONTEXT, () => {})
    expect(result.statusCode).toBe(200)
  })

  it('returns 400 on missing body', async () => {
    const event = { body: null } as APIGatewayProxyEvent
    const result = await handler(event, MOCK_CONTEXT, () => {})
    expect(result.statusCode).toBe(400)
  })

  // ... aggiungi edge case + negative path
})
```

Crea `skills/code-coverage/templates/vitest-lambda-module.template.ts` (per moduli used dentro handler):

```typescript
// ====================================================================
// VITEST LAMBDA MODULE TEMPLATE
// Per moduli (services/utils) usati DENTRO i Lambda handler.
// Equivalente al vitest.template.ts standard ma con mock SDK pre-configurato.
// ====================================================================
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { {{SUT_FUNCTIONS}} } from '{{SUT_PATH}}'

vi.mock('aws-sdk', () => ({
  DynamoDB: { DocumentClient: vi.fn(() => ({ get: vi.fn(), put: vi.fn() })) },
  SQS: vi.fn(() => ({ sendMessage: vi.fn() })),
}))

beforeEach(() => { vi.clearAllMocks() })

describe('{{SUT_NAME}}', () => {
  // Standard AAA tests
})
```

### Step 11 — Cancella `vitest-lambda.template.ts` originale

```bash
git rm skills/code-coverage/templates/vitest-lambda.template.ts
```

### Step 12 — Aggiorna `stack-matrix.json` per Lambda detection

In `skills/code-coverage/assets/stack-matrix.json`, aggiorna l'entry `vitest-lambda` (se esistente) o aggiungi:

```json
{
  "vitest-lambda": {
    "framework": "vitest",
    "template_handler_path": "templates/vitest-lambda-handler.template.ts",
    "template_module_path": "templates/vitest-lambda-module.template.ts",
    "detection_signal": "src/handlers/**/*.ts AND aws-lambda in package.json deps",
    "coverage_command": "npx vitest run --coverage --coverage.reporter=json-summary",
    "coverage_report_format": "vitest",
    "coverage_report_path": "coverage/coverage-summary.json"
  }
}
```

### Step 13 — Final integration smoke test

```bash
# Run full pipeline su benchmark MEDIUM (post task-08 finale)
bash tools/benchmark-skill.sh /tmp/bench-medium final

# Verifica delta vs baseline
python3 -c "
import json
data = json.load(open('docs/plans/2026-05-09-code-coverage-optimization/baseline-metrics.json'))
medium = [d for d in data if d['repo_name'] == 'digital-channels-sport-fe']
baseline = next(d for d in medium if d['run_label'] == 'baseline')
final = next(d for d in medium if d['run_label'] == 'final')
print(f\"Round-trip: {baseline['metrics']['user_round_trips']} → {final['metrics']['user_round_trips']}\")
print(f\"Coverage runs: {baseline['metrics']['full_coverage_runs']} → {final['metrics']['full_coverage_runs']}\")
print(f\"Wall-clock: {baseline['metrics']['wall_clock_seconds']}s → {final['metrics']['wall_clock_seconds']}s\")
print(f\"Coverage global: {baseline['metrics']['global_coverage_pct']}% → {final['metrics']['global_coverage_pct']}%\")
"
```

Atteso: round-trip 0, coverage runs 1-2, wall-clock < 60% baseline, coverage ≥ 70%.

### Step 14 — Spec-reviewer + Commit + PR

```bash
git add skills/code-coverage/scripts/plan_batches.py \
        skills/code-coverage/scripts/tests/test_plan_batches.py \
        skills/code-coverage/scripts/tests/fixtures/plan-input/ \
        skills/code-coverage/templates/vitest.template.ts \
        skills/code-coverage/templates/vitest-lambda-handler.template.ts \
        skills/code-coverage/templates/vitest-lambda-module.template.ts \
        skills/code-coverage/references/phase-5-generation.md \
        skills/code-coverage/assets/stack-matrix.json
# vitest-lambda.template.ts già staged via git rm

git commit -m "feat(code-coverage): plan_batches.py + multi-dep variants + lambda split (P8, ST3, ST8)

ST3: nuovo scripts/plan_batches.py con D1 conditional ordering
  - tier-first SE module_coverage non-empty
  - p-tier-fallback altrimenti
  - batch ceiling per tier (T1=3, T2=2, T3=1, T4=1)
  - skip patterns applied
  - 2 test pytest (con/senza module_coverage)

P8: selective dependency export grep deterministico in phase-5-generation.md
  - grep -nE per export shape detection
  - cache per (dep_path, session)
  - vitest.template.ts esteso con 4 variants (NO_DEPS, SINGLE_DEP, TWO_DEPS, MULTI_DEPS)

ST8: split vitest-lambda.template.ts in 2 file dedicati:
  - vitest-lambda-handler.template.ts (per Lambda handlers)
  - vitest-lambda-module.template.ts (per moduli interni)
  Eliminato dual-section warning.
  stack-matrix.json aggiornato con template_handler_path / template_module_path.

Refs design doc 2026-05-09-code-coverage-optimization-design.md PR8.

CHIUSURA PIANO: questa è l'ultima PR. Post-merge: ri-eseguire tools/benchmark-skill.sh
final su 3 repo benchmark per validare hard + soft acceptance criteria.

Co-Authored-By: SIAE DevForge"

git push -u origin feat/code-coverage-opt-plan-batches
gh pr create --title "feat(code-coverage): plan_batches + multi-dep + lambda split (P8, ST3, ST8)" --body "$(cat <<'EOF'
## Summary
- Nuovo `scripts/plan_batches.py` con D1 conditional ordering (tier-first vs P-tier fallback)
- 2 test pytest con fixture (with-coverage / no-coverage)
- vitest.template.ts esteso con 4 multi-dep variants
- `vitest-lambda.template.ts` split in handler + module template
- phase-5-generation.md aggiornato con grep deterministico P8

CHIUSURA PIANO: ultima PR del workflow.

Refs: docs/plans/2026-05-09-code-coverage-optimization-design.md PR8

## Test plan
- [x] 2 test plan_batches.py PASS
- [x] Coverage plan_batches.py >=70%
- [ ] Smoke test integrato: `bash tools/benchmark-skill.sh /tmp/bench-medium final` → verifica delta vs baseline
- [ ] Hard acceptance criteria (design doc §5.3) tutti soddisfatti
- [ ] Soft acceptance criteria → check policy go/no-go
- [ ] Spec-reviewer PASS

Co-Authored-By: SIAE DevForge
EOF
)"
```

---

## Acceptance criteria

- [ ] `scripts/plan_batches.py` esiste, eseguibile
- [ ] 2 test in `test_plan_batches.py` PASS
- [ ] Coverage `plan_batches.py` ≥ 70%
- [ ] D1 ordering verified: con `module_coverage` non-empty → tier-first; con empty → P-tier
- [ ] Batch ceiling rispettato (T1=3 max, T2=2, T3=1, T4=1)
- [ ] `phase-5-generation.md` Pre-Generation Checklist 3b contiene grep deterministico
- [ ] `vitest.template.ts` ha 4 varianti commentate
- [ ] `vitest-lambda-handler.template.ts` + `vitest-lambda-module.template.ts` esistenti
- [ ] `vitest-lambda.template.ts` originale cancellato (git rm)
- [ ] `stack-matrix.json` ha template_handler_path / template_module_path per Lambda
- [ ] Smoke integration: `bash tools/benchmark-skill.sh /tmp/bench-medium final` → metrics delta soddisfa hard criteria
- [ ] Spec-reviewer PASS

## Note operative

- Questa è la PR di chiusura: integra plan_batches con detect_stack (PR5) + parse_coverage (PR3) + categorize_failure (PR4)
- Post-merge eseguire benchmark finale su tutti i 3 repo (SMALL/MEDIUM/LARGE)
- Se hard criteria FAIL → rollback PR sospetta + retrospettiva
- Se soft criteria zona FAIL (vedi design doc §5.3) → rework prima di chiudere il piano
- A5/A8 hanno documentato il rischio "T1=3 round-trip non ammortizzati" su LARGE → A/B test post-merge con T1=5 per confermare/refutare
