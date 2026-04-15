# Task 03 — F1 PR States + 6 KPI

**Goal:** Fetch PR in tutti gli stati (OPEN/DRAFT/CLOSED/REOPENED/MERGED) + 6 KPI in-flight.
**AC coperti:** CF1, IF1-IF6 (design §5.3)
**Dipendenze:** Task 01
**Effort:** ~50 min
**Test nuovi:** 19 (1 happy, 3 stati, 9 fault injection, 6 KPI)

## File coinvolti

- `scripts/collect_github.py` — estendi query GraphQL per tutti stati + timeline events
- `scripts/compute_kpis.py` — aggiungi funzioni `kpi_open_prs_count`, `kpi_draft_prs_count`, `kpi_stuck_prs_count`, `kpi_closed_unmerged_count`, `kpi_reopen_count`, `kpi_oldest_open_pr_age_days`
- `tests/test_collect_github.py` — estendi
- `tests/test_compute_kpis.py` — estendi con 6 KPI test
- `tests/fixtures/github_api_response.json` — estendi con PR OPEN/DRAFT/CLOSED/REOPENED

## Step 1 — Estendi GraphQL query

Sostituisci `pullRequests(states: MERGED, ...)` con:
```graphql
pullRequests(states: [OPEN, MERGED, CLOSED], first: 100, orderBy: {field: UPDATED_AT, direction: DESC}) {
  nodes {
    number author{login} createdAt mergedAt closedAt updatedAt
    state isDraft
    timelineItems(itemTypes: [REOPENED_EVENT], first: 5) { totalCount }
    commits(first: 1) { nodes { commit { committedDate } } }
    reviews(first: 50) { nodes { createdAt state comments { totalCount } } }
    files(first: 100) { nodes { path additions deletions } }
    body
  }
}
```

## Step 2 — Estendi `extract_pr_records` con nuovi campi

Aggiungi campi: `state`, `is_draft`, `updated_at`, `closed_at`, `reopen_count` (da timelineItems.totalCount), `is_stuck` (computed: state=OPEN AND now-updated > 7d).

## Step 3 — 6 KPI functions in compute_kpis.py

```python
def kpi_open_prs_count(prs: pd.DataFrame) -> dict[str, int]:
    if prs.empty: return {}
    open_prs = prs[prs["state"] == "OPEN"]
    return open_prs.groupby("author").size().to_dict()


def kpi_draft_prs_count(prs: pd.DataFrame) -> dict[str, int]:
    if prs.empty: return {}
    drafts = prs[(prs["state"] == "OPEN") & (prs["is_draft"] == True)]
    return drafts.groupby("author").size().to_dict()


def kpi_stuck_prs_count(prs: pd.DataFrame, threshold_days: int = 7) -> dict[str, int]:
    if prs.empty: return {}
    stuck = prs[prs["is_stuck"] == True]
    return stuck.groupby("author").size().to_dict()


def kpi_closed_unmerged_count(prs: pd.DataFrame) -> dict[str, int]:
    if prs.empty: return {}
    closed_unmerged = prs[(prs["state"] == "CLOSED") & (prs["merged_at"].isna())]
    return closed_unmerged.groupby("author").size().to_dict()


def kpi_reopen_count(prs: pd.DataFrame) -> dict[str, int]:
    if prs.empty: return {}
    return prs.groupby("author")["reopen_count"].sum().to_dict()


def kpi_oldest_open_pr_age_days(prs: pd.DataFrame) -> dict[str, float]:
    if prs.empty: return {}
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    open_prs = prs[prs["state"] == "OPEN"].copy()
    if open_prs.empty:
        return {}
    open_prs["age_days"] = open_prs["created_at"].apply(
        lambda s: (now - pd.Timestamp(s)).days if pd.notna(s) else 0
    )
    return open_prs.groupby("author")["age_days"].max().to_dict()
```

## Step 4 — Test nuovi (19)

Pattern fault injection (NF9-NF17) sulla GraphQL query estesa: auth/timeout/rate-limit/500/404/malformed/empty. Più 6 test KPI happy path.

Esempio test stuck:
```python
def test_kpi_stuck_prs_counts_only_open_over_7d():
    prs = pd.DataFrame([
        {"state": "OPEN", "is_stuck": True, "author": "alice"},
        {"state": "OPEN", "is_stuck": False, "author": "alice"},
        {"state": "CLOSED", "is_stuck": False, "author": "bob"},
    ])
    result = ck.kpi_stuck_prs_count(prs)
    assert result == {"alice": 1}
```

## Verify

```bash
PYTHONPATH=skills/siae-dev-analytics/scripts python3 -m pytest skills/siae-dev-analytics/tests/test_collect_github.py skills/siae-dev-analytics/tests/test_compute_kpis.py -v
```

Output atteso: `+19 new tests passing`.

## Criteri accettazione

- [ ] GraphQL fetcha OPEN/DRAFT/CLOSED/MERGED/REOPENED
- [ ] 6 KPI implementati in compute_kpis.py
- [ ] Fault injection 9 scenari testati
- [ ] PR Excel report (in task-12) include sezione "In-Flight Work"
