"""Tests for lib/review_evidence/thresholds.py — env-driven hard-block thresholds."""
import pytest
from lib.review_evidence.thresholds import (
    load_thresholds,
    compute_verdict,
    Thresholds,
)


def test_load_thresholds_defaults(monkeypatch):
    for v in [
        "DEVFORGE_EVIDENCE_MIN_COVERAGE",
        "DEVFORGE_EVIDENCE_MAX_COVERAGE_DELTA",
        "DEVFORGE_EVIDENCE_MAX_LINT_ERRORS",
        "DEVFORGE_EVIDENCE_MAX_COMPLEXITY",
        "DEVFORGE_EVIDENCE_CI_SARIF_BLOCK_LEVEL",
        "DEVFORGE_EVIDENCE_SPEC_DRIFT_BLOCK",
    ]:
        monkeypatch.delenv(v, raising=False)
    t = load_thresholds()
    assert t.min_coverage == 60.0
    assert t.max_coverage_delta == -5.0
    assert t.max_lint_errors == 0
    assert t.max_complexity == 15
    assert t.ci_sarif_block_level == "critical"
    assert t.spec_drift_block is True


def test_load_thresholds_env_override(monkeypatch):
    monkeypatch.setenv("DEVFORGE_EVIDENCE_MIN_COVERAGE", "75")
    monkeypatch.setenv("DEVFORGE_EVIDENCE_MAX_LINT_ERRORS", "3")
    monkeypatch.setenv("DEVFORGE_EVIDENCE_CI_SARIF_BLOCK_LEVEL", "off")
    t = load_thresholds()
    assert t.min_coverage == 75.0
    assert t.max_lint_errors == 3
    assert t.ci_sarif_block_level == "off"


def test_verdict_clean():
    t = Thresholds()
    metrics = {
        "coverage": {"overall_pct": 85.0, "delta_vs_base": 0.5},
        "lint": {"errors": 0, "warnings": 2},
        "complexity": {"max_cyclomatic": 8},
        "ci_quality": {"available": False, "problems_critical": 0, "problems_high": 0},
    }
    v = compute_verdict(metrics, spec_drift=None, t=t)
    assert v["block"] is False
    assert v["block_reasons"] == []


def test_verdict_coverage_block():
    t = Thresholds()
    metrics = {
        "coverage": {"overall_pct": 45.0, "delta_vs_base": -8.0},
        "lint": {"errors": 0, "warnings": 0},
        "complexity": {"max_cyclomatic": 5},
        "ci_quality": {"available": False, "problems_critical": 0, "problems_high": 0},
    }
    v = compute_verdict(metrics, spec_drift=None, t=t)
    assert v["block"] is True
    assert any("coverage" in r for r in v["block_reasons"])
    assert any("delta" in r for r in v["block_reasons"])


def test_verdict_lint_complexity_block():
    t = Thresholds()
    metrics = {
        "coverage": {"overall_pct": 80.0, "delta_vs_base": 0.0},
        "lint": {"errors": 5, "warnings": 0},
        "complexity": {"max_cyclomatic": 22},
        "ci_quality": {"available": False, "problems_critical": 0, "problems_high": 0},
    }
    v = compute_verdict(metrics, spec_drift=None, t=t)
    assert v["block"] is True
    assert any("lint_errors" in r for r in v["block_reasons"])
    assert any("complexity" in r for r in v["block_reasons"])


def test_verdict_ci_critical_block():
    t = Thresholds()
    metrics = {
        "coverage": {"overall_pct": 80.0, "delta_vs_base": 0.0},
        "lint": {"errors": 0, "warnings": 0},
        "complexity": {"max_cyclomatic": 5},
        "ci_quality": {"available": True, "problems_critical": 2, "problems_high": 0},
    }
    v = compute_verdict(metrics, spec_drift=None, t=t)
    assert v["block"] is True
    assert any("ci_critical" in r for r in v["block_reasons"])


def test_verdict_spec_drift_high_block():
    t = Thresholds()
    metrics = {
        "coverage": {"overall_pct": 80.0, "delta_vs_base": 0.0},
        "lint": {"errors": 0, "warnings": 0},
        "complexity": {"max_cyclomatic": 5},
        "ci_quality": {"available": False, "problems_critical": 0, "problems_high": 0},
    }
    drift = {"drift_severity": "high"}
    v = compute_verdict(metrics, spec_drift=drift, t=t)
    assert v["block"] is True
    assert any("drift" in r for r in v["block_reasons"])


def test_verdict_ci_block_level_off(monkeypatch):
    monkeypatch.setenv("DEVFORGE_EVIDENCE_CI_SARIF_BLOCK_LEVEL", "off")
    t = load_thresholds()
    metrics = {
        "coverage": {"overall_pct": 80.0, "delta_vs_base": 0.0},
        "lint": {"errors": 0, "warnings": 0},
        "complexity": {"max_cyclomatic": 5},
        "ci_quality": {"available": True, "problems_critical": 10, "problems_high": 50},
    }
    v = compute_verdict(metrics, spec_drift=None, t=t)
    assert v["block"] is False
