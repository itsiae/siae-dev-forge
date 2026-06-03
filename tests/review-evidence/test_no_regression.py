"""Verify that adding the review-evidence hook didn't break existing hooks.

We invoke the ACTUAL existing bash test scripts under tests/hooks/ rather than
fictitious test_*.py files. The plan-review iter 1 caught that referencing
non-existent files (with `returncode == 5: return` early-exit) silently passes
the no-regression check — that's exactly the kind of false safety we want to
avoid.

Path note: this file lives under `tests/review-evidence/` (subdir-flat layout
kept post plan-review iter 2 for the no-regression suite specifically). The
root `tests/conftest.py` is loaded by pytest discovery so `from lib.*` imports
still resolve.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


EXISTING_BASH_TESTS = [
    REPO_ROOT / "tests" / "hooks" / "post-commit-review-sha.test.sh",
    REPO_ROOT / "tests" / "hooks" / "post-commit-pr-lifecycle.test.sh",
    REPO_ROOT / "tests" / "hooks" / "hooks-json-var-expansion.test.sh",
    REPO_ROOT / "tests" / "hooks" / "brainstorming-gate.test.sh",
]


@pytest.mark.parametrize(
    "test_script", EXISTING_BASH_TESTS, ids=lambda p: p.name
)
def test_existing_hook_test_passes(test_script):
    """Each existing hook test must still pass after we added review-evidence."""
    if not test_script.exists():
        pytest.skip(f"test script not present: {test_script.name}")
    p = subprocess.run(
        ["bash", str(test_script)],
        capture_output=True, text=True, cwd=REPO_ROOT, timeout=120,
    )
    assert p.returncode == 0, (
        f"{test_script.name} broke:\n"
        f"--- STDOUT ---\n{p.stdout}\n"
        f"--- STDERR ---\n{p.stderr}"
    )


def test_hook_dispatcher_loads_review_evidence_without_error(tmp_path):
    """Smoke: hooks/run-hook.cmd is invokable for review-evidence script.

    Empty/non-matching command → hook emits `{}` and exits 0. We isolate
    HOME so any local bypass state file doesn't mask the real path.
    """
    import os as _os
    dispatcher = REPO_ROOT / "hooks" / "run-hook.cmd"
    if not dispatcher.exists():
        pytest.skip("run-hook.cmd not present")
    env = _os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    env["HOME"] = str(tmp_path)
    p = subprocess.run(
        ["bash", str(dispatcher), "review-evidence"],
        input='{"command": "echo nothing"}',
        capture_output=True, text=True, env=env, timeout=20,
    )
    assert p.returncode == 0, (
        f"hook dispatcher failed:\n--- STDOUT ---\n{p.stdout}\n--- STDERR ---\n{p.stderr}"
    )
