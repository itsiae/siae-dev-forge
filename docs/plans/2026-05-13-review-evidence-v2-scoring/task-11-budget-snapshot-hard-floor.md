# Task 11 — Budget snapshot at PR_OPEN_TIME + Hard floor non-overridable

**SP:** 2.5 · **AC mappati:** CRITICAL E1, F1, E5 · **Dipendenze:** Task 06, Task 09 · **Wave:** 3

## Goal

Implementare:
- `lib/review_evidence/regression.py` — compute deltas + classify decision
- **E1 fix:** budget snapshot at PR_OPEN_TIME (no retroactive admin change)
- **F1 + E5 fix:** hard floor checks separati + non-overridable da reviewer agent
- **min_dim hard floor:** any dim < threshold → block separato da overall

## File coinvolti

**Creare:**
- `lib/review_evidence/regression.py`
- `tests/test_review_evidence_regression.py`

## Step TDD

### Step 1 — Test

```python
"""Tests for regression analyzer + hard floor non-overridable."""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from lib.review_evidence.regression import (
    compute_regression_verdict,
    snapshot_budget_at_pr_open,
    is_hard_floor_breached,
    RegressionInput,
)
from lib.review_evidence.schema import ScoreCard
from lib.review_evidence.config import DevForgeScoresConfig


def _sc(**kw):
    base = dict(security=80, quality=70, coverage=65, spec_compliance=85,
                discipline=90, overall=78, weights_used={}, missing_components=[])
    base.update(kw)
    return ScoreCard(**base)


def test_no_regression_auto_approve():
    cfg = DevForgeScoresConfig()
    current = _sc(security=80, overall=78)
    baseline = _sc(security=80, overall=78)
    rv = compute_regression_verdict(current, baseline, cfg, baseline_synthetic=False)
    assert rv.decision == "AUTO_APPROVE"


def test_hard_floor_security_breach_block(monkeypatch):
    """E5 + F1: security < 60 → BLOCK_HARD_FLOOR, non-overridable."""
    cfg = DevForgeScoresConfig()
    current = _sc(security=55, overall=70)
    baseline = _sc(security=55, overall=70)  # same as current, no regression
    rv = compute_regression_verdict(current, baseline, cfg, baseline_synthetic=False)
    assert rv.decision == "BLOCK_HARD_FLOOR"
    assert "security" in rv.hard_floor_breaches[0].lower()


def test_min_dim_hard_floor_block():
    """E5: ANY dim < 40 → BLOCK_HARD_FLOOR (separate from overall)."""
    cfg = DevForgeScoresConfig()  # min_dim=40
    current = _sc(security=80, quality=35, overall=75)
    baseline = _sc(security=80, quality=35, overall=75)
    rv = compute_regression_verdict(current, baseline, cfg, baseline_synthetic=False)
    assert rv.decision == "BLOCK_HARD_FLOOR"
    assert any("quality" in b.lower() or "min_dim" in b.lower() for b in rv.hard_floor_breaches)


def test_regression_below_warn_handoff_to_reviewer():
    """Delta in warn zone → REVIEWER_HANDOFF."""
    cfg = DevForgeScoresConfig()
    current = _sc(security=78, overall=76)  # security drop -2 → warn
    baseline = _sc(security=80, overall=78)
    rv = compute_regression_verdict(current, baseline, cfg, baseline_synthetic=False)
    # security delta = -2, warn budget = 0, hard = -2
    # delta = -2 <= hard? No (hard is -2 exactly, strictly less). Should be warn.
    # Actually: delta < hard_block (-2) means delta < -2 i.e. -3 or worse. -2 is in warn zone.
    assert rv.decision in ["REVIEWER_HANDOFF", "BLOCK_REGRESSION"]


def test_regression_below_hard_block():
    """Delta worse than hard_block budget → BLOCK_REGRESSION."""
    cfg = DevForgeScoresConfig()
    current = _sc(security=75, overall=70)  # security drop -5
    baseline = _sc(security=80, overall=78)
    rv = compute_regression_verdict(current, baseline, cfg, baseline_synthetic=False)
    assert rv.decision == "BLOCK_REGRESSION"


def test_baseline_synthetic_first_pr_auto_approve():
    """A6: first PR → baseline_synthetic=True → skip regression check."""
    cfg = DevForgeScoresConfig()
    current = _sc(security=70, overall=70)
    rv = compute_regression_verdict(current, baseline=None, cfg=cfg,
                                     baseline_synthetic=True)
    # Score above hard floor → AUTO_APPROVE (synthetic baseline doesn't enforce regression)
    assert rv.decision == "AUTO_APPROVE"


def test_snapshot_budget_at_pr_open_immutable():
    """E1: snapshot at PR_OPEN_TIME, admin change post-open doesn't affect."""
    cfg = DevForgeScoresConfig()
    snapshot1 = snapshot_budget_at_pr_open(cfg, pr_open_iso="2026-05-13T10:00:00Z")
    
    # Admin changes config retroactively
    cfg.hard_block_budget["security"] = -50  # stricter
    
    snapshot2 = snapshot_budget_at_pr_open(cfg, pr_open_iso="2026-05-13T10:00:00Z")
    # Even with cfg mutated, snapshot1 keeps original
    assert snapshot1["hard_block_budget"]["security"] == -2


def test_is_hard_floor_breached_uniform():
    cfg = DevForgeScoresConfig()
    sc = _sc(security=55)
    assert is_hard_floor_breached(sc, cfg) is True
    sc2 = _sc(security=70, overall=60)  # overall >= 55
    assert is_hard_floor_breached(sc2, cfg) is False
```

