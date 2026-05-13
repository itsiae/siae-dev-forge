"""Tests for v2 schema extensions — ScoreCard, RegressionVerdict, ReviewerVerdict."""
import json
from pathlib import Path

import pytest

from lib.review_evidence.schema import (
    EvidenceV2,
    ScoreCard,
    RegressionVerdict,
    ReviewerVerdict,
    evidence_from_json,
    evidence_to_json,
)

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_schema_version_2_0_supported():
    """v2 deserialize OK."""
    raw = json.loads((FIX / "evidence_v2_clean.json").read_text())
    ev = evidence_from_json(raw)
    assert ev.schema_version == "2.0"
    assert isinstance(ev, EvidenceV2)
    assert ev.current_scores.security == 85.0


def test_scorecard_fields():
    sc = ScoreCard(
        security=85.0, quality=72.0, coverage=68.0,
        spec_compliance=90.0, discipline=80.0, overall=79.0,
        weights_used={"security": 0.30, "quality": 0.20, "coverage": 0.20,
                       "spec_compliance": 0.15, "discipline": 0.15},
        missing_components=[],
    )
    assert sc.overall == 79.0
    assert sum(sc.weights_used.values()) == pytest.approx(1.0, abs=0.01)


def test_regression_verdict_5_decision_values():
    """F2 iter2 fix: 5 decision branch enum (no 4)."""
    valid = {"AUTO_APPROVE", "REVIEWER_HANDOFF", "BLOCK_HARD_FLOOR",
             "BLOCK_REGRESSION", "SEVERELY_DEGRADED"}
    for decision in valid:
        rv = RegressionVerdict(
            block_dimensions=[], warn_dimensions=[],
            improved_dimensions=[], hard_floor_breaches=[],
            decision=decision, reason="test",
        )
        assert rv.decision == decision


def test_reviewer_verdict_status():
    rv = ReviewerVerdict(
        status="APPROVED", reason="all good", invoked_at="2026-05-13T10:00:00Z",
        block=False,
    )
    assert rv.status == "APPROVED"
    assert rv.block is False


def test_forward_compat_unknown_fields_stripped():
    """Schema 1.5 (future minor) con UNKNOWN_FIELD non rompe."""
    raw = json.loads((FIX / "evidence_v2_with_unknown_fields.json").read_text())
    ev = evidence_from_json(raw)
    assert ev.schema_version == "1.5"
    # Unknown fields silently filtered (CRITICAL-1 fix from PR #241)
    assert ev.verdict.block is False


def test_v1_evidence_still_deserialize_as_v2():
    """v1 fixture (existing tests/fixtures/review-evidence/evidence_clean.json) must work."""
    raw = json.loads((FIX / "evidence_clean.json").read_text())
    ev = evidence_from_json(raw)
    assert ev.schema_version == "1.0"
    # v2-only fields are None on v1 deserialize (v1 returns plain Evidence,
    # not EvidenceV2, so v2-only attributes simply don't exist on it).
    assert getattr(ev, "current_scores", None) is None


def test_v2_roundtrip():
    raw = json.loads((FIX / "evidence_v2_clean.json").read_text())
    ev = evidence_from_json(raw)
    rebuilt = json.loads(evidence_to_json(ev))
    assert rebuilt["schema_version"] == "2.0"
    assert rebuilt["current_scores"]["security"] == 85.0
