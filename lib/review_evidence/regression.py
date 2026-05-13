"""Regression analyzer + hard floor enforcement (Task 11).

Computes deltas between current and baseline ScoreCard and classifies the
PR into one of five decision branches consumed by the renderer + reviewer
agent gatekeeper.

Critical fixes addressed (review-evidence-v2 design doc):

- **E1** — ``snapshot_budget_at_pr_open`` returns a deepcopy of the budget
  config at PR_OPEN_TIME. Subsequent admin mutations of the live
  ``DevForgeScoresConfig`` must NOT bleed into the already-open PR's
  enforcement budget (no retroactive stricter rules).

- **F1 + E5** — Hard floor checks are evaluated FIRST and the resulting
  ``BLOCK_HARD_FLOOR`` decision is **non-overridable** by the reviewer
  agent. Any dimension below its dedicated floor *or* below the shared
  ``min_dim`` floor (default 40) triggers the block, even when the overall
  weighted score still clears its own floor (E5: per-dim floor separate
  from overall floor).

- **A6** — When the baseline is synthetic (e.g. first PR on a fresh
  repo with no history), the regression check is skipped: we still run
  the hard floor gate but, if it passes, the decision is
  ``AUTO_APPROVE`` regardless of "deltas" (there is no real baseline).

Decision priority (highest → lowest):

1. ``BLOCK_HARD_FLOOR`` — any hard floor breach, non-overridable.
2. ``BLOCK_REGRESSION`` — at least one dim regressed past
   ``hard_block_budget``.
3. ``REVIEWER_HANDOFF`` — at least one dim regressed past
   ``warn_budget`` (reviewer agent gatekeeps).
4. ``AUTO_APPROVE`` — everything else (incl. baseline_synthetic with
   floors cleared).

``SEVERELY_DEGRADED`` is reserved for an upstream caller (e.g. when
multiple dims hit hard_block at once) and is NOT emitted here.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from lib.review_evidence.config import DevForgeScoresConfig
from lib.review_evidence.schema import RegressionVerdict, ScoreCard


_DIMENSIONS = ("security", "quality", "coverage", "spec_compliance", "discipline")


@dataclass
class RegressionInput:
    """Bundle of the inputs needed to compute a regression verdict.

    Kept as a separate dataclass so callers (orchestrator, renderer) can
    build it incrementally without ordering arguments by hand.
    """

    current: ScoreCard
    baseline: Optional[ScoreCard]
    cfg: DevForgeScoresConfig
    baseline_synthetic: bool = False


def snapshot_budget_at_pr_open(
    cfg: DevForgeScoresConfig, pr_open_iso: str
) -> Dict[str, Any]:
    """E1 — Immutable snapshot of budget config at PR_OPEN_TIME.

    Uses ``copy.deepcopy`` on every mutable subfield so subsequent admin
    mutations of the live ``cfg`` (post-snapshot) cannot retroactively
    tighten the rules for an already-open PR. The returned dict is owned
    by the caller and safe to persist alongside the evidence payload.
    """
    return {
        "pr_open_iso": pr_open_iso,
        "weights": copy.deepcopy(cfg.weights),
        "hard_floors": copy.deepcopy(cfg.hard_floors),
        "hard_block_budget": copy.deepcopy(cfg.hard_block_budget),
        "warn_budget": copy.deepcopy(cfg.warn_budget),
    }


def is_hard_floor_breached(sc: ScoreCard, cfg: DevForgeScoresConfig) -> bool:
    """E5 — True iff any dimension or overall breaches its hard floor.

    Two independent floors apply:

    - Dedicated floors: ``security``, ``coverage``, ``overall`` (from
      ``cfg.hard_floors``).
    - Shared per-dim floor: ``min_dim`` (default 40). Triggers on any of
      the 5 dimensions, separately from the overall floor — so a PR can
      still block even when ``overall >= floor`` if a single dim collapses.
    """
    if sc.security < cfg.hard_floors.get("security", 60):
        return True
    if sc.coverage < cfg.hard_floors.get("coverage", 50):
        return True
    if sc.overall < cfg.hard_floors.get("overall", 55):
        return True

    min_dim = cfg.hard_floors.get("min_dim", 40)
    for dim_name in _DIMENSIONS:
        if getattr(sc, dim_name) < min_dim:
            return True
    return False


def _hard_floor_breaches_list(
    sc: ScoreCard, cfg: DevForgeScoresConfig
) -> List[str]:
    """Detailed, human-readable list of every breached floor.

    Kept separate from ``is_hard_floor_breached`` so the boolean fast
    path stays cheap for hot call sites (renderer pre-checks).
    """
    out: List[str] = []

    security_floor = cfg.hard_floors.get("security", 60)
    if sc.security < security_floor:
        out.append(f"security({sc.security:.1f}) < hard_floor({security_floor})")

    coverage_floor = cfg.hard_floors.get("coverage", 50)
    if sc.coverage < coverage_floor:
        out.append(f"coverage({sc.coverage:.1f}) < hard_floor({coverage_floor})")

    overall_floor = cfg.hard_floors.get("overall", 55)
    if sc.overall < overall_floor:
        out.append(f"overall({sc.overall:.1f}) < hard_floor({overall_floor})")

    min_dim = cfg.hard_floors.get("min_dim", 40)
    for dim_name in _DIMENSIONS:
        val = getattr(sc, dim_name)
        if val < min_dim:
            out.append(f"{dim_name}({val:.1f}) < min_dim({min_dim})")
    return out


def compute_regression_verdict_from_input(inp: RegressionInput) -> RegressionVerdict:
    """Convenience wrapper that consumes a ``RegressionInput`` bundle.

    Added in the fresh-eyes review iter 1 follow-up to give callers a way to
    actually use the ``RegressionInput`` dataclass (previously a dead bundle:
    declared but never consumed). The positional-arg signature stays the
    canonical entry point — this just unpacks the fields.
    """
    return compute_regression_verdict(
        current=inp.current,
        baseline=inp.baseline,
        cfg=inp.cfg,
        baseline_synthetic=inp.baseline_synthetic,
    )


def compute_regression_verdict(
    current: ScoreCard,
    baseline: Optional[ScoreCard],
    cfg: DevForgeScoresConfig,
    baseline_synthetic: bool = False,
) -> RegressionVerdict:
    """Classify the PR into one of the 5 decision branches.

    See module docstring for the priority order. The function never
    raises on missing budget keys: an unset entry falls back to a
    sentinel (``-999``) that effectively disables that dim's check so
    new dims can be added to ScoreCard without forcing a config bump.
    """
    # 1. Hard floor gate (F1 + E5) — NON-OVERRIDABLE by reviewer agent.
    floor_breaches = _hard_floor_breaches_list(current, cfg)
    if floor_breaches:
        return RegressionVerdict(
            block_dimensions=[],
            warn_dimensions=[],
            improved_dimensions=[],
            hard_floor_breaches=floor_breaches,
            decision="BLOCK_HARD_FLOOR",
            reason=(
                f"Hard floor breached: {'; '.join(floor_breaches)}. "
                "NON-OVERRIDABLE by reviewer."
            ),
        )

    # 2. A6 — synthetic baseline (first PR, no history): skip regression.
    if baseline_synthetic or baseline is None:
        return RegressionVerdict(
            block_dimensions=[],
            warn_dimensions=[],
            improved_dimensions=[],
            hard_floor_breaches=[],
            decision="AUTO_APPROVE",
            reason="First PR (baseline_synthetic). Floor checks pass.",
        )

    # 3. Per-dim delta classification against budgets.
    block_dims: List[str] = []
    warn_dims: List[str] = []
    improved_dims: List[str] = []

    for dim in _DIMENSIONS:
        cur = getattr(current, dim)
        base = getattr(baseline, dim)
        delta = cur - base

        hard_budget = cfg.hard_block_budget.get(dim, -999)
        warn_limit = cfg.warn_budget.get(dim, -999)

        if delta < hard_budget:
            block_dims.append(f"{dim}:{delta:+.1f}")
        elif delta < warn_limit:
            warn_dims.append(f"{dim}:{delta:+.1f}")
        elif delta > 0:
            improved_dims.append(f"{dim}:+{delta:.1f}")

    if block_dims:
        return RegressionVerdict(
            block_dimensions=block_dims,
            warn_dimensions=warn_dims,
            improved_dimensions=improved_dims,
            hard_floor_breaches=[],
            decision="BLOCK_REGRESSION",
            reason=f"Regression block: {'; '.join(block_dims)}",
        )

    if warn_dims:
        return RegressionVerdict(
            block_dimensions=[],
            warn_dimensions=warn_dims,
            improved_dimensions=improved_dims,
            hard_floor_breaches=[],
            decision="REVIEWER_HANDOFF",
            reason=(
                f"Regression warn: {'; '.join(warn_dims)}. "
                "Reviewer agent gatekeeps."
            ),
        )

    return RegressionVerdict(
        block_dimensions=[],
        warn_dimensions=[],
        improved_dimensions=improved_dims,
        hard_floor_breaches=[],
        decision="AUTO_APPROVE",
        reason="All checks pass.",
    )
