"""Test compute_ai_impact.py — AI Impact dual-window + attribution."""
import math
import pandas as pd
import compute_ai_impact as ai


def test_is_ai_assisted_detects_devforge_trailer():
    msg = "feat(auth): add login\n\nCo-Authored-By: SIAE DevForge <devforge@siae.it>"
    assert ai.is_ai_assisted(msg) is True


def test_is_ai_assisted_detects_claude_trailer():
    msg = "fix: resolve bug\n\nCo-Authored-By: Claude <claude@anthropic.com>"
    assert ai.is_ai_assisted(msg) is True


def test_is_ai_assisted_case_insensitive():
    msg = "feat: x\n\nco-authored-by: siae devforge <d@s.it>"
    assert ai.is_ai_assisted(msg) is True


def test_is_ai_assisted_multiline_match():
    msg = "feat: x\n\nReviewed-By: bob\nCo-Authored-By: Anthropic <a@a.com>\nSigned-off-by: alice"
    assert ai.is_ai_assisted(msg) is True


def test_is_ai_assisted_empty_returns_false():
    assert ai.is_ai_assisted("") is False
    assert ai.is_ai_assisted(None) is False


def test_compute_delta_improvement_lower_better():
    d = ai.compute_delta(10.0, 5.0, lower_is_better=True)
    assert d.trend == "IMPROVED"
    assert d.delta_pct == -50.0


def test_compute_delta_clamp_infinity_at_9999():
    d = ai.compute_delta(0.0, 100.0)
    assert d.delta_pct == 9999.0


def test_compute_delta_stable_threshold_5pct():
    d = ai.compute_delta(100.0, 103.0)  # +3%
    assert d.trend == "STABLE"


def test_ai_velocity_multiplier_happy():
    result = ai.kpi_ai_velocity_multiplier(
        ai_cycle={"alice": 5.0, "bob": 3.0},
        manual_cycle={"carol": 12.0, "dave": 8.0},
    )
    # median(manual) = 10.0, median(ai) = 4.0 → 2.5
    assert result == 2.5


def test_ai_velocity_multiplier_zero_ai_returns_1():
    assert ai.kpi_ai_velocity_multiplier({}, {"carol": 12.0}) == 1.0


def test_skill_correlation_returns_nan_if_N_lt_3():
    result = ai.skill_usage_correlation({"alice": 10}, {"alice": 5.0})
    assert math.isnan(result)


def test_skill_correlation_positive_computed():
    skill = {"alice": 10, "bob": 20, "carol": 30}
    roi = {"alice": 1.0, "bob": 2.0, "carol": 3.0}
    result = ai.skill_usage_correlation(skill, roi)
    assert result > 0.9  # Perfect positive correlation
