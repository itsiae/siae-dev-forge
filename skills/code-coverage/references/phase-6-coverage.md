# Phase 6 — Coverage Measurement

**Goal**: misurare la coverage finale dopo Phase 5 e produrre il report tipizzato consumato dal Phase 6→7 Gate.

## Comando

```bash
# Lookup framework + comando da assets/stack-matrix.json (key: stack rilevato in Phase 1)
STACK_KEY=$(jq -r '.stack_key' .code-coverage/stack.json)
COV_CMD=$(jq -r --arg s "$STACK_KEY" '.stacks[$s].coverage_command' skills/code-coverage/assets/stack-matrix.json)
REPORT_PATH=$(jq -r --arg s "$STACK_KEY" '.stacks[$s].coverage_report_path' skills/code-coverage/assets/stack-matrix.json)
FORMAT=$(jq -r --arg s "$STACK_KEY" '.stacks[$s].coverage_report_format' skills/code-coverage/assets/stack-matrix.json)

# Esegui coverage (output framework-specific su REPORT_PATH)
cd <target_repo> && eval "$COV_CMD" 2>&1 | tee .code-coverage/coverage-stdout.log

# Parse deterministico via parse_coverage.py (output: .code-coverage/coverage-report.json)
python3 skills/code-coverage/scripts/parse_coverage.py "$FORMAT" "<target_repo>/$REPORT_PATH" \
  > <target_repo>/.code-coverage/coverage-report.json
```

Framework supportati da `parse_coverage.py`: `vitest`, `jest`, `pytest`, `jacoco`, `kover`, `go-test`, `cargo`, `dotnet`.

## Output Contract — `.code-coverage/coverage-report.json`

```json
{
  "global_pct": 75.5,
  "global_branch_pct": 70.0,
  "modules": [
    {"path": "src/services/payment.ts", "lines_pct": 85.0, "branch_pct": 80.0,
     "priority": "P1", "threshold": 80.0, "status": "PASS"}
  ],
  "failing": ["src/utils/format.ts"],
  "framework": "vitest",
  "error": null
}
```

`failing` contiene il subset di moduli con `status == "FAIL"`. `error` è `null` se parse ha avuto successo, altrimenti contiene il messaggio diagnostico (in tal caso il report è degraded ma non blocca).

## Fallback per framework esotici

Se `coverage_report_format` non è disponibile o il file non esiste:
1. Cerca tabella coverage in stdout: `tail -n 400 .code-coverage/coverage-stdout.log | grep -E '<framework_table_pattern>'`
2. Se grep trova match, parsing manuale ad-hoc (degraded mode, log in `decisions.log`).
3. Altrimenti emit `error: "no coverage data captured"` in `coverage-report.json` e prosegui a OUTPUT con avviso.

## Phase 6 → Phase 7 Gate

```python
import json
report = json.load(open(".code-coverage/coverage-report.json"))
needs_repair = (
    report["global_pct"] < 70
    or any(m["status"] == "FAIL" for m in report["modules"] if m.get("priority"))
)
# needs_repair == False -> skip Phase 7, vai direttamente a OUTPUT
# needs_repair == True  -> entra in Phase 7 con failing[] come input
```

Il gate consuma SOLO `coverage-report.json` — la skill NON ri-parsea stdout in questa fase.
