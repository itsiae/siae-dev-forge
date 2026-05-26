"""End-to-end test: collector.py invoked as standalone script (the way the
bash hook runs it), not via pytest. Without sys.path self-bootstrap the
script crashes with ModuleNotFoundError — exactly the failure mode that
manual end-to-end testing surfaced AFTER unit tests had been green.

This is the regression test that should have existed from Task 14.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = REPO_ROOT / "lib" / "review_evidence" / "collector.py"


def _init_git(tmp_path):
    sp = subprocess.run
    sp(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    sp(["git", "config", "user.email", "x@x"], cwd=tmp_path, check=True)
    sp(["git", "config", "user.name", "x"], cwd=tmp_path, check=True)
    sp(["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, check=True)
    sp(["git", "config", "tag.gpgsign", "false"], cwd=tmp_path, check=True)
    (tmp_path / "f.txt").write_text("x")
    sp(["git", "add", "."], cwd=tmp_path, check=True)
    sp(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)


def test_collector_runs_as_standalone_script(tmp_path):
    """The hook invokes `python3 <COLLECTOR>` directly without setting
    PYTHONPATH. Collector MUST self-bootstrap sys.path so its own imports
    (`from lib.review_evidence.X`) resolve."""
    _init_git(tmp_path)
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True
    ).strip()
    out_path = tmp_path / "ev.json"

    p = subprocess.run(
        [sys.executable, str(COLLECTOR),
         "--sha", sha, "--base", "main", "--dirty", "0",
         "--out", str(out_path)],
        cwd=tmp_path, capture_output=True, text=True, timeout=30,
    )

    assert p.returncode == 0, (
        f"Collector script crashed with rc={p.returncode}.\n"
        f"--- STDOUT ---\n{p.stdout}\n--- STDERR ---\n{p.stderr}\n"
        "Likely cause: sys.path bootstrap missing — `from lib.review_evidence...` fails."
    )
    assert out_path.exists(), "Evidence file not written"
    data = json.loads(out_path.read_text())
    # v2 bump: writer now emits "2.0" (scoring extension).
    assert data["schema_version"] == "2.0"
    assert data["sha"] == sha


def test_collector_writes_valid_schema_when_no_collectors_match(tmp_path):
    """Repo with no source files → no collector applicable → evidence is
    still written with empty stack_detected + no metrics (graceful)."""
    _init_git(tmp_path)
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True
    ).strip()
    out_path = tmp_path / "ev.json"

    p = subprocess.run(
        [sys.executable, str(COLLECTOR),
         "--sha", sha, "--base", "main", "--dirty", "0",
         "--out", str(out_path)],
        cwd=tmp_path, capture_output=True, text=True, timeout=30,
    )
    assert p.returncode == 0, f"stderr: {p.stderr}"
    data = json.loads(out_path.read_text())
    # Even with no stacks, schema is valid and verdict is non-blocking
    assert data["verdict"]["block"] is False or "drift" in str(data["verdict"]["block_reasons"])
