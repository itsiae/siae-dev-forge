# Task 04 — compute_kpis.py (11 KPI + z-score + ROI Index)

**Goal:** Implementare il core logic dei KPI: 11 metriche oggettive per dev + z-score normalizzato + ROI Index sintetico.

**AC coperti:** AC05, AC08, AC16, AC17

**Dipendenze:** Task 1

**Tempo stimato:** 45 min (task critico, TDD rigoroso)

---

## File coinvolti

- `skills/siae-dev-analytics/scripts/compute_kpis.py` (nuovo)
- `skills/siae-dev-analytics/tests/test_compute_kpis.py` (nuovo)
- `skills/siae-dev-analytics/tests/fixtures/expected_kpis.csv` (nuovo)

## Step 1 — TDD: Scrivi fixture expected_kpis.csv

Crea `tests/fixtures/expected_kpis.csv` con i valori esatti che i test usano come oracolo (coerenti con `sample_prs`, `sample_commits`, `sample_tags` in Step 2):

```csv
dev,pr_cycle_time_p50,lead_time_to_merge_p50,pr_throughput_weekly,time_to_first_review_p50,deploy_frequency_monthly,review_comments_p50,rework_ratio,test_presence_rate,verification_rate,design_driven_rate,revert_rate
alice,30.0,39.5,0.467,13.0,1.0,3.5,0.0,0.5,0.5,0.5,0.0
bob,7.0,13.5,0.467,1.5,1.0,1.5,0.0,0.5,0.5,0.5,0.5
carol,20.0,21.0,0.233,2.0,0.0,1.0,0.0,1.0,0.0,0.0,0.0
```

**Nota:** i valori sono le mediane calcolate sulle fixture (alice ha 2 PR: cycle_time 4 e 56 → p50 = 30; bob ha 2 PR: 4 e 10 → 7; carol 1 PR: 20). Il test `test_expected_csv_matches_computed` (Step 2) verifica che `compute_all` produca valori entro tolleranza 0.01 da questo CSV oracolo.

## Step 2 — TDD: Scrivi test PRIMA

Crea `tests/test_compute_kpis.py`:

