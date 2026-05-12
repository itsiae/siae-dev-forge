"""Tests for TypeScript collector."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from lib.review_evidence.collectors.typescript import TypeScriptCollector
from lib.review_evidence.collectors._lcov import parse_lcov

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_parse_lcov_aggregates_line_hit():
    lcov = (FIX / "lcov.info").read_text()
    parsed = parse_lcov(lcov)
    assert parsed["total_lines"] == 70
    assert parsed["hit_lines"] == 52
    assert round(parsed["pct"], 1) == 74.3
    assert len(parsed["per_file"]) == 2


def test_is_applicable_package_json_with_ts(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"typescript": "5"}}))
    assert TypeScriptCollector().is_applicable(tmp_path) is True


def test_is_applicable_ts_files(tmp_path):
    (tmp_path / "main.ts").write_text("export {}")
    assert TypeScriptCollector().is_applicable(tmp_path) is True


def test_not_applicable_plain_js_only(tmp_path):
    (tmp_path / "main.js").write_text("// js")
    # No package.json, no .ts — should be False (collector è TS-first)
    assert TypeScriptCollector().is_applicable(tmp_path) is False


def test_collect_with_lcov_and_eslint(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"typescript": "5"}}))
    cov_dir = tmp_path / "coverage"
    cov_dir.mkdir()
    (cov_dir / "lcov.info").write_text((FIX / "lcov.info").read_text())

    eslint_out = (FIX / "eslint_output.json").read_text()

    def fake_run(cmd, **kwargs):
        from subprocess import CompletedProcess
        if "eslint" in " ".join(cmd):
            return CompletedProcess(cmd, 0, stdout=eslint_out, stderr="")
        # complexity-report missing
        raise FileNotFoundError(cmd[0])

    with patch("lib.review_evidence.collectors.typescript.subprocess.run", side_effect=fake_run):
        result = TypeScriptCollector().collect(tmp_path, "main", "HEAD")

    assert result["stack"] == "typescript"
    assert round(result["coverage"]["overall_pct"], 1) == 74.3
    assert result["coverage"]["source"] == "local:lcov"
    assert result["lint"]["errors"] == 1
    assert result["lint"]["warnings"] == 1
    assert result["lint"]["source"] == "local:eslint"
    # complexity-report missing → complexity is None
    assert result["complexity"] is None or result["complexity"].get("source") is None


def test_collect_missing_lcov_returns_none_coverage(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"typescript": "5"}}))

    def fake_run(cmd, **kwargs):
        raise FileNotFoundError(cmd[0])

    with patch("lib.review_evidence.collectors.typescript.subprocess.run", side_effect=fake_run):
        result = TypeScriptCollector().collect(tmp_path, "main", "HEAD")
    assert result["coverage"] is None
