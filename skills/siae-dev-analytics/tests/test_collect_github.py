"""Test per collect_github.py."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

import collect_github as cg


@pytest.fixture
def tmp_cache(tmp_path, monkeypatch):
    """Cache in directory temporanea."""
    cache_dir = tmp_path / ".cache" / "github"
    cache_dir.mkdir(parents=True)
    monkeypatch.setattr(cg, "CACHE_DIR", cache_dir)
    return cache_dir


def test_cache_key_deterministic():
    """Stesso repo + window -> stesso hash."""
    k1 = cg.cache_key("itsiae/foo", "2026-01-01", "2026-04-01")
    k2 = cg.cache_key("itsiae/foo", "2026-01-01", "2026-04-01")
    assert k1 == k2


def test_cache_key_different_for_different_window():
    """Finestra diversa -> hash diverso."""
    k1 = cg.cache_key("itsiae/foo", "2026-01-01", "2026-04-01")
    k2 = cg.cache_key("itsiae/foo", "2026-02-01", "2026-04-01")
    assert k1 != k2


def test_cache_miss_invokes_subprocess(tmp_cache, sample_pr_data):
    """Cold cache -> subprocess gh invocato."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(sample_pr_data),
        )
        data = cg.fetch_repo_data("itsiae/sample", "2026-03-01", "2026-03-31")

    assert mock_run.called
    assert "pullRequests" in data["repository"]


def test_cache_hit_does_not_invoke_subprocess(tmp_cache, sample_pr_data):
    """Warm cache -> subprocess NON invocato."""
    # Popola cache
    key = cg.cache_key("itsiae/sample", "2026-03-01", "2026-03-31")
    (tmp_cache / f"{key}.json").write_text(json.dumps(sample_pr_data))

    with patch("subprocess.run") as mock_run:
        data = cg.fetch_repo_data("itsiae/sample", "2026-03-01", "2026-03-31")

    assert not mock_run.called
    assert data["repository"]["nameWithOwner"] == "itsiae/sample-repo"


def test_rate_limit_triggers_backoff(tmp_cache):
    """Response 'rate limit exceeded' -> retry con backoff."""
    responses = [
        MagicMock(returncode=1, stdout="", stderr="API rate limit exceeded"),
        MagicMock(returncode=0, stdout='{"repository": {"pullRequests": {"nodes": []}}}'),
    ]
    with patch("subprocess.run", side_effect=responses), \
         patch("time.sleep") as mock_sleep:
        data = cg.fetch_repo_data("itsiae/foo", "2026-01-01", "2026-02-01")

    assert mock_sleep.called
    assert data["repository"]["pullRequests"] == {"nodes": []}


def test_unauthenticated_raises(tmp_cache):
    """Response 'not authenticated' -> RuntimeError."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=4, stdout="", stderr="gh: Not authenticated")
        with pytest.raises(RuntimeError, match="authent"):
            cg.fetch_repo_data("itsiae/foo", "2026-01-01", "2026-02-01")


def test_private_repo_no_access_skips(tmp_cache, caplog):
    """Response 'Could not resolve repo' -> skip con warning."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Could not resolve to a Repository")
        data = cg.fetch_repo_data("itsiae/private", "2026-01-01", "2026-02-01", skip_on_error=True)
    assert data is None


def test_extract_pr_fields():
    """fetch_repo_data -> normalized PR records (dev, repo, cycle_time, ecc.)."""
    raw = {
        "repository": {
            "nameWithOwner": "itsiae/repo",
            "pullRequests": {"nodes": [
                {
                    "number": 1,
                    "author": {"login": "alice"},
                    "createdAt": "2026-03-01T10:00:00Z",
                    "mergedAt": "2026-03-01T14:00:00Z",
                    "commits": {"nodes": [{"commit": {"committedDate": "2026-03-01T09:00:00Z"}}]},
                    "reviews": {"nodes": []},
                    "files": {"nodes": [{"path": "src/a.py"}]},
                    "body": "",
                }
            ]},
        }
    }
    prs = cg.extract_pr_records(raw)
    assert len(prs) == 1
    assert prs[0]["author"] == "alice"
    assert prs[0]["cycle_time_hours"] == 4.0
    assert prs[0]["repo"] == "itsiae/repo"
    assert prs[0]["number"] == 1


