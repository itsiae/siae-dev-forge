"""Branch KPI: 8 metriche su branch attivi.

Funzioni compute per branch tracking (F1b).
Ogni KPI accetta un DataFrame con colonne branch e ritorna
dict per-developer o scalare aggregato.
"""
from __future__ import annotations

import logging
import re
from datetime import timezone

import pandas as pd

log = logging.getLogger(__name__)

__all__: list[str] = [
    "kpi_active_branches_per_dev",
    "kpi_branches_without_pr",
    "kpi_branches_age_p50_days",
    "kpi_branches_size_p50_commits",
    "kpi_branches_loc_p50",
    "kpi_stale_branches_count",
    "kpi_branch_naming_compliance_rate",
    "kpi_hotfix_branches_count",
]

SIAE_BRANCH_NAMING = re.compile(
    r"^(feat|fix|refactor|hotfix|chore|docs)/", re.IGNORECASE
)
HOTFIX_PATTERN = re.compile(r"^hotfix/", re.IGNORECASE)


def _is_active(branch: dict, days: int = 7) -> bool:
    """Branch active if last commit <= *days* ago."""
    if not branch.get("last_commit_at"):
        return False
    last = pd.Timestamp(branch["last_commit_at"])
    now = pd.Timestamp.now(tz=timezone.utc)
    return (now - last).days <= days


def _is_stale(branch: dict, days: int = 30) -> bool:
    """Branch stale if last commit > *days* ago AND not merged."""
    if not branch.get("last_commit_at"):
        return True
    last = pd.Timestamp(branch["last_commit_at"])
    now = pd.Timestamp.now(tz=timezone.utc)
    return (now - last).days > days and not branch.get("merged", False)


# ── KPI functions ──────────────────────────────────────────────


def kpi_active_branches_per_dev(branches: pd.DataFrame) -> dict[str, int]:
    """Active branches (commit <= 7 days ago) grouped by developer."""
    if branches.empty:
        return {}
    active = branches[branches.apply(lambda r: _is_active(r.to_dict()), axis=1)]
    if active.empty:
        return {}
    return active.groupby("author").size().to_dict()


def kpi_branches_without_pr(branches: pd.DataFrame) -> dict[str, int]:
    """Branches with zero associated PRs, grouped by developer."""
    if branches.empty:
        return {}
    no_pr = branches[branches["pr_count"] == 0]
    if no_pr.empty:
        return {}
    return no_pr.groupby("author").size().to_dict()


def kpi_branches_age_p50_days(branches: pd.DataFrame) -> dict[str, float]:
    """Median branch age in days, per developer."""
    if branches.empty:
        return {}
    return branches.groupby("author")["age_days"].median().to_dict()


def kpi_branches_size_p50_commits(branches: pd.DataFrame) -> dict[str, float]:
    """Median commit count per branch, per developer."""
    if branches.empty:
        return {}
    return branches.groupby("author")["commit_count"].median().to_dict()


def kpi_branches_loc_p50(branches: pd.DataFrame) -> dict[str, float]:
    """Median LOC delta per branch, per developer."""
    if branches.empty or "loc_delta" not in branches.columns:
        return {}
    return branches.groupby("author")["loc_delta"].median().to_dict()


def kpi_stale_branches_count(branches: pd.DataFrame) -> int:
    """Total count of stale branches (> 30 days, not merged)."""
    if branches.empty:
        return 0
    return int(branches.apply(lambda r: _is_stale(r.to_dict()), axis=1).sum())


def kpi_branch_naming_compliance_rate(branches: pd.DataFrame) -> float:
    """Fraction of branches matching SIAE naming convention.

    Convention: ^(feat|fix|refactor|hotfix|chore|docs)/ (case-insensitive).
    """
    if branches.empty:
        return 0.0
    compliant = branches["name"].apply(
        lambda n: bool(SIAE_BRANCH_NAMING.match(n or ""))
    )
    return float(compliant.mean())


def kpi_hotfix_branches_count(branches: pd.DataFrame) -> int:
    """Count of branches matching ^hotfix/ pattern."""
    if branches.empty:
        return 0
    return int(
        branches["name"].apply(lambda n: bool(HOTFIX_PATTERN.match(n or ""))).sum()
    )
