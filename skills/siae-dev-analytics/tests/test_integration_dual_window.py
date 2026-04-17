"""Integration tests dual-window AI Impact end-to-end (8 test)."""
from __future__ import annotations

import pandas as pd
import pytest

import compute_ai_impact as ai
import compute_kpis as ck
import seasonality as s


def _make_prs(state="MERGED", n=5, author="alice"):
    """Helper: crea DataFrame PR mock."""
    return pd.DataFrame([{
        "repo": "itsiae/test-repo",
        "number": i + 1,
        "author": author,
        "created_at": f"2026-0{(i % 3) + 1}-15T10:00:00+00:00",
        "merged_at": f"2026-0{(i % 3) + 1}-16T14:00:00+00:00" if state == "MERGED" else None,
        "closed_at": None,
        "updated_at": f"2026-0{(i % 3) + 1}-16T14:00:00+00:00",
        "state": state,
        "is_draft": False,
        "reopen_count": 0,
        "is_stuck": False,
        "cycle_time_hours": 28.0 + i,
        "lead_time_hours": 30.0 + i,
        "time_to_first_review_hours": 4.0,
        "review_comments": 2,
        "has_tests": True,
        "has_design_link": i % 2 == 0,
        "additions": 100 + i * 10,
        "deletions": 20 + i,
    } for i in range(n)])


def _make_commits(n=10, author="alice", with_ai=False):
    return pd.DataFrame([{
        "author": author,
        "committed_at": f"2026-02-{10+i}T10:00:00+00:00",
        "message": f"{'feat' if i%3==0 else 'fix'}(core): change {i}"
                   + ("\n\nCo-Authored-By: SIAE DevForge <d@s.it>" if with_ai and i % 2 == 0 else ""),
        "is_revert": False,
        "has_verified_trailer": i % 3 == 0,
    } for i in range(n)])


def test_dual_window_before_after_comparison_produces_deltas():
    """E2E: baseline + current → Delta per KPI."""
    baseline = ai.WindowMetrics(
        kpis={"pr_cycle_time_p50": {"alice": 48.0}, "pr_throughput_weekly": {"alice": 2.0}},
        window=("2026-01-01", "2026-02-14"),
        n_prs=5,
    )
    current = ai.WindowMetrics(
        kpis={"pr_cycle_time_p50": {"alice": 24.0}, "pr_throughput_weekly": {"alice": 5.0}},
        window=("2026-02-15", "2026-04-15"),
        n_prs=10,
    )
    deltas = ai.before_after_comparison(baseline, current)
    assert "pr_cycle_time_p50" in deltas
    assert deltas["pr_cycle_time_p50"].trend == "IMPROVED"  # lower is better
    assert deltas["pr_throughput_weekly"].trend == "IMPROVED"  # higher is better


def test_dual_window_overlap_raises_actionable():
    """TimeWindowDual con overlap → ValueError con messaggio actionable."""
    from validators import TimeWindowDual, TimeWindowSingle
    with pytest.raises(Exception) as exc_info:
        TimeWindowDual(
            baseline=TimeWindowSingle(**{"from": "2026-01-01", "to": "2026-03-01"}),
            current=TimeWindowSingle(**{"from": "2026-02-15", "to": "2026-04-15"}),
        )
    assert "Configura" in str(exc_info.value) or "overlap" in str(exc_info.value).lower()


def test_dual_window_baseline_empty_no_crash_warning():
    """Baseline vuota → deltas calcolati con 0, nessun crash."""
    baseline = ai.WindowMetrics(kpis={}, window=("2026-01-01", "2026-02-14"))
    current = ai.WindowMetrics(kpis={"pr_throughput_weekly": {"alice": 5.0}}, window=("2026-02-15", "2026-04-15"))
    deltas = ai.before_after_comparison(baseline, current)
    assert "pr_throughput_weekly" in deltas


def test_dual_window_current_empty_no_crash():
    baseline = ai.WindowMetrics(kpis={"pr_throughput_weekly": {"alice": 3.0}}, window=("2026-01-01", "2026-02-14"))
    current = ai.WindowMetrics(kpis={}, window=("2026-02-15", "2026-04-15"))
    deltas = ai.before_after_comparison(baseline, current)
    assert deltas["pr_throughput_weekly"].trend == "DEGRADED"


def test_dual_window_ai_impact_kpi_computed():
    """AI-assisted PR rate e velocity multiplier calcolabili."""
    prs = _make_prs()
    commits = _make_commits(with_ai=True)
    rate = ai.kpi_ai_assisted_pr_rate(prs, commits)
    assert "alice" in rate
    assert 0 <= rate["alice"] <= 1


def test_dual_window_seasonality_adjustment_applied():
    """seasonality_adj in agosto < 1.0."""
    adj = s.seasonality_adj("2026-08-01", "2026-08-31")
    assert adj < 0.75


def test_dual_window_velocity_multiplier_with_data():
    """ai_velocity_multiplier con dati reali non crasha."""
    m = ai.kpi_ai_velocity_multiplier({"alice": 24.0}, {"bob": 48.0})
    assert m == 2.0


def test_dual_window_correlation_3_devs():
    """Correlation con 3+ dev produce valore finito."""
    import math
    corr = ai.skill_usage_correlation(
        {"alice": 10, "bob": 20, "carol": 30},
        {"alice": 1.0, "bob": 2.0, "carol": 3.0},
    )
    assert math.isfinite(corr)
    assert corr > 0.9
