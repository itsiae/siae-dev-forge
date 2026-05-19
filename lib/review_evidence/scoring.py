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
    # Wave 1 follow-up: distinguish "0 findings (clean)" vs "tool not ran"
    # (EC-22 EVIDENCE_TOOL_MISSING distinct from BLOCK_REGRESSION).
    tool_unavailable_reason: Optional[str] = None
    # by_family breakdown per traceability (rule-id siae.<family>.<...>).
    by_family: dict[str, int] = field(default_factory=dict)

    @classmethod
    def tool_unavailable(cls, reason: str) -> "SecurityFindings":
        """Factory: build SecurityFindings marking tool as unavailable."""
        return cls(tool_unavailable_reason=reason)


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


@dataclass
class MutationFindings:
    """Test-quality verification — mutation testing output.

    Advisory metric (v1.58+): mutation_score < threshold triggers
    REVIEWER_HANDOFF, never BLOCK. Opt-in via DEVFORGE_MUTATION_ENABLED.
    See docs/plans/2026-05-14-mutation-testing-design.md.
    """
    score_pct: float = 0.0     # 0-100 — killed / total ratio
    killed: int = 0
    survived: int = 0
    timeout: int = 0
    no_coverage: int = 0
    total_mutants: int = 0
    tool: str = ""              # "pit" | "mutmut" | "stryker"


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
    """Edge C1: bot-pr -> 100 sempre."""
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