def test_extract_commit_records_with_trailer():
    """Commit con verified-by trailer -> flag True."""
    raw = {
        "repository": {
            "defaultBranchRef": {"target": {"history": {"nodes": [
                {"oid": "abc1", "author": {"user": {"login": "alice"}}, "committedDate": "2026-03-01T09:00:00Z",
                 "message": "feat: x\n\nverified-by: siae-verification"},
                {"oid": "abc2", "author": {"user": {"login": "bob"}}, "committedDate": "2026-03-02T10:00:00Z",
                 "message": "fix: y"},
            ]}}}
        }
    }
    commits = cg.extract_commit_records(raw)
    assert len(commits) == 2
    assert commits[0]["has_verified_trailer"] is True
    assert commits[1]["has_verified_trailer"] is False


def test_extract_deploy_tags_attributes_to_commit_author(sample_pr_data):
    """Tag SIAE -> attribuiti all'autore del commit taggato."""
    pr_records = cg.extract_pr_records(sample_pr_data)
    commit_records = cg.extract_commit_records(sample_pr_data)
    tag_records = cg.extract_deploy_tags(sample_pr_data, commit_records, pr_records)

    # fixture ha COLLAUDO-v1.0.0 su abc3 (bob) e PRODUZIONE-v1.0.0 su abc1 (alice)
    assert len(tag_records) == 2
    names = {t["tag_name"]: t["attributed_to"] for t in tag_records}
    assert names["COLLAUDO-v1.0.0"] == "bob"
    assert names["PRODUZIONE-v1.0.0"] == "alice"


def test_cache_expired_refetches(tmp_cache, sample_pr_data, monkeypatch):
    """Cache file più vecchio di CACHE_TTL_DAYS → re-fetch (invalidazione)."""
    import os, time as time_mod
    key = cg.cache_key("itsiae/sample", "2026-03-01", "2026-03-31")
    cache_file = tmp_cache / f"{key}.json"
    cache_file.write_text(json.dumps({"repository": {"nameWithOwner": "stale"}}))
    # Set mtime a 10 giorni fa
    old_time = time_mod.time() - (10 * 86400)
    os.utime(cache_file, (old_time, old_time))

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(sample_pr_data))
        data = cg.fetch_repo_data("itsiae/sample", "2026-03-01", "2026-03-31")

    assert mock_run.called, "Cache scaduta doveva triggerare re-fetch"
    assert data["repository"]["nameWithOwner"] != "stale"


def test_cache_fresh_hit_no_refetch(tmp_cache, sample_pr_data):
    """Cache file <= CACHE_TTL_DAYS → cache hit normale."""
    import os, time as time_mod
    key = cg.cache_key("itsiae/sample", "2026-03-01", "2026-03-31")
    cache_file = tmp_cache / f"{key}.json"
    cache_file.write_text(json.dumps(sample_pr_data))
    # mtime a 1 giorno fa (fresh)
    recent = time_mod.time() - 86400
    os.utime(cache_file, (recent, recent))

    with patch("subprocess.run") as mock_run:
        data = cg.fetch_repo_data("itsiae/sample", "2026-03-01", "2026-03-31")

    assert not mock_run.called
    assert data["repository"]["nameWithOwner"] == "itsiae/sample-repo"


