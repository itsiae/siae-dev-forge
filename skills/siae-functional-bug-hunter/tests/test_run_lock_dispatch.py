"""test_run_lock_dispatch.py — Phase 0 runtime mode dispatcher.

Covers the 3 (mode) × 5 (event) action matrix declared in
references/runtime_modes.md. Plus 2 negative cases (unknown mode,
unknown event).

Run: pytest tests/test_run_lock_dispatch.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = THIS_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import pytest  # noqa: E402

from run_lock import dispatch, DispatchError  # noqa: E402


@pytest.mark.parametrize(
    "mode,event,expected",
    [
        # interactive — always PAUSE
        ("interactive", "STOP_DEPENDENCY_CLOSURE", "PAUSE"),
        ("interactive", "STOP_FINDING_THRESHOLD", "PAUSE"),
        ("interactive", "STOP_WALLCLOCK_EXCEEDED", "PAUSE"),
        ("interactive", "STOP_DIRTY_WORKING_TREE", "PAUSE"),
        ("interactive", "STOP_AMBIGUOUS_SCOPE", "PAUSE"),
        # strict — always CONTINUE (caller flags low-confidence)
        ("strict", "STOP_DEPENDENCY_CLOSURE", "CONTINUE"),
        ("strict", "STOP_FINDING_THRESHOLD", "CONTINUE"),
        ("strict", "STOP_WALLCLOCK_EXCEEDED", "CONTINUE"),
        ("strict", "STOP_DIRTY_WORKING_TREE", "CONTINUE"),
        ("strict", "STOP_AMBIGUOUS_SCOPE", "CONTINUE"),
        # report-only — DEGRADE on dependency closure, CONTINUE elsewhere
        ("report-only", "STOP_DEPENDENCY_CLOSURE", "DEGRADE"),
        ("report-only", "STOP_FINDING_THRESHOLD", "CONTINUE"),
        ("report-only", "STOP_WALLCLOCK_EXCEEDED", "CONTINUE"),
        ("report-only", "STOP_DIRTY_WORKING_TREE", "CONTINUE"),
        ("report-only", "STOP_AMBIGUOUS_SCOPE", "CONTINUE"),
    ],
)
def test_dispatch_matrix(mode: str, event: str, expected: str) -> None:
    assert dispatch(mode, event) == expected


def test_dispatch_unknown_mode() -> None:
    with pytest.raises(DispatchError, match="unknown mode"):
        dispatch("turbo", "STOP_AMBIGUOUS_SCOPE")


def test_dispatch_unknown_event() -> None:
    with pytest.raises(DispatchError, match="unknown event"):
        dispatch("strict", "STOP_COSMIC_RAY")
