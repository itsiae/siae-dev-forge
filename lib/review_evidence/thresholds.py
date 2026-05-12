"""Env-driven hard-block thresholds for review-evidence."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Thresholds:
    min_coverage: float = 60.0
    max_coverage_delta: float = -5.0
    max_lint_errors: int = 0
    max_complexity: int = 15
    ci_sarif_block_level: str = "critical"  # critical | high | off
    spec_drift_block: bool = True


def load_thresholds() -> Thresholds:
    return Thresholds(
        min_coverage=float(os.environ.get("DEVFORGE_EVIDENCE_MIN_COVERAGE", "60")),
        max_coverage_delta=float(os.environ.get("DEVFORGE_EVIDENCE_MAX_COVERAGE_DELTA", "-5")),
        max_lint_errors=int(os.environ.get("DEVFORGE_EVIDENCE_MAX_LINT_ERRORS", "0")),
        max_complexity=int(os.environ.get("DEVFORGE_EVIDENCE_MAX_COMPLEXITY", "15")),
        ci_sarif_block_level=os.environ.get("DEVFORGE_EVIDENCE_CI_SARIF_BLOCK_LEVEL", "critical"),
        spec_drift_block=os.environ.get("DEVFORGE_EVIDENCE_SPEC_DRIFT_BLOCK", "1") == "1",
    )


def compute_verdict(metrics: dict, spec_drift: dict | None, t: Thresholds) -> dict:
    reasons: list[str] = []
    warnings: list[str] = []

    cov = metrics.get("coverage", {})
    if isinstance(cov, dict) and cov.get("overall_pct") is not None:
        if cov["overall_pct"] < t.min_coverage:
            reasons.append(f"coverage_below_threshold:{cov['overall_pct']}<{t.min_coverage}")
        if cov.get("delta_vs_base") is not None and cov["delta_vs_base"] < t.max_coverage_delta:
            reasons.append(f"coverage_delta:{cov['delta_vs_base']}<{t.max_coverage_delta}")

    lint = metrics.get("lint", {})
    if isinstance(lint, dict) and lint.get("errors", 0) > t.max_lint_errors:
        reasons.append(f"lint_errors:{lint['errors']}>{t.max_lint_errors}")

    cx = metrics.get("complexity", {})
    if isinstance(cx, dict) and cx.get("max_cyclomatic", 0) > t.max_complexity:
        reasons.append(f"complexity_max:{cx['max_cyclomatic']}>{t.max_complexity}")

    ci = metrics.get("ci_quality", {})
    if isinstance(ci, dict) and ci.get("available"):
        if t.ci_sarif_block_level == "critical" and ci.get("problems_critical", 0) > 0:
            reasons.append(f"ci_critical:{ci['problems_critical']}>0")
        elif t.ci_sarif_block_level == "high" and (
            ci.get("problems_critical", 0) > 0 or ci.get("problems_high", 0) > 0
        ):
            reasons.append(
                f"ci_high:critical={ci.get('problems_critical', 0)},high={ci.get('problems_high', 0)}"
            )

    if spec_drift and t.spec_drift_block and spec_drift.get("drift_severity") == "high":
        reasons.append("drift_severity_high")

    return {"block": bool(reasons), "block_reasons": reasons, "warnings": warnings}
