"""Tests for bandit runner."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from lib.review_evidence.runners.bandit import BanditRunner

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_is_applicable_python_repo(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool]")
    assert BanditRunner().is_applicable(tmp_path) is True


def test_not_applicable_non_python(tmp_path):
    assert BanditRunner().is_applicable(tmp_path) is False


def test_run_parses_severities(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool]")
    bandit_out = (FIX / "bandit_output.json").read_text()

    def fake_run(cmd, **kw):
        from subprocess import CompletedProcess

        return CompletedProcess(cmd, 0, stdout=bandit_out, stderr="")

    with patch("lib.review_evidence.runners.bandit.subprocess.run", side_effect=fake_run):
        result = BanditRunner().run(tmp_path)
    assert result.high == 1
    assert result.medium == 2
    assert result.low == 0
    assert result.critical == 0


def test_run_missing_bandit_returns_none(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool]")

    def fake_run(cmd, **kw):
        raise FileNotFoundError("bandit")

    with patch("lib.review_evidence.runners.bandit.subprocess.run", side_effect=fake_run):
        assert BanditRunner().run(tmp_path) is None