def test_fetch_logs_warning_on_truncation(tmp_cache, caplog):
    """Se PR nodes count == 100, log WARNING su possibile truncation."""
    import logging
    truncated_data = {
        "repository": {
            "nameWithOwner": "itsiae/big-repo",
            "pullRequests": {"nodes": [{"number": i, "author": {"login": "x"},
                                        "createdAt": "2026-03-01T10:00:00Z",
                                        "mergedAt": "2026-03-01T14:00:00Z",
                                        "commits": {"nodes": []},
                                        "reviews": {"nodes": []},
                                        "files": {"nodes": []}, "body": ""}
                                       for i in range(100)]},
            "defaultBranchRef": {"target": {"history": {"nodes": []}}},
            "refs": {"nodes": []},
        }
    }
    with patch("subprocess.run") as mock_run, caplog.at_level(logging.WARNING):
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(truncated_data))
        cg.fetch_repo_data("itsiae/big-repo", "2026-03-01", "2026-03-31")
    assert any("truncat" in r.message.lower() or "page" in r.message.lower()
               for r in caplog.records), f"No truncation warning in: {[r.message for r in caplog.records]}"


def test_extract_deploy_tags_filters_non_siae_tags():
    """Tag non-SIAE ignorati (es. 'v1.0.0' da lib)."""
    raw = {
        "repository": {
            "nameWithOwner": "itsiae/r",
            "defaultBranchRef": {"target": {"history": {"nodes": []}}},
            "refs": {"nodes": [
                {"name": "v1.0.0", "target": {"oid": "abc"}},
                {"name": "release-1.2", "target": {"oid": "def"}},
                {"name": "COLLAUDO-v1", "target": {"oid": "ghi"}},
            ]},
        }
    }
    tags = cg.extract_deploy_tags(raw, [], [])
    assert len(tags) == 1
    assert tags[0]["tag_name"] == "COLLAUDO-v1"


# ────────────────────────────────────────────────────────
# Task 03: PR States — extract_pr_records v2 fields
# ────────────────────────────────────────────────────────

def test_extract_pr_records_all_states(sample_pr_data):
    """Happy path: fixture has MERGED/OPEN/DRAFT/CLOSED/REOPENED PRs, all extracted with v2 fields."""
    prs = cg.extract_pr_records(sample_pr_data)
    # Fixture has 9 PRs total: 5 MERGED + 1 OPEN + 1 DRAFT(OPEN) + 1 CLOSED + 1 REOPENED(OPEN)
    assert len(prs) == 9
    # All v2 fields present
    for pr in prs:
        assert "state" in pr, f"PR #{pr['number']} missing 'state'"
        assert "is_draft" in pr, f"PR #{pr['number']} missing 'is_draft'"
        assert "updated_at" in pr, f"PR #{pr['number']} missing 'updated_at'"
        assert "closed_at" in pr or pr["closed_at"] is None, f"PR #{pr['number']} missing 'closed_at'"
        assert "reopen_count" in pr, f"PR #{pr['number']} missing 'reopen_count'"
        assert "is_stuck" in pr, f"PR #{pr['number']} missing 'is_stuck'"


def test_extract_pr_records_open_state():
    """OPEN PR extracted with state=OPEN, is_draft=False."""
    raw = {
        "repository": {
            "nameWithOwner": "itsiae/repo",
            "pullRequests": {"nodes": [
                {
                    "number": 200,
                    "author": {"login": "alice"},
                    "createdAt": "2026-03-25T09:00:00Z",
                    "mergedAt": None,
                    "closedAt": None,
                    "updatedAt": "2026-03-25T10:00:00Z",
                    "state": "OPEN",
                    "isDraft": False,
                    "timelineItems": {"totalCount": 0},
                    "commits": {"nodes": [{"commit": {"committedDate": "2026-03-25T08:00:00Z"}}]},
                    "reviews": {"nodes": []},
                    "files": {"nodes": [{"path": "src/a.py", "additions": 10, "deletions": 0}]},
                    "body": "",
                }
            ]},
        }
    }
    prs = cg.extract_pr_records(raw)
    assert len(prs) == 1
    assert prs[0]["state"] == "OPEN"
    assert prs[0]["is_draft"] is False
    assert prs[0]["merged_at"] is None
    assert prs[0]["closed_at"] is None


