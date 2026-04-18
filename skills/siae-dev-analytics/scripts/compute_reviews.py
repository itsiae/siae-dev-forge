"""Review activity KPI — 5 metriche per review engagement e onboarding."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

import pandas as pd

__all__ = [
    "kpi_reviews_given_count",
    "kpi_review_turnaround_p50_h",
    "kpi_approvals_given_count",
    "kpi_co_authored_prs_count",
    "compute_onboarding_flag",
]


def kpi_reviews_given_count(reviews: pd.DataFrame) -> dict:
    """R1: Count of reviews given per reviewer, excluding self-reviews and bots."""
    if reviews.empty:
        return {}
    # Exclude self-reviews (reviewer == target_author)
    own = reviews[reviews["reviewer"] != reviews["target_author"]]
    # Exclude bot reviewers
    own = own[~own["reviewer"].str.contains(r"\[bot\]", na=False)]
    return own.groupby("reviewer").size().to_dict()


def kpi_review_turnaround_p50_h(reviews: pd.DataFrame) -> dict:
    """R2: Median turnaround hours per reviewer (review created_at - pr_latest_commit_at)."""
    if reviews.empty:
        return {}
    if "pr_latest_commit_at" not in reviews.columns:
        return {}
    df = reviews.copy()
    # Exclude bot reviewers
    df = df[~df["reviewer"].str.contains(r"\[bot\]", na=False)]
    df["turnaround_h"] = df.apply(
        lambda r: (pd.Timestamp(r["created_at"]) - pd.Timestamp(r["pr_latest_commit_at"])).total_seconds() / 3600
        if pd.notna(r["pr_latest_commit_at"]) else None,
        axis=1,
    )
    return df.groupby("reviewer")["turnaround_h"].median().dropna().to_dict()


def kpi_approvals_given_count(reviews: pd.DataFrame) -> dict:
    """R3: Count of APPROVED reviews per reviewer. DISMISSED excluded."""
    if reviews.empty:
        return {}
    approved = reviews[reviews["state"] == "APPROVED"]
    # Exclude bot reviewers
    approved = approved[~approved["reviewer"].str.contains(r"\[bot\]", na=False)]
    return approved.groupby("reviewer").size().to_dict()


def kpi_co_authored_prs_count(prs_with_coauthors: pd.DataFrame) -> dict:
    """R4: PR con trailer Co-Authored-By, count per co-author."""
    if prs_with_coauthors.empty:
        return {}
    c: Counter = Counter()
    for _, row in prs_with_coauthors.iterrows():
        for coauth in row.get("co_authors", []) or []:
            c[coauth] += 1
    return dict(c)


def compute_onboarding_flag(
    first_commit_dates: dict,
    window_start: str,
    threshold_days: int = 60,
) -> dict:
    """R5: Returns {dev: True} if first_commit_date > window_start - threshold_days.

    Strictly greater than: dev at exact cutoff -> False.
    """
    window_start_dt = pd.Timestamp(window_start)
    cutoff = window_start_dt - pd.Timedelta(days=threshold_days)
    return {
        dev: pd.Timestamp(fcd) > cutoff
        for dev, fcd in first_commit_dates.items()
    }
