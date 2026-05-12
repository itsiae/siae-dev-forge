"""Tests for Java collector — static analysis (checkstyle + pmd)."""
import shutil
from pathlib import Path

from lib.review_evidence.collectors._checkstyle import parse_checkstyle_xml
from lib.review_evidence.collectors._pmd import parse_pmd_xml
from lib.review_evidence.collectors.java import JavaCollector

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_parse_checkstyle_counts():
    parsed = parse_checkstyle_xml((FIX / "checkstyle_result.xml").read_text())
    assert parsed["errors"] == 2
    assert parsed["warnings"] == 1
    assert len(parsed["findings"]) == 3


def test_parse_pmd_counts_by_priority():
    parsed = parse_pmd_xml((FIX / "pmd_report.xml").read_text())
    # priority 1-2 = error, 3-5 = warning
    assert parsed["errors"] == 1
    assert parsed["warnings"] == 1


def test_collect_java_aggregates_lint(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")

    cs_target = tmp_path / "target"
    cs_target.mkdir()
    shutil.copyfile(FIX / "checkstyle_result.xml", cs_target / "checkstyle-result.xml")

    pmd_target = tmp_path / "target"
    shutil.copyfile(FIX / "pmd_report.xml", pmd_target / "pmd.xml")

    result = JavaCollector().collect(tmp_path, "main", "HEAD")
    assert result["lint"] is not None
    assert result["lint"]["errors"] == 2 + 1   # 2 checkstyle + 1 pmd
    assert result["lint"]["warnings"] == 1 + 1
    assert "checkstyle" in result["lint"]["source"]
    assert "pmd" in result["lint"]["source"]


def test_collect_only_checkstyle(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    cs_target = tmp_path / "target"
    cs_target.mkdir()
    shutil.copyfile(FIX / "checkstyle_result.xml", cs_target / "checkstyle-result.xml")

    result = JavaCollector().collect(tmp_path, "main", "HEAD")
    assert result["lint"]["errors"] == 2
    assert result["lint"]["warnings"] == 1
    assert result["lint"]["source"] == "local:checkstyle"


def test_collect_no_static_returns_lint_none(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    result = JavaCollector().collect(tmp_path, "main", "HEAD")
    assert result["lint"] is None
