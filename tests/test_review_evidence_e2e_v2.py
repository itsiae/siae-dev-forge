"""E2E test full pipeline v2 — hook → orchestrator → S3 → reviewer."""
import json
import os
import subprocess
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / "hooks" / "review-evidence"


def _init_repo(tmp_path):
    sp = subprocess.run
    sp(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    sp(["git", "config", "user.email", "x@x"], cwd=tmp_path, check=True)
    sp(["git", "config", "user.name", "x"], cwd=tmp_path, check=True)
    sp(["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, check=True)
    sp(["git", "config", "tag.gpgsign", "false"], cwd=tmp_path, check=True)
    (tmp_path / "main.py").write_text("def main(): pass\n")
    sp(["git", "add", "."], cwd=tmp_path, check=True)
    sp(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)


def _run_hook(stdin_obj, cwd, env_extra=None):
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    env["DEVFORGE_SCORING_V2_ENABLED"] = "1"
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(stdin_obj),
        capture_output=True, text=True, env=env, cwd=str(cwd), timeout=60,
    )


@mock_aws
def test_e2e_first_pr_baseline_synthetic_auto_approve(tmp_path):
    """First PR, no baseline → baseline_synthetic=True → AUTO_APPROVE."""
    boto3.client("s3", region_name="eu-west-1").create_bucket(
        Bucket="itsiae-review-evidence-baseline-prod",
        CreateBucketConfiguration={"LocationConstraint": "eu-west-1"},
    )
    _init_repo(tmp_path)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path).decode().strip()

    # Trigger hook
    p = _run_hook({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                    "command": "gh pr create --title test"}, tmp_path)

    assert p.returncode == 0
    # Hook should NOT block (synthetic baseline + no runners installed → SEVERELY_DEGRADED OR AUTO_APPROVE)
    out = json.loads(p.stdout or "{}")
    assert out.get("decision") != "block"
    # Evidence file should exist
    evidence_file = tmp_path / ".claude" / "review-evidence" / f"{sha}.json"
    assert evidence_file.exists()
    ev = json.loads(evidence_file.read_text())
    assert ev["schema_version"] == "2.0"
    assert ev["baseline_synthetic"] is True


def test_e2e_block_hard_floor_security_breach(tmp_path):
    """Pre-write evidence with security < 60 → hook emit decision:block hard floor."""
    _init_repo(tmp_path)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path).decode().strip()
    ev_dir = tmp_path / ".claude" / "review-evidence"
    ev_dir.mkdir(parents=True)
    blocked = {
        "schema_version": "2.0", "sha": sha, "branch": "x",
        "computed_at": "now", "dirty_tree": False, "base_branch": "main",
        "stack_detected": [], "metrics": {}, "spec_drift": None,
        "verdict": {"block": True, "block_reasons": [], "warnings": []},
        "regression_verdict": {
            "block_dimensions": [], "warn_dimensions": [],
            "improved_dimensions": [], "hard_floor_breaches": ["security(45) < hard_floor(60)"],
            "decision": "BLOCK_HARD_FLOOR",
            "reason": "Hard floor breached: security(45) < hard_floor(60)",
        },
        "current_scores": {"security": 45, "quality": 70, "coverage": 65,
                            "spec_compliance": 80, "discipline": 90, "overall": 68,
                            "weights_used": {}, "missing_components": []},
        "baseline_synthetic": True,
    }
    (ev_dir / f"{sha}.json").write_text(json.dumps(blocked))

    p = _run_hook({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                    "command": "gh pr create --title test"}, tmp_path)

    out = json.loads(p.stdout or "{}")
    assert out.get("decision") == "block"
    assert "hard floor" in out.get("reason", "").lower()
    assert "BREAK-GLASS" in out.get("reason", "")


def test_e2e_severely_degraded_no_block(tmp_path):
    """No runners installed → SEVERELY_DEGRADED → no block, advisory."""
    _init_repo(tmp_path)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path).decode().strip()
    ev_dir = tmp_path / ".claude" / "review-evidence"
    ev_dir.mkdir(parents=True)
    degraded = {
        "schema_version": "2.0", "sha": sha, "branch": "x",
        "computed_at": "now", "dirty_tree": False, "base_branch": "main",
        "stack_detected": [], "metrics": {}, "spec_drift": None,
        "verdict": {"block": False, "block_reasons": [], "warnings": []},
        "regression_verdict": {
            "block_dimensions": [], "warn_dimensions": [],
            "improved_dimensions": [], "hard_floor_breaches": [],
            "decision": "SEVERELY_DEGRADED",
            "reason": "All runners missing — bandit, gitleaks, pip-audit, npm-audit, eslint-security",
        },
        "current_scores": {"security": 0, "quality": 0, "coverage": 0,
                            "spec_compliance": 0, "discipline": 50, "overall": 50,
                            "weights_used": {}, "missing_components": ["security", "quality", "coverage", "spec_compliance"]},
        "baseline_synthetic": True,
    }
    (ev_dir / f"{sha}.json").write_text(json.dumps(degraded))

    p = _run_hook({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                    "command": "gh pr create --title test"}, tmp_path)

    out = json.loads(p.stdout or "{}")
    assert out.get("decision") != "block"
    assert "DEGRADED" in out.get("additional_context", "").upper() or "degraded" in out.get("additional_context", "")


def test_e2e_v1_evidence_no_regression(tmp_path):
    """v1 evidence (no regression_verdict) still works via fallback."""
    _init_repo(tmp_path)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path).decode().strip()
    ev_dir = tmp_path / ".claude" / "review-evidence"
    ev_dir.mkdir(parents=True)
    v1 = {
        "schema_version": "1.0", "sha": sha, "branch": "x",
        "computed_at": "now", "dirty_tree": False, "base_branch": "main",
        "stack_detected": [], "metrics": {}, "spec_drift": None,
        "verdict": {"block": False, "block_reasons": [], "warnings": []},
    }
    (ev_dir / f"{sha}.json").write_text(json.dumps(v1))

    p = _run_hook({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                    "command": "gh pr create --title test"}, tmp_path)

    assert p.returncode == 0  # No crash, falls back to v1 advisory path


def test_e2e_full_suite_no_regression():
    """Full pytest suite includes v1 + v2 — must be all green.

    Plan-review iter1 fix: exclude self via -p no:cacheprovider + ignore current file
    to avoid infinite recursion (pytest dentro pytest).
    """
    p = subprocess.run(
        ["python3", "-m", "pytest", "tests/", "-q", "--no-header",
         "--ignore=tests/test_review_evidence_e2e_v2.py",
         "-p", "no:cacheprovider"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=120,
    )
    # 158 v1 + ~50 v2 = ~210 atteso (minus 6 self tests excluded)
    assert p.returncode == 0, f"Test suite failed:\n{p.stdout}\n{p.stderr}"


def test_coverage_gate_85_percent():
    """AC #14: coverage ≥85% su lib/review_evidence/."""
    p = subprocess.run(
        ["python3", "-m", "pytest", "tests/", "--cov=lib.review_evidence",
         "--cov-report=term", "-q", "--no-header",
         "--ignore=tests/test_review_evidence_e2e_v2.py",
         "-p", "no:cacheprovider"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=180,
    )
    # Plan-review iter1 fix: explicit assertion on match presence
    import re
    match = re.search(r"TOTAL.*?(\d+)%", p.stdout)
    assert match is not None, f"Coverage report parse failed:\n{p.stdout}"
    coverage_pct = int(match.group(1))
    assert coverage_pct >= 85, f"Coverage {coverage_pct}% < 85% gate"
