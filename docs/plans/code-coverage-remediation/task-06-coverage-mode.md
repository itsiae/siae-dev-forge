# Task 06 — `classify_coverage_mode.py`

**Goal:** Nuovo script che assegna a ogni file `coverage_mode = "branch-priority" | "line-priority"`. È `branch-priority` se `branch_operator_count > 20` **oppure** (line già ≥ 85% del target E branch < 80% del target). Default `line-priority`. Risolve gap 6.6/R3 (la skill genera happy-path che alza line ma non branch).

**WS:** WS-2 · **Dipendenze:** Task 05 (`branch_operator_count`), Task 01 (`pre_existing_branch_pct`).

## File coinvolti
- Crea: `skills/code-coverage/scripts/classify_coverage_mode.py`
- Crea: `skills/code-coverage/scripts/tests/test_classify_coverage_mode.py`

## Step TDD

### Step 1 — Test fallente
Crea `skills/code-coverage/scripts/tests/test_classify_coverage_mode.py`:

```python
import classify_coverage_mode as ccm


def test_branch_heavy_forces_branch_priority():
    assert ccm.classify(branch_operator_count=30, current_line=10, current_branch=10,
                         target_line=70, target_branch=60) == "branch-priority"


def test_line_done_branch_far():
    # line quasi al target (60 >= 70*0.85=59.5), branch lontana (40 < 60*0.8=48)
    assert ccm.classify(branch_operator_count=5, current_line=60, current_branch=40,
                        target_line=70, target_branch=60) == "branch-priority"


def test_default_line_priority():
    assert ccm.classify(branch_operator_count=0, current_line=10, current_branch=10,
                        target_line=70, target_branch=60) == "line-priority"
```

### Step 2 — Verifica che fallisce
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_classify_coverage_mode.py -v`
Output atteso: ImportError → 3 FAILED.

### Step 3 — Implementa `scripts/classify_coverage_mode.py`

```python
#!/usr/bin/env python3
"""classify_coverage_mode.py — assegna coverage_mode per-file.

branch-priority se:
  - branch_operator_count > 20  (file branch-heavy), OPPURE
  - current_line >= target_line * 0.85  AND  current_branch < target_branch * 0.80
Altrimenti line-priority (default first-pass).

CLI: aggiunge "coverage_mode" a ogni file in batch-plan.json.pending_batches[].files[]
leggendo branch-count/<file>.json (Task 05) e stack.json (Task 01).
"""
import json
import sys
from pathlib import Path


def classify(branch_operator_count: int, current_line: float, current_branch: float,
             target_line: float, target_branch: float) -> str:
    branch_heavy = branch_operator_count > 20
    line_nearly_done = current_line >= target_line * 0.85
    branch_far = current_branch < target_branch * 0.80
    if branch_heavy or (line_nearly_done and branch_far):
        return "branch-priority"
    return "line-priority"


def _branch_count_for(repo: Path, file_path: str) -> int:
    safe = file_path.replace("/", "__")
    bc = repo / ".code-coverage" / "branch-count" / f"{safe}.json"
    try:
        return int(json.loads(bc.read_text()).get("count", 0))
    except Exception:
        return 0


def main() -> None:
    repo = Path(sys.argv[1]).resolve()
    bp_path = repo / ".code-coverage" / "batch-plan.json"
    uc_path = repo / ".code-coverage" / "user-choice.json"
    stack_path = repo / ".code-coverage" / "stack.json"
    bp = json.loads(bp_path.read_text())
    uc = json.loads(uc_path.read_text()) if uc_path.exists() else {}
    stack = json.loads(stack_path.read_text()) if stack_path.exists() else {}
    target_line = float(uc.get("target_line", 70))
    target_branch = float(uc.get("target_branch", 60))
    cur_line = float(stack.get("pre_existing_coverage_pct", 0) or 0)
    cur_branch = float(stack.get("pre_existing_branch_pct", 0) or 0)

    for batch in bp.get("pending_batches", []):
        for f in batch.get("files", []):
            path = f.get("path", "")
            boc = f.get("branch_operator_count")
            if boc is None:
                boc = _branch_count_for(repo, path)
                f["branch_operator_count"] = boc
            f["coverage_mode"] = classify(boc, cur_line, cur_branch,
                                          target_line, target_branch)
    bp_path.write_text(json.dumps(bp, indent=2))
    print(json.dumps({"status": "ok", "files_classified":
                      sum(len(b.get("files", [])) for b in bp.get("pending_batches", []))}))


if __name__ == "__main__":
    main()
```

### Step 4 — Verifica che passa
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_classify_coverage_mode.py -v`
Output atteso: `3 passed`.

### Step 5 — Commit
```
git add skills/code-coverage/scripts/classify_coverage_mode.py skills/code-coverage/scripts/tests/test_classify_coverage_mode.py
git commit -m "feat(code-coverage): classify per-file coverage_mode (line vs branch priority)"
```

## Criteri di accettazione
- [ ] `branch_operator_count>20` → `branch-priority` indipendentemente dalla coverage corrente.
- [ ] line≥85%·target e branch<80%·target → `branch-priority`.
- [ ] caso base → `line-priority`.
- [ ] CLI aggiorna `batch-plan.json` aggiungendo `coverage_mode` e `branch_operator_count` per file.
