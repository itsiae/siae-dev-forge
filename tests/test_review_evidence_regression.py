"""Tests for the review-evidence v2 regression analyzer + hard floor gate.

Covers Task 11 critical fixes:

- **E1** budget snapshot is immutable (deepcopy at PR_OPEN_TIME).
- **F1 + E5** hard floor priority above regression check, non-overridable.
- **E5** ``min_dim`` floor blocks even when ``overall`` clears its floor.
- **A6** first-PR baseline_synthetic → AUTO_APPROVE on score above floor.

Decision priority asserted across the suite (high → low):
``BLOCK_HARD_FLOOR`` → ``BLOCK_REGRESSION`` → ``REVIEWER_HANDOFF`` →
``AUTO_APPROVE``.
"""
from __future__ import annotations

from lib.review_evidence.config import DevForgeScoresConfig
from lib.review_evidence.regression import (
    RegressionInput,
    compute_regression_verdict,
    compute_regression_verdict_from_input,
    is_hard_floor_breached,
    snapshot_budget_at_pr_open,
)
from lib.review_evidence.schema import ScoreCard


def _sc(**kw) -> ScoreCard:
    """Build a ScoreCard with sensible defaults, overridable per test.

    Defaults are deliberately above every hard floor so tests can opt-in
    to a specific failure mode by overriding only the relevant fields.
    """
    base = dict(
        security=80,
        quality=70,
        coverage=65,
        spec_compliance=85,
        discipline=90,
        overall=78,
        weights_used={},
        missing_components=[],
    )
    base.update(kw)
    return ScoreCard(**base)


def test_no_regression_auto_approve():
    """Identical current/baseline above floor → AUTO_APPROVE."""
    cfg = DevForgeScoresConfig()
    current = _sc(security=80, overall=78)
    baseline = _sc(security=80, overall=78)
    rv = compute_regression_verdict(current, baseline, cfg, baseline_synthetic=False)
    assert rv.decision == "AUTO_APPROVE"
    assert rv.block_dimensions == []
    assert rv.warn_dimensions == []
    assert rv.hard_floor_breaches == []


def test_hard_floor_security_breach_block():
    """E5 + F1: security < 60 → BLOCK_HARD_FLOOR, non-overridable."""
    cfg = DevForgeScoresConfig()
    # security=55 breaches the dedicated security floor (60).
    # Baseline equals current so there is no regression signal — the
    # gate must still fire because hard floor is non-overridable.
    current = _sc(security=55, overall=70)
    baseline = _sc(security=55, overall=70)
    rv = compute_regression_verdict(current, baseline, cfg, baseline_synthetic=False)
    assert rv.decision == "BLOCK_HARD_FLOOR"
    assert rv.hard_floor_breaches, "must populate breaches list for renderer"
    assert "security" in rv.hard_floor_breaches[0].lower()
    assert "non-overridable" in rv.reason.lower()


def test_min_dim_hard_floor_block():
    """E5: ANY dim < 40 → BLOCK_HARD_FLOOR (separate from overall floor)."""
    cfg = DevForgeScoresConfig()  # min_dim=40
    # quality=35 < min_dim=40 even though overall=75 clears its own floor.
    # This proves the min_dim check is INDEPENDENT from the overall check.
    current = _sc(security=80, quality=35, overall=75)
    baseline = _sc(security=80, quality=35, overall=75)
    rv = compute_regression_verdict(current, baseline, cfg, baseline_synthetic=False)
    assert rv.decision == "BLOCK_HARD_FLOOR"
    assert any(
        "quality" in b.lower() or "min_dim" in b.lower()
        for b in rv.hard_floor_breaches
    )


def test_regression_below_warn_handoff_to_reviewer():
    """Delta in warn zone → REVIEWER_HANDOFF.

    security delta = -2; hard_block_budget=-2 (strict less-than → NOT
    block); warn_budget=0 → warn zone. Reviewer agent gatekeeps.
    """
    cfg = DevForgeScoresConfig()
    current = _sc(security=78, overall=76)
    baseline = _sc(security=80, overall=78)
    rv = compute_regression_verdict(current, baseline, cfg, baseline_synthetic=False)
    # security delta=-2, hard_block=-2 (not strictly less), warn=0 → warn.
    assert rv.decision == "REVIEWER_HANDOFF"
    assert any("security" in w for w in rv.warn_dimensions)
    assert rv.hard_floor_breaches == []


