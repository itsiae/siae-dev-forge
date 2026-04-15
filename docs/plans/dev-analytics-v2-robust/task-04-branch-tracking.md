# Task 04 — F1b Branch Tracking + 8 KPI

**Goal:** Fetch branch attivi + compute 8 branch KPI.
**AC coperti:** CF2, BT1-BT3, B1-B8 (design §5.4)
**Dipendenze:** Task 01
**Effort:** ~60 min
**Test nuovi:** 13 (1 happy + 4 edge + 8 KPI)

## File coinvolti

- `scripts/collect_github.py` — aggiungi `fetch_branches(repo, since)`
- `scripts/compute_branches.py` — implementa 8 KPI
- `tests/fixtures/branches_sample.json` — fixture
- `tests/test_collect_github.py` — estendi con test branches
- `tests/test_compute_branches.py` — 13 test

## Step 1 — fetch_branches GraphQL

```graphql
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    refs(refPrefix: "refs/heads/", first: 200, orderBy: {field: TAG_COMMIT_DATE, direction: DESC}) {
      nodes {
        name
        target { ... on Commit {
          oid
          committedDate
          author { user { login } }
          history(first: 1) { totalCount }
          associatedPullRequests(first: 3) {
            nodes { number state isDraft }
          }
        }}
      }
    }
  }
}
```

## Step 2 — compute_branches.py — 8 KPI

```python
"""Branch KPI: 8 metriche su branch attivi."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import re
import pandas as pd

SIAE_BRANCH_NAMING = re.compile(r"^(feat|fix|refactor|hotfix|chore|docs)/", re.IGNORECASE)
HOTFIX_PATTERN = re.compile(r"^hotfix/", re.IGNORECASE)


def _is_active(branch: dict, days: int = 7) -> bool:
    """Branch active if last commit <= days ago."""
    if not branch.get("last_commit_at"):
        return False
    last = pd.Timestamp(branch["last_commit_at"])
    now = pd.Timestamp.now(tz=timezone.utc)
    return (now - last).days <= days


def _is_stale(branch: dict, days: int = 30) -> bool:
    if not branch.get("last_commit_at"):
        return True
    last = pd.Timestamp(branch["last_commit_at"])
    now = pd.Timestamp.now(tz=timezone.utc)
    return (now - last).days > days and not branch.get("merged", False)


def kpi_active_branches_per_dev(branches: pd.DataFrame) -> dict[str, int]:
    if branches.empty: return {}
    active = branches[branches.apply(lambda r: _is_active(r.to_dict()), axis=1)]
    return active.groupby("author").size().to_dict()


def kpi_branches_without_pr(branches: pd.DataFrame) -> dict[str, int]:
    if branches.empty: return {}
    no_pr = branches[branches["pr_count"] == 0]
    return no_pr.groupby("author").size().to_dict()


def kpi_branches_age_p50_days(branches: pd.DataFrame) -> dict[str, float]:
    if branches.empty: return {}
    return branches.groupby("author")["age_days"].median().to_dict()


def kpi_branches_size_p50_commits(branches: pd.DataFrame) -> dict[str, float]:
    if branches.empty: return {}
    return branches.groupby("author")["commit_count"].median().to_dict()


def kpi_branches_loc_p50(branches: pd.DataFrame) -> dict[str, float]:
    if branches.empty or "loc_delta" not in branches.columns: return {}
    return branches.groupby("author")["loc_delta"].median().to_dict()


def kpi_stale_branches_count(branches: pd.DataFrame) -> int:
    if branches.empty: return 0
    return int(branches.apply(lambda r: _is_stale(r.to_dict()), axis=1).sum())


def kpi_branch_naming_compliance_rate(branches: pd.DataFrame) -> float:
    if branches.empty: return 0.0
    compliant = branches["name"].apply(lambda n: bool(SIAE_BRANCH_NAMING.match(n or "")))
    return float(compliant.mean())


def kpi_hotfix_branches_count(branches: pd.DataFrame) -> int:
    if branches.empty: return 0
    return int(branches["name"].apply(lambda n: bool(HOTFIX_PATTERN.match(n or ""))).sum())
```

## Step 3 — Test (13)

In `tests/test_compute_branches.py`, 1 fixture + 13 test (uno per KPI + edge cases: empty, single-branch, no-author, unicode name).

## Verify

```bash
PYTHONPATH=skills/siae-dev-analytics/scripts python3 -m pytest skills/siae-dev-analytics/tests/test_compute_branches.py -v
```

Output atteso: `13 passed`.

## Criteri accettazione

- [ ] fetch_branches GraphQL fetcha 200 branch
- [ ] 8 KPI implementati
- [ ] Edge case: empty DataFrame ritorna {} o 0, no crash
- [ ] Unicode branch names preservati
