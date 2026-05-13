"""JSON schema for review-evidence framework.

Dataclass + serialization. Versioned schema with explicit upgrade path.

v1 (1.x) — original review-evidence (PR #241):
    Binary block/no-block verdict.

v2 (2.x) — scoring extension (this PR):
    Additive Optional fields on ``Evidence`` via ``EvidenceV2(Evidence)``.
    Adds ScoreCard/RegressionVerdict/ReviewerVerdict. v1 clients can still
    read v2 payloads because the new fields are stripped via ``_safe_kwargs``
    (CRITICAL-1 forward-compat from PR #241).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

SCHEMA_VERSION = "2.0"  # current writer version
# Versions historically present in fixtures + the new v2 writer. Forward-compat
# for any 1.x or 2.x minor bump is handled by `_check_version` below.
SUPPORTED_VERSIONS = {"1.0", "1.1", "2.0"}
# Majors accepted by this reader. 1.x stays readable so v1 fixtures keep
# working; 2.x is the current writer. A new major bump (3.x) must explicitly
# extend this set after auditing breakage. E12 mitigation.
SUPPORTED_MAJORS = {1, 2}


# ---------------------------------------------------------------------------
# v1 dataclass (PR #241)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# v2 dataclass (scoring extension)
# ---------------------------------------------------------------------------


@dataclass
class ScoreCard:
    """Score deterministico per 5 dimensioni (0-100) + overall weighted.

    Emesso sia per il commit corrente (``current_scores``) sia per la
    baseline (``baseline_scores``) recuperata da S3 / fallback locale.
    """
    security: float
    quality: float
    coverage: float
    spec_compliance: float
    discipline: float
    overall: float
    weights_used: dict[str, float] = field(default_factory=dict)
    missing_components: list[str] = field(default_factory=list)


@dataclass
class RegressionVerdict:
    """Verdict scoring-based con 5 decision branch (F2 iter2 fix)."""
    block_dimensions: list[str]
    warn_dimensions: list[str]
    improved_dimensions: list[str]
    hard_floor_breaches: list[str]
    # 5 valori ammessi:
    #   AUTO_APPROVE | REVIEWER_HANDOFF | BLOCK_HARD_FLOOR
    #   | BLOCK_REGRESSION | SEVERELY_DEGRADED
    decision: str
    reason: str


@dataclass
class ReviewerVerdict:
    """Esito gatekeeper agent (Step 0.6) — emesso solo se reviewer invocato."""
    status: str  # APPROVED|REJECTED|PENDING|NOT_INVOKED
    reason: str
    invoked_at: Optional[str] = None
    block: bool = False


@dataclass
class EvidenceV2(Evidence):
    """Extension v1 → v2 — additive Optional fields only.

    v1 clients ignore these fields (CRITICAL-1 forward-compat from PR #241).
    """
    base_sha: Optional[str] = None
    baseline_scores: Optional[ScoreCard] = None
    current_scores: Optional[ScoreCard] = None
    deltas: Optional[dict[str, float]] = None
    regression_verdict: Optional[RegressionVerdict] = None
    reviewer_verdict: Optional[ReviewerVerdict] = None
    budget_snapshot_at: Optional[str] = None
    baseline_synthetic: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _version_tuple(version: str) -> tuple[int, ...]:
    """Parse ``"1.10"`` → ``(1, 10)`` so numeric comparison is safe.

    String compare would give ``"1.10" < "2.0"`` lexicographically — correct
    here, but ``"1.10" < "1.2"`` lexicographically — wrong. Always use the
    tuple form when comparing schema versions.
    """
    parts = version.split(".")
    out: list[int] = []
    for p in parts:
        if not p.isdigit():
            raise ValueError(f"unsupported schema_version: {version}")
        out.append(int(p))
    return tuple(out)


def _check_version(version: str) -> None:
    """Accept any minor bump within a supported major; reject other majors.

    Forward-compat contract: minor bumps are additive only, so a reader for
    ``N.0`` must keep accepting ``N.x`` payloads. A new major signals a
    breaking change and must extend ``SUPPORTED_MAJORS`` explicitly.
    """
    if version in SUPPORTED_VERSIONS:
        return
    try:
        major = _version_tuple(version)[0]
    except ValueError:
        raise ValueError(f"unsupported schema_version: {version}")
    if major in SUPPORTED_MAJORS:
        return  # forward-compat minor (e.g. "1.1", "1.42", "2.7")
    raise ValueError(f"unsupported schema_version: {version}")


def _safe_kwargs(cls, data: dict) -> dict:
    """Strip unknown kwargs so dataclass __init__ doesn't raise on
    forward-compat fields (E12, CRITICAL-1 PR #241). A reader for ``N.0``
    must keep accepting ``N.x`` payloads even if minor bumps introduce new
    fields — by contract minor bumps are additive only, so unknown fields
    are safe to ignore.
    """
    if not data:
        return {}
    known = cls.__dataclass_fields__
    return {k: v for k, v in data.items() if k in known}


def _parse_metrics(raw_metrics: dict[str, Any]) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    if "coverage" in raw_metrics:
        metrics["coverage"] = CoverageMetric(**_safe_kwargs(CoverageMetric, raw_metrics["coverage"]))
    if "lint" in raw_metrics:
        metrics["lint"] = LintMetric(**_safe_kwargs(LintMetric, raw_metrics["lint"]))
    if "complexity" in raw_metrics:
        metrics["complexity"] = ComplexityMetric(**_safe_kwargs(ComplexityMetric, raw_metrics["complexity"]))
    if "ci_quality" in raw_metrics:
        metrics["ci_quality"] = CiQualityMetric(**_safe_kwargs(CiQualityMetric, raw_metrics["ci_quality"]))
    return metrics


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def evidence_from_json(raw: dict[str, Any]) -> Evidence:
    version = raw["schema_version"]
    _check_version(version)

    metrics = _parse_metrics(raw.get("metrics", {}))

    spec_drift: Optional[SpecDrift] = None
    if raw.get("spec_drift"):
        spec_drift = SpecDrift(**_safe_kwargs(SpecDrift, raw["spec_drift"]))

    verdict = Verdict(**_safe_kwargs(Verdict, raw["verdict"]))

    # v2+ payload → emit EvidenceV2 with the optional scoring fields parsed.
    # v1 payloads (1.x) keep the legacy ``Evidence`` return so existing
    # collectors / tests that introspect attributes don't break.
    major = _version_tuple(version)[0]
    if major >= 2:
        current_scores = (
            ScoreCard(**_safe_kwargs(ScoreCard, raw["current_scores"]))
            if raw.get("current_scores") else None
        )
        baseline_scores = (
            ScoreCard(**_safe_kwargs(ScoreCard, raw["baseline_scores"]))
            if raw.get("baseline_scores") else None
        )
        regression_verdict = (
            RegressionVerdict(**_safe_kwargs(RegressionVerdict, raw["regression_verdict"]))
            if raw.get("regression_verdict") else None
        )
        reviewer_verdict = (
            ReviewerVerdict(**_safe_kwargs(ReviewerVerdict, raw["reviewer_verdict"]))
            if raw.get("reviewer_verdict") else None
        )
        return EvidenceV2(
            schema_version=version,
            sha=raw["sha"],
            branch=raw["branch"],
            computed_at=raw["computed_at"],
            dirty_tree=raw["dirty_tree"],
            base_branch=raw["base_branch"],
            stack_detected=raw["stack_detected"],
            metrics=metrics,
            spec_drift=spec_drift,
            verdict=verdict,
            base_sha=raw.get("base_sha"),
            baseline_scores=baseline_scores,
            current_scores=current_scores,
            deltas=raw.get("deltas"),
            regression_verdict=regression_verdict,
            reviewer_verdict=reviewer_verdict,
            budget_snapshot_at=raw.get("budget_snapshot_at"),
            baseline_synthetic=raw.get("baseline_synthetic", False),
        )

    # v1.x — existing return path unchanged
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
        verdict=verdict,
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
    # v2 additive fields — only serialized when the instance actually carries
    # them, so v1 ``Evidence`` instances round-trip identically.
    if isinstance(ev, EvidenceV2):
        out["current_scores"] = asdict(ev.current_scores) if ev.current_scores else None
        out["baseline_scores"] = asdict(ev.baseline_scores) if ev.baseline_scores else None
        out["deltas"] = ev.deltas
        out["regression_verdict"] = asdict(ev.regression_verdict) if ev.regression_verdict else None
        out["reviewer_verdict"] = asdict(ev.reviewer_verdict) if ev.reviewer_verdict else None
        out["base_sha"] = ev.base_sha
        out["budget_snapshot_at"] = ev.budget_snapshot_at
        out["baseline_synthetic"] = ev.baseline_synthetic
    return json.dumps(out, indent=2, sort_keys=False)
