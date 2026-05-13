"""Tests for checkov runner."""
from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from lib.review_evidence.runners.checkov import CheckovRunner

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_is_applicable_with_tf(tmp_path):
    (tmp_path / "main.tf").write_text("")
    assert CheckovRunner().is_applicable(tmp_path) is True


def test_is_applicable_with_dockerfile(tmp_path):
    (tmp_path / "Dockerfile").write_text("FROM alpine:3.18")
    assert CheckovRunner().is_applicable(tmp_path) is True


def test_not_applicable_without_iac(tmp_path):
    # Only a stray text file -> no Terraform, no YAML, no Dockerfile.
    (tmp_path / "README.md").write_text("hello")
    assert CheckovRunner().is_applicable(tmp_path) is False


def test_run_parses_severities_info_collapses_to_low(tmp_path):
    (tmp_path / "main.tf").write_text("")
    out = (FIX / "checkov_output.json").read_text()

    def fake_run(cmd, **kw):
        # checkov exits 1 when findings present, but JSON is on stdout.
        return CompletedProcess(cmd, 1, stdout=out, stderr="")

    with patch(
        "lib.review_evidence.runners.checkov.subprocess.run", side_effect=fake_run
    ):
        result = CheckovRunner().run(tmp_path)
    assert result is not None
    assert result.critical == 1
    assert result.high == 1
    assert result.medium == 1
    # LOW + INFO -> both collapse to `low`
    assert result.low == 2
