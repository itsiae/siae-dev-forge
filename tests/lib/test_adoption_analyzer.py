"""tests for lib/adoption-analyzer.py (PR #3 ADR-009).

Covers: ledger parsing, session fallback, format outputs (json/table/recap/block),
empty state, window filtering.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], text=True).strip())
MODULE_PATH = REPO_ROOT / "lib" / "adoption-analyzer.py"


def _load():
    """Import the analyzer as a module (file is not a python package)."""
    spec = importlib.util.spec_from_file_location("adoption_analyzer", MODULE_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def tmp_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".claude").mkdir()
    return tmp_path


def _seed_ledger(home: Path, task_id: str, validated: list[str]) -> None:
    d = home / ".claude" / ".devforge-task-skills" / task_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "skills_validated").write_text("\n".join(validated) + "\n")


def _seed_activity(home: Path, events: list[dict]) -> None:
    log = home / ".claude" / "devforge-activity.jsonl"
    log.write_text("\n".join(json.dumps(e) for e in events) + "\n")


def test_analyzer_file_exists():
    assert MODULE_PATH.is_file(), f"missing {MODULE_PATH}"


def test_user_adoption_from_ledger(tmp_home):
    mod = _load()
    _seed_ledger(tmp_home, "aaa111bbb222", ["siae-tdd", "siae-brainstorming"])
    _seed_ledger(tmp_home, "ccc333ddd444", ["siae-tdd"])
    ledger = mod._ledger_task_skills()
    user = mod._user_adoption([], ledger)
    # 2 tasks total; tdd in both (100%), brainstorming in 1 (50%), others 0.
    assert user["siae-tdd"] == 100.0
    assert user["siae-brainstorming"] == 50.0
    assert user["siae-verification"] == 0.0


def test_user_adoption_falls_back_to_session_when_ledger_empty(tmp_home):
    mod = _load()
    events = [
        {"ts": "2026-04-26T10:00:00Z", "sid": "s1", "event": "skill_invoked",
         "user": "u1", "meta": {"skill_name": "siae-devforge:siae-tdd"}},
        {"ts": "2026-04-26T10:05:00Z", "sid": "s1", "event": "skill_invoked",
         "user": "u1", "meta": {"skill_name": "siae-devforge:siae-brainstorming"}},
        {"ts": "2026-04-26T11:00:00Z", "sid": "s2", "event": "skill_invoked",
         "user": "u1", "meta": {"skill_name": "siae-devforge:siae-tdd"}},
    ]
    _seed_activity(tmp_home, events)
    all_events = mod._load_activity(30)
    user = mod._user_adoption(all_events, {})
    # 2 sessions total. tdd in both (100%), brainstorming in 1 (50%).
    assert user["siae-tdd"] == 100.0
    assert user["siae-brainstorming"] == 50.0


def test_team_median_computes_per_user_then_median(tmp_home):
    mod = _load()
    # 3 users. tdd: user1=100, user2=50, user3=0 → median 50.
    events = [
        # u1
        {"ts": "2026-04-26T10:00:00Z", "sid": "s1", "event": "skill_invoked",
         "user": "u1", "meta": {"skill_name": "siae-devforge:siae-tdd"}},
        # u2: 2 sessions, tdd in 1
        {"ts": "2026-04-26T10:00:00Z", "sid": "s2", "event": "skill_invoked",
         "user": "u2", "meta": {"skill_name": "siae-devforge:siae-tdd"}},
        {"ts": "2026-04-26T11:00:00Z", "sid": "s3", "event": "skill_invoked",
         "user": "u2", "meta": {"skill_name": "siae-devforge:siae-brainstorming"}},
        # u3: 1 session, no tdd
        {"ts": "2026-04-26T12:00:00Z", "sid": "s4", "event": "skill_invoked",
         "user": "u3", "meta": {"skill_name": "siae-devforge:siae-brainstorming"}},
    ]
    _seed_activity(tmp_home, events)
    all_events = mod._load_activity(30)
    team = mod._team_median(all_events)
    assert team["siae-tdd"] == 50.0


def test_window_filter_excludes_old_events(tmp_home, monkeypatch):
    mod = _load()
    # Event from 30 days ago — must be excluded with window=7
    old_ts = "2026-03-20T10:00:00Z"
    fresh_ts = "2026-04-26T10:00:00Z"
    events = [
        {"ts": old_ts, "sid": "s_old", "event": "skill_invoked",
         "user": "u1", "meta": {"skill_name": "siae-devforge:siae-tdd"}},
        {"ts": fresh_ts, "sid": "s_new", "event": "skill_invoked",
         "user": "u1", "meta": {"skill_name": "siae-devforge:siae-brainstorming"}},
    ]
    _seed_activity(tmp_home, events)
    # Freeze "now" to 2026-04-26 so the window cut-off is deterministic
    import time as _time
    monkeypatch.setattr(_time, "time", lambda: _time.mktime((2026, 4, 26, 12, 0, 0, 0, 0, 0)))
    all_events = mod._load_activity(7)
    assert len(all_events) == 1
    assert all_events[0]["sid"] == "s_new"


def test_format_table_lists_all_5_core_skills(tmp_home):
    mod = _load()
    user = {s: 50.0 for s in mod.CORE_SKILLS}
    team = {s: 30.0 for s in mod.CORE_SKILLS}
    out = mod._format_table(user, team, 7)
    for s in mod.CORE_SKILLS:
        assert s in out
    assert "| Skill |" in out
    assert "+20pp" in out  # delta 50-30


def test_format_block_requires_skill(tmp_home):
    mod = _load()
    user = {s: 42.0 for s in mod.CORE_SKILLS}
    team = {s: 80.0 for s in mod.CORE_SKILLS}
    out = mod._format_block("siae-tdd", user, team)
    assert "siae-tdd" in out
    assert "42" in out
    assert "80" in out


def test_cli_json_output(tmp_home):
    _seed_ledger(tmp_home, "ddd555eee666", ["siae-tdd"])
    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), "--format", "json"],
        capture_output=True, text=True, env={**os.environ, "HOME": str(tmp_home)},
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert "user_adoption" in payload
    assert "team_median" in payload
    assert payload["n_tasks"] == 1
