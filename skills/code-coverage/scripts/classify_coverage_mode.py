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
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: classify_coverage_mode.py <repo_path>"}),
              file=sys.stderr)
        sys.exit(1)
    repo = Path(sys.argv[1]).resolve()
    bp_path = repo / ".code-coverage" / "batch-plan.json"
    uc_path = repo / ".code-coverage" / "user-choice.json"
    stack_path = repo / ".code-coverage" / "stack.json"

    if not bp_path.exists():
        print(json.dumps({"status": "error", "error": f"batch-plan.json not found: {bp_path}"}))
        sys.exit(0)

    bp = json.loads(bp_path.read_text())
    uc = json.loads(uc_path.read_text()) if uc_path.exists() else {}
    stack = json.loads(stack_path.read_text()) if stack_path.exists() else {}
    target_line = float(uc.get("target_line", 70))
    target_branch = float(uc.get("target_branch", 60))
    cur_line = float(stack.get("pre_existing_coverage_pct", 0) or 0)
    cur_branch = float(stack.get("pre_existing_branch_pct", 0) or 0)

    # Supporta sia "batches" (chiave prodotta da plan_batches.build_plan) sia
    # "pending_batches" (chiave legacy) per retrocompatibilità.
    batches = bp.get("batches", bp.get("pending_batches", []))
    for batch in batches:
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
                      sum(len(b.get("files", [])) for b in batches)}))


if __name__ == "__main__":
    main()
