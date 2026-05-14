"""Tests for swiftlint runner (iOS Swift quality + security)."""
from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from lib.review_evidence.runners.swiftlint import SwiftlintRunner

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_is_applicable_with_swift_file(tmp_path):
    (tmp_path / "App.swift").write_text("import Foundation\n")
    assert SwiftlintRunner().is_applicable(tmp_path) is True


def test_is_applicable_with_package_swift(tmp_path):
    (tmp_path / "Package.swift").write_text("// swift-tools-version:5.5\n")
    assert SwiftlintRunner().is_applicable(tmp_path) is True


def test_not_applicable_non_swift_repo(tmp_path):
    (tmp_path / "README.md").write_text("hi")
    assert SwiftlintRunner().is_applicable(tmp_path) is False


def test_run_parses_severities_from_fixture(tmp_path):
    (tmp_path / "App.swift").write_text("import Foundation\n")
    out = (FIX / "swiftlint_output.json").read_text()

    def fake_run(cmd, **kw):
        return CompletedProcess(cmd, 0, stdout=out, stderr="")

    with patch(
        "lib.review_evidence.runners.swiftlint.subprocess.run", side_effect=fake_run
    ):
        result = SwiftlintRunner().run(tmp_path)
    assert result is not None
    # fixture: 2 error -> high, 3 warning -> medium
    assert result.high == 2
    assert result.medium == 3
    assert result.critical == 0
    assert result.low == 0


def test_run_missing_tool_returns_none(tmp_path):
    (tmp_path / "App.swift").write_text("")

    def fake_run(cmd, **kw):
        raise FileNotFoundError("swiftlint")

    with patch(
        "lib.review_evidence.runners.swiftlint.subprocess.run", side_effect=fake_run
    ):
        assert SwiftlintRunner().run(tmp_path) is None
