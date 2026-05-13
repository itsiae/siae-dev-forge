"""Integration tests: orchestrate_v2 produces ScoreCard + RegressionVerdict.

PR-A foundation scope (Task 07):
- evidence v2 valid with current_scores + regression_verdict
- baseline_synthetic=True on first PR (no baseline cache yet)
- decision in {AUTO_APPROVE, SEVERELY_DEGRADED} when runners missing
  (no false-block on absent tooling — plan-review iter1 sec_score fix)

Baseline cache, budget snapshot, reviewer agent: deferred to PR-B.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from lib.review_evidence.collector import orchestrate_v2


def _init_git(tmp_path: Path) -> None:
    """Bootstrap an empty repo so `git diff base...sha` doesn't crash."""
    sp = subprocess.run
    sp(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    sp(["git", "config", "user.email", "x@x"], cwd=tmp_path, check=True)
    sp(["git", "config", "user.name", "x"], cwd=tmp_path, check=True)
    sp(["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, check=True)
    sp(["git", "config", "tag.gpgsign", "false"], cwd=tmp_path, check=True)
    (tmp_path / "main.py").write_text("# main\n")
    sp(["git", "add", "."], cwd=tmp_path, check=True)
    sp(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )


def _head_sha(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()


def test_orchestrate_v2_produces_evidence_with_scorecard(tmp_path: Path) -> None:
    """Smoke: orchestrate_v2 writes v2 evidence with scorecard + verdict.

    AC #14 — current_scores + regression_verdict always present, even when
    runners are missing (no tooling installed in tmp_path).
    """
    _init_git(tmp_path)
    sha = _head_sha(tmp_path)
    out = tmp_path / "ev.json"

    code = orchestrate_v2(
        sha=sha, base="main", dirty=False, out_path=out, repo_root=tmp_path
    )
    assert code == 0

    data = json.loads(out.read_text())
    assert data["schema_version"] == "2.0"
    assert data["sha"] == sha
    assert "current_scores" in data
    assert data["current_scores"] is not None
    assert "regression_verdict" in data
    assert data["regression_verdict"] is not None
    # Discipline placeholder (W4 fallback) must be 50.0
    assert data["current_scores"]["discipline"] == 50.0


def test_orchestrate_v2_baseline_synthetic_first_pr(tmp_path: Path) -> None:
    """A6: first PR, no baseline cache → baseline_synthetic=True."""
    _init_git(tmp_path)
    sha = _head_sha(tmp_path)
    out = tmp_path / "ev.json"

    code = orchestrate_v2(
        sha=sha, base="main", dirty=False, out_path=out, repo_root=tmp_path
    )
    assert code == 0

    data = json.loads(out.read_text())
    assert data["baseline_synthetic"] is True
    # PR-A: baseline is never populated; PR-B will add the S3 cache.
    assert data["baseline_scores"] in (None, {})
    assert data["deltas"] is None
    assert data["reviewer_verdict"] is None
    assert data["budget_snapshot_at"] is None


def test_orchestrate_v2_severely_degraded_skips_block(tmp_path: Path) -> None:
    """D6: no runners running → severely degraded path, decision must NOT block.

    Plan-review iter1: sec_score stays None when applicable runners return
    None (tool missing), so we don't false-flag a hard-floor breach.
    """
    _init_git(tmp_path)
    sha = _head_sha(tmp_path)
    out = tmp_path / "ev.json"

    code = orchestrate_v2(
        sha=sha, base="main", dirty=False, out_path=out, repo_root=tmp_path
    )
    assert code == 0

    data = json.loads(out.read_text())
    rv = data.get("regression_verdict") or {}
    # No runners → discipline=50 + spec_compliance=100 ⇒ 2 dims available
    # ⇒ NOT degraded, decision AUTO_APPROVE. But on a host with discipline
    # only (≤1 dim), compute_overall flags severely_degraded → both paths
    # are valid for PR-A foundation.
    assert rv.get("decision") in ("SEVERELY_DEGRADED", "AUTO_APPROVE")
    # Crucially: never a BLOCK_HARD_FLOOR purely because tooling is missing
    assert rv.get("decision") != "BLOCK_HARD_FLOOR"
    # No top-level block when runners are simply absent
    assert data["verdict"]["block"] is False
