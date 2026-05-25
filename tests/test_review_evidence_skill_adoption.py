"""Tests for skill_adoption check (4-tier fallback signal, W4 spec)."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone

import pytest

from lib.review_evidence.checks.skill_adoption import (
    SkillAdoptionResult,
    detect_skill_adoption,
)


@pytest.fixture(autouse=True)
def _isolate_activity_env(monkeypatch, tmp_path):
    """Default: no activity.jsonl resolution unless test opts in.

    Points HOME to an empty tmp dir and clears DEVFORGE_ACTIVITY_PROJECT so
    Tier 1 returns False unless a test explicitly sets up fixtures.
    """
    fake_home = tmp_path / "_isolated_home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.delenv("DEVFORGE_ACTIVITY_PROJECT", raising=False)


def test_bot_pr_label_skips_check(tmp_path):
    """C1: label ``bot-pr`` -> ``is_bot_pr=True``, score irrelevant."""
    result = detect_skill_adoption(
        repo_root=tmp_path,
        pr_open_time=datetime.now(timezone.utc),
        pr_labels=["bot-pr"],
        pr_user="ci-bot",
    )

    assert isinstance(result, SkillAdoptionResult)
    assert result.is_bot_pr is True
    assert result.brainstorming_done is False
    assert result.tdd_cycle_seen is False
    assert result.verification_run is False
    assert result.discipline_signal_missing is False


def test_bot_user_dependabot(tmp_path):
    """C1 variant: user ``dependabot[bot]`` -> ``is_bot_pr=True``."""
    result = detect_skill_adoption(
        repo_root=tmp_path,
        pr_open_time=datetime.now(timezone.utc),
        pr_labels=[],
        pr_user="dependabot[bot]",
    )

    assert result.is_bot_pr is True


def test_brainstorming_signal_from_design_doc(tmp_path):
    """Tier 2: ``docs/plans/<topic>/overview.md`` recent -> brainstorming_done."""
    plans = tmp_path / "docs" / "plans" / "2026-05-13-test"
    plans.mkdir(parents=True)
    overview = plans / "overview.md"
    overview.write_text("# Test plan\nstatus: approved\n")

    result = detect_skill_adoption(
        repo_root=tmp_path,
        pr_open_time=datetime.now(timezone.utc),
        pr_labels=[],
        pr_user="lorenzo",
    )

    assert result.brainstorming_done is True
    assert result.discipline_signal_missing is False


def test_no_signal_neutral_50(tmp_path):
    """W4: dev without DevForge -> discipline_signal_missing=True."""
    result = detect_skill_adoption(
        repo_root=tmp_path,
        pr_open_time=datetime.now(timezone.utc),
        pr_labels=[],
        pr_user="external-contributor",
    )

    assert result.discipline_signal_missing is True
    assert result.brainstorming_done is False
    assert result.tdd_cycle_seen is False
    assert result.verification_run is False
    assert result.is_bot_pr is False


def test_tdd_signal_from_git_log(tmp_path):
    """Tier 3: ``git log --grep "test:"`` returns >=1 -> tdd_cycle_seen."""
    subprocess.run(
        ["git", "init"], cwd=tmp_path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "x@x"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "x"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=tmp_path,
        check=True,
    )
    (tmp_path / "f.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "test: add foo"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    result = detect_skill_adoption(
        repo_root=tmp_path,
        pr_open_time=datetime.now(timezone.utc),
        pr_labels=[],
        pr_user="lorenzo",
    )

    assert result.tdd_cycle_seen is True


def test_activity_jsonl_signal(tmp_path, monkeypatch):
    """Tier 1: ``activity.jsonl`` event ``brainstorming_done`` within cutoff."""
    fake_home = tmp_path / "home"
    activity_dir = (
        fake_home
        / ".claude"
        / "projects"
        / "test-project"
        / "devforge-state"
    )
    activity_dir.mkdir(parents=True)
    activity = activity_dir / "activity.jsonl"
    now = datetime.now(timezone.utc)
    line = json.dumps(
        {"event": "brainstorming_done", "timestamp": now.isoformat()}
    )
    activity.write_text(line + "\n")

    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("DEVFORGE_ACTIVITY_PROJECT", "test-project")

    result = detect_skill_adoption(
        repo_root=tmp_path,
        pr_open_time=now,
        pr_labels=[],
        pr_user="lorenzo",
    )

    assert result.brainstorming_done is True
    assert result.discipline_signal_missing is False