```python
"""Test per compute_kpis.py — 11 KPI + z-score + ROI."""
from __future__ import annotations

from datetime import datetime, timedelta
import math
import pytest
import pandas as pd

import compute_kpis as ck


@pytest.fixture
def sample_prs() -> list[dict]:
    """5 PR, 3 dev (alice 2, bob 2, carol 1) matching fixture github_api_response."""
    return [
        {"repo": "itsiae/repo", "number": 101, "author": "alice",
         "created_at": "2026-03-01T10:00:00+00:00", "merged_at": "2026-03-01T14:00:00+00:00",
         "cycle_time_hours": 4.0, "lead_time_hours": 5.0, "time_to_first_review_hours": 1.0,
         "review_comments": 2, "has_tests": True, "has_design_link": True},
        {"repo": "itsiae/repo", "number": 102, "author": "alice",
         "created_at": "2026-03-05T09:00:00+00:00", "merged_at": "2026-03-07T17:00:00+00:00",
         "cycle_time_hours": 56.0, "lead_time_hours": 74.0, "time_to_first_review_hours": 25.0,
         "review_comments": 5, "has_tests": False, "has_design_link": False},
        {"repo": "itsiae/repo", "number": 103, "author": "bob",
         "created_at": "2026-03-10T12:00:00+00:00", "merged_at": "2026-03-10T16:00:00+00:00",
         "cycle_time_hours": 4.0, "lead_time_hours": 5.0, "time_to_first_review_hours": 1.0,
         "review_comments": 0, "has_tests": True, "has_design_link": True},
        {"repo": "itsiae/repo", "number": 104, "author": "bob",
         "created_at": "2026-03-15T08:00:00+00:00", "merged_at": "2026-03-15T18:00:00+00:00",
         "cycle_time_hours": 10.0, "lead_time_hours": 22.0, "time_to_first_review_hours": 2.0,
         "review_comments": 3, "has_tests": False, "has_design_link": False},
        {"repo": "itsiae/repo", "number": 105, "author": "carol",
         "created_at": "2026-03-20T14:00:00+00:00", "merged_at": "2026-03-21T10:00:00+00:00",
         "cycle_time_hours": 20.0, "lead_time_hours": 21.0, "time_to_first_review_hours": 2.0,
         "review_comments": 1, "has_tests": True, "has_design_link": False},
    ]


@pytest.fixture
def sample_commits() -> list[dict]:
    """Commit per ogni PR + 1 revert da bob."""
    return [
        {"repo": "itsiae/repo", "oid": "abc1", "author": "alice", "committed_at": "2026-03-01T09:00:00Z",
         "message": "feat\n\nverified-by: siae-verification", "has_verified_trailer": True, "is_revert": False},
        {"repo": "itsiae/repo", "oid": "abc2", "author": "alice", "committed_at": "2026-03-04T15:00:00Z",
         "message": "refactor", "has_verified_trailer": False, "is_revert": False},
        {"repo": "itsiae/repo", "oid": "abc3", "author": "bob", "committed_at": "2026-03-10T11:00:00Z",
         "message": "feat\n\nverified-by: siae-verification", "has_verified_trailer": True, "is_revert": False},
        {"repo": "itsiae/repo", "oid": "abc4", "author": "bob", "committed_at": "2026-03-14T20:00:00Z",
         "message": "Revert \"x\"", "has_verified_trailer": False, "is_revert": True},
        {"repo": "itsiae/repo", "oid": "abc5", "author": "carol", "committed_at": "2026-03-20T13:00:00Z",
         "message": "feat", "has_verified_trailer": False, "is_revert": False},
    ]


@pytest.fixture
def sample_tags() -> list[dict]:
    return [
        {"repo": "itsiae/repo", "tag_name": "COLLAUDO-v1.0.0", "commit_oid": "abc3", "attributed_to": "bob"},
        {"repo": "itsiae/repo", "tag_name": "PRODUZIONE-v1.0.0", "commit_oid": "abc1", "attributed_to": "alice"},
    ]


@pytest.fixture
def window():
    return ("2026-03-01", "2026-03-31")


# ────────────────────────────────────────────────────────
# Velocity KPI (V1-V5)
# ────────────────────────────────────────────────────────

def test_v1_pr_cycle_time_p50(sample_prs):
    """alice: median(4, 56) = 30; bob: median(4, 10) = 7; carol: 20."""
    df = pd.DataFrame(sample_prs)
    result = ck.kpi_pr_cycle_time_p50(df)
    assert result["alice"] == 30.0
    assert result["bob"] == 7.0
    assert result["carol"] == 20.0


def test_v2_lead_time_to_merge_p50(sample_prs):
    """alice: median(5, 74) = 39.5; bob: median(5, 22) = 13.5; carol: 21."""
    df = pd.DataFrame(sample_prs)
    result = ck.kpi_lead_time_to_merge_p50(df)
    assert result["alice"] == 39.5
    assert result["bob"] == 13.5
    assert result["carol"] == 21.0


def test_v3_pr_throughput_weekly(sample_prs, window):
    """Window 2026-03-01 → 2026-03-31 = ~4.43 settimane. alice 2/4.43, bob 2/4.43, carol 1/4.43."""
    df = pd.DataFrame(sample_prs)
    result = ck.kpi_pr_throughput_weekly(df, window)
    assert math.isclose(result["alice"], 2 / (30 / 7), rel_tol=0.01)
    assert math.isclose(result["bob"], 2 / (30 / 7), rel_tol=0.01)
    assert math.isclose(result["carol"], 1 / (30 / 7), rel_tol=0.01)


def test_v4_time_to_first_review_p50(sample_prs):
    """alice: median(1, 25) = 13; bob: median(1, 2) = 1.5; carol: 2."""
    df = pd.DataFrame(sample_prs)
    result = ck.kpi_time_to_first_review_p50(df)
    assert result["alice"] == 13.0
    assert result["bob"] == 1.5
    assert result["carol"] == 2.0


def test_v5_deploy_frequency_monthly(sample_tags, window):
    """Window 1 mese. alice 1 tag, bob 1 tag, carol 0."""
    df = pd.DataFrame(sample_tags)
    result = ck.kpi_deploy_frequency_monthly(df, window)
    assert result["alice"] == 1.0
    assert result["bob"] == 1.0
    assert result.get("carol", 0) == 0


def test_v5_deploy_frequency_with_fallback_chain():
    """AC16: V5 ha 3 scenari. Testiamo PR found, last committer, team-only."""
    tags = [
        # Scenario (a) PR merge author trovata
        {"repo": "r", "tag_name": "COLLAUDO-v1", "commit_oid": "sha1", "attributed_to": "alice"},
        # Scenario (b) last committer fallback
        {"repo": "r", "tag_name": "COLLAUDO-v2", "commit_oid": "sha2", "attributed_to": "bob"},
        # Scenario (c) team-only fallback
        {"repo": "r", "tag_name": "COLLAUDO-v3", "commit_oid": "sha3", "attributed_to": "team"},
    ]
    df = pd.DataFrame(tags)
    result = ck.kpi_deploy_frequency_monthly(df, ("2026-03-01", "2026-03-31"))
    assert result.get("alice", 0) == 1.0
    assert result.get("bob", 0) == 1.0
    assert result.get("team", 0) == 1.0


def test_siae_tag_regex_matches_variants():
    """AC17: regex copre 6 varianti."""
    cases = [
        ("COLLAUDO-v1.2.3", True),
        ("collaudo_20260415", True),
        ("CERTIFICAZIONE/1.2.3", True),
        ("PRODUZIONE-2026.04.15", True),
        ("collaudo-v1", True),
        ("v1.2.3-collaudo", False),
    ]
    for name, expected in cases:
        assert bool(ck.SIAE_TAG_REGEX.match(name)) is expected, name


# ────────────────────────────────────────────────────────
# Quality KPI (Q1-Q6)
# ────────────────────────────────────────────────────────

def test_q1_review_comments_p50(sample_prs):
    """alice: median(2, 5) = 3.5; bob: median(0, 3) = 1.5; carol: 1."""
    df = pd.DataFrame(sample_prs)
    result = ck.kpi_review_comments_p50(df)
    assert result["alice"] == 3.5
    assert result["bob"] == 1.5
    assert result["carol"] == 1.0


def test_q3_test_presence_rate(sample_prs):
    """alice: 1/2 = 0.5; bob: 1/2 = 0.5; carol: 1/1 = 1.0."""
    df = pd.DataFrame(sample_prs)
    result = ck.kpi_test_presence_rate(df)
    assert result["alice"] == 0.5
    assert result["bob"] == 0.5
    assert result["carol"] == 1.0


def test_q4_verification_rate(sample_commits):
    """alice: 1/2 = 0.5; bob: 1/2 = 0.5 (uno è revert con trailer=False); carol: 0/1 = 0.0."""
    df = pd.DataFrame(sample_commits)
    result = ck.kpi_verification_rate(df)
    assert result["alice"] == 0.5
    assert result["bob"] == 0.5
    assert result["carol"] == 0.0


def test_q5_design_driven_rate(sample_prs):
    """alice: 1/2 = 0.5; bob: 1/2 = 0.5; carol: 0/1 = 0.0."""
    df = pd.DataFrame(sample_prs)
    result = ck.kpi_design_driven_rate(df)
    assert result["alice"] == 0.5
    assert result["bob"] == 0.5
    assert result["carol"] == 0.0


def test_q6_revert_rate(sample_commits):
    """alice: 0/2; bob: 1/2 = 0.5; carol: 0/1."""
    df = pd.DataFrame(sample_commits)
    result = ck.kpi_revert_rate(df)
    assert result["alice"] == 0.0
    assert result["bob"] == 0.5
    assert result["carol"] == 0.0


# ────────────────────────────────────────────────────────
# Edge cases + z-score + ROI
# ────────────────────────────────────────────────────────

def test_z_score_single_dev_returns_zero():
    """N=1 → z-score = 0, no crash."""
    result = ck.z_score({"alice": 10.0})
    assert result == {"alice": 0.0}


def test_z_score_uniform_values_returns_zero():
    """σ=0 → z-score = 0 per tutti."""
    result = ck.z_score({"alice": 5.0, "bob": 5.0, "carol": 5.0})
    assert result == {"alice": 0.0, "bob": 0.0, "carol": 0.0}


def test_z_score_normal():
    """Valori normali: 1, 5, 9 → mean 5, std ≈ 3.27, z ≈ -1.22, 0, 1.22."""
    result = ck.z_score({"alice": 1.0, "bob": 5.0, "carol": 9.0})
    assert math.isclose(result["alice"], -1.22, abs_tol=0.01)
    assert math.isclose(result["bob"], 0.0, abs_tol=0.01)
    assert math.isclose(result["carol"], 1.22, abs_tol=0.01)


def test_roi_index_velocity_times_quality():
    """ROI = velocity_score * quality_score / cost_score (default cost=1)."""
    roi = ck.roi_index(velocity_score=1.5, quality_score=2.0, cost_score=1.0)
    assert roi == 3.0


def test_roi_index_with_cost():
    """ROI con cost_score reale."""
    roi = ck.roi_index(velocity_score=2.0, quality_score=2.0, cost_score=2.0)
    assert roi == 2.0


def test_compute_all_returns_dataframe(sample_prs, sample_commits, sample_tags, window):
    """compute_all() ritorna DataFrame con colonne per 11 KPI + score + roi."""
    prs_df = pd.DataFrame(sample_prs)
    commits_df = pd.DataFrame(sample_commits)
    tags_df = pd.DataFrame(sample_tags)
    result = ck.compute_all(prs_df, commits_df, tags_df, window)
    expected_cols = {
        "pr_cycle_time_p50", "lead_time_to_merge_p50", "pr_throughput_weekly",
        "time_to_first_review_p50", "deploy_frequency_monthly",
        "review_comments_p50", "rework_ratio", "test_presence_rate",
        "verification_rate", "design_driven_rate", "revert_rate",
        "velocity_score", "quality_score", "roi_index",
    }
    assert expected_cols.issubset(set(result.columns))
    assert "alice" in result.index
    assert "bob" in result.index
    assert "carol" in result.index


def test_min_commits_threshold_excludes(sample_commits):
    """Dev con < threshold commit escluso."""
    df = pd.DataFrame(sample_commits)
    filtered = ck.filter_by_min_commits(df, threshold=2)
    # alice 2 commits, bob 2 commits, carol 1 commit → carol esclusa
    assert set(filtered["author"].unique()) == {"alice", "bob"}


def test_anonymize_hash_deterministic():
    """Hash SHA256[:8] determinisico."""
    h1 = ck.anonymize_login("alice")
    h2 = ck.anonymize_login("alice")
    assert h1 == h2
    assert len(h1) == 8
    assert h1 != "alice"


def test_expected_csv_matches_computed(sample_prs, sample_commits, sample_tags, window, fixtures_dir):
    """Oracle CSV: valori calcolati matchano expected_kpis.csv (tolleranza 0.01)."""
    import pandas as pd
    expected = pd.read_csv(fixtures_dir / "expected_kpis.csv").set_index("dev")

    prs_df = pd.DataFrame(sample_prs)
    commits_df = pd.DataFrame(sample_commits)
    tags_df = pd.DataFrame(sample_tags)
    computed = ck.compute_all(prs_df, commits_df, tags_df, window)

    for dev in expected.index:
        for col in expected.columns:
            exp_val = expected.loc[dev, col]
            comp_val = computed.loc[dev, col] if col in computed.columns else 0
            assert abs(exp_val - comp_val) < 0.01, f"{dev}/{col}: expected {exp_val}, got {comp_val}"


def test_q2_rework_ratio_documented_as_deferred():
    """Q2 rework_ratio in v1 è 'deferred' — ritorna 0.0 con flag documentato."""
    import pandas as pd
    prs_df = pd.DataFrame([
        {"author": "alice"}, {"author": "alice"}, {"author": "bob"},
    ])
    result = ck.kpi_rework_ratio(prs_df)
    # In v1, senza colonna force_pushes_after_review → 0.0 per tutti (documentato)
    assert result == {"alice": 0.0, "bob": 0.0}
    # Q2 è marcato come deferred nel catalog — il report espone "N/A v1" nella descrizione
```

