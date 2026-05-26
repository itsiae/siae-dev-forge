"""Tests for hook bash v2 — 5 decision branch logic."""
import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / "hooks" / "review-evidence"


def _init_repo(tmp_path):
    sp = subprocess.run
    sp(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    sp(["git", "config", "user.email", "x@x"], cwd=tmp_path, check=True)
    sp(["git", "config", "user.name", "x"], cwd=tmp_path, check=True)
    sp(["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, check=True)
    sp(["git", "config", "tag.gpgsign", "false"], cwd=tmp_path, check=True)
    (tmp_path / "f.txt").write_text("x")
    sp(["git", "add", "."], cwd=tmp_path, check=True)
    sp(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)


def _write_evidence(tmp_path, sha, decision, reason="test reason"):
    ev_dir = tmp_path / ".claude" / "review-evidence"
    ev_dir.mkdir(parents=True)
    evidence = {
        "schema_version": "2.0",
        "sha": sha, "branch": "feat/x", "computed_at": "now",
        "dirty_tree": False, "base_branch": "main", "stack_detected": [],
        "metrics": {}, "spec_drift": None,
        "verdict": {"block": decision.startswith("BLOCK"),
                     "block_reasons": [reason], "warnings": []},
        "regression_verdict": {
            "block_dimensions": [], "warn_dimensions": [],
            "improved_dimensions": [], "hard_floor_breaches": [],
            "decision": decision, "reason": reason,
        },
        "current_scores": {"security": 80, "quality": 75, "coverage": 70,
                            "spec_compliance": 85, "discipline": 90, "overall": 80,
                            "weights_used": {"security": 0.30, "quality": 0.20,
                                              "coverage": 0.20, "spec_compliance": 0.15,
                                              "discipline": 0.15},
                            "missing_components": []},
    }
    (ev_dir / f"{sha}.json").write_text(json.dumps(evidence))
    return ev_dir


def _run_hook(stdin_obj, cwd):
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(stdin_obj),
        capture_output=True, text=True, env=env, cwd=str(cwd), timeout=20,
    )


def test_decision_auto_approve_emits_advisory(tmp_path):
    _init_repo(tmp_path)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path).decode().strip()
    _write_evidence(tmp_path, sha, "AUTO_APPROVE")
    p = _run_hook({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                    "command": "gh pr create --title x"}, tmp_path)
    out = json.loads(p.stdout or "{}")
    assert out.get("decision") != "block"
    assert "AUTO_APPROVE" in out.get("additional_context", "")


def test_decision_block_hard_floor_blocks(tmp_path):
    _init_repo(tmp_path)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path).decode().strip()
    _write_evidence(tmp_path, sha, "BLOCK_HARD_FLOOR", reason="security < 60")
    p = _run_hook({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                    "command": "gh pr create --title x"}, tmp_path)
    out = json.loads(p.stdout or "{}")
    assert out.get("decision") == "block"
    assert "hard floor" in out.get("reason", "").lower()
    assert "BREAK-GLASS" in out.get("reason", "")


def test_decision_block_regression_blocks_overridable(tmp_path):
    _init_repo(tmp_path)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path).decode().strip()
    _write_evidence(tmp_path, sha, "BLOCK_REGRESSION", reason="coverage regressed -8pp")
    p = _run_hook({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                    "command": "gh pr create --title x"}, tmp_path)
    out = json.loads(p.stdout or "{}")
    assert out.get("decision") == "block"
    assert "regression" in out.get("reason", "").lower()


def test_decision_reviewer_handoff_advisory_no_block(tmp_path):
    _init_repo(tmp_path)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path).decode().strip()
    _write_evidence(tmp_path, sha, "REVIEWER_HANDOFF")
    p = _run_hook({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                    "command": "gh pr create --title x"}, tmp_path)
    out = json.loads(p.stdout or "{}")
    assert out.get("decision") != "block"
    assert "reviewer" in out.get("additional_context", "").lower()


def test_decision_severely_degraded_skips_block(tmp_path):
    """F2 iter2 fix: SEVERELY_DEGRADED = tooling broken, skip hard floor."""
    _init_repo(tmp_path)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path).decode().strip()
    _write_evidence(tmp_path, sha, "SEVERELY_DEGRADED")
    p = _run_hook({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                    "command": "gh pr create --title x"}, tmp_path)
    out = json.loads(p.stdout or "{}")
    assert out.get("decision") != "block"
    assert "DEGRADED" in out.get("additional_context", "") or "degraded" in out.get("additional_context", "")


def test_v1_evidence_no_decision_field_still_works(tmp_path):
    """No regression: v1 evidence (no regression_verdict) → fallback to v1 logic."""
    _init_repo(tmp_path)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path).decode().strip()
    ev_dir = tmp_path / ".claude" / "review-evidence"
    ev_dir.mkdir(parents=True)
    v1_evidence = {
        "schema_version": "1.0", "sha": sha, "branch": "x",
        "computed_at": "now", "dirty_tree": False, "base_branch": "main",
        "stack_detected": [], "metrics": {}, "spec_drift": None,
        "verdict": {"block": False, "block_reasons": [], "warnings": []},
    }
    (ev_dir / f"{sha}.json").write_text(json.dumps(v1_evidence))
    p = _run_hook({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                    "command": "gh pr create --title x"}, tmp_path)
    assert p.returncode == 0
    # v1 fallback: emit advisory, no block
    out = json.loads(p.stdout or "{}")
    assert out.get("decision") != "block"
