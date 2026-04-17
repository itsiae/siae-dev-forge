"""Test per compute_branches.py — 8 KPI + edge cases (13 test)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

import compute_branches as cb


@pytest.fixture
def branches_df(fixtures_dir: Path) -> pd.DataFrame:
    """DataFrame from branches_sample.json fixture."""
    fixture = fixtures_dir / "branches_sample.json"
    data = json.loads(fixture.read_text())
    return pd.DataFrame(data)


@pytest.fixture
def empty_df() -> pd.DataFrame:
    """Empty DataFrame con colonne schema branch."""
    return pd.DataFrame(columns=[
        "name", "author", "last_commit_at", "age_days",
        "commit_count", "loc_delta", "pr_count", "merged",
    ])


# ── Freeze time for deterministic _is_active / _is_stale ──
_FROZEN_NOW = pd.Timestamp("2026-04-15T12:00:00", tz=timezone.utc)


@pytest.fixture(autouse=True)
def freeze_time():
    """Patch pd.Timestamp.now to return deterministic time."""
    with patch("compute_branches.pd.Timestamp.now", return_value=_FROZEN_NOW):
        yield


# ── KPI happy-path tests (1 per KPI = 8 tests) ──

class TestKpiActiveBranchesPerDev:
    def test_happy(self, branches_df):
        """Active branches (commit <= 7 days ago) grouped by dev."""
        result = cb.kpi_active_branches_per_dev(branches_df)
        # alice: feat/auth-v2 (1d), fix/login-bug (5d), docs/readme-update (1d) = 3
        # bob: hotfix/critical-crash (2d), feat/unicode (4d) = 2
        # carol: experiment-spike (3d) = 1
        assert result == {"alice": 3, "bob": 2, "carol": 1}


class TestKpiBranchesWithoutPr:
    def test_happy(self, branches_df):
        """Branches with pr_count == 0 grouped by dev."""
        result = cb.kpi_branches_without_pr(branches_df)
        # bob: hotfix/critical-crash, refactor/db-layer = 2
        # carol: experiment-spike = 1
        assert result == {"bob": 2, "carol": 1}


class TestKpiBranchesAgeP50Days:
    def test_happy(self, branches_df):
        """Median age_days per dev."""
        result = cb.kpi_branches_age_p50_days(branches_df)
        # alice: [3, 7, 1] -> median = 3.0
        # bob: [2, 45, 4] -> median = 4.0
        # carol: [5, 60] -> median = 32.5
        assert result["alice"] == pytest.approx(3.0)
        assert result["bob"] == pytest.approx(4.0)
        assert result["carol"] == pytest.approx(32.5)


class TestKpiBranchesSizeP50Commits:
    def test_happy(self, branches_df):
        """Median commit_count per dev."""
        result = cb.kpi_branches_size_p50_commits(branches_df)
        # alice: [5, 2, 1] -> median = 2.0
        # bob: [1, 12, 4] -> median = 4.0
        # carol: [3, 1] -> median = 2.0
        assert result["alice"] == pytest.approx(2.0)
        assert result["bob"] == pytest.approx(4.0)
        assert result["carol"] == pytest.approx(2.0)


class TestKpiBranchesLocP50:
    def test_happy(self, branches_df):
        """Median loc_delta per dev."""
        result = cb.kpi_branches_loc_p50(branches_df)
        # alice: [120, 30, 15] -> median = 30.0
        # bob: [10, 500, 200] -> median = 200.0
        # carol: [80, 5] -> median = 42.5
        assert result["alice"] == pytest.approx(30.0)
        assert result["bob"] == pytest.approx(200.0)
        assert result["carol"] == pytest.approx(42.5)


class TestKpiStaleBranchesCount:
    def test_happy(self, branches_df):
        """Stale branches: last commit > 30 days AND not merged."""
        result = cb.kpi_stale_branches_count(branches_df)
        # refactor/db-layer: 45 days, not merged -> stale
        # chore/update-deps: 60 days, merged -> NOT stale
        assert result == 1


class TestKpiBranchNamingComplianceRate:
    def test_happy(self, branches_df):
        """Compliant = match ^(feat|fix|refactor|hotfix|chore|docs)/."""
        result = cb.kpi_branch_naming_compliance_rate(branches_df)
        # Compliant: feat/auth-v2, fix/login-bug, hotfix/critical-crash,
        #   refactor/db-layer, chore/update-deps, docs/readme-update,
        #   feat/unicode-branch = 7
        # Not compliant: experiment-spike = 1
        # Rate = 7/8 = 0.875
        assert result == pytest.approx(0.875)


class TestKpiHotfixBranchesCount:
    def test_happy(self, branches_df):
        """Count branches matching ^hotfix/."""
        result = cb.kpi_hotfix_branches_count(branches_df)
        # hotfix/critical-crash = 1
        assert result == 1


# ── Helper tests (1) ──

class TestHelpers:
    def test_is_active_and_is_stale_logic(self, freeze_time):
        """_is_active and _is_stale helpers boundary logic."""
        recent = {"last_commit_at": "2026-04-14T10:00:00+00:00", "merged": False}
        old = {"last_commit_at": "2026-03-01T10:00:00+00:00", "merged": False}
        old_merged = {"last_commit_at": "2026-03-01T10:00:00+00:00", "merged": True}
        no_commit = {"merged": False}

        assert cb._is_active(recent) is True
        assert cb._is_active(old) is False
        assert cb._is_stale(recent) is False
        assert cb._is_stale(old) is True
        assert cb._is_stale(old_merged) is False  # merged -> not stale
        assert cb._is_stale(no_commit) is True  # no commit -> stale
        assert cb._is_active(no_commit) is False  # no commit -> not active


# ── Edge-case tests (4) ──

class TestEdgeCases:
    def test_empty_dataframe_returns_empty_or_zero(self, empty_df):
        """All KPIs handle empty DataFrame gracefully."""
        assert cb.kpi_active_branches_per_dev(empty_df) == {}
        assert cb.kpi_branches_without_pr(empty_df) == {}
        assert cb.kpi_branches_age_p50_days(empty_df) == {}
        assert cb.kpi_branches_size_p50_commits(empty_df) == {}
        assert cb.kpi_branches_loc_p50(empty_df) == {}
        assert cb.kpi_stale_branches_count(empty_df) == 0
        assert cb.kpi_branch_naming_compliance_rate(empty_df) == 0.0
        assert cb.kpi_hotfix_branches_count(empty_df) == 0

    def test_single_branch(self, freeze_time):
        """Single branch in DataFrame."""
        df = pd.DataFrame([{
            "name": "feat/solo",
            "author": "alice",
            "last_commit_at": "2026-04-14T10:00:00+00:00",
            "age_days": 1,
            "commit_count": 3,
            "loc_delta": 50,
            "pr_count": 1,
            "merged": False,
        }])
        assert cb.kpi_active_branches_per_dev(df) == {"alice": 1}
        assert cb.kpi_branches_without_pr(df) == {}
        assert cb.kpi_branches_age_p50_days(df) == {"alice": 1.0}
        assert cb.kpi_stale_branches_count(df) == 0
        assert cb.kpi_branch_naming_compliance_rate(df) == pytest.approx(1.0)
        assert cb.kpi_hotfix_branches_count(df) == 0

    def test_no_author_field(self, freeze_time):
        """Branch with None author doesn't crash — returns gracefully."""
        df = pd.DataFrame([{
            "name": "feat/orphan",
            "author": None,
            "last_commit_at": "2026-04-14T10:00:00+00:00",
            "age_days": 1,
            "commit_count": 2,
            "loc_delta": 10,
            "pr_count": 0,
            "merged": False,
        }])
        # Should not raise — groupby drops NaN authors gracefully
        result = cb.kpi_active_branches_per_dev(df)
        assert isinstance(result, dict)
        # Also non-groupby KPIs must not crash
        assert cb.kpi_stale_branches_count(df) == 0
        assert cb.kpi_branch_naming_compliance_rate(df) == pytest.approx(1.0)
        assert cb.kpi_hotfix_branches_count(df) == 0

    def test_unicode_branch_name_preserved(self, branches_df):
        """Unicode characters in branch names are preserved (NF26)."""
        names = branches_df["name"].tolist()
        assert any("\u00fc" in n or "\u00e4" in n or "\u00f1" in n for n in names)
        # Naming compliance still works on unicode names
        rate = cb.kpi_branch_naming_compliance_rate(branches_df)
        assert isinstance(rate, float)
        assert 0.0 <= rate <= 1.0