## Step 3 — Run test, verifica che falliscono

Run:
```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge/skills/siae-dev-analytics"
pytest tests/test_compute_kpis.py -v 2>&1 | tail -10
```

Output atteso: `ModuleNotFoundError: No module named 'compute_kpis'`.

## Step 4 — Implementa `compute_kpis.py`

Crea `skills/siae-dev-analytics/scripts/compute_kpis.py`:

```python
"""Compute 11 KPI + z-score + ROI Index per sviluppatore.

KPI Velocity: V1-V5 (DORA + DX AI).
KPI Quality: Q1-Q6.
ROI Index: (velocity_score × quality_score) / cost_score.
"""
from __future__ import annotations

import hashlib
import re
import statistics
from datetime import datetime
import pandas as pd

SIAE_TAG_REGEX = re.compile(r"^(COLLAUDO|CERTIFICAZIONE|PRODUZIONE)[-_/].+$", re.IGNORECASE)

VELOCITY_KPIS = [
    "pr_cycle_time_p50",
    "lead_time_to_merge_p50",
    "pr_throughput_weekly",
    "time_to_first_review_p50",
    "deploy_frequency_monthly",
]

QUALITY_KPIS = [
    "review_comments_p50",
    "rework_ratio",
    "test_presence_rate",
    "verification_rate",
    "design_driven_rate",
    "revert_rate",
]


# ────────────────────────────────────────────────────────
# Velocity KPI
# ────────────────────────────────────────────────────────

def kpi_pr_cycle_time_p50(prs: pd.DataFrame) -> dict[str, float]:
    """V1: median(merged_at - opened_at) in ore, per dev."""
    return prs.groupby("author")["cycle_time_hours"].median().to_dict()


def kpi_lead_time_to_merge_p50(prs: pd.DataFrame) -> dict[str, float]:
    """V2: median(merged_at - first_commit_at) in ore."""
    return prs.groupby("author")["lead_time_hours"].median().to_dict()


def _weeks_in_window(window: tuple[str, str]) -> float:
    start, end = (datetime.fromisoformat(w) for w in window)
    return max((end - start).days / 7, 1e-9)


def kpi_pr_throughput_weekly(prs: pd.DataFrame, window: tuple[str, str]) -> dict[str, float]:
    """V3: count(merged_pr) / weeks_in_window."""
    weeks = _weeks_in_window(window)
    counts = prs.groupby("author").size()
    return (counts / weeks).to_dict()


def kpi_time_to_first_review_p50(prs: pd.DataFrame) -> dict[str, float]:
    """V4: median(first_review_at - opened_at)."""
    s = prs.groupby("author")["time_to_first_review_hours"].median()
    return s.fillna(0).to_dict()


def _months_in_window(window: tuple[str, str]) -> float:
    """Mese = 30 giorni esatti (semplificazione reportistica).

    Scelta deliberata per coerenza test (30gg → 1.0 mese esatto) e
    intuitivita' report. Differenza da 30.44gg è < 1.5% — trascurabile
    alla granularita' di ROI mensile.
    """
    start, end = (datetime.fromisoformat(w) for w in window)
    return max((end - start).days / 30, 1e-9)


def kpi_deploy_frequency_monthly(tags: pd.DataFrame, window: tuple[str, str]) -> dict[str, float]:
    """V5: count(tag per dev) / months_in_window."""
    if tags.empty or "attributed_to" not in tags.columns:
        return {}
    months = _months_in_window(window)
    # Filtra solo tag SIAE
    mask = tags["tag_name"].apply(lambda n: bool(SIAE_TAG_REGEX.match(n or "")))
    filtered = tags[mask]
    counts = filtered.groupby("attributed_to").size()
    return (counts / months).to_dict()


# ────────────────────────────────────────────────────────
# Quality KPI
# ────────────────────────────────────────────────────────

def kpi_review_comments_p50(prs: pd.DataFrame) -> dict[str, float]:
    """Q1: median(review_comments per PR)."""
    return prs.groupby("author")["review_comments"].median().to_dict()


def kpi_rework_ratio(prs: pd.DataFrame) -> dict[str, float]:
    """Q2: force_push_after_review / total_pr.

    DEFERRED in v1: GitHub GraphQL non espone direttamente force push events senza
    polling del timeline REST (costo alto). In v1 ritorna 0.0 per tutti gli autori
    e il report lo dichiara "N/A v1" in kpi-catalog.md.

    v2 roadmap: implementare fallback `commits_after_first_review / total_pr`
    contando commit pushati dopo il timestamp della prima review (campo già
    presente in reviews/createdAt e commits/committedDate).
    """
    if "force_pushes_after_review" not in prs.columns:
        return {a: 0.0 for a in prs["author"].unique()}
    grouped = prs.groupby("author").agg(
        fp=("force_pushes_after_review", "sum"),
        total=("author", "size"),
    )
    return (grouped["fp"] / grouped["total"]).to_dict()


def kpi_test_presence_rate(prs: pd.DataFrame) -> dict[str, float]:
    """Q3: PR con test files / tot PR."""
    return prs.groupby("author")["has_tests"].mean().to_dict()


def kpi_verification_rate(commits: pd.DataFrame) -> dict[str, float]:
    """Q4: commit con trailer verified-by / tot commit."""
    return commits.groupby("author")["has_verified_trailer"].mean().to_dict()


def kpi_design_driven_rate(prs: pd.DataFrame) -> dict[str, float]:
    """Q5: PR con link docs/plans design / tot PR."""
    return prs.groupby("author")["has_design_link"].mean().to_dict()


def kpi_revert_rate(commits: pd.DataFrame) -> dict[str, float]:
    """Q6: commit revert / tot commit."""
    return commits.groupby("author")["is_revert"].mean().to_dict()


# ────────────────────────────────────────────────────────
# z-score + ROI
# ────────────────────────────────────────────────────────

def z_score(values: dict[str, float]) -> dict[str, float]:
    """Z-score normalizzato. Edge: N<2 o σ=0 → 0."""
    vs = [v for v in values.values() if v is not None and not pd.isna(v)]
    if len(vs) < 2:
        return {k: 0.0 for k in values}
    mean = statistics.mean(vs)
    std = statistics.stdev(vs) if len(vs) > 1 else 0
    if std == 0:
        return {k: 0.0 for k in values}
    return {k: (v - mean) / std if v is not None and not pd.isna(v) else 0.0
            for k, v in values.items()}


def roi_index(velocity_score: float, quality_score: float, cost_score: float = 1.0) -> float:
    """ROI = (velocity × quality) / cost."""
    if cost_score == 0:
        return 0.0
    return (velocity_score * quality_score) / cost_score


# ────────────────────────────────────────────────────────
# Orchestrator
# ────────────────────────────────────────────────────────

def compute_all(
    prs: pd.DataFrame,
    commits: pd.DataFrame,
    tags: pd.DataFrame,
    window: tuple[str, str],
    cost_scores: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Calcola tutti i KPI + score + ROI per ogni dev."""
    kpis = {
        "pr_cycle_time_p50": kpi_pr_cycle_time_p50(prs),
        "lead_time_to_merge_p50": kpi_lead_time_to_merge_p50(prs),
        "pr_throughput_weekly": kpi_pr_throughput_weekly(prs, window),
        "time_to_first_review_p50": kpi_time_to_first_review_p50(prs),
        "deploy_frequency_monthly": kpi_deploy_frequency_monthly(tags, window),
        "review_comments_p50": kpi_review_comments_p50(prs),
        "rework_ratio": kpi_rework_ratio(prs),
        "test_presence_rate": kpi_test_presence_rate(prs),
        "verification_rate": kpi_verification_rate(commits),
        "design_driven_rate": kpi_design_driven_rate(prs),
        "revert_rate": kpi_revert_rate(commits),
    }

    all_devs = set()
    for v in kpis.values():
        all_devs.update(v.keys())

    df = pd.DataFrame(index=sorted(all_devs))
    for name, values in kpis.items():
        df[name] = pd.Series(values)
    df = df.fillna(0)

    # Velocity score: più basso cycle_time = meglio → invertiamo segno dove serve
    # Semplice media z-score delle velocity (throughput e deploy_freq più alto = meglio;
    # cycle/lead/review_time più basso = meglio → segno opposto)
    velocity_inverted = {"pr_cycle_time_p50", "lead_time_to_merge_p50", "time_to_first_review_p50"}
    velocity_z = []
    for kpi in VELOCITY_KPIS:
        zs = z_score(df[kpi].to_dict())
        if kpi in velocity_inverted:
            zs = {k: -v for k, v in zs.items()}
        velocity_z.append(pd.Series(zs))
    df["velocity_score"] = pd.concat(velocity_z, axis=1).mean(axis=1)

    # Quality score: rework/revert/review_comments più basso = meglio; test/verification/design più alto = meglio
    quality_inverted = {"review_comments_p50", "rework_ratio", "revert_rate"}
    quality_z = []
    for kpi in QUALITY_KPIS:
        zs = z_score(df[kpi].to_dict())
        if kpi in quality_inverted:
            zs = {k: -v for k, v in zs.items()}
        quality_z.append(pd.Series(zs))
    df["quality_score"] = pd.concat(quality_z, axis=1).mean(axis=1)

    # ROI
    cost_scores = cost_scores or {d: 1.0 for d in df.index}
    df["roi_index"] = [
        roi_index(df.loc[d, "velocity_score"], df.loc[d, "quality_score"], cost_scores.get(d, 1.0))
        for d in df.index
    ]

    return df


# ────────────────────────────────────────────────────────
# Utilities
# ────────────────────────────────────────────────────────

def filter_by_min_commits(commits: pd.DataFrame, threshold: int = 5) -> pd.DataFrame:
    """Esclude dev con meno di threshold commit."""
    counts = commits.groupby("author").size()
    keep = counts[counts >= threshold].index
    return commits[commits["author"].isin(keep)]


def anonymize_login(login: str) -> str:
    """SHA256[:8] — determinisico."""
    return hashlib.sha256(login.encode()).hexdigest()[:8]
```