def test_extract_pr_records_draft_state():
    """DRAFT PR extracted with is_draft=True."""
    raw = {
        "repository": {
            "nameWithOwner": "itsiae/repo",
            "pullRequests": {"nodes": [
                {
                    "number": 201,
                    "author": {"login": "bob"},
                    "createdAt": "2026-03-22T08:00:00Z",
                    "mergedAt": None,
                    "closedAt": None,
                    "updatedAt": "2026-03-22T09:00:00Z",
                    "state": "OPEN",
                    "isDraft": True,
                    "timelineItems": {"totalCount": 0},
                    "commits": {"nodes": [{"commit": {"committedDate": "2026-03-22T07:00:00Z"}}]},
                    "reviews": {"nodes": []},
                    "files": {"nodes": []},
                    "body": "",
                }
            ]},
        }
    }
    prs = cg.extract_pr_records(raw)
    assert len(prs) == 1
    assert prs[0]["state"] == "OPEN"
    assert prs[0]["is_draft"] is True


def test_extract_pr_records_closed_unmerged():
    """CLOSED PR (not merged) has state=CLOSED, merged_at=None, closed_at set."""
    raw = {
        "repository": {
            "nameWithOwner": "itsiae/repo",
            "pullRequests": {"nodes": [
                {
                    "number": 202,
                    "author": {"login": "carol"},
                    "createdAt": "2026-03-18T10:00:00Z",
                    "mergedAt": None,
                    "closedAt": "2026-03-19T12:00:00Z",
                    "updatedAt": "2026-03-19T12:00:00Z",
                    "state": "CLOSED",
                    "isDraft": False,
                    "timelineItems": {"totalCount": 0},
                    "commits": {"nodes": [{"commit": {"committedDate": "2026-03-18T09:00:00Z"}}]},
                    "reviews": {"nodes": []},
                    "files": {"nodes": []},
                    "body": "",
                }
            ]},
        }
    }
    prs = cg.extract_pr_records(raw)
    assert len(prs) == 1
    assert prs[0]["state"] == "CLOSED"
    assert prs[0]["merged_at"] is None
    assert prs[0]["closed_at"] is not None


# ────────────────────────────────────────────────────────
# Task 03: Fault injection NF9-NF17 (extended GraphQL query)
# ────────────────────────────────────────────────────────

def _make_all_states_response() -> dict:
    """Minimal valid response with all PR states for fault injection tests."""
    return {
        "data": {
            "repository": {
                "nameWithOwner": "itsiae/test",
                "pullRequests": {"nodes": [
                    {
                        "number": 1,
                        "author": {"login": "dev"},
                        "createdAt": "2026-03-01T10:00:00Z",
                        "mergedAt": "2026-03-01T14:00:00Z",
                        "closedAt": None,
                        "updatedAt": "2026-03-01T14:00:00Z",
                        "state": "MERGED",
                        "isDraft": False,
                        "timelineItems": {"totalCount": 0},
                        "commits": {"nodes": [{"commit": {"committedDate": "2026-03-01T09:00:00Z"}}]},
                        "reviews": {"nodes": []},
                        "files": {"nodes": []},
                        "body": "",
                    }
                ]},
                "defaultBranchRef": {"target": {"history": {"nodes": []}}},
                "refs": {"nodes": []},
            }
        }
    }


def test_nf9_success_all_states(tmp_cache):
    """NF9: Successful fetch with all-states query returns valid data."""
    resp = _make_all_states_response()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(resp))
        data = cg.fetch_repo_data("itsiae/test", "2026-03-01", "2026-03-31")
    assert "pullRequests" in data["repository"]
    prs = cg.extract_pr_records(data)
    assert len(prs) == 1
    assert prs[0]["state"] == "MERGED"


