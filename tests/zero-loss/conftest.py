"""Shared fixtures for zero-loss test suite.

Provides:
- tmp_session_dir: isolated DEVFORGE_SESSION_DIR per test
- atomic_write module path injection (lib/ on sys.path)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LIB_DIR = REPO_ROOT / "lib"

# Make lib/ importable in tests
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))


@pytest.fixture
def tmp_session_dir(tmp_path, monkeypatch):
    """Isolated session directory mirroring ~/.claude/devforge-state/<sid>/ layout."""
    sid = "test1234"
    session_dir = tmp_path / "devforge-state" / sid
    session_dir.mkdir(parents=True)
    (session_dir / "outbox").mkdir()
    monkeypatch.setenv("DEVFORGE_SESSION_DIR", str(session_dir))
    monkeypatch.setenv("DEVFORGE_PINNED_SID", sid)
    return session_dir


@pytest.fixture
def activity_file(tmp_session_dir):
    """Empty activity.jsonl in isolated session dir."""
    path = tmp_session_dir / "activity.jsonl"
    path.touch()
    return path
