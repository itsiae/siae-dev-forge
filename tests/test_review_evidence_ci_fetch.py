"""Tests for CI-fetch SARIF parser + gh run download orchestration."""
import json
from pathlib import Path
from unittest.mock import patch


from lib.review_evidence._sarif import parse_sarif, aggregate_sarif_dir
from lib.review_evidence.ci_fetch import fetch_ci_sarif

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_parse_qodana_sarif():
    parsed = parse_sarif((FIX / "qodana_sample.sarif").read_text())
    assert parsed["tool_name"] == "Qodana"
    assert parsed["problems_critical"] == 1
    assert parsed["problems_high"] == 1
    assert len(parsed["findings"]) == 2


def test_parse_sonar_sarif():
    parsed = parse_sarif((FIX / "sonar_sample.sarif").read_text())
    assert parsed["tool_name"] == "SonarQube"
    assert parsed["problems_critical"] == 1
    assert parsed["problems_high"] == 0


def test_parse_codeql_sarif():
    parsed = parse_sarif((FIX / "codeql_sample.sarif").read_text())
    assert parsed["tool_name"] == "CodeQL"
    assert parsed["problems_critical"] == 1
    # level=note → not counted as critical/high (informational)
    assert parsed["problems_high"] == 0


def test_aggregate_sarif_dir(tmp_path):
    (tmp_path / "qodana.sarif").write_text((FIX / "qodana_sample.sarif").read_text())
    (tmp_path / "sonar.sarif").write_text((FIX / "sonar_sample.sarif").read_text())

    agg = aggregate_sarif_dir(tmp_path)
    assert agg["problems_critical"] == 2  # 1 qodana + 1 sonar
    assert agg["problems_high"] == 1      # 1 qodana
    assert "Qodana" in agg["source"]
    assert "SonarQube" in agg["source"]


def test_fetch_ci_sarif_no_runs(tmp_path):
    def fake_run(cmd, **kwargs):
        from subprocess import CompletedProcess
        if cmd[0] == "gh" and "list" in cmd:
            return CompletedProcess(cmd, 0, stdout="[]", stderr="")
        return CompletedProcess(cmd, 1, stdout="", stderr="?")

    with patch("lib.review_evidence.ci_fetch.subprocess.run", side_effect=fake_run):
        result = fetch_ci_sarif(sha="abc123", repo_root=tmp_path)
    assert result["available"] is False
    assert "no completed" in result["reason"].lower() or "no runs" in result["reason"].lower()


def test_fetch_ci_sarif_with_download(tmp_path, monkeypatch):
    runs_listing = json.dumps([
        {"databaseId": 9876, "workflowName": "Qodana", "conclusion": "success"}
    ])

    def fake_run(cmd, **kwargs):
        from subprocess import CompletedProcess
        if cmd[0] == "gh" and "list" in cmd:
            return CompletedProcess(cmd, 0, stdout=runs_listing, stderr="")
        if cmd[0] == "gh" and "download" in cmd:
            # Simulate gh run download placing a sarif file in --dir
            dl_dir = Path(cmd[cmd.index("--dir") + 1])
            dl_dir.mkdir(parents=True, exist_ok=True)
            (dl_dir / "qodana.sarif").write_text((FIX / "qodana_sample.sarif").read_text())
            return CompletedProcess(cmd, 0, stdout="", stderr="")
        return CompletedProcess(cmd, 1, stdout="", stderr="?")

    with patch("lib.review_evidence.ci_fetch.subprocess.run", side_effect=fake_run):
        result = fetch_ci_sarif(sha="abc123", repo_root=tmp_path)

    assert result["available"] is True
    assert result["problems_critical"] == 1
    assert result["problems_high"] == 1
    assert "qodana" in result["source"].lower()


def test_fetch_ci_sarif_gh_missing(tmp_path):
    def fake_run(cmd, **kwargs):
        raise FileNotFoundError("gh")

    with patch("lib.review_evidence.ci_fetch.subprocess.run", side_effect=fake_run):
        result = fetch_ci_sarif(sha="abc", repo_root=tmp_path)
    assert result["available"] is False
    assert "gh" in result["reason"].lower()
