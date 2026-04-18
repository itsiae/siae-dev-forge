"""Property-based tests via hypothesis (10 test)."""
from __future__ import annotations

import math
import statistics

from hypothesis import given, settings, strategies as st

import compute_ai_impact as ai
import compute_kpis as ck
import seasonality as s
from validators import assert_rate_in_range


@given(devs=st.dictionaries(
    st.text(min_size=1, max_size=10),
    st.floats(allow_nan=False, allow_infinity=False, allow_subnormal=False, min_value=-1000, max_value=1000),
    min_size=3, max_size=20,
))
@settings(max_examples=100, deadline=5000)
def test_z_score_sum_near_zero(devs):
    """Invariant: sum(z_score) ~ 0 per population."""
    result = ck.z_score(devs)
    if not result:
        return
    total = sum(result.values())
    assert abs(total) < 0.5, f"Sum z-scores too far from zero: {total}"


@given(devs=st.dictionaries(
    st.text(min_size=1, max_size=10),
    st.floats(allow_nan=False, allow_infinity=False, allow_subnormal=False, min_value=0, max_value=1000),
    min_size=3, max_size=20,
))
@settings(max_examples=50, deadline=5000)
def test_z_score_finite(devs):
    result = ck.z_score(devs)
    assert all(math.isfinite(v) for v in result.values())


@given(
    baseline=st.floats(min_value=0.01, max_value=1e6),
    current=st.floats(min_value=0, max_value=1e6),
)
@settings(max_examples=100)
def test_compute_delta_trend_never_nan(baseline, current):
    d = ai.compute_delta(baseline, current)
    assert d.trend in {"IMPROVED", "DEGRADED", "STABLE"}
    assert math.isfinite(d.delta_pct)


@given(year=st.integers(min_value=2020, max_value=2030))
def test_italian_holidays_count_is_12(year):
    assert len(s.italian_holidays(year)) == 12


@given(
    since=st.dates(
        min_value=__import__("datetime").date(2020, 1, 1),
        max_value=__import__("datetime").date(2030, 12, 31),
    ),
    days=st.integers(min_value=1, max_value=365),
)
def test_working_days_never_exceeds_total(since, days):
    from datetime import timedelta
    until = since + timedelta(days=days)
    wd = s.working_days_in_window(since.isoformat(), until.isoformat())
    assert 0 <= wd <= days + 1


@given(v=st.floats(allow_nan=False, allow_infinity=False, min_value=-10, max_value=10))
def test_z_score_uniform_returns_zero(v):
    devs = {"a": v, "b": v, "c": v}
    result = ck.z_score(devs)
    assert all(abs(z) < 1e-9 for z in result.values())


@given(
    skill_counts=st.dictionaries(st.text(min_size=1), st.integers(min_value=0, max_value=1000), min_size=3, max_size=20),
    roi=st.dictionaries(st.text(min_size=1), st.floats(allow_nan=False, allow_infinity=False, min_value=-5, max_value=5), min_size=3, max_size=20),
)
def test_correlation_in_range_minus1_to_1(skill_counts, roi):
    corr = ai.skill_usage_correlation(skill_counts, roi)
    if not math.isnan(corr):
        assert -1.001 <= corr <= 1.001


@given(rate=st.floats(min_value=0, max_value=1))
def test_rate_invariant_accepts_valid(rate):
    assert_rate_in_range(rate, "test")  # no raise


@given(bad_rate=st.floats(allow_nan=False, min_value=1.001, max_value=1e6))
def test_rate_invariant_rejects_invalid(bad_rate):
    import pytest as pt
    with pt.raises(ValueError):
        assert_rate_in_range(bad_rate, "test")


@given(items=st.lists(st.floats(allow_nan=False, min_value=0, max_value=1e4), min_size=1, max_size=50))
def test_median_robust_to_any_input_size(items):
    m = statistics.median(items)
    assert math.isfinite(m)
