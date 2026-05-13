# Task 02 — Score algorithm 5 formule + compute_overall + coverage anti-gaming

**SP:** 3.0 · **AC mappati:** AC #10, B1+B7 (CRITICAL), C5 (CRITICAL), E4, E5 · **Dipendenze:** Task 01 · **Wave:** 1

## Goal

Implementare `lib/review_evidence/scoring.py` con 5 funzioni di scoring (`score_security`, `score_quality`, `score_coverage`, `score_spec_compliance`, `score_discipline`) + `compute_overall(scores, weights) -> tuple[float, bool]`. La funzione `score_coverage` deve avere **anti-gaming** via `lines_covered` absolute drop penalty (CRITICAL B1+B7+C5). `compute_overall` ritorna `severely_degraded` flag se <2 dim disponibili (D6).

## File coinvolti

**Creare:**
- `lib/review_evidence/scoring.py`
- `tests/test_review_evidence_scoring.py`

## Step TDD

### Step 1 — Test fallente

`tests/test_review_evidence_scoring.py`:

```python
"""Tests for scoring algorithm — 5 score functions + compute_overall."""
import pytest

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
```

### Step 2 — Esegui (fail)

```bash
python3 -m pytest tests/test_review_evidence_scoring.py -v
```

**Output atteso:** `ModuleNotFoundError: lib.review_evidence.scoring`.

### Step 3 — Implementa scoring.py

```python
"""Score algorithm 5 dimensioni + compute_overall.

Anti-gaming: score_coverage usa lines_covered absolute drop penalty (CRITICAL
B1+B7+C5 from design v2). See design doc sezione "Scoring algorithm".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SecurityFindings:
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


@dataclass
class QualityFindings:
    lint_errors: int = 0
    complexity_files_over_threshold: int = 0
    dead_code_blocks: int = 0
    type_errors: int = 0


@dataclass
class CoverageInput:
    line_pct: Optional[float] = None
    branch_pct: Optional[float] = None
    current_lines_covered: int = 0
    baseline_lines_covered: Optional[int] = None


@dataclass
class SpecDriftInput:
    unplanned_files: list[str] = field(default_factory=list)


@dataclass
class ArchDriftInput:
    violations: list[str] = field(default_factory=list)


@dataclass
class SkillAdoptionInput:
    is_bot_pr: bool = False
    brainstorming_done: bool = False
    tdd_cycle_seen: bool = False
    verification_run: bool = False


def score_security(findings: SecurityFindings) -> float:
    penalty = (findings.critical * 30 + findings.high * 10
                + findings.medium * 3 + findings.low * 1)
    return max(0.0, 100.0 - penalty)


def score_quality(findings: QualityFindings) -> float:
    penalty = (findings.lint_errors * 5
                + findings.complexity_files_over_threshold * 10
                + findings.dead_code_blocks * 2
                + findings.type_errors * 4)
    return max(0.0, 100.0 - penalty)


def score_coverage(cov: Optional[CoverageInput],
                    baseline_synthetic: bool = False) -> Optional[float]:
    """B1+B7+C5 (CRITICAL): anti-gaming via lines_covered absolute drop."""
    if cov is None or cov.line_pct is None:
        return None
    base = min(cov.line_pct, cov.branch_pct or cov.line_pct)
    if baseline_synthetic or cov.baseline_lines_covered is None:
        return base
    lines_drop = max(0, cov.baseline_lines_covered - cov.current_lines_covered)
    penalty = min(20.0, lines_drop * 0.5)
    return max(0.0, base - penalty)


def score_spec_compliance(sd: SpecDriftInput, ad: ArchDriftInput) -> float:
    return max(0.0, 100.0 - len(sd.unplanned_files) * 3 - len(ad.violations) * 15)


def score_discipline(adoption: SkillAdoptionInput) -> float:
    """Edge C1: bot-pr → 100 sempre."""
    if adoption.is_bot_pr:
        return 100.0
    penalty = (
        (40 if not adoption.brainstorming_done else 0)
        + (30 if not adoption.tdd_cycle_seen else 0)
        + (30 if not adoption.verification_run else 0)
    )
    return max(0.0, 100.0 - penalty)


def compute_overall(scores: dict, weights: dict) -> tuple[float, bool]:
    """D6: severely_degraded=True if <2 dim available."""
    available = {k: v for k, v in scores.items() if v is not None}
    if not available:
        return 0.0, True
    if len(available) < 2:
        return float(next(iter(available.values()))), True
    available_weights = {k: weights.get(k, 0.0) for k in available}
    norm = sum(available_weights.values())
    if norm == 0:
        return 0.0, True
    weighted = sum(score * weights.get(k, 0.0) / norm
                    for k, score in available.items())
    return round(weighted, 2), False
```

### Step 4 — Esegui test

```bash
python3 -m pytest tests/test_review_evidence_scoring.py -v
```

**Output atteso:** 22 passed.

### Step 5 — Commit

```bash
git add lib/review_evidence/scoring.py tests/test_review_evidence_scoring.py
git commit -m "feat(review-evidence-v2): scoring algorithm 5 formule + coverage anti-gaming + compute_overall (#task-02)"
```

## Criteri di accettazione

- [ ] 5 score functions implementate con formule esplicite (security/quality/coverage/spec/discipline)
- [ ] **CRITICAL B1+B7+C5:** `score_coverage` anti-gaming via `lines_covered` drop penalty (capped 20pt)
- [ ] **CRITICAL E5:** `compute_overall` returns tuple `(score, severely_degraded)` con D6 logic
- [ ] Bot PR skippa discipline check (edge C1)
- [ ] Re-weighting su missing dim (edge E4 — sum weights ≈ 1)
- [ ] 22 test passano (4 security + 2 quality + 6 coverage + 2 spec + 4 discipline + 4 overall)
- [ ] No regression suite v1 PASS
