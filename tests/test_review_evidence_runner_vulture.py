"""Tests for vulture runner (Python dead code)."""
from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from lib.review_evidence.runners.vulture import VultureRunner

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_is_applicable_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool]")
    assert VultureRunner().is_applicable(tmp_path) is True


def test_is_applicable_python_file(tmp_path):
    (tmp_path / "main.py").write_text("x = 1\n")
    assert VultureRunner().is_applicable(tmp_path) is True


def test_not_applicable_non_python(tmp_path):
    assert VultureRunner().is_applicable(tmp_path) is False


def test_run_parses_findings_to_dead_code_blocks(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool]")
    out = (FIX / "vulture_output.txt").read_text()

    def fake_run(cmd, **kw):
        # vulture exits 3 when findings exist
        return CompletedProcess(cmd, 3, stdout=out, stderr="")

    with patch(
        "lib.review_evidence.runners.vulture.subprocess.run", side_effect=fake_run
    ):
        result = VultureRunner().run(tmp_path)
    assert result is not None
    # fixture has 3 finding lines, all map to dead_code_blocks
    assert result.dead_code_blocks == 3
    assert result.lint_errors == 0
    assert result.type_errors == 0


def test_run_no_findings(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool]")

    def fake_run(cmd, **kw):
        return CompletedProcess(cmd, 0, stdout="", stderr="")

    with patch(
        "lib.review_evidence.runners.vulture.subprocess.run", side_effect=fake_run
    ):
        result = VultureRunner().run(tmp_path)
    assert result is not None
    assert result.dead_code_blocks == 0


def test_run_missing_tool_returns_none(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool]")

    def fake_run(cmd, **kw):
        raise FileNotFoundError("vulture")

    with patch(
        "lib.review_evidence.runners.vulture.subprocess.run", side_effect=fake_run
    ):
        assert VultureRunner().run(tmp_path) is None
