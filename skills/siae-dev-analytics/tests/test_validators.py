"""Test per validators.py — Pydantic v2 config models + runtime invariants + ROI v2.

15 test:
  3 happy-path: single_window_valid, dual_window_valid, scope_repos_only
  7 validation: repo_format_no_slash, invalid_date_format, to_before_from,
                dual_overlap, empty_scope, parallel_fetch_out_of_range (0, 17),
                format_invalid (pdf)
  4 invariants: rate_in_range_valid, rate_in_range_invalid,
                finite_nan_raises, finite_inf_raises
  3 ROI v2: happy_path, zero_cost_fallback, zero_seasonality_fallback
"""
from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

import validators as v


# ────────────────────────────────────────────────────────
# Happy-path (3)
# ────────────────────────────────────────────────────────

def test_single_window_valid():
    """TimeWindowSingle accetta date ISO valide con to >= from."""
    tw = v.TimeWindowSingle(**{"from": "2026-01-01", "to": "2026-03-31"})
    assert tw.from_ == "2026-01-01"
    assert tw.to == "2026-03-31"


def test_dual_window_valid():
    """TimeWindowDual accetta baseline + current non-overlapping."""
    tw = v.TimeWindowDual(
        baseline=v.TimeWindowSingle(**{"from": "2025-01-01", "to": "2025-06-30"}),
        current=v.TimeWindowSingle(**{"from": "2026-01-01", "to": "2026-03-31"}),
        enable_ai_impact=True,
    )
    assert tw.baseline.from_ == "2025-01-01"
    assert tw.current.to == "2026-03-31"
    assert tw.enable_ai_impact is True


def test_scope_repos_only():
    """ScopeConfigV2 valida con solo repos in formato owner/name."""
    scope = v.ScopeConfigV2(repos=["itsiae/repo-alpha", "itsiae/repo-beta"])
    assert len(scope.repos) == 2
    assert scope.teams == []
    assert scope.topics == []


# ────────────────────────────────────────────────────────
# Validation errors (7)
# ────────────────────────────────────────────────────────

def test_repo_format_no_slash():
    """Repo senza '/' deve fallire con messaggio actionable >= 20 char."""
    with pytest.raises(ValidationError, match="Usa il formato owner/name"):
        v.ScopeConfigV2(repos=["invalid-repo-no-slash"])


def test_invalid_date_format():
    """Data non ISO deve fallire con messaggio actionable."""
    with pytest.raises(ValidationError, match="Usa il formato ISO"):
        v.TimeWindowSingle(**{"from": "01/01/2026", "to": "2026-03-31"})


def test_to_before_from():
    """to < from deve fallire con messaggio actionable."""
    with pytest.raises(ValidationError, match="Verifica che 'to' sia >= 'from'"):
        v.TimeWindowSingle(**{"from": "2026-06-01", "to": "2026-01-01"})


def test_dual_overlap():
    """Baseline.to >= current.from deve fallire (overlap)."""
    with pytest.raises(ValidationError, match="Configura baseline.to < current.from"):
        v.TimeWindowDual(
            baseline=v.TimeWindowSingle(**{"from": "2026-01-01", "to": "2026-06-30"}),
            current=v.TimeWindowSingle(**{"from": "2026-03-01", "to": "2026-09-30"}),
        )


def test_empty_scope():
    """Scope vuoto (no repos/teams/topics) deve fallire."""
    with pytest.raises(ValidationError, match="Configura almeno uno tra repos, teams, topics"):
        v.AnalyticsConfigV2(
            scope=v.ScopeConfigV2(),
            time_window=v.TimeWindowSingle(**{"from": "2026-01-01", "to": "2026-03-31"}),
        )


def test_parallel_fetch_out_of_range():
    """parallel_fetch=0 (< 1) e parallel_fetch=17 (> 16) devono fallire."""
    with pytest.raises(ValidationError):
        v.OptionsConfigV2(parallel_fetch=0)
    with pytest.raises(ValidationError):
        v.OptionsConfigV2(parallel_fetch=17)


