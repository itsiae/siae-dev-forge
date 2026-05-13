"""Tests for pip-audit runner."""
from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from lib.review_evidence.runners.pip_audit import PipAuditRunner

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_is_applicable_requirements_txt(tmp_path):
    (tmp_path / "requirements.txt").write_text("django==3.2.0")
    assert PipAuditRunner().is_applicable(tmp_path) is True


def test_is_applicable_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool]")
    assert PipAuditRunner().is_applicable(tmp_path) is True


def test_not_applicable_non_python(tmp_path):
    assert PipAuditRunner().is_applicable(tmp_path) is False


def test_run_parses_severities(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool]")
    out = (FIX / "pip_audit_output.json").read_text()

    def fake_run(cmd, **kw):
        # pip-audit exits 1 when vulns are found, but stdout has the JSON
        return CompletedProcess(cmd, 1, stdout=out, stderr="")

    with patch(
        "lib.review_evidence.runners.pip_audit.subprocess.run", side_effect=fake_run
    ):
        result = PipAuditRunner().run(tmp_path)
    assert result is not None
    assert result.critical == 0
    assert result.high == 1
    assert result.medium == 1
    assert result.low == 0


def test_run_missing_tool_returns_none(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool]")

    def fake_run(cmd, **kw):
        raise FileNotFoundError("pip-audit")

    with patch(
        "lib.review_evidence.runners.pip_audit.subprocess.run", side_effect=fake_run
    ):
        assert PipAuditRunner().run(tmp_path) is None
