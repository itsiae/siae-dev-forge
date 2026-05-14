"""Tests for spotbugs runner (Java security via spotbugs + find-sec-bugs)."""
from __future__ import annotations

import shutil
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from lib.review_evidence.runners.spotbugs import SpotbugsRunner

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_is_applicable_maven(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    assert SpotbugsRunner().is_applicable(tmp_path) is True


def test_is_applicable_gradle(tmp_path):
    (tmp_path / "build.gradle").write_text("// gradle")
    assert SpotbugsRunner().is_applicable(tmp_path) is True


def test_not_applicable_non_java(tmp_path):
    assert SpotbugsRunner().is_applicable(tmp_path) is False


def test_run_parses_existing_report_priority_mapping(tmp_path):
    """Prefer pre-existing target/spotbugsXml.xml over invoking Maven."""
    (tmp_path / "pom.xml").write_text("<project/>")
    target = tmp_path / "target"
    target.mkdir()
    shutil.copy(FIX / "spotbugs_report.xml", target / "spotbugsXml.xml")
    # No subprocess invocation should happen on the fast path; assert via mock.
    with patch(
        "lib.review_evidence.runners.spotbugs.subprocess.run"
    ) as mock_run:
        result = SpotbugsRunner().run(tmp_path)
        mock_run.assert_not_called()
    assert result is not None
    # fixture: priority 1 -> critical, 2 -> high, 3 -> medium, 4 -> low
    assert result.critical == 1
    assert result.high == 1
    assert result.medium == 1
    assert result.low == 1


def test_run_missing_mvn_returns_none(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")

    def fake_run(cmd, **kw):
        raise FileNotFoundError("mvn")

    with patch(
        "lib.review_evidence.runners.spotbugs.subprocess.run", side_effect=fake_run
    ):
        assert SpotbugsRunner().run(tmp_path) is None
