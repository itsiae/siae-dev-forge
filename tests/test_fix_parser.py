"""Unit tests for lib/review_evidence/fix_parser.py (MVP — 2 atomic patterns).

Out-of-scope MVP: E2E loop test (deferred to follow-up PR-D).
"""
from __future__ import annotations

from lib.review_evidence.fix_parser import FixAction, parse_block_reasons
from lib.review_evidence.schema import Evidence, Verdict


def _evidence_with_reasons(reasons: list[str]) -> Evidence:
    """Minimal Evidence stub with only the fields fix_parser reads."""
    return Evidence(
        sha="abc1234",
        branch="feat/test",
        computed_at="2026-05-13T00:00:00Z",
        dirty_tree=False,
        base_branch="main",
        stack_detected=["python"],
        metrics={},
        spec_drift=None,
        verdict=Verdict(block=bool(reasons), block_reasons=reasons, warnings=[]),
    )


def test_coverage_below_threshold_matched() -> None:
    ev = _evidence_with_reasons(["coverage_below_threshold:45<60"])
    actions = parse_block_reasons(ev)
    assert len(actions) == 1
    a = actions[0]
    assert a.kind == "coverage"
    assert a.sub_skill == "siae-tdd"
    assert a.priority == 2
    assert "45" in a.prompt and "60" in a.prompt
    assert "metrics.coverage.per_file" in a.prompt


def test_lint_errors_matched() -> None:
    ev = _evidence_with_reasons(["lint_errors:3>0"])
    actions = parse_block_reasons(ev)
    assert len(actions) == 1
    a = actions[0]
    assert a.kind == "lint"
    assert a.sub_skill == "siae-code-standards"
    assert a.priority == 1
    assert "3" in a.prompt
    assert "metrics.lint.findings" in a.prompt


def test_both_reasons_sorted_by_priority() -> None:
    """Lint (priority=1) must come before coverage (priority=2), regardless
    of insertion order in block_reasons."""
    ev = _evidence_with_reasons([
        "coverage_below_threshold:45<60",
        "lint_errors:3>0",
    ])
    actions = parse_block_reasons(ev)
    assert len(actions) == 2
    assert actions[0].kind == "lint"
    assert actions[1].kind == "coverage"


def test_unknown_reason_emits_unknown_action() -> None:
    """Non-matching reason -> kind='unknown', sub_skill=None so the loop
    can escalate instead of crashing on a new upstream reason format."""
    ev = _evidence_with_reasons(["complexity_max:25>15"])
    actions = parse_block_reasons(ev)
    assert len(actions) == 1
    a = actions[0]
    assert a.kind == "unknown"
    assert a.sub_skill is None
    assert "complexity_max:25>15" in a.prompt


def test_empty_block_reasons_returns_empty_list() -> None:
    """No reasons -> no actions. Caller treats this as AUTO_APPROVE."""
    ev = _evidence_with_reasons([])
    actions = parse_block_reasons(ev)
    assert actions == []
