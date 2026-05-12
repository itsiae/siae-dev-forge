"""Tests for lib/review_evidence/schema.py — JSON schema v1."""
import json
from pathlib import Path

import pytest

from lib.review_evidence.schema import (
    Evidence,
    CoverageMetric,
    LintMetric,
    ComplexityMetric,
    CiQualityMetric,
    SpecDrift,
    Verdict,
    SCHEMA_VERSION,
    evidence_from_json,
    evidence_to_json,
)

FIXTURES = Path(__file__).parent / "fixtures" / "review-evidence"


def test_schema_version_is_1_0():
    assert SCHEMA_VERSION == "1.0"


def test_evidence_clean_roundtrip():
    raw = json.loads((FIXTURES / "evidence_clean.json").read_text())
    ev = evidence_from_json(raw)
    assert ev.sha == "abc123"
    assert ev.verdict.block is False
    assert ev.verdict.block_reasons == []
    assert ev.dirty_tree is False
    roundtrip = json.loads(evidence_to_json(ev))
    assert roundtrip == raw


def test_evidence_full_block_has_reasons():
    raw = json.loads((FIXTURES / "evidence_full_block.json").read_text())
    ev = evidence_from_json(raw)
    assert ev.verdict.block is True
    assert len(ev.verdict.block_reasons) >= 1
    assert ev.metrics["coverage"].overall_pct < 60.0


def test_missing_required_field_raises():
    with pytest.raises(KeyError):
        evidence_from_json({"sha": "abc"})  # manca schema_version


def test_unknown_schema_version_raises():
    bad = {"schema_version": "99.0", "sha": "x", "branch": "x", "computed_at": "x",
            "dirty_tree": False, "base_branch": "main", "stack_detected": [],
            "metrics": {}, "spec_drift": None, "verdict": {"block": False, "block_reasons": [], "warnings": []}}
    with pytest.raises(ValueError, match="unsupported schema_version"):
        evidence_from_json(bad)


def test_schema_forward_compat_minor_strips_unknown_fields():
    """Schema 1.x must accept unknown fields gracefully (forward-compat promise).

    A reader written for 1.0 must NOT raise when it encounters unknown
    fields in a 1.x payload — minor bumps are additive by contract, so
    unknown fields are expected and must be silently ignored. Without
    filtering, ``LintMetric(**raw_metrics["lint"])`` would raise
    ``TypeError: __init__() got an unexpected keyword argument`` on any
    new field introduced in 1.1+.
    """
    raw = {
        "schema_version": "1.1",
        "sha": "abc",
        "branch": "x",
        "computed_at": "x",
        "dirty_tree": False,
        "base_branch": "main",
        "stack_detected": [],
        "metrics": {
            "lint": {
                "errors": 0,
                "warnings": 0,
                "findings": [],
                "source": "x",
                "available": True,
                "reason": None,
                "UNKNOWN_NEW_FIELD_1_2": "future",  # forward-compat field
            },
            "coverage": {
                "overall_pct": 80.0,
                "delta_vs_base": 0.0,
                "per_file": [],
                "source": "x",
                "UNKNOWN_COVERAGE_FIELD": 42,
            },
            "complexity": {
                "max_cyclomatic": 5,
                "files_over_threshold": [],
                "source": "x",
                "UNKNOWN_COMPLEXITY_FIELD": True,
            },
            "ci_quality": {
                "available": True,
                "ci_run_id": "1",
                "problems_critical": 0,
                "problems_high": 0,
                "findings": [],
                "source": "x",
                "UNKNOWN_CI_FIELD": "future",
            },
        },
        "spec_drift": {
            "design_doc_path": "x",
            "files_in_plan": [],
            "files_changed": [],
            "unplanned_files": [],
            "drift_severity": "none",
            "UNKNOWN_DRIFT_FIELD": "future",
        },
        "verdict": {
            "block": False,
            "block_reasons": [],
            "warnings": [],
            "UNKNOWN_VERDICT_FIELD": "future",
        },
    }
    ev = evidence_from_json(raw)  # must NOT raise
    assert ev.schema_version == "1.1"
    assert ev.metrics["lint"].errors == 0
    assert ev.metrics["coverage"].overall_pct == 80.0
    assert ev.metrics["complexity"].max_cyclomatic == 5
    assert ev.metrics["ci_quality"].available is True
    assert ev.spec_drift is not None
    assert ev.spec_drift.drift_severity == "none"
    assert ev.verdict.block is False
