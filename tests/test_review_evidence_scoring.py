"""Tests for scoring algorithm — 5 score functions + compute_overall."""

from lib.review_evidence.scoring import (
    score_security,
    score_quality,
    score_coverage,
    score_spec_compliance,
    score_discipline,
    compute_overall,
    SecurityFindings,
    QualityFindings,
    CoverageInput,
    SpecDriftInput,
    ArchDriftInput,
    SkillAdoptionInput,
)


# --- score_security ---

def test_security_no_findings_100():
    sf = SecurityFindings(critical=0, high=0, medium=0, low=0)
    assert score_security(sf) == 100.0


def test_security_1_critical_70():
    sf = SecurityFindings(critical=1, high=0, medium=0, low=0)
    assert score_security(sf) == 70.0


def test_security_1_high_90():
    sf = SecurityFindings(critical=0, high=1, medium=0, low=0)
    assert score_security(sf) == 90.0


def test_security_4_critical_clamp_0():
    sf = SecurityFindings(critical=4, high=0, medium=0, low=0)
    assert score_security(sf) == 0.0  # 100 - 120 clamped to 0


# --- score_quality ---

def test_quality_no_issues_100():
    qf = QualityFindings(lint_errors=0, complexity_files_over_threshold=0,
                          dead_code_blocks=0, type_errors=0)
    assert score_quality(qf) == 100.0


def test_quality_5_lint_errors_75():
    qf = QualityFindings(lint_errors=5, complexity_files_over_threshold=0,
                          dead_code_blocks=0, type_errors=0)
    assert score_quality(qf) == 75.0


# --- score_coverage with anti-gaming (CRITICAL B1+B7+C5) ---

def test_coverage_first_pr_skip_anti_gaming():
    """B1: baseline_synthetic=True → return base, no penalty."""
    cov = CoverageInput(line_pct=75.0, branch_pct=70.0,
                        current_lines_covered=100, baseline_lines_covered=None)
    assert score_coverage(cov, baseline_synthetic=True) == 70.0  # min(75, 70)


def test_coverage_lines_drop_anti_gaming_penalty():
    """C5: dev cancella test (lines drop) ma % rises → penalty kicks in."""
    cov = CoverageInput(line_pct=80.0, branch_pct=80.0,
                        current_lines_covered=40, baseline_lines_covered=80)
    # base = 80, lines_drop = 40, penalty = min(20, 40 * 0.5) = 20
    assert score_coverage(cov, baseline_synthetic=False) == 60.0


def test_coverage_none_returns_none():
    """Edge D6: missing coverage → None → re-weight."""
    assert score_coverage(None) is None


def test_coverage_missing_line_pct_returns_none():
    cov = CoverageInput(line_pct=None, branch_pct=None,
                        current_lines_covered=0, baseline_lines_covered=0)
    assert score_coverage(cov) is None


def test_coverage_no_lines_drop_no_penalty():
    cov = CoverageInput(line_pct=80.0, branch_pct=80.0,
                        current_lines_covered=80, baseline_lines_covered=80)
    assert score_coverage(cov, baseline_synthetic=False) == 80.0


def test_coverage_penalty_capped_at_20():
    """Edge: extreme lines drop doesn't make score negative."""
    cov = CoverageInput(line_pct=70.0, branch_pct=70.0,
                        current_lines_covered=0, baseline_lines_covered=1000)
    # base=70, lines_drop=1000, penalty=min(20, 500)=20
    assert score_coverage(cov, baseline_synthetic=False) == 50.0


# --- score_spec_compliance ---

def test_spec_compliance_no_drift_100():
    sd = SpecDriftInput(unplanned_files=[])
    ad = ArchDriftInput(violations=[])
    assert score_spec_compliance(sd, ad) == 100.0


def test_spec_compliance_3_unplanned_1_arch_76():
    """3 unplanned * 3 + 1 arch * 15 = 9 + 15 = 24 penalty → 76."""
    sd = SpecDriftInput(unplanned_files=["a", "b", "c"])
    ad = ArchDriftInput(violations=["v1"])
    assert score_spec_compliance(sd, ad) == 76.0


# --- score_discipline ---

def test_discipline_bot_pr_always_100():
    """Edge C1: bot-pr skippa discipline check."""
    adoption = SkillAdoptionInput(is_bot_pr=True, brainstorming_done=False,
                                    tdd_cycle_seen=False, verification_run=False)
    assert score_discipline(adoption) == 100.0


def test_discipline_full_devforge_chain_100():
    adoption = SkillAdoptionInput(is_bot_pr=False, brainstorming_done=True,
                                    tdd_cycle_seen=True, verification_run=True)
    assert score_discipline(adoption) == 100.0


def test_discipline_no_brainstorming_60():
    adoption = SkillAdoptionInput(is_bot_pr=False, brainstorming_done=False,
                                    tdd_cycle_seen=True, verification_run=True)
    assert score_discipline(adoption) == 60.0  # 100 - 40


def test_discipline_nothing_done_0():
    adoption = SkillAdoptionInput(is_bot_pr=False, brainstorming_done=False,
                                    tdd_cycle_seen=False, verification_run=False)
    assert score_discipline(adoption) == 0.0  # 100 - 40 - 30 - 30


# --- compute_overall + D6 severely_degraded ---

def test_compute_overall_all_dims_weighted():
    scores = {"security": 80, "quality": 70, "coverage": 60,
              "spec_compliance": 90, "discipline": 100}
    weights = {"security": 0.30, "quality": 0.20, "coverage": 0.20,
                "spec_compliance": 0.15, "discipline": 0.15}
    overall, degraded = compute_overall(scores, weights)
    # 80*0.30 + 70*0.20 + 60*0.20 + 90*0.15 + 100*0.15 = 24+14+12+13.5+15 = 78.5
    assert overall == 78.5
    assert degraded is False


def test_compute_overall_d6_severely_degraded():
    """D6: < 2 dim available → severely_degraded=True."""
    scores = {"security": 80, "quality": None, "coverage": None,
              "spec_compliance": None, "discipline": None}
    weights = {"security": 0.30, "quality": 0.20, "coverage": 0.20,
                "spec_compliance": 0.15, "discipline": 0.15}
    overall, degraded = compute_overall(scores, weights)
    assert overall == 80.0  # single available
    assert degraded is True


def test_compute_overall_all_none_zero_degraded():
    scores = {"security": None, "quality": None, "coverage": None,
              "spec_compliance": None, "discipline": None}
    weights = {"security": 0.20, "quality": 0.20, "coverage": 0.20,
                "spec_compliance": 0.20, "discipline": 0.20}
    overall, degraded = compute_overall(scores, weights)
    assert overall == 0.0
    assert degraded is True


def test_compute_overall_reweight_on_missing():
    """3 dim available → re-weight su 1.0 totale (E4)."""
    scores = {"security": 100, "quality": 100, "coverage": 100,
              "spec_compliance": None, "discipline": None}
    weights = {"security": 0.30, "quality": 0.20, "coverage": 0.20,
                "spec_compliance": 0.15, "discipline": 0.15}
    overall, degraded = compute_overall(scores, weights)
    assert overall == 100.0  # tutti 100 con qualunque weight
    assert degraded is False
