"""Tests for pyright runner (Python type errors)."""
from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from lib.review_evidence.runners.pyright import PyrightRunner

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_is_applicable_pyrightconfig(tmp_path):
    (tmp_path / "pyrightconfig.json").write_text("{}")
    assert PyrightRunner().is_applicable(tmp_path) is True


def test_is_applicable_pyproject_tool_pyright(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.pyright]\nstrict = []\n")
    assert PyrightRunner().is_applicable(tmp_path) is True


def test_not_applicable_python_repo_without_pyright_config(tmp_path):
    # pyproject without [tool.pyright] section -> opt-in only
    (tmp_path / "pyproject.toml").write_text("[tool.poetry]\nname = 'x'\n")
    assert PyrightRunner().is_applicable(tmp_path) is False


def test_run_parses_error_and_warning_counts(tmp_path):
    (tmp_path / "pyrightconfig.json").write_text("{}")
    out = (FIX / "pyright_output.json").read_text()

    def fake_run(cmd, **kw):
        return CompletedProcess(cmd, 1, stdout=out, stderr="")

    with patch(
        "lib.review_evidence.runners.pyright.subprocess.run", side_effect=fake_run
    ):
        result = PyrightRunner().run(tmp_path)
    assert result is not None
    # fixture: errorCount=2, warningCount=1
    assert result.type_errors == 2
    assert result.lint_errors == 1
    assert result.dead_code_blocks == 0


def test_run_missing_tool_returns_none(tmp_path):
    (tmp_path / "pyrightconfig.json").write_text("{}")

    def fake_run(cmd, **kw):
        raise FileNotFoundError("pyright")

    with patch(
        "lib.review_evidence.runners.pyright.subprocess.run", side_effect=fake_run
    ):
        assert PyrightRunner().run(tmp_path) is None
