# Task 07 — F4a-c ROI Metrics Extended (15 KPI)

**Goal:** Implementa Cost (4) + Value (7) + Delivery (4) KPI.
**AC coperti:** C1-C4, VA1-VA7, D1-D4 (design §5.6, 5.7, 5.8)
**Dipendenze:** Task 02 (cost sources), 03 (PR states), 04 (branch)
**Effort:** ~110 min
**Test nuovi:** 22 (15 KPI × 1 happy + 7 edge)

## File coinvolti

- `scripts/compute_kpis.py` — aggiungi 15 funzioni
- `tests/test_compute_kpis.py` — 22 test

## Step 1 — Parser commit types

Aggiungi in compute_kpis.py:
```python
import re
COMMIT_TYPE_RE = re.compile(r"^(feat|fix|refactor|perf|test|docs|chore|build|ci|style)(\([^)]+\))?:", re.MULTILINE)

def extract_commit_type(message: str) -> str | None:
    m = COMMIT_TYPE_RE.search(message or "")
    return m.group(1).lower() if m else None
```

## Step 2 — Cost KPI (4)

```python
def kpi_eur_per_merged_pr(cost_by_dev: dict[str, float], merged_pr_count: dict[str, int]) -> dict[str, float]:
    result = {}
    for dev, cost in cost_by_dev.items():
        prs = merged_pr_count.get(dev, 0)
        if prs > 0:
            result[dev] = cost / prs
    return result


def kpi_eur_per_accepted_loc(cost_by_dev: dict, net_loc_by_dev: dict) -> dict[str, float]:
    result = {}
    for dev, cost in cost_by_dev.items():
        loc = net_loc_by_dev.get(dev, 0)
        if loc > 0:
            result[dev] = cost / loc
    return result


def kpi_tokens_per_completed_pr(tokens_by_dev: dict, merged_pr_count: dict) -> dict[str, float]:
    result = {}
    for dev, tok in tokens_by_dev.items():
        prs = merged_pr_count.get(dev, 0)
        if prs > 0:
            result[dev] = tok / prs
    return result


def kpi_cost_per_story_point(cost_by_dev: dict, sp_closed: dict) -> dict[str, float]:
    result = {}
    for dev, cost in cost_by_dev.items():
        sp = sp_closed.get(dev, 0)
        if sp > 0:
            result[dev] = cost / sp
    return result
```

## Step 3 — Value KPI (7)

```python
def kpi_features_shipped(commits: pd.DataFrame) -> dict[str, int]:
    if commits.empty: return {}
    commits = commits.copy()
    commits["type"] = commits["message"].apply(extract_commit_type)
    feat = commits[commits["type"] == "feat"]
    return feat.groupby("author").size().to_dict()


def kpi_bugs_fixed(commits: pd.DataFrame) -> dict[str, int]:
    if commits.empty: return {}
    commits = commits.copy()
    commits["type"] = commits["message"].apply(extract_commit_type)
    fix = commits[commits["type"] == "fix"]
    return fix.groupby("author").size().to_dict()


def kpi_tech_debt_reduced(commits: pd.DataFrame) -> dict[str, int]:
    if commits.empty: return {}
    commits = commits.copy()
    commits["type"] = commits["message"].apply(extract_commit_type)
    td = commits[commits["type"].isin(["refactor", "perf"])]
    return td.groupby("author").size().to_dict()


def kpi_net_loc_shipped(prs: pd.DataFrame) -> dict[str, int]:
    if prs.empty or "additions" not in prs.columns: return {}
    prs = prs.copy()
    prs["net"] = prs["additions"] - prs["deletions"]
    return prs.groupby("author")["net"].sum().to_dict()


def kpi_compliance_bundle_rate(prs: pd.DataFrame, commits: pd.DataFrame) -> dict[str, float]:
    """PR con (test + design link + verified-by trailer) / total."""
    if prs.empty: return {}
    # PR bundle = has_tests AND has_design_link AND has_verified_commit
    # Approssimazione: join con commits per verified_trailer
    if commits.empty:
        prs["bundled"] = prs["has_tests"] & prs["has_design_link"]
    else:
        verif_by_dev = commits.groupby("author")["has_verified_trailer"].any().to_dict()
        prs["has_verified"] = prs["author"].map(verif_by_dev).fillna(False)
        prs["bundled"] = prs["has_tests"] & prs["has_design_link"] & prs["has_verified"]
    return prs.groupby("author")["bundled"].mean().to_dict()


def kpi_first_shot_quality(prs: pd.DataFrame) -> dict[str, float]:
    """PR senza force-push post first review / total. Fallback: 1.0 se nessun dato."""
    if prs.empty: return {}
    col = "force_push_after_review" if "force_push_after_review" in prs.columns else None
    if col is None:
        return {a: 1.0 for a in prs["author"].unique()}
    prs = prs.copy()
    prs["no_rework"] = ~prs[col]
    return prs.groupby("author")["no_rework"].mean().to_dict()


def kpi_design_adherence_rate(prs: pd.DataFrame) -> dict[str, float]:
    """Alias di design_driven_rate ma esplicito per ROI side."""
    if prs.empty: return {}
    return prs.groupby("author")["has_design_link"].mean().to_dict()
```