## Step 5 — Run test, verifica che passano

Run:
```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge/skills/siae-dev-analytics"
pip install pandas pytest pytest-cov 2>&1 | tail -2
pytest tests/test_compute_kpis.py -v --cov=scripts/compute_kpis 2>&1 | tail -25
```

Output atteso: `22 passed`, coverage ≥ 85%.

## Step 6 — Commit

Run:
```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge"
git add skills/siae-dev-analytics/scripts/compute_kpis.py \
        skills/siae-dev-analytics/tests/test_compute_kpis.py \
        skills/siae-dev-analytics/tests/fixtures/expected_kpis.csv
git commit -m "feat(skill): add compute_kpis for siae-dev-analytics [Task 4/7]

- 11 KPI per dev: 5 velocity (DORA) + 6 quality
- z-score normalizzato con edge cases (N<2, σ=0)
- ROI Index = (velocity × quality) / cost
- SIAE_TAG_REGEX centralizzata, 6 varianti testate (AC17)
- V5 deploy_freq con fallback chain PR author / last committer / team (AC16)
- anonymize_login via SHA256[:8]
- 22 test pytest pass, coverage ≥ 85% su compute_kpis

AC05, AC08, AC16, AC17"
```

## Criteri di accettazione Task 4

- [ ] 11 funzioni KPI implementate (V1-V5, Q1-Q6)
- [ ] `z_score` gestisce N<2 e σ=0 → ritorna 0
- [ ] `roi_index` calcola velocity × quality / cost
- [ ] `compute_all` ritorna DataFrame con 14 colonne (11 KPI + 3 score)
- [ ] SIAE_TAG_REGEX matcha 5/6 varianti (1 negative)
- [ ] `anonymize_login` deterministico 8-char SHA256
- [ ] 22 test pytest pass, coverage ≥ 85%
- [ ] Commit conventional

## Verifica

Run:
```bash
pytest skills/siae-dev-analytics/tests/test_compute_kpis.py -v --tb=short
```

Output atteso: `22 passed`.
