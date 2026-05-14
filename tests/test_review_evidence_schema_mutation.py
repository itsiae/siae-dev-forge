"""Schema additive tests for MutationFindings field (v1.58+).

Forward-compat:
- v2 payload WITHOUT `mutation` field → deserialize ok, mutation=None
- v2 payload WITH `mutation` field → deserialize + roundtrip ok
- v1 payload → ignored mutation field (legacy reader doesn't see it)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from lib.review_evidence.schema import (  # noqa: E402
    Evidence,
    EvidenceV2,
    evidence_from_json,
    evidence_to_json,
)
from lib.review_evidence.scoring import MutationFindings  # noqa: E402


def _base_v2_payload() -> dict:
    return {
        "schema_version": "2.0",
        "sha": "abc123",
        "branch": "feat/x",
        "computed_at": "2026-05-14T10:00:00Z",
        "dirty_tree": False,
        "base_branch": "main",
        "stack_detected": ["python"],
        "metrics": {},
        "spec_drift": None,
        "verdict": {"block": False, "block_reasons": [], "warnings": []},
    }


def test_v2_without_mutation_field_deserializes_with_mutation_none():
    payload = _base_v2_payload()
    ev = evidence_from_json(payload)
    assert isinstance(ev, EvidenceV2)
    assert ev.mutation is None


def test_v2_with_mutation_findings_roundtrip():
    payload = _base_v2_payload()
    payload["mutation"] = {
        "score_pct": 72.5,
        "killed": 145,
        "survived": 50,
        "timeout": 5,
        "no_coverage": 0,
        "total_mutants": 200,
        "tool": "pit",
    }
    ev = evidence_from_json(payload)
    assert isinstance(ev, EvidenceV2)
    assert ev.mutation is not None
    assert ev.mutation.score_pct == 72.5
    assert ev.mutation.killed == 145
    assert ev.mutation.survived == 50
    assert ev.mutation.timeout == 5
    assert ev.mutation.total_mutants == 200
    assert ev.mutation.tool == "pit"

    # Roundtrip serialize
    out = json.loads(evidence_to_json(ev))
    assert out["mutation"]["score_pct"] == 72.5
    assert out["mutation"]["tool"] == "pit"


def test_v2_with_explicit_null_mutation():
    payload = _base_v2_payload()
    payload["mutation"] = None
    ev = evidence_from_json(payload)
    assert isinstance(ev, EvidenceV2)
    assert ev.mutation is None


def test_v1_payload_ignores_mutation_field():
    """v1 reader path should not even look at mutation; v1 still returns Evidence (not V2)."""
    payload = _base_v2_payload()
    payload["schema_version"] = "1.0"
    # Even if mutation field is sneaked into v1 payload, the v1 path
    # returns base Evidence (no mutation attribute).
    payload["mutation"] = {"score_pct": 50, "tool": "x"}
    ev = evidence_from_json(payload)
    assert isinstance(ev, Evidence)
    assert not isinstance(ev, EvidenceV2)
    assert not hasattr(ev, "mutation")


def test_v2_evidence_default_mutation_none_when_constructed_directly():
    ev = EvidenceV2(
        sha="x",
        branch="y",
        computed_at="z",
        dirty_tree=False,
        base_branch="main",
        stack_detected=[],
        metrics={},
        spec_drift=None,
        verdict=type("V", (), {"block": False, "block_reasons": [], "warnings": []})(),
    )
    assert ev.mutation is None


def test_mutation_findings_defaults():
    """All MutationFindings fields have safe defaults (allow gradual fill)."""
    m = MutationFindings()
    assert m.score_pct == 0.0
    assert m.killed == 0
    assert m.survived == 0
    assert m.timeout == 0
    assert m.no_coverage == 0
    assert m.total_mutants == 0
    assert m.tool == ""


def test_mutation_findings_full_construction():
    m = MutationFindings(
        score_pct=85.0,
        killed=170,
        survived=30,
        timeout=0,
        no_coverage=0,
        total_mutants=200,
        tool="mutmut",
    )
    assert m.score_pct == 85.0
    assert m.tool == "mutmut"


def test_v2_safe_kwargs_drops_unknown_mutation_fields():
    """Future-extended mutation field with extra keys must not crash deser."""
    payload = _base_v2_payload()
    payload["mutation"] = {
        "score_pct": 60,
        "killed": 60,
        "total_mutants": 100,
        "tool": "stryker",
        "fancy_future_field": "ignored",  # noqa: future-compat
    }
    ev = evidence_from_json(payload)
    assert isinstance(ev, EvidenceV2)
    assert ev.mutation is not None
    assert ev.mutation.tool == "stryker"
