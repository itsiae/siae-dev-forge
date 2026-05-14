"""Tests for cfn-lint runner (AWS CloudFormation security/correctness)."""
from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from lib.review_evidence.runners.cfn_lint import CfnLintRunner

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_is_applicable_yaml_with_aws_template_marker(tmp_path):
    (tmp_path / "api.yml").write_text(
        "AWSTemplateFormatVersion: '2010-09-09'\nResources:\n  Bucket:\n    Type: AWS::S3::Bucket\n"
    )
    assert CfnLintRunner().is_applicable(tmp_path) is True


def test_is_applicable_yaml_with_resources_top_level(tmp_path):
    (tmp_path / "stack.yml").write_text(
        "Resources:\n  Q:\n    Type: AWS::SQS::Queue\n"
    )
    assert CfnLintRunner().is_applicable(tmp_path) is True


def test_not_applicable_generic_yaml(tmp_path):
    (tmp_path / "ci.yml").write_text("name: build\nsteps:\n  - run: echo hi\n")
    assert CfnLintRunner().is_applicable(tmp_path) is False


def test_run_parses_severities_from_fixture(tmp_path):
    (tmp_path / "api.yml").write_text(
        "AWSTemplateFormatVersion: '2010-09-09'\nResources:\n  Q:\n    Type: AWS::SQS::Queue\n"
    )
    out = (FIX / "cfn_lint_output.json").read_text()

    def fake_run(cmd, **kw):
        return CompletedProcess(cmd, 1, stdout=out, stderr="")

    with patch(
        "lib.review_evidence.runners.cfn_lint.subprocess.run", side_effect=fake_run
    ):
        result = CfnLintRunner().run(tmp_path)
    assert result is not None
    # fixture: 2 Error -> high, 1 Warning -> medium, 1 Informational -> low
    assert result.high == 2
    assert result.medium == 1
    assert result.low == 1
    assert result.critical == 0


def test_run_missing_tool_returns_none(tmp_path):
    (tmp_path / "api.yml").write_text(
        "AWSTemplateFormatVersion: '2010-09-09'\nResources: {}\n"
    )

    def fake_run(cmd, **kw):
        raise FileNotFoundError("cfn-lint")

    with patch(
        "lib.review_evidence.runners.cfn_lint.subprocess.run", side_effect=fake_run
    ):
        assert CfnLintRunner().run(tmp_path) is None
