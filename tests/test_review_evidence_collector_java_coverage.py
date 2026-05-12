"""Tests for Java collector -- coverage (jacoco)."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from lib.review_evidence.collectors.java import JavaCollector
from lib.review_evidence.collectors._jacoco import parse_jacoco_xml

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_parse_jacoco_overall_pct():
    xml = (FIX / "jacoco_maven.xml").read_text()
    data = parse_jacoco_xml(xml)
    # 17 / (17+3) = 85.0
    assert data["overall_pct"] == 85.0
    assert len(data["per_file"]) == 1


def test_is_applicable_maven(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    assert JavaCollector().is_applicable(tmp_path) is True


def test_is_applicable_gradle(tmp_path):
    (tmp_path / "build.gradle").write_text("plugins { id 'java' }")
    assert JavaCollector().is_applicable(tmp_path) is True


def test_is_applicable_gradle_kts(tmp_path):
    (tmp_path / "build.gradle.kts").write_text("plugins { java }")
    assert JavaCollector().is_applicable(tmp_path) is True


def test_not_applicable_otherwise(tmp_path):
    (tmp_path / "README.md").write_text("md")
    assert JavaCollector().is_applicable(tmp_path) is False


def test_collect_maven_jacoco_path(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    target = tmp_path / "target" / "site" / "jacoco"
    target.mkdir(parents=True)
    shutil.copyfile(FIX / "jacoco_maven.xml", target / "jacoco.xml")

    result = JavaCollector().collect(tmp_path, "main", "HEAD")
    assert result["stack"] == "java"
    assert result["coverage"]["overall_pct"] == 85.0
    assert result["coverage"]["source"] == "local:jacoco-maven"


def test_collect_gradle_jacoco_path(tmp_path):
    (tmp_path / "build.gradle").write_text("plugins{}")
    target = tmp_path / "build" / "reports" / "jacoco" / "test"
    target.mkdir(parents=True)
    shutil.copyfile(FIX / "jacoco_gradle.xml", target / "jacocoTestReport.xml")

    result = JavaCollector().collect(tmp_path, "main", "HEAD")
    assert result["coverage"]["overall_pct"] == 80.0
    assert result["coverage"]["source"] == "local:jacoco-gradle"


def test_collect_missing_jacoco_returns_none(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    result = JavaCollector().collect(tmp_path, "main", "HEAD")
    assert result["coverage"] is None
