"""JSON schema v1 for review-evidence framework.

Dataclass + serialization. Versioned schema with explicit upgrade path.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

SCHEMA_VERSION = "1.0"
SUPPORTED_VERSIONS = {"1.0"}
# Forward-compat: accept any 1.x version on read (minor bumps are additive
# only by contract). Major version bumps (2.x) must be rejected — they
# signal a breaking change that an old reader cannot interpret safely.
# E12 mitigation.
CURRENT_MAJOR = 1


@dataclass
class CoverageMetric:
    overall_pct: float
    delta_vs_base: float
    per_file: list[dict[str, Any]] = field(default_factory=list)
    source: str = "local:unknown"


@dataclass
class LintMetric:
    errors: int
    warnings: int
    findings: list[dict[str, Any]] = field(default_factory=list)
    source: str = "local:unknown"
    # MAJOR-3: surface tool availability + reason so consumers can tell
    # "0 findings" apart from "tool missing / config error" (E25, E27).
    available: bool = True
    reason: Optional[str] = None


@dataclass
class ComplexityMetric:
    max_cyclomatic: int
    files_over_threshold: list[dict[str, Any]] = field(default_factory=list)
    source: str = "local:unknown"


@dataclass
class CiQualityMetric:
    available: bool
    ci_run_id: Optional[str] = None
    problems_critical: int = 0
    problems_high: int = 0
    findings: list[dict[str, Any]] = field(default_factory=list)
    source: Optional[str] = None


@dataclass
class SpecDrift:
    design_doc_path: str
    files_in_plan: list[str]
    files_changed: list[str]
    unplanned_files: list[str]
    drift_severity: str  # none|low|medium|high


@dataclass
class Verdict:
    block: bool
    block_reasons: list[str]
    warnings: list[str]


@dataclass
class Evidence:
    sha: str
    branch: str
    computed_at: str
    dirty_tree: bool
    base_branch: str
    stack_detected: list[str]
    metrics: dict[str, Any]  # keys: coverage, lint, complexity, ci_quality
    spec_drift: Optional[SpecDrift]
    verdict: Verdict
    schema_version: str = SCHEMA_VERSION


def _check_version(version: str) -> None:
    """E12: accept any 1.x (minor bumps are additive only by contract),
    raise on major bumps (2.x and beyond) which signal breaking changes.

    The previous strict-set rejected ``1.1`` even though we contract minor
    bumps to be backward-readable. A reader written for 1.0 must keep
    accepting 1.x payloads; only a major version bump warrants rejection.
    """
    if version in SUPPORTED_VERSIONS:
        return
    parts = version.split(".")
    if len(parts) >= 1 and parts[0].isdigit():
        major = int(parts[0])
        if major == CURRENT_MAJOR:
            return  # forward-compat minor (e.g. "1.1", "1.42")
    raise ValueError(f"unsupported schema_version: {version}")


def _safe_kwargs(cls, data: dict) -> dict:
    """Strip unknown kwargs so dataclass __init__ doesn't raise on
    forward-compat fields (E12). A reader for 1.0 must keep accepting
    1.x payloads even if minor bumps introduce new fields — by contract
    minor bumps are additive only, so unknown fields are safe to ignore.
    """
    if not data:
        return {}
    known = cls.__dataclass_fields__
    return {k: v for k, v in data.items() if k in known}


def evidence_from_json(raw: dict[str, Any]) -> Evidence:
    version = raw["schema_version"]
    _check_version(version)

    metrics = {}
    raw_metrics = raw.get("metrics", {})
    if "coverage" in raw_metrics:
        metrics["coverage"] = CoverageMetric(**_safe_kwargs(CoverageMetric, raw_metrics["coverage"]))
    if "lint" in raw_metrics:
        metrics["lint"] = LintMetric(**_safe_kwargs(LintMetric, raw_metrics["lint"]))
    if "complexity" in raw_metrics:
        metrics["complexity"] = ComplexityMetric(**_safe_kwargs(ComplexityMetric, raw_metrics["complexity"]))
    if "ci_quality" in raw_metrics:
        metrics["ci_quality"] = CiQualityMetric(**_safe_kwargs(CiQualityMetric, raw_metrics["ci_quality"]))

    spec_drift = None
    if raw.get("spec_drift"):
        spec_drift = SpecDrift(**_safe_kwargs(SpecDrift, raw["spec_drift"]))

    return Evidence(
        schema_version=version,
        sha=raw["sha"],
        branch=raw["branch"],
        computed_at=raw["computed_at"],
        dirty_tree=raw["dirty_tree"],
        base_branch=raw["base_branch"],
        stack_detected=raw["stack_detected"],
        metrics=metrics,
        spec_drift=spec_drift,
        verdict=Verdict(**_safe_kwargs(Verdict, raw["verdict"])),
    )


def evidence_to_json(ev: Evidence) -> str:
    out: dict[str, Any] = {
        "schema_version": ev.schema_version,
        "sha": ev.sha,
        "branch": ev.branch,
        "computed_at": ev.computed_at,
        "dirty_tree": ev.dirty_tree,
        "base_branch": ev.base_branch,
        "stack_detected": ev.stack_detected,
        "metrics": {k: asdict(v) for k, v in ev.metrics.items()},
        "spec_drift": asdict(ev.spec_drift) if ev.spec_drift else None,
        "verdict": asdict(ev.verdict),
    }
    return json.dumps(out, indent=2, sort_keys=False)
