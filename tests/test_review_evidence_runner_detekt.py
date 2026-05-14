"""Tests for detekt runner (Android/Kotlin static analysis)."""
from __future__ import annotations

import shutil
from pathlib import Path

from lib.review_evidence.runners.detekt import DetektRunner

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_is_applicable_with_kotlin_file(tmp_path):
    (tmp_path / "App.kt").write_text("package foo\n")
    assert DetektRunner().is_applicable(tmp_path) is True


def test_is_applicable_with_detekt_plugin_in_gradle_kts(tmp_path):
    (tmp_path / "build.gradle.kts").write_text(
        'plugins {\n    id("io.gitlab.arturbosch.detekt") version "1.23.0"\n}\n'
    )
    assert DetektRunner().is_applicable(tmp_path) is True


def test_not_applicable_non_kotlin_repo(tmp_path):
    (tmp_path / "README.md").write_text("hi")
    assert DetektRunner().is_applicable(tmp_path) is False


def test_run_parses_existing_xml_report(tmp_path):
    (tmp_path / "App.kt").write_text("package foo\n")
    report_dir = tmp_path / "build" / "reports" / "detekt"
    report_dir.mkdir(parents=True)
    shutil.copy(FIX / "detekt_report.xml", report_dir / "detekt.xml")
    result = DetektRunner().run(tmp_path)
    assert result is not None
    # fixture: 1 error + 2 warning + 1 info -> all into lint_errors
    assert result.lint_errors == 4


def test_run_missing_report_returns_none(tmp_path):
    (tmp_path / "App.kt").write_text("package foo\n")
    assert DetektRunner().run(tmp_path) is None
