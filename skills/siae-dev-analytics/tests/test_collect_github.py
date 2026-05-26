"""Test per collect_github.py."""
from __future__ import annotations

import json
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