## Step 4 — Delivery KPI (4) DORA extended

```python
def kpi_time_to_production_p50(tags: pd.DataFrame, prs: pd.DataFrame) -> dict[str, float]:
    """median(tag PRODUZIONE_date - PR merge_date) per dev."""
    if tags.empty or prs.empty: return {}
    prod_tags = tags[tags["tag_name"].str.contains("PRODUZIONE", case=False, na=False)]
    if prod_tags.empty: return {}
    # Join tag.commit_oid → PR → compute delta; simplified: per-dev median
    # Implementation detail: require join by commit_oid → PR merge_date
    # Placeholder deterministic for testing:
    return {}  # Task implementer implementerà con join reale


def kpi_change_failure_rate(commits: pd.DataFrame, deploy_window_days: int = 7) -> dict[str, float]:
    """count(revert in 7gg post deploy) / count(deploy per dev)."""
    if commits.empty: return {}
    # DORA CFR proxy
    reverts = commits[commits["is_revert"] == True]
    deploys = commits  # placeholder: in reale, filter by tag events
    if deploys.empty: return {}
    result = {}
    for dev in commits["author"].unique():
        dev_reverts = len(reverts[reverts["author"] == dev])
        dev_deploys = len(deploys[deploys["author"] == dev])
        if dev_deploys > 0:
            result[dev] = dev_reverts / dev_deploys
    return result


def kpi_incident_free_days(commits: pd.DataFrame) -> int:
    """Days since last revert globally."""
    if commits.empty: return 0
    reverts = commits[commits["is_revert"] == True]
    if reverts.empty:
        return 999  # no reverts ever (cap)
    last_revert = pd.Timestamp(reverts["committed_at"].max())
    now = pd.Timestamp.now(tz="UTC")
    return max(0, (now - last_revert).days)


def kpi_deploy_lead_time_p50(commits: pd.DataFrame, tags: pd.DataFrame) -> dict[str, float]:
    """median(commit_date - tag PRODUZIONE_date) per dev. Richiede join commit ↔ tag."""
    # Simplified per v2: team-level
    if commits.empty or tags.empty: return {}
    return {}  # Implementer: join
```

## Step 5 — Test (22)

1 happy test per ogni KPI (15) + 7 edge: empty input, zero denominator, None in delta, missing column, unicode author, single-dev, negative values.

## Verify

```bash
PYTHONPATH=skills/siae-dev-analytics/scripts python3 -m pytest skills/siae-dev-analytics/tests/test_compute_kpis.py -v
```

Output atteso: `+22 new tests`.

## Criteri accettazione

- [ ] 15 funzioni KPI implementate
- [ ] Division by zero → None/0 esplicito + log, NO NaN silent
- [ ] extract_commit_type regex matcha tutti i conventional commit types
- [ ] Test edge case: empty input per ogni funzione
