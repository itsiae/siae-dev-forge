"""Tests for mvn-deps (OWASP dependency-check) runner."""
from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from lib.review_evidence.runners.mvn_deps import MvnDepsRunner

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_is_applicable_pom_xml(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    assert MvnDepsRunner().is_applicable(tmp_path) is True


def test_not_applicable_without_pom(tmp_path):
    assert MvnDepsRunner().is_applicable(tmp_path) is False


def test_run_returns_none_when_report_missing(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    # No target/dependency-check-report.json -> short-circuit None.
    assert MvnDepsRunner().run(tmp_path) is None


def test_run_parses_severities_from_fixture(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    target = tmp_path / "target"
    target.mkdir()
    report_path = target / "dependency-check-report.json"
    payload = (FIX / "mvn_deps_output.json").read_text()
    report_path.write_text(payload)

    def fake_run(cmd, **kw):
        return CompletedProcess(cmd, 0, stdout=payload, stderr="")

    with patch(
        "lib.review_evidence.runners.mvn_deps.subprocess.run", side_effect=fake_run
    ):
        result = MvnDepsRunner().run(tmp_path)
    assert result is not None
    assert result.critical == 1
    assert result.high == 1
    assert result.medium == 1
    assert result.low == 1