def test_nf10_timeout_all_states(tmp_cache):
    """NF10: Subprocess timeout raises RuntimeError."""
    import subprocess as sp
    with patch("subprocess.run", side_effect=sp.TimeoutExpired(cmd="gh", timeout=120)):
        with pytest.raises(sp.TimeoutExpired):
            cg.fetch_repo_data("itsiae/test", "2026-03-01", "2026-03-31")


def test_nf11_auth_401_all_states(tmp_cache):
    """NF11: 401 authentication error raises RuntimeError."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=4, stdout="", stderr="gh: authentication required")
        with pytest.raises(RuntimeError, match="authent"):
            cg.fetch_repo_data("itsiae/test", "2026-03-01", "2026-03-31")


def test_nf12_rate_limit_429_all_states(tmp_cache):
    """NF12: Rate limit triggers backoff retry."""
    resp = _make_all_states_response()
    responses = [
        MagicMock(returncode=1, stdout="", stderr="API rate limit exceeded"),
        MagicMock(returncode=0, stdout=json.dumps(resp)),
    ]
    with patch("subprocess.run", side_effect=responses), \
         patch("time.sleep") as mock_sleep:
        data = cg.fetch_repo_data("itsiae/test", "2026-03-01", "2026-03-31")
    assert mock_sleep.called
    assert data is not None


def test_nf13_rate_limit_secondary_all_states(tmp_cache):
    """NF13: Secondary rate limit (all retries exhausted) raises RuntimeError."""
    responses = [
        MagicMock(returncode=1, stdout="", stderr="secondary rate limit exceeded"),
        MagicMock(returncode=1, stdout="", stderr="secondary rate limit exceeded"),
        MagicMock(returncode=1, stdout="", stderr="secondary rate limit exceeded"),
    ]
    with patch("subprocess.run", side_effect=responses), \
         patch("time.sleep"):
        with pytest.raises(RuntimeError, match="failed after"):
            cg.fetch_repo_data("itsiae/test", "2026-03-01", "2026-03-31")


def test_nf14_not_found_404_all_states(tmp_cache):
    """NF14: Repo not found -> None with skip_on_error, RuntimeError otherwise."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Could not resolve to a Repository")
        result = cg.fetch_repo_data("itsiae/missing", "2026-03-01", "2026-03-31", skip_on_error=True)
    assert result is None

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="not found")
        with pytest.raises(RuntimeError):
            cg.fetch_repo_data("itsiae/missing", "2026-03-01", "2026-03-31")


def test_nf15_server_error_500_all_states(tmp_cache):
    """NF15: Server 500 error exhausts retries and raises RuntimeError."""
    responses = [
        MagicMock(returncode=1, stdout="", stderr="internal server error"),
        MagicMock(returncode=1, stdout="", stderr="internal server error"),
        MagicMock(returncode=1, stdout="", stderr="internal server error"),
    ]
    with patch("subprocess.run", side_effect=responses):
        with pytest.raises(RuntimeError, match="failed after"):
            cg.fetch_repo_data("itsiae/test", "2026-03-01", "2026-03-31")


def test_nf16_malformed_json_all_states(tmp_cache):
    """NF16: Malformed JSON in response raises error."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="{invalid json")
        with pytest.raises(json.JSONDecodeError):
            cg.fetch_repo_data("itsiae/test", "2026-03-01", "2026-03-31")


def test_nf17_empty_nodes_all_states(tmp_cache):
    """NF17: Empty PR nodes returns empty list from extract_pr_records."""
    empty_resp = {
        "data": {
            "repository": {
                "nameWithOwner": "itsiae/empty",
                "pullRequests": {"nodes": []},
                "defaultBranchRef": {"target": {"history": {"nodes": []}}},
                "refs": {"nodes": []},
            }
        }
    }
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(empty_resp))
        data = cg.fetch_repo_data("itsiae/empty", "2026-03-01", "2026-03-31")
    prs = cg.extract_pr_records(data)
    assert prs == []
