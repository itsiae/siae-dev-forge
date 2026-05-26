"""Criterion 17: Security vulnerability state (MVP HEAD-only, ADR-11).

NO baseline delta in MVP — evolution path in design sez. 12 backlog.
"""
from __future__ import annotations

import os
from pathlib import Path
from lib.release_risk.schema import CriterionResult

CRITICAL_TRIGGER = 0  # > this → trigger
HIGH_TRIGGER = 5      # > this → trigger


def _load_runners():
    """Carica runners disponibili. Returns list[runner_instance]."""
    runners = []
    try:
        from lib.review_evidence.runners.pip_audit import PipAuditRunner
        runners.append(PipAuditRunner())
    except ImportError:
        pass
    try:
        from lib.review_evidence.runners.npm_audit import NpmAuditRunner
        runners.append(NpmAuditRunner())
    except ImportError:
        pass
    return runners


def evaluate_criterion_17(repo_root: Path, runners_override=None) -> CriterionResult:
    """Criterion 17 entry HEAD-only.

    Args:
        runners_override: list di runner per test injection.

    Returns:
        CriterionResult weight=2.
    """
    runners = runners_override if runners_override is not None else _load_runners()
    applicable_runners = [r for r in runners if r.is_applicable(repo_root)]

    if not applicable_runners:
        return CriterionResult(
            id=17, name="Security vulnerability state",
            status="TOOL_UNAVAILABLE", weight=2,
            evidence=["No applicable runner (pip-audit/npm-audit) for this tech stack"],
            source="runners",
            notes="Maven repos: run mvn dependency-check or trivy fs manually",
        )

    # Aggrega counts dai runner applicabili
    total_critical = 0
    total_high = 0
    runner_names = []
    threshold_critical_override = int(os.environ.get("DEVFORGE_RELEASE_RISK_SECURITY_CRITICAL_THRESHOLD", CRITICAL_TRIGGER))
    threshold_high_override = int(os.environ.get("DEVFORGE_RELEASE_RISK_SECURITY_HIGH_THRESHOLD", HIGH_TRIGGER))

    for runner in applicable_runners:
        findings = runner.run(repo_root)
        if findings is None:
            continue
        total_critical += findings.critical
        total_high += findings.high
        runner_names.append(type(runner).__name__)

    if not runner_names:
        return CriterionResult(
            id=17, name="Security vulnerability state",
            status="TOOL_UNAVAILABLE", weight=2,
            evidence=["Runners applicable but all returned None"],
            source="runners",
        )

    trigger = (total_critical > threshold_critical_override or
               total_high > threshold_high_override)
    suggested_followup = (total_critical > 0 or total_high > 10)

    return CriterionResult(
        id=17, name="Security vulnerability state",
        status="YES" if trigger else "NO", weight=2,
        evidence=[
            f"runners={','.join(runner_names)}",
            f"critical={total_critical}", f"high={total_high}",
            f"threshold_critical={threshold_critical_override}",
            f"threshold_high={threshold_high_override}",
            f"suggested_followup_security={suggested_followup}",
        ],
        source="runners",
        notes="MVP HEAD-only state, no delta vs baseline. Vedi design sez. 12 backlog per v2.x delta.",
    )
