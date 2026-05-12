"""Tests for Python collector."""
import json
from pathlib import Path
from unittest.mock import patch
import pytest

from lib.review_evidence.collectors.python import PythonCollector

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_is_applicable_when_pyproject_present(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool]")
    c = PythonCollector()
    assert c.is_applicable(tmp_path) is True


def test_is_applicable_when_py_files(tmp_path):
    (tmp_path / "main.py").write_text("# py")
    c = PythonCollector()
    assert c.is_applicable(tmp_path) is True


def test_not_applicable_otherwise(tmp_path):
    (tmp_path / "README.md").write_text("md")
    c = PythonCollector()
    assert c.is_applicable(tmp_path) is False


def test_collect_parses_coverage_ruff_radon(tmp_path):
    cov = (FIX / "coverage_python.json").read_text()
    ruff = (FIX / "ruff_output.json").read_text()
    radon = (FIX / "radon_cc.json").read_text()

    def fake_run(cmd, **kwargs):
        from subprocess import CompletedProcess
        if "coverage" in cmd[0] or "coverage" in (cmd[1] if len(cmd) > 1 else ""):
            return CompletedProcess(cmd, 0, stdout=cov, stderr="")
        if "ruff" in cmd[0]:
            return CompletedProcess(cmd, 0, stdout=ruff, stderr="")
        if "radon" in cmd[0]:
            return CompletedProcess(cmd, 0, stdout=radon, stderr="")
        return CompletedProcess(cmd, 1, stdout="", stderr="not found")

    (tmp_path / "pyproject.toml").write_text("[tool]")
    with patch("lib.review_evidence.collectors.python.subprocess.run", side_effect=fake_run):
        c = PythonCollector()
        result = c.collect(tmp_path, "main", "HEAD")

    assert result["stack"] == "python"
    assert result["coverage"]["overall_pct"] == 65.0
    assert result["coverage"]["source"] == "local:coverage.py"
    assert result["lint"]["errors"] + result["lint"]["warnings"] == 2
    assert result["lint"]["source"] == "local:ruff"
    assert result["complexity"]["max_cyclomatic"] == 22
    assert any(f["function"] == "process" for f in result["complexity"]["files_over_threshold"])


def test_collect_handles_missing_tools(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool]")

    def fake_run(cmd, **kwargs):
        raise FileNotFoundError(f"missing: {cmd[0]}")

    with patch("lib.review_evidence.collectors.python.subprocess.run", side_effect=fake_run):
        c = PythonCollector()
        result = c.collect(tmp_path, "main", "HEAD")

    assert result["stack"] == "python"
    # Each metric block reports availability flag
    assert result["coverage"] in (None, {}) or result["coverage"].get("overall_pct") in (None, 0.0)
    # Should not raise