def test_format_invalid():
    """format='pdf' deve fallire."""
    with pytest.raises(ValidationError):
        v.OutputConfigV2(format="pdf")


# ────────────────────────────────────────────────────────
# Runtime invariants (4)
# ────────────────────────────────────────────────────────

def test_rate_in_range_valid():
    """assert_rate_in_range accetta valori 0 <= x <= 1."""
    v.assert_rate_in_range(0.0, "test_rate")
    v.assert_rate_in_range(0.5, "test_rate")
    v.assert_rate_in_range(1.0, "test_rate")


def test_rate_in_range_invalid():
    """assert_rate_in_range rifiuta valori fuori range con messaggio actionable."""
    with pytest.raises(ValueError, match="Verifica che test_rate"):
        v.assert_rate_in_range(1.5, "test_rate")
    with pytest.raises(ValueError, match="Verifica che neg_rate"):
        v.assert_rate_in_range(-0.1, "neg_rate")


def test_finite_nan_raises():
    """assert_finite rifiuta NaN con messaggio actionable."""
    with pytest.raises(ValueError, match="Verifica che roi_nan"):
        v.assert_finite(float("nan"), "roi_nan")


def test_finite_inf_raises():
    """assert_finite rifiuta +inf/-inf con messaggio actionable."""
    with pytest.raises(ValueError, match="Verifica che roi_inf"):
        v.assert_finite(float("inf"), "roi_inf")
    with pytest.raises(ValueError, match="Verifica che roi_neg_inf"):
        v.assert_finite(float("-inf"), "roi_neg_inf")


# ────────────────────────────────────────────────────────
# ROI v2 index (3)
# ────────────────────────────────────────────────────────

def test_roi_v2_happy_path():
    """kpi_roi_v2_index con dati normali produce risultato finito."""
    from compute_kpis import kpi_roi_v2_index

    result = kpi_roi_v2_index(
        features_shipped={"alice": 10, "bob": 5},
        complexity_weight_by_dev={"alice": 1.2, "bob": 0.8},
        compliance_rate_by_dev={"alice": 0.9, "bob": 0.7},
        cost_by_dev={"alice": 100.0, "bob": 50.0},
        seasonality_adj=1.0,
    )
    # alice: (10 * 1.2 * 0.9) / (100 * 1.0) = 10.8 / 100 = 0.108
    assert math.isclose(result["alice"], 0.108, rel_tol=1e-6)
    # bob: (5 * 0.8 * 0.7) / (50 * 1.0) = 2.8 / 50 = 0.056
    assert math.isclose(result["bob"], 0.056, rel_tol=1e-6)


def test_roi_v2_zero_cost_fallback():
    """cost=0 deve usare fallback 1.0 (no ZeroDivisionError)."""
    from compute_kpis import kpi_roi_v2_index

    result = kpi_roi_v2_index(
        features_shipped={"alice": 10},
        complexity_weight_by_dev={"alice": 1.0},
        compliance_rate_by_dev={"alice": 1.0},
        cost_by_dev={"alice": 0},
        seasonality_adj=1.0,
    )
    # cost=0 -> fallback 1.0, roi = (10 * 1.0 * 1.0) / (1.0 * 1.0) = 10.0
    assert math.isclose(result["alice"], 10.0, rel_tol=1e-6)


def test_roi_v2_zero_seasonality_fallback():
    """seasonality_adj <= 0 deve usare fallback 1.0."""
    from compute_kpis import kpi_roi_v2_index

    result = kpi_roi_v2_index(
        features_shipped={"alice": 10},
        complexity_weight_by_dev={"alice": 1.0},
        compliance_rate_by_dev={"alice": 1.0},
        cost_by_dev={"alice": 50.0},
        seasonality_adj=0.0,
    )
    # seasonality_adj=0 -> fallback 1.0, roi = (10 * 1.0 * 1.0) / (50 * 1.0) = 0.2
    assert math.isclose(result["alice"], 0.2, rel_tol=1e-6)
