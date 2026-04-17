"""AI Impact: dual-window before/after + attribution + correlation.

Core del messaggio "con AI funzioniamo meglio":
- Dual-window comparison (baseline pre-AI / current post-AI)
- Co-Authored-By attribution (SIAE DevForge, Claude, Anthropic)
- Velocity multiplier, correlation skill usage → ROI
"""
from __future__ import annotations

import math
import re
import statistics
from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

AI_ATTRIBUTION_RE = re.compile(
    r"^Co-Authored-By:\s*(?:SIAE\s*DevForge|Claude|Anthropic)",
    re.MULTILINE | re.IGNORECASE,
)


def is_ai_assisted(commit_message: str) -> bool:
    """True se commit contiene Co-Authored-By trailer di AI."""
    return bool(AI_ATTRIBUTION_RE.search(commit_message or ""))


@dataclass
class WindowMetrics:
    kpis: dict[str, dict[str, float]]  # {kpi_name: {dev: value}}
    window: tuple[str, str]
    n_prs: int = 0
    n_commits: int = 0


@dataclass
class Delta:
    baseline: float
    current: float
    delta_abs: float
    delta_pct: float
    trend: Literal["IMPROVED", "DEGRADED", "STABLE"]


def compute_delta(baseline_val: float, current_val: float, lower_is_better: bool = False) -> Delta:
    """Compute delta con trend classification."""
    if baseline_val == 0:
        delta_abs = current_val - baseline_val
        delta_pct = 9999.0 if current_val > 0 else 0.0
    else:
        delta_abs = current_val - baseline_val
        delta_pct = (delta_abs / baseline_val) * 100
    # Clamp infinity
    if delta_pct > 9999:
        delta_pct = 9999.0
    elif delta_pct < -9999:
        delta_pct = -9999.0
    # Trend: +/-5% threshold for STABLE
    threshold = 5.0
    if abs(delta_pct) < threshold:
        trend: Literal["IMPROVED", "DEGRADED", "STABLE"] = "STABLE"
    else:
        improved = (delta_pct < 0) if lower_is_better else (delta_pct > 0)
        trend = "IMPROVED" if improved else "DEGRADED"
    return Delta(baseline_val, current_val, delta_abs, delta_pct, trend)


def before_after_comparison(
    baseline: WindowMetrics,
    current: WindowMetrics,
) -> dict[str, Delta]:
    """Per ogni KPI team-level, compute delta baseline -> current."""
    LOWER_BETTER = {"pr_cycle_time_p50", "lead_time_to_merge_p50", "time_to_first_review_p50",
                    "review_comments_p50", "rework_ratio", "revert_rate", "oldest_open_pr_age_days"}
    deltas = {}
    for kpi_name in baseline.kpis.keys() | current.kpis.keys():
        b_vals = list(baseline.kpis.get(kpi_name, {}).values())
        c_vals = list(current.kpis.get(kpi_name, {}).values())
        b = statistics.median(b_vals) if b_vals else 0
        c = statistics.median(c_vals) if c_vals else 0
        deltas[kpi_name] = compute_delta(b, c, lower_is_better=(kpi_name in LOWER_BETTER))
    return deltas


def kpi_ai_assisted_pr_rate(prs: pd.DataFrame, commits: pd.DataFrame) -> dict[str, float]:
    """% PR con almeno 1 commit AI-attributed."""
    if prs.empty or commits.empty:
        return {}
    ai_commits_by_dev = commits.copy()
    ai_commits_by_dev["is_ai"] = ai_commits_by_dev["message"].apply(is_ai_assisted)
    ai_by_dev = ai_commits_by_dev.groupby("author")["is_ai"].mean()
    return ai_by_dev.to_dict()


def kpi_ai_vs_manual_cycle_time(prs: pd.DataFrame, commits: pd.DataFrame) -> tuple[dict, dict]:
    """Cycle time separato AI-assisted vs manual per dev."""
    if prs.empty or commits.empty:
        return {}, {}
    ai_authors = set(commits[commits["message"].apply(is_ai_assisted)]["author"].unique())
    ai_prs = prs[prs["author"].isin(ai_authors)]
    manual_prs = prs[~prs["author"].isin(ai_authors)]
    ai_cycle = ai_prs.groupby("author")["cycle_time_hours"].median().to_dict() if not ai_prs.empty else {}
    manual_cycle = manual_prs.groupby("author")["cycle_time_hours"].median().to_dict() if not manual_prs.empty else {}
    return ai_cycle, manual_cycle


def kpi_ai_velocity_multiplier(ai_cycle: dict, manual_cycle: dict) -> float:
    """Team-level: median(manual_cycle) / median(ai_cycle). >1 = AI faster."""
    if not ai_cycle or not manual_cycle:
        return 1.0
    m = statistics.median(manual_cycle.values())
    a = statistics.median(ai_cycle.values())
    if a == 0:
        return 1.0
    return m / a


def skill_usage_correlation(skill_counts: dict[str, int], roi_by_dev: dict[str, float]) -> float:
    """Pearson correlation. NaN se N<3 o variance 0."""
    devs = list(set(skill_counts) & set(roi_by_dev))
    if len(devs) < 3:
        return float('nan')
    xs = [skill_counts[d] for d in devs]
    ys = [roi_by_dev[d] for d in devs]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return float('nan')
    return num / (dx * dy)
