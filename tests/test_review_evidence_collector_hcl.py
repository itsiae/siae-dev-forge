"""Tests for HCL collector."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from lib.review_evidence.collectors.hcl import HCLCollector

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_is_applicable_tf_file(tmp_path):
    (tmp_path / "main.tf").write_text("# tf")
    assert HCLCollector().is_applicable(tmp_path) is True


def test_not_applicable_otherwise(tmp_path):
    (tmp_path / "README.md").write_text("md")
    assert HCLCollector().is_applicable(tmp_path) is False


def test_collect_with_tflint_and_validate(tmp_path):
    (tmp_path / "main.tf").write_text("# tf")
    tflint_out = (FIX / "tflint_output.json").read_text()
    tfval_out = (FIX / "terraform_validate.json").read_text()

    def fake_run(cmd, **kwargs):
        from subprocess import CompletedProcess
        if cmd[0] == "tflint":
            return CompletedProcess(cmd, 0, stdout=tflint_out, stderr="")
        if cmd[0] == "terraform" and "validate" in cmd:
            return CompletedProcess(cmd, 0, stdout=tfval_out, stderr="")
        return CompletedProcess(cmd, 1, stdout="", stderr="?")

    with patch("lib.review_evidence.collectors.hcl.subprocess.run", side_effect=fake_run):
        result = HCLCollector().collect(tmp_path, "main", "HEAD")

    assert result["stack"] == "hcl"
    assert result["coverage"] is None  # HCL doesn't have coverage
    # 1 tflint error + 1 terraform validate error = 2 errors
    assert result["lint"]["errors"] == 2
    assert result["lint"]["warnings"] == 1  # 1 tflint warning
    assert "tflint" in result["lint"]["source"]
    assert "terraform" in result["lint"]["source"]


def test_collect_missing_tools_returns_lint_none(tmp_path):
    (tmp_path / "main.tf").write_text("# tf")

    def fake_run(cmd, **kwargs):
        raise FileNotFoundError(cmd[0])

    with patch("lib.review_evidence.collectors.hcl.subprocess.run", side_effect=fake_run):
        result = HCLCollector().collect(tmp_path, "main", "HEAD")
    assert result["lint"] is None
