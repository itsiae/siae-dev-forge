"""Tests for eslint-security runner."""
from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from lib.review_evidence.runners.eslint_security import EslintSecurityRunner

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_is_applicable_node_with_js(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "index.js").write_text("console.log('x');")
    assert EslintSecurityRunner().is_applicable(tmp_path) is True


def test_is_applicable_node_with_ts(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "main.ts").write_text("const x = 1;")
    assert EslintSecurityRunner().is_applicable(tmp_path) is True


def test_not_applicable_node_without_sources(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    assert EslintSecurityRunner().is_applicable(tmp_path) is False


def test_run_maps_errors_to_high_warnings_to_medium(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "main.js").write_text("eval('x')")
    out = (FIX / "eslint_security_output.json").read_text()

    def fake_run(cmd, **kw):
        return CompletedProcess(cmd, 1, stdout=out, stderr="")

    with patch(
        "lib.review_evidence.runners.eslint_security.subprocess.run",
        side_effect=fake_run,
    ):
        result = EslintSecurityRunner().run(tmp_path)
    assert result is not None
    # fixture: errorCount totals = 1, warningCount totals = 2
    assert result.high == 1
    assert result.medium == 2
    assert result.critical == 0


def test_run_missing_tool_returns_none(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "main.js").write_text("const x = 1;")

    def fake_run(cmd, **kw):
        raise FileNotFoundError("npx")

    with patch(
        "lib.review_evidence.runners.eslint_security.subprocess.run",
        side_effect=fake_run,
    ):
        assert EslintSecurityRunner().run(tmp_path) is None
