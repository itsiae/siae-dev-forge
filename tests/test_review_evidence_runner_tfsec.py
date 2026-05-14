"""Tests for tfsec runner."""
from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from lib.review_evidence.runners.tfsec import TfsecRunner

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_is_applicable_with_tf_files(tmp_path):
    (tmp_path / "main.tf").write_text('resource "aws_s3_bucket" "demo" {}')
    assert TfsecRunner().is_applicable(tmp_path) is True


def test_not_applicable_without_tf(tmp_path):
    assert TfsecRunner().is_applicable(tmp_path) is False


def test_run_parses_severities_from_fixture(tmp_path):
    (tmp_path / "main.tf").write_text('resource "aws_s3_bucket" "demo" {}')
    out = (FIX / "tfsec_output.json").read_text()

    def fake_run(cmd, **kw):
        return CompletedProcess(cmd, 1, stdout=out, stderr="")

    with patch(
        "lib.review_evidence.runners.tfsec.subprocess.run", side_effect=fake_run
    ):
        result = TfsecRunner().run(tmp_path)
    assert result is not None
    assert result.critical == 1
    assert result.high == 1
    assert result.medium == 1
    # LOW + UNKNOWN both bucketed into `low`
    assert result.low == 2


def test_run_missing_tool_returns_none(tmp_path):
    (tmp_path / "main.tf").write_text("")

    def fake_run(cmd, **kw):
        raise FileNotFoundError("tfsec")

    with patch(
        "lib.review_evidence.runners.tfsec.subprocess.run", side_effect=fake_run
    ):
        assert TfsecRunner().run(tmp_path) is None
