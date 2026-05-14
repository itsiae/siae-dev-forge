from unittest.mock import patch
from pathlib import Path
import pytest
from lib.release_risk.genesis import (
    extract_merge_commits, evaluate_criterion_18, build_genesis_info,
    FEATURE_BRANCH_PATTERN,
)
from lib.release_risk.schema import GenesisInfo


def test_no_merges_found(tmp_path):
    gi = GenesisInfo(merge_commits=[], no_merges_found=True)
    r = evaluate_criterion_18(gi)
    assert r.status == "NO"
    assert "linearly" in r.evidence[0]


def test_declined_returns_requires_input(tmp_path):
    gi = GenesisInfo(merge_commits=[{"sha": "abc", "subject": "..."}], declined=True)
    r = evaluate_criterion_18(gi)
    assert r.status == "REQUIRES_INPUT"
    assert "user declined" in r.evidence[0]


def test_all_confirmed_returns_no(tmp_path):
    merge_commits = [{"sha": "abc", "subject": "Merge", "feature_branch": "f1"}]
    gi = build_genesis_info(merge_commits, user_confirmed=["f1"])
    assert gi.anomaly is False
    r = evaluate_criterion_18(gi)
    assert r.status == "NO"


def test_partial_confirmed_anomaly_yes(tmp_path):
    merge_commits = [
        {"sha": "abc", "subject": "Merge", "feature_branch": "feature/x"},
        {"sha": "def", "subject": "Merge", "feature_branch": "feature/y"},
    ]
    gi = build_genesis_info(merge_commits, user_confirmed=["feature/x"])
    assert gi.anomaly is True
    assert "feature/y" in gi.unexpected
    r = evaluate_criterion_18(gi)
    assert r.status == "YES"
    assert r.weight == 2


def test_parser_regex_branch_format():
    m = FEATURE_BRANCH_PATTERN.search("Merge branch 'feature/users' into main")
    assert m
    assert m.group(1) == "feature/users"


def test_parser_regex_pull_request_format():
    m = FEATURE_BRANCH_PATTERN.search("Merge pull request #42 from itsiae/feature/billing")
    assert m
    assert m.group(1) == "feature/billing"


def test_parser_regex_remote_tracking_format():
    m = FEATURE_BRANCH_PATTERN.search("Merge remote-tracking branch 'origin/feature/payments' into main")
    assert m
    assert m.group(1) == "origin/feature/payments"


def test_extract_merge_commits_subprocess_error(tmp_path):
    import subprocess
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")):
        commits = extract_merge_commits(tmp_path, "release/1.0.0")
        assert commits == []


def test_extract_merge_commits_parses_output(tmp_path):
    mock_output = (
        "abc123|Merge branch 'feature/users' into release/2.0.0\n"
        "def456|Merge pull request #99 from itsiae/feature/billing"
    )
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = mock_output
        mock_run.return_value.returncode = 0
        commits = extract_merge_commits(tmp_path, "release/2.0.0")
        assert len(commits) == 2
        assert commits[0]["sha"] == "abc123"
        assert commits[0]["feature_branch"] == "feature/users"
        assert commits[1]["feature_branch"] == "feature/billing"
