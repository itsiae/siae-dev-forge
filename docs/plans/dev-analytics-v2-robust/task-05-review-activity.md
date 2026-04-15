# Task 05 — F2 Review Activity + 5 KPI

**Goal:** Fetch review activity + co-authored detection + 5 KPI review.
**AC coperti:** CF3, CF5, R1-R5 (design §5.5)
**Dipendenze:** Task 01
**Effort:** ~45 min
**Test nuovi:** 11

## File coinvolti

- `scripts/collect_github.py` — aggiungi `fetch_reviews(repo, since)` + `extract_co_authored(commit_message)`
- `scripts/compute_reviews.py` — 5 KPI
- `tests/fixtures/reviews_sample.json` — fixture
- `tests/test_compute_reviews.py` — 11 test

## Step 1 — fetch_reviews GraphQL

Estendi query PR con:
```graphql
reviews(first: 50) {
  nodes {
    author { login }
    state  # APPROVED, CHANGES_REQUESTED, COMMENTED, DISMISSED
    createdAt
    comments { totalCount }
  }
}
```

Estrai record: `{"reviewer": login, "pr_number": N, "state": "APPROVED", "created_at": "...", "target_author": pr_author, "pr_latest_commit_at": ...}`.

## Step 2 — Co-authored detection

```python
CO_AUTHORED_RE = re.compile(r"^Co-Authored-By:\s*(.+?)\s*<(.+?)>", re.MULTILINE | re.IGNORECASE)


def extract_co_authored(commit_message: str) -> list[str]:
    """Returns list of co-author emails/names from trailer."""
    if not commit_message:
        return []
    matches = CO_AUTHORED_RE.findall(commit_message)
    return [m[1] for m in matches]  # email
```

## Step 3 — compute_reviews.py — 5 KPI

```python
"""Review activity KPI."""
from __future__ import annotations
from datetime import datetime, timezone
import pandas as pd


def kpi_reviews_given_count(reviews: pd.DataFrame) -> dict[str, int]:
    if reviews.empty: return {}
    # Review given by X on PR where author != X
    own = reviews[reviews["reviewer"] != reviews["target_author"]]
    return own.groupby("reviewer").size().to_dict()


def kpi_review_turnaround_p50_h(reviews: pd.DataFrame) -> dict[str, float]:
    if reviews.empty: return {}
    if "pr_latest_commit_at" not in reviews.columns: return {}
    reviews = reviews.copy()
    reviews["turnaround_h"] = reviews.apply(
        lambda r: (pd.Timestamp(r["created_at"]) - pd.Timestamp(r["pr_latest_commit_at"])).total_seconds() / 3600
        if pd.notna(r["pr_latest_commit_at"]) else None, axis=1
    )
    return reviews.groupby("reviewer")["turnaround_h"].median().dropna().to_dict()


def kpi_approvals_given_count(reviews: pd.DataFrame) -> dict[str, int]:
    if reviews.empty: return {}
    approved = reviews[reviews["state"] == "APPROVED"]
    return approved.groupby("reviewer").size().to_dict()


def kpi_co_authored_prs_count(prs_with_coauthors: pd.DataFrame) -> dict[str, int]:
    """PR con trailer Co-Authored-By, count per co-author."""
    if prs_with_coauthors.empty: return {}
    from collections import Counter
    c: Counter = Counter()
    for _, row in prs_with_coauthors.iterrows():
        for coauth in row.get("co_authors", []) or []:
            c[coauth] += 1
    return dict(c)


def compute_onboarding_flag(first_commit_dates: dict[str, str], window_start: str, threshold_days: int = 60) -> dict[str, bool]:
    """Returns {dev: True} se first_commit_date > window_start - threshold_days."""
    window_start_dt = pd.Timestamp(window_start)
    cutoff = window_start_dt - pd.Timedelta(days=threshold_days)
    return {
        dev: pd.Timestamp(fcd) > cutoff
        for dev, fcd in first_commit_dates.items()
    }
```

## Step 4 — Test (11)

11 test: 1 happy per KPI + 4 edge (empty, single-reviewer, DISMISSED filtered, onboarding boundary).

## Verify

```bash
PYTHONPATH=skills/siae-dev-analytics/scripts python3 -m pytest skills/siae-dev-analytics/tests/test_compute_reviews.py -v
```

Output atteso: `11 passed`.

## Criteri accettazione

- [ ] 5 KPI review implementati
- [ ] DISMISSED reviews escluse da approvals_given
- [ ] Co-Authored-By regex case-insensitive + multi-line
- [ ] Edge: empty / bot-reviewer escluso