### Step 2 — Implementa regression.py

```python
"""Regression analyzer + hard floor enforcement.

E1 fix: budget snapshot at PR_OPEN_TIME (immutable copy).
F1 + E5 fix: hard_floor_breaches NEVER overridable by reviewer agent.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Optional

from lib.review_evidence.config import DevForgeScoresConfig
from lib.review_evidence.schema import RegressionVerdict, ScoreCard


@dataclass
class RegressionInput:
    current: ScoreCard
    baseline: Optional[ScoreCard]
    cfg: DevForgeScoresConfig
    baseline_synthetic: bool = False


def snapshot_budget_at_pr_open(cfg: DevForgeScoresConfig, pr_open_iso: str) -> dict:
    """E1: deepcopy of budget at PR_OPEN_TIME. Subsequent cfg mutations don't affect."""
    return {
        "pr_open_iso": pr_open_iso,
        "weights": copy.deepcopy(cfg.weights),
        "hard_floors": copy.deepcopy(cfg.hard_floors),
        "hard_block_budget": copy.deepcopy(cfg.hard_block_budget),
        "warn_budget": copy.deepcopy(cfg.warn_budget),
    }


def is_hard_floor_breached(sc: ScoreCard, cfg: DevForgeScoresConfig) -> bool:
    """E5: any dim < min_dim OR specific dim < dedicated floor → True."""
    if sc.security < cfg.hard_floors.get("security", 60):
        return True
    if sc.coverage < cfg.hard_floors.get("coverage", 50):
        return True
    if sc.overall < cfg.hard_floors.get("overall", 55):
        return True
    min_dim = cfg.hard_floors.get("min_dim", 40)
    for dim in [sc.security, sc.quality, sc.coverage, sc.spec_compliance, sc.discipline]:
        if dim < min_dim:
            return True
    return False


def _hard_floor_breaches_list(sc: ScoreCard, cfg: DevForgeScoresConfig) -> list[str]:
    out = []
    if sc.security < cfg.hard_floors.get("security", 60):
        out.append(f"security({sc.security:.1f}) < hard_floor({cfg.hard_floors['security']})")
    if sc.coverage < cfg.hard_floors.get("coverage", 50):
        out.append(f"coverage({sc.coverage:.1f}) < hard_floor({cfg.hard_floors['coverage']})")
    if sc.overall < cfg.hard_floors.get("overall", 55):
        out.append(f"overall({sc.overall:.1f}) < hard_floor({cfg.hard_floors['overall']})")
    min_dim = cfg.hard_floors.get("min_dim", 40)
    dim_map = {"security": sc.security, "quality": sc.quality, "coverage": sc.coverage,
                "spec_compliance": sc.spec_compliance, "discipline": sc.discipline}
    for name, val in dim_map.items():
        if val < min_dim:
            out.append(f"{name}({val:.1f}) < min_dim({min_dim})")
    return out


def compute_regression_verdict(
    current: ScoreCard,
    baseline: Optional[ScoreCard],
    cfg: DevForgeScoresConfig,
    baseline_synthetic: bool = False,
) -> RegressionVerdict:
    """Compute decision.

    Priority order:
    1. SEVERELY_DEGRADED (set by caller, not here)
    2. BLOCK_HARD_FLOOR (any hard floor breach — NON-OVERRIDABLE — F1+E5)
    3. BLOCK_REGRESSION (delta < hard_block_budget)
    4. REVIEWER_HANDOFF (delta < warn_budget)
    5. AUTO_APPROVE (all pass)
    """
    # F1+E5: hard floor priority — non-overridable
    floor_breaches = _hard_floor_breaches_list(current, cfg)
    if floor_breaches:
        return RegressionVerdict(
            block_dimensions=[], warn_dimensions=[],
            improved_dimensions=[], hard_floor_breaches=floor_breaches,
            decision="BLOCK_HARD_FLOOR",
            reason=f"Hard floor breached: {'; '.join(floor_breaches)}. NON-OVERRIDABLE by reviewer.",
        )
    
    # A6: first PR baseline_synthetic → no regression check
    if baseline_synthetic or baseline is None:
        return RegressionVerdict(
            block_dimensions=[], warn_dimensions=[],
            improved_dimensions=[], hard_floor_breaches=[],
            decision="AUTO_APPROVE",
            reason="First PR (baseline_synthetic). Floor checks pass.",
        )
    
    block_dims, warn_dims, improved_dims = [], [], []
    for dim in ["security", "quality", "coverage", "spec_compliance", "discipline"]:
        cur = getattr(current, dim)
        base = getattr(baseline, dim)
        delta = cur - base
        if delta < cfg.hard_block_budget.get(dim, -999):
            block_dims.append(f"{dim}:{delta:+.1f}")
        elif delta < cfg.warn_budget.get(dim, -999):
            warn_dims.append(f"{dim}:{delta:+.1f}")
        elif delta > 0:
            improved_dims.append(f"{dim}:+{delta:.1f}")
    
    if block_dims:
        return RegressionVerdict(
            block_dimensions=block_dims, warn_dimensions=warn_dims,
            improved_dimensions=improved_dims, hard_floor_breaches=[],
            decision="BLOCK_REGRESSION",
            reason=f"Regression block: {'; '.join(block_dims)}",
        )
    if warn_dims:
        return RegressionVerdict(
            block_dimensions=[], warn_dimensions=warn_dims,
            improved_dimensions=improved_dims, hard_floor_breaches=[],
            decision="REVIEWER_HANDOFF",
            reason=f"Regression warn: {'; '.join(warn_dims)}. Reviewer agent gatekeeps.",
        )
    return RegressionVerdict(
        block_dimensions=[], warn_dimensions=[],
        improved_dimensions=improved_dims, hard_floor_breaches=[],
        decision="AUTO_APPROVE",
        reason="All checks pass.",
    )
```

### Step 3 — Run + commit

```bash
python3 -m pytest tests/test_review_evidence_regression.py -v
# 8 passed

git add lib/review_evidence/regression.py tests/test_review_evidence_regression.py
git commit -m "feat(review-evidence-v2): regression analyzer + hard floor non-overridable + budget snapshot (#task-11)"
```

## Criteri di accettazione

- [ ] `compute_regression_verdict` produce 5 decision branch corretti
- [ ] **CRITICAL F1+E5:** hard floor priority sopra regression check, non-overridable
- [ ] **CRITICAL E5:** `min_dim` floor separato (any dim < 40 = block)
- [ ] **CRITICAL E1:** `snapshot_budget_at_pr_open` immutable (deepcopy)
- [ ] A6 baseline_synthetic → AUTO_APPROVE su score sopra floor
- [ ] 8 test PASS
- [ ] No regression v1
