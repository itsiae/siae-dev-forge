"""Tests for npm-audit runner."""
from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from lib.review_evidence.runners.npm_audit import NpmAuditRunner

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_is_applicable_package_json(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    assert NpmAuditRunner().is_applicable(tmp_path) is True


def test_not_applicable_non_node(tmp_path):
    assert NpmAuditRunner().is_applicable(tmp_path) is False


def test_run_maps_moderate_to_medium(tmp_path):
    """npm audit emits 'moderate' but SecurityFindings uses 'medium'."""
    (tmp_path / "package.json").write_text("{}")
    payload = {
        "metadata": {
            "vulnerabilities": {
                "critical": 0,
                "high": 0,
                "moderate": 3,
                "low": 1,
                "info": 0,
                "total": 4,
            }
        }
    }
    import json as _json

    def fake_run(cmd, **kw):
        return CompletedProcess(cmd, 1, stdout=_json.dumps(payload), stderr="")

    with patch(
        "lib.review_evidence.runners.npm_audit.subprocess.run", side_effect=fake_run
    ):
        result = NpmAuditRunner().run(tmp_path)
    assert result is not None
    assert result.medium == 3
    assert result.low == 1
    assert result.critical == 0
    assert result.high == 0


def test_run_parses_severities_from_fixture(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    out = (FIX / "npm_audit_output.json").read_text()

    def fake_run(cmd, **kw):
        return CompletedProcess(cmd, 1, stdout=out, stderr="")

    with patch(
        "lib.review_evidence.runners.npm_audit.subprocess.run", side_effect=fake_run
    ):
        result = NpmAuditRunner().run(tmp_path)
    assert result is not None
    assert result.critical == 1
    assert result.high == 1
    assert result.medium == 0
    assert result.low == 0


def test_run_missing_tool_returns_none(tmp_path):
    (tmp_path / "package.json").write_text("{}")

    def fake_run(cmd, **kw):
        raise FileNotFoundError("npm")

    with patch(
        "lib.review_evidence.runners.npm_audit.subprocess.run", side_effect=fake_run
    ):
        assert NpmAuditRunner().run(tmp_path) is None
