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
    """Window 2026-03-01 -> 2026-03-31 = ~4.43 settimane. alice 2/4.43, bob 2/4.43, carol 1/4.43."""
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
    """alice: 1/2 = 0.5; bob: 1/2 = 0.5 (uno e revert con trailer=False); carol: 0/1 = 0.0."""
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
    """N=1 -> z-score = 0, no crash."""
    result = ck.z_score({"alice": 10.0})
    assert result == {"alice": 0.0}


def test_z_score_uniform_values_returns_zero():
    """sigma=0 -> z-score = 0 per tutti."""
    result = ck.z_score({"alice": 5.0, "bob": 5.0, "carol": 5.0})
    assert result == {"alice": 0.0, "bob": 0.0, "carol": 0.0}


def test_z_score_normal():
    """Valori normali: 1, 5, 9 -> mean 5, std ~ 3.27, z ~ -1.22, 0, 1.22."""
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
    # alice 2 commits, bob 2 commits, carol 1 commit -> carol esclusa
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
    """Q2 rework_ratio in v1 e 'deferred' -- ritorna 0.0 con flag documentato."""
    import pandas as pd
    prs_df = pd.DataFrame([
        {"author": "alice"}, {"author": "alice"}, {"author": "bob"},
    ])
    result = ck.kpi_rework_ratio(prs_df)
    # In v1, senza colonna force_pushes_after_review -> 0.0 per tutti (documentato)
    assert result == {"alice": 0.0, "bob": 0.0}
    # Q2 e marcato come deferred nel catalog -- il report espone "N/A v1" nella descrizione
