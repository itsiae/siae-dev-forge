"""Test per compute_reviews.py — 5 KPI review + co-authored detection (11 test)."""
from __future__ import annotations

import json
import pytest
import pandas as pd

import compute_reviews as cr
from collect_github import extract_co_authored


# ────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────

@pytest.fixture
def reviews_df(fixtures_dir) -> pd.DataFrame:
    """Load reviews from fixture (7 records: 5 human + 1 DISMISSED + 1 bot)."""
    data = json.loads((fixtures_dir / "reviews_sample.json").read_text())
    return pd.DataFrame(data)


@pytest.fixture
def reviews_no_bot(reviews_df) -> pd.DataFrame:
    """Reviews excluding bot reviewers (6 records)."""
    return reviews_df[~reviews_df["reviewer"].str.contains(r"\[bot\]", na=False)]


# ────────────────────────────────────────────────────────
# Happy path — 1 per KPI (5 test)
# ────────────────────────────────────────────────────────

def test_r1_reviews_given_count(reviews_no_bot):
    """R1: bob reviewed alice+carol (2), carol reviewed alice (1), alice reviewed bob+carol (3).
    Self-reviews excluded. Bot excluded by pre-filter.
    alice: PR#103(bob)+PR#104(bob)+PR#105(carol DISMISSED but still a review given) = 3."""
    result = cr.kpi_reviews_given_count(reviews_no_bot)
    assert result["bob"] == 2      # PR#101 (alice), PR#105 (carol)
    assert result["carol"] == 1    # PR#101 (alice)
    assert result["alice"] == 3    # PR#103 (bob), PR#104 (bob), PR#105 (carol)


def test_r2_review_turnaround_p50_h(reviews_no_bot):
    """R2: median turnaround per reviewer (hours).
    bob: PR#101 = 2h, PR#105 = 16h -> median = 9.0h
    carol: PR#101 = 1h -> 1.0h
    alice: PR#103 = 3h, PR#104 = 2h, PR#105(DISMISSED) = 4h -> median = 3.0h
    """
    result = cr.kpi_review_turnaround_p50_h(reviews_no_bot)
    assert result["bob"] == 9.0
    assert result["carol"] == 1.0
    assert result["alice"] == 3.0


def test_r3_approvals_given_count(reviews_no_bot):
    """R3: APPROVED only, DISMISSED excluded.
    bob: 2 (PR#101, PR#105). alice: 1 (PR#104). carol: 0 (COMMENTED only).
    alice DISMISSED on PR#105 -> not counted."""
    result = cr.kpi_approvals_given_count(reviews_no_bot)
    assert result["bob"] == 2
    assert result["alice"] == 1
    assert "carol" not in result  # 0 approvals -> not in dict


def test_r4_co_authored_prs_count():
    """R4: count PRs per co-author from Co-Authored-By trailers."""
    prs = pd.DataFrame([
        {"pr_number": 1, "co_authors": ["alice@siae.it"]},
        {"pr_number": 2, "co_authors": ["alice@siae.it", "bob@siae.it"]},
        {"pr_number": 3, "co_authors": []},
    ])
    result = cr.kpi_co_authored_prs_count(prs)
    assert result["alice@siae.it"] == 2
    assert result["bob@siae.it"] == 1


def test_r5_onboarding_flag():
    """R5: dev with first commit < 60 days before window_start -> onboarding=True."""
    first_dates = {
        "alice": "2026-02-01",   # 28 days before window_start -> within 60d -> True
        "bob": "2025-12-01",     # 90 days before -> False
        "carol": "2026-02-28",   # 1 day before -> True
    }
    result = cr.compute_onboarding_flag(first_dates, "2026-03-01", threshold_days=60)
    assert result["alice"] is True
    assert result["bob"] is False
    assert result["carol"] is True


# ────────────────────────────────────────────────────────
# Edge cases (4 test)
# ────────────────────────────────────────────────────────

def test_edge_empty_dataframe_no_crash():
    """Empty DataFrame -> empty dict for all KPIs."""
    empty = pd.DataFrame(columns=["reviewer", "pr_number", "state",
                                   "created_at", "target_author", "pr_latest_commit_at"])
    assert cr.kpi_reviews_given_count(empty) == {}
    assert cr.kpi_review_turnaround_p50_h(empty) == {}
    assert cr.kpi_approvals_given_count(empty) == {}


def test_edge_single_reviewer_is_author():
    """Single review where reviewer == target_author -> excluded from reviews_given."""
    self_review = pd.DataFrame([{
        "reviewer": "alice",
        "pr_number": 1,
        "state": "APPROVED",
        "created_at": "2026-03-01T10:00:00+00:00",
        "target_author": "alice",
        "pr_latest_commit_at": "2026-03-01T08:00:00+00:00",
    }])
    assert cr.kpi_reviews_given_count(self_review) == {}


def test_edge_dismissed_filtered_from_approvals():
    """DISMISSED reviews are not counted as approvals."""
    reviews = pd.DataFrame([
        {"reviewer": "alice", "pr_number": 1, "state": "DISMISSED",
         "created_at": "2026-03-01T10:00:00+00:00", "target_author": "bob",
         "pr_latest_commit_at": "2026-03-01T08:00:00+00:00"},
        {"reviewer": "alice", "pr_number": 2, "state": "APPROVED",
         "created_at": "2026-03-02T10:00:00+00:00", "target_author": "bob",
         "pr_latest_commit_at": "2026-03-02T08:00:00+00:00"},
    ])
    result = cr.kpi_approvals_given_count(reviews)
    assert result["alice"] == 1  # Only APPROVED counted, not DISMISSED


def test_edge_onboarding_boundary():
    """Dev with first_commit exactly at cutoff boundary -> onboarding=False (> not >=)."""
    first_dates = {"dev_at_boundary": "2026-01-01"}
    # window_start 2026-03-01, threshold 60 -> cutoff = 2025-12-31
    # 2026-01-01 > 2025-12-31 -> True (onboarding)
    result = cr.compute_onboarding_flag(first_dates, "2026-03-01", threshold_days=60)
    assert result["dev_at_boundary"] is True

    # Exact cutoff: first_commit == cutoff -> False (not strictly >)
    first_dates_exact = {"dev_exact": "2025-12-31"}
    result_exact = cr.compute_onboarding_flag(first_dates_exact, "2026-03-01", threshold_days=60)
    assert result_exact["dev_exact"] is False


# ────────────────────────────────────────────────────────
# Co-Authored-By detection (2 test)
# ────────────────────────────────────────────────────────

def test_co_authored_single_trailer():
    """Single Co-Authored-By trailer extracted correctly."""
    msg = "feat: add X\n\nCo-Authored-By: Alice Smith <alice@siae.it>"
    result = extract_co_authored(msg)
    assert result == ["alice@siae.it"]


def test_co_authored_multiple_trailers():
    """Multiple Co-Authored-By trailers + case insensitive."""
    msg = (
        "feat: collab\n\n"
        "co-authored-by: Alice Smith <alice@siae.it>\n"
        "CO-AUTHORED-BY: Bob Jones <bob@siae.it>"
    )
    result = extract_co_authored(msg)
    assert result == ["alice@siae.it", "bob@siae.it"]
