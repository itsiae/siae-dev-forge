# Phase 7 — Repair Loop

**Goal**: dopo Phase 6, riparare moduli/test sotto threshold tramite categorizzazione deterministica + grouping per `error_signature` + fix scoped + progress guard.

**Pre-requisito**: `.code-coverage/coverage-report.json` (output di parse_coverage.py) + esecuzione test runner che ha prodotto stderr per ogni file failing.

## Algoritmo

```python
import json
import subprocess
from collections import defaultdict
from pathlib import Path

report = json.loads(Path(".code-coverage/coverage-report.json").read_text())
failing_tests = []  # popolato dal framework runner: list of (test_file, stderr_blob)

iteration = 0
max_iter = 3
prev_global_pct = 0.0
prev_failing_count = len(failing_tests)
loop_max_remaining = max_iter

while iteration < loop_max_remaining and (
    report["global_pct"] < 70
    or any(m["status"] == "FAIL" for m in report["modules"] if m.get("priority"))
):
    iteration += 1

    # 1) Categorize tutti i failure (scoped, no full-file regen)
    failures = []
    for test_file, stderr in failing_tests:
        cat_result = subprocess.run(
            ["python3", "skills/code-coverage/scripts/categorize_failure.py"],
            input=stderr, capture_output=True, text=True, check=True,
        ).stdout
        failures.append({"test_file": test_file, **json.loads(cat_result)})

    # Persisti per audit (TTL per-iter)
    Path(".code-coverage/failures.json").write_text(json.dumps({
        "iteration": iteration, "failures": failures
    }, indent=2))

    # 2) GROUPING per error_signature
    grouped = defaultdict(list)
    for f in failures:
        grouped[f["signature"]].append(f)

    # 3) SYSTEMIC FIX detection: count >= max(2, 30% del totale) E categoria systemic_eligible
    total_failing = max(len(failing_tests), 1)
    systemic_threshold = max(2, int(total_failing * 0.30))

    for signature, group in grouped.items():
        first = group[0]
        if first["systemic_eligible"] and len(group) >= systemic_threshold:
            apply_systemic_fix(first)  # config-level UNA volta
            continue
        for f in group:
            apply_scoped_fix(f)  # Edit del solo blocco failing

    # 4) Re-run SOLO test file modificati (no --coverage qui)
    rerun_modified_tests(failing_tests)

    # 5) Run full coverage UNA VOLTA per iterazione (Phase 6 redirect + parse_coverage.py)
    run_full_coverage()
    report = json.loads(Path(".code-coverage/coverage-report.json").read_text())
    new_failing_count = sum(1 for m in report["modules"] if m["status"] == "FAIL")

    # 6) PROGRESS GUARD
    delta_global = report["global_pct"] - prev_global_pct
    delta_failing = prev_failing_count - new_failing_count
    if delta_global < 0.5 and delta_failing <= 0:
        log("STOP: progress guard triggered (Δglobal<0.5pp AND no failure reduction)")
        break

    # 7) AUTONOMOUS EARLY-ABORT iter 1 (deterministico, zero prompt utente)
    if iteration == 1 and report["global_pct"] < 30:
        p1_modules = [m for m in report["modules"] if m.get("priority") == "P1"]
        if any(m["lines_pct"] < 40 for m in p1_modules):
            loop_max_remaining = iteration + 1  # 1 sola iter aggiuntiva
            log("WARN: critical low coverage, single retry attempted")

    prev_global_pct = report["global_pct"]
    prev_failing_count = new_failing_count

# OUTPUT — Block 8 con remaining failing + stalled files
emit_block_8_with_remaining_failing()
```

## Categorie failure (vedi `assets/repair-strategies.json`)

| Cat | Name       | Pattern signal                                       | Systemic eligible |
|-----|------------|------------------------------------------------------|-------------------|
| 1   | dependency | `Cannot find module`, `ModuleNotFoundError`         | YES (count≥2)     |
| 2   | import     | `does not provide an export`, `cannot import name`  | NO                |
| 3   | runtime    | `ReferenceError`, `is not defined`, timeout         | YES (count≥2)     |
| 4   | mock       | `expected mock to have been called`, factory error  | NO                |
| 5   | assertion  | `AssertionError`, expect mismatch                   | NO                |
| 6   | transient  | `ECONNRESET`, `OOM`, `EBUSY` (eval prima di Cat 1-5) | NO                |

L'ordine di valutazione è hardcoded in `categorize_failure.py`: Cat 6 (transient) PRIMA di Cat 1-5 per evitare false positive.

## Best-Effort Report (max_iter raggiunto / progress guard / early-abort)

In OUTPUT Block 8 aggiungi sotto-tabella **Stalled Files**:

```
| File | Iter | Last category | Last signature                       | Suggested action  |
|------|------|---------------|--------------------------------------|-------------------|
| ...  | 3    | mock          | ·expected mock·to have been called·  | Manual review     |
```

`signature` è output di `normalize()` da `categorize_failure.py` (path/timestamp/hex/ANSI stripped, max 200 char).
