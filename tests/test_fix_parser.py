"""Unit tests for lib/review_evidence/fix_parser.py.

Covers all 5 atomic patterns (MVP + follow-up PR-D):
    - coverage_below_threshold (priority 2)
    - lint_errors              (priority 1)
    - complexity_max           (priority 3)
    - drift_severity_high      (priority 4)
    - ci_critical              (priority 0 — security highest)
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
    ev = _evidence_with_reasons(["foobar_unmapped:42>0"])
    actions = parse_block_reasons(ev)
    assert len(actions) == 1
    a = actions[0]
    assert a.kind == "unknown"
    assert a.sub_skill is None
    assert "foobar_unmapped:42>0" in a.prompt


def test_empty_block_reasons_returns_empty_list() -> None:
    """No reasons -> no actions. Caller treats this as AUTO_APPROVE."""
    ev = _evidence_with_reasons([])
    actions = parse_block_reasons(ev)
    assert actions == []


def test_complexity_max_matched() -> None:
    """complexity_max:X>Y -> siae-tdd refactor, priority 3."""
    ev = _evidence_with_reasons(["complexity_max:25>15"])
    actions = parse_block_reasons(ev)
    assert len(actions) == 1
    a = actions[0]
    assert a.kind == "complexity"
    assert a.sub_skill == "siae-tdd"
    assert a.priority == 3
    assert "25" in a.prompt and "15" in a.prompt
    assert "metrics.complexity.files_over_threshold" in a.prompt


def test_drift_severity_high_matched() -> None:
    """drift_severity_high -> siae-brainstorming, priority 4 (lowest)."""
    ev = _evidence_with_reasons(["drift_severity_high"])
    actions = parse_block_reasons(ev)
    assert len(actions) == 1
    a = actions[0]
    assert a.kind == "drift"
    assert a.sub_skill == "siae-brainstorming"
    assert a.priority == 4
    assert "spec_drift.unplanned_files" in a.prompt
    assert "spec_drift.design_doc_path" in a.prompt


def test_ci_critical_matched_and_full_priority_order() -> None:
    """ci_critical:X>Y -> siae-debugging SARIF fix at priority 0 (highest),
    AND edge-case: when ALL 5 atomic patterns are present with shuffled
    insertion order they must sort
    ci_critical (0) -> lint (1) -> coverage (2) -> complexity (3) -> drift (4).
    """
    # Single-pattern attribute checks
    ev = _evidence_with_reasons(["ci_critical:7>0"])
    actions = parse_block_reasons(ev)
    assert len(actions) == 1
    a = actions[0]
    assert a.kind == "ci_critical"
    assert a.sub_skill == "siae-debugging"
    assert a.priority == 0
    assert "7" in a.prompt
    assert "metrics.ci_quality.findings" in a.prompt

    # Edge case: full priority order with shuffled insertion order
    ev_all = _evidence_with_reasons([
        "drift_severity_high",
        "coverage_below_threshold:45<60",
        "ci_critical:2>0",
        "complexity_max:25>15",
        "lint_errors:3>0",
    ])
    actions_all = parse_block_reasons(ev_all)
    assert [x.kind for x in actions_all] == [
        "ci_critical", "lint", "coverage", "complexity", "drift",
    ]
    assert [x.priority for x in actions_all] == [0, 1, 2, 3, 4]
