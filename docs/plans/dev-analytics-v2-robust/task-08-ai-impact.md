# Task 08 — F4b AI Impact (Dual-Window + Attribution + 5 KPI)

**Goal:** Core del messaggio "con AI funzioniamo meglio". Dual-window + AI attribution via Co-Authored-By + 5 KPI.
**AC coperti:** AI1-AI6, ADR-008, ADR-009, AC-MACRO-5
**Dipendenze:** Task 03, 07
**Effort:** ~90 min
**Test nuovi:** 12

## File coinvolti

- `scripts/compute_ai_impact.py` — implementazione completa
- `scripts/run_analytics.py` — aggiorna cmd_run per dual-window loop
- `tests/test_compute_ai_impact.py` — 12 test
- `tests/fixtures/ai_attributed_commits.json` — fixture
- `tests/fixtures/before_after_windows.json` — fixture

## Step 1 — compute_ai_impact.py

```python
"""AI Impact: dual-window before/after + attribution + correlation."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Literal
import pandas as pd
import statistics

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
        delta_pct = float('inf') if current_val > 0 else 0.0
    else:
        delta_abs = current_val - baseline_val
        delta_pct = (delta_abs / baseline_val) * 100
    # Clamp infinity
    if delta_pct > 9999:
        delta_pct = 9999.0
    elif delta_pct < -9999:
        delta_pct = -9999.0
    # Trend
    threshold = 5.0  # ±5% stable
    if abs(delta_pct) < threshold:
        trend = "STABLE"
    else:
        improved = (delta_pct < 0) if lower_is_better else (delta_pct > 0)
        trend = "IMPROVED" if improved else "DEGRADED"
    return Delta(baseline_val, current_val, delta_abs, delta_pct, trend)


def before_after_comparison(
    baseline: WindowMetrics,
    current: WindowMetrics,
) -> dict[str, Delta]:
    """Per ogni KPI team-level, compute delta baseline → current."""
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
    if prs.empty or commits.empty: return {}
    # Join: PR number → commits nella PR (semplificato: per-dev aggregate)
    ai_commits_by_dev = commits.copy()
    ai_commits_by_dev["is_ai"] = ai_commits_by_dev["message"].apply(is_ai_assisted)
    ai_by_dev = ai_commits_by_dev.groupby("author")["is_ai"].mean()
    return ai_by_dev.to_dict()


def kpi_ai_vs_manual_cycle_time(prs: pd.DataFrame, commits: pd.DataFrame) -> tuple[dict, dict]:
    """Cycle time separato AI-assisted vs manual per dev."""
    if prs.empty or commits.empty: return {}, {}
    # Marker PR as AI-assisted se qualsiasi commit nel PR è AI
    # Semplificato: per ogni PR, se author ha AI commits recenti → classifica AI
    ai_authors = set(commits[commits["message"].apply(is_ai_assisted)]["author"].unique())
    ai_prs = prs[prs["author"].isin(ai_authors)]
    manual_prs = prs[~prs["author"].isin(ai_authors)]
    ai_cycle = ai_prs.groupby("author")["cycle_time_hours"].median().to_dict()
    manual_cycle = manual_prs.groupby("author")["cycle_time_hours"].median().to_dict()
    return ai_cycle, manual_cycle


def kpi_ai_velocity_multiplier(ai_cycle: dict, manual_cycle: dict) -> float:
    """Team-level: median(manual_cycle) / median(ai_cycle). >1 = AI più veloce."""
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
    import math
    xs = [skill_counts[d] for d in devs]
    ys = [roi_by_dev[d] for d in devs]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return float('nan')
    return num / (dx * dy)
```

## Step 2 — run_analytics.py dual-window loop

Modifica `cmd_run` per rilevare `time_window` v2 con `baseline` + `current`. Se presente, loop 2 volte con window diverso, produce 2 WindowMetrics, poi chiama `before_after_comparison`.

## Step 3 — Test (12)

Pattern:
- `test_is_ai_assisted_detects_devforge_trailer`
- `test_is_ai_assisted_detects_claude_trailer`
- `test_is_ai_assisted_case_insensitive`
- `test_is_ai_assisted_multiline_match`
- `test_is_ai_assisted_empty_returns_false`
- `test_compute_delta_improvement_lower_better`
- `test_compute_delta_clamp_infinity_at_9999`
- `test_compute_delta_stable_threshold_5pct`
- `test_ai_velocity_multiplier_happy`
- `test_ai_velocity_multiplier_zero_ai_returns_1`
- `test_skill_correlation_returns_nan_if_N_lt_3`
- `test_skill_correlation_positive_computed`

## Verify

```bash
PYTHONPATH=skills/siae-dev-analytics/scripts python3 -m pytest skills/siae-dev-analytics/tests/test_compute_ai_impact.py -v
```

Output: `12 passed`.

## Criteri accettazione

- [ ] Co-Authored-By regex matcha "Claude", "SIAE DevForge", "Anthropic", case-insensitive multi-line
- [ ] compute_delta con baseline=0 → clamp infinity a ±9999%, no math.inf
- [ ] Trend classification: STABLE se |%| < 5
- [ ] skill_usage_correlation N<3 → NaN esplicito, no crash
- [ ] Dual-window loop in run_analytics.py produce 2 WindowMetrics
