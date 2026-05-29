#!/usr/bin/env python3
"""predict_coverage.py — prediction upfront di line/branch post Phase 6/7.

Coefficienti empirici (calibrati su 1 post-mortem). Confidence mai HIGH in v1.
Usage CLI: predict_coverage.py <repo>   (legge size/stack/user-choice/batch-plan)
Scrive .code-coverage/coverage-prediction.json
"""
import json
import math
import sys
from pathlib import Path

_LINE_GAIN = {"SMALL": 8, "MEDIUM": 6, "LARGE": 5, "VERY_LARGE": 4}
_BRANCH_GAIN = {"SMALL": 5, "MEDIUM": 4, "LARGE": 3, "VERY_LARGE": 2}
_BRANCH_OPS_PER_LOC = 0.015


def predict(size_class: str, n_batches: int, total_loc: int, pre_line: float,
            pre_branch: float, target_line: float, target_branch: float) -> dict:
    """Calcola la prediction di line/branch coverage post Phase 6/7.

    Args:
        size_class: classe dimensionale del repository (SMALL/MEDIUM/LARGE/VERY_LARGE).
        n_batches: numero di batch nel batch-plan.
        total_loc: linee di codice totali del repository.
        pre_line: percentuale di line coverage pre-esistente.
        pre_branch: percentuale di branch coverage pre-esistente (0 se assente).
        target_line: target di line coverage richiesto dall'utente.
        target_branch: target di branch coverage richiesto dall'utente.

    Returns:
        dict con chiavi: schema_version, inputs, predictions (con confidence),
        risk_flags.
    """
    est_ops = int(total_loc * _BRANCH_OPS_PER_LOC)
    line_gain = n_batches * _LINE_GAIN.get(size_class, 4)
    branch_gain = n_batches * _BRANCH_GAIN.get(size_class, 2)
    p6_line = min(95, pre_line + line_gain)
    p6_branch = min(95, pre_branch + branch_gain)
    max_iter = min(10, max(3, math.ceil(n_batches * 1.5))) if n_batches else 3
    p7_line = min(95, p6_line + max_iter * 1.5)
    p7_branch = min(95, p6_branch + max_iter * 2.5)

    risk_flags = []
    gap = target_branch - p7_branch
    if gap > 0:
        risk_flags.append({
            "flag": "BRANCH_GAP_HIGH_RISK",
            "description": f"Predicted branch after Phase 7 ({p7_branch:.1f}%) is "
                           f"{gap:.1f}pp below target ({target_branch}%).",
            "recommended_action": "branch-priority mode OR accept BEST_EFFORT",
        })

    if pre_branch == 0:
        conf, reason = "LOW", "No pre-existing branch data; LOC-only estimate"
    elif est_ops > 300:
        conf, reason = "LOW", f"High branch-operator density (~{est_ops})"
    else:
        conf, reason = "MEDIUM", "Pre-existing branch data available"

    return {
        "schema_version": "1.0",
        "inputs": {"size_class": size_class, "batch_count": n_batches,
                   "total_branch_operators_estimated": est_ops,
                   "pre_existing_line_pct": pre_line, "pre_existing_branch_pct": pre_branch,
                   "target_line": target_line, "target_branch": target_branch},
        "predictions": {
            "predicted_line_after_phase6": round(p6_line, 1),
            "predicted_branch_after_phase6": round(p6_branch, 1),
            "predicted_line_after_phase7": round(p7_line, 1),
            "predicted_branch_after_phase7": round(p7_branch, 1),
            "confidence": conf, "confidence_reason": reason,
        },
        "risk_flags": risk_flags,
    }


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: predict_coverage.py <repo>"}),
              file=sys.stderr)
        sys.exit(1)
    repo = Path(sys.argv[1]).resolve()
    cc = repo / ".code-coverage"
    size = json.loads((cc / "size.json").read_text()) if (cc / "size.json").exists() else {}
    stack = json.loads((cc / "stack.json").read_text()) if (cc / "stack.json").exists() else {}
    uc = json.loads((cc / "user-choice.json").read_text()) if (cc / "user-choice.json").exists() else {}
    bp = json.loads((cc / "batch-plan.json").read_text()) if (cc / "batch-plan.json").exists() else {}
    out = predict(
        size_class=size.get("class", "MEDIUM"),
        n_batches=len(bp.get("batches", bp.get("pending_batches", []))),
        total_loc=int(size.get("loc", 0) or 0),
        pre_line=float(stack.get("pre_existing_coverage_pct", 0) or 0),
        pre_branch=float(stack.get("pre_existing_branch_pct", 0) or 0),
        target_line=float(uc.get("target_line", 70)),
        target_branch=float(uc.get("target_branch", 60)),
    )
    (cc / "coverage-prediction.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out["predictions"]))


if __name__ == "__main__":
    main()
