"""Tests for ktlint runner (Kotlin formatter/linter)."""
from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from lib.review_evidence.runners.ktlint import KtlintRunner

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_is_applicable_with_kotlin_file(tmp_path):
    (tmp_path / "App.kt").write_text("package foo\n")
    assert KtlintRunner().is_applicable(tmp_path) is True


def test_not_applicable_non_kotlin_repo(tmp_path):
    (tmp_path / "README.md").write_text("hi")
    assert KtlintRunner().is_applicable(tmp_path) is False


def test_run_counts_all_errors_as_lint_errors(tmp_path):
    (tmp_path / "App.kt").write_text("package foo\n")
    out = (FIX / "ktlint_output.json").read_text()

    def fake_run(cmd, **kw):
        return CompletedProcess(cmd, 1, stdout=out, stderr="")

    with patch(
        "lib.review_evidence.runners.ktlint.subprocess.run", side_effect=fake_run
    ):
        result = KtlintRunner().run(tmp_path)
    assert result is not None
    # fixture: 3 errors in Login.kt + 1 in Profile.kt = 4
    assert result.lint_errors == 4
    assert result.type_errors == 0
    assert result.dead_code_blocks == 0


def test_run_missing_tool_returns_none(tmp_path):
    (tmp_path / "App.kt").write_text("")

    def fake_run(cmd, **kw):
        raise FileNotFoundError("ktlint")

    with patch(
        "lib.review_evidence.runners.ktlint.subprocess.run", side_effect=fake_run
    ):
        assert KtlintRunner().run(tmp_path) is None