def test_regression_below_hard_block():
    """Delta worse than hard_block budget → BLOCK_REGRESSION."""
    cfg = DevForgeScoresConfig()
    # security delta=-5 < hard_block=-2 → block.
    current = _sc(security=75, overall=70)
    baseline = _sc(security=80, overall=78)
    rv = compute_regression_verdict(current, baseline, cfg, baseline_synthetic=False)
    assert rv.decision == "BLOCK_REGRESSION"
    assert any("security" in b for b in rv.block_dimensions)
    # No hard-floor breach because current security=75 still >= 60.
    assert rv.hard_floor_breaches == []


def test_baseline_synthetic_first_pr_auto_approve():
    """A6: first PR → baseline_synthetic=True → skip regression check."""
    cfg = DevForgeScoresConfig()
    # Score is intentionally modest (70/70) — well above every floor but
    # would still trigger regression checks vs an imaginary perfect
    # baseline. baseline_synthetic must short-circuit that path.
    current = _sc(security=70, overall=70)
    rv = compute_regression_verdict(
        current, baseline=None, cfg=cfg, baseline_synthetic=True
    )
    assert rv.decision == "AUTO_APPROVE"
    assert "synthetic" in rv.reason.lower() or "first pr" in rv.reason.lower()


def test_snapshot_budget_at_pr_open_immutable():
    """E1: snapshot at PR_OPEN_TIME is immune to subsequent admin mutations."""
    cfg = DevForgeScoresConfig()
    snapshot1 = snapshot_budget_at_pr_open(cfg, pr_open_iso="2026-05-13T10:00:00Z")

    # Admin retroactively tightens the budget on the live cfg.
    cfg.hard_block_budget["security"] = -50
    cfg.hard_floors["security"] = 90
    cfg.weights["security"] = 0.99

    # Taking a fresh snapshot would reflect the new values, but snapshot1
    # must keep the original ones — that's the whole point of E1.
    snapshot2 = snapshot_budget_at_pr_open(cfg, pr_open_iso="2026-05-13T10:00:00Z")
    assert snapshot1["hard_block_budget"]["security"] == -2
    assert snapshot1["hard_floors"]["security"] == 60
    assert snapshot1["weights"]["security"] == 0.30
    # And snapshot2 sees the mutated values, proving deepcopy is per-call.
    assert snapshot2["hard_block_budget"]["security"] == -50
    assert snapshot2["hard_floors"]["security"] == 90
    # ISO timestamp is echoed back verbatim so callers can persist it.
    assert snapshot1["pr_open_iso"] == "2026-05-13T10:00:00Z"


def test_is_hard_floor_breached_uniform():
    """``is_hard_floor_breached`` boolean fast-path matches the detailed gate."""
    cfg = DevForgeScoresConfig()

    # security=55 < hard_floor.security=60 → breached.
    sc_breached = _sc(security=55)
    assert is_hard_floor_breached(sc_breached, cfg) is True

    # All dims and overall above their floors → not breached. Note
    # overall=60 >= 55 floor; security=70 >= 60; coverage=65 >= 50.
    sc_ok = _sc(security=70, overall=60)
    assert is_hard_floor_breached(sc_ok, cfg) is False


# ---------------------------------------------------------------------------
# Light coverage of the auxiliary dataclass so it doesn't bit-rot.
# Not part of the 8 "must-pass" core tests in the task plan but free
# insurance against accidental field renames.
# ---------------------------------------------------------------------------


def test_regression_input_dataclass_roundtrip():
    cfg = DevForgeScoresConfig()
    current = _sc()
    baseline = _sc()
    inp = RegressionInput(
        current=current, baseline=baseline, cfg=cfg, baseline_synthetic=False
    )
    assert inp.current is current
    assert inp.baseline is baseline
    assert inp.cfg is cfg
    assert inp.baseline_synthetic is False


def test_compute_regression_verdict_from_input_delegates():
    """Convenience wrapper produces the same verdict as the positional form.

    Closes the dead-code gap on ``RegressionInput`` (fresh-eyes review iter 1
    finding): the dataclass now has a real consumer.
    """
    cfg = DevForgeScoresConfig()
    current = _sc(security=80, overall=78)
    baseline = _sc(security=80, overall=78)
    inp = RegressionInput(
        current=current, baseline=baseline, cfg=cfg, baseline_synthetic=False
    )

    rv_via_input = compute_regression_verdict_from_input(inp)
    rv_positional = compute_regression_verdict(
        current=current, baseline=baseline, cfg=cfg, baseline_synthetic=False
    )

    assert rv_via_input.decision == rv_positional.decision
    assert rv_via_input.reason == rv_positional.reason
    assert rv_via_input.block_dimensions == rv_positional.block_dimensions
