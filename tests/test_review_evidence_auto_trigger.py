"""Tests for hook bash auto-trigger fully-autonomous signal (PR #244 follow-up).

Verifies that ``hooks/review-evidence`` emits the canonical
``AUTO_FIX_TRIGGER:/forge-fix-evidence:sha=<SHA>`` marker in
``additional_context`` when:

  * ``DEVFORGE_FIX_EVIDENCE_AUTO=1`` is set, AND
  * decision == BLOCK_REGRESSION, AND
  * ``hard_floor_breaches`` is empty, AND
  * ``GITHUB_ACTOR`` does NOT match a bot pattern.

The block ``decision`` is always preserved (signal is ADDITIVE, not a
replacement) so the safety net stays in place if the agent fails to
intercept the marker.
"""
import json
import os
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / "hooks" / "review-evidence"

SIGNAL_RE = re.compile(
    r"AUTO_FIX_TRIGGER:/forge-fix-evidence:sha=([0-9a-f]{40})"
)


def _init_repo(tmp_path):
    sp = subprocess.run
    sp(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    sp(["git", "config", "user.email", "x@x"], cwd=tmp_path, check=True)
    sp(["git", "config", "user.name", "x"], cwd=tmp_path, check=True)
    sp(["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, check=True)
    sp(["git", "config", "tag.gpgsign", "false"], cwd=tmp_path, check=True)
    (tmp_path / "f.txt").write_text("x")
    sp(["git", "add", "."], cwd=tmp_path, check=True)
    sp(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )


def _write_evidence(
    tmp_path,
    sha,
    *,
    decision="BLOCK_REGRESSION",
    reason="coverage regressed -8pp",
    hard_floor_breaches=None,
):
    ev_dir = tmp_path / ".claude" / "review-evidence"
    ev_dir.mkdir(parents=True, exist_ok=True)
    evidence = {
        "schema_version": "2.0",
        "sha": sha,
        "branch": "feat/x",
        "computed_at": "now",
        "dirty_tree": False,
        "base_branch": "main",
        "stack_detected": [],
        "metrics": {},
        "spec_drift": None,
        "verdict": {
            "block": decision.startswith("BLOCK"),
            "block_reasons": [reason],
            "warnings": [],
        },
        "regression_verdict": {
            "block_dimensions": [],
            "warn_dimensions": [],
            "improved_dimensions": [],
            "hard_floor_breaches": hard_floor_breaches or [],
            "decision": decision,
            "reason": reason,
        },
        "current_scores": {
            "security": 80,
            "quality": 75,
            "coverage": 70,
            "spec_compliance": 85,
            "discipline": 90,
            "overall": 80,
            "weights_used": {
                "security": 0.30,
                "quality": 0.20,
                "coverage": 0.20,
                "spec_compliance": 0.15,
                "discipline": 0.15,
            },
            "missing_components": [],
        },
    }
    (ev_dir / f"{sha}.json").write_text(json.dumps(evidence))
    return ev_dir


def _run_hook(stdin_obj, cwd, *, extra_env=None):
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    # Strip any AUTO env from the parent process so tests are deterministic.
    env.pop("DEVFORGE_FIX_EVIDENCE_AUTO", None)
    env.pop("GITHUB_ACTOR", None)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(stdin_obj),
        capture_output=True,
        text=True,
        env=env,
        cwd=str(cwd),
        timeout=20,
    )


def _head_sha(repo):
    return (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo)
        .decode()
        .strip()
    )


# ---------------------------------------------------------------------------
# Happy path: AUTO=1 + clean BLOCK_REGRESSION -> signal emitted
# ---------------------------------------------------------------------------


def test_block_regression_with_auto_enabled_emits_signal(tmp_path):
    _init_repo(tmp_path)
    sha = _head_sha(tmp_path)
    _write_evidence(tmp_path, sha)
    p = _run_hook(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "command": "gh pr create --title x",
        },
        tmp_path,
        extra_env={"DEVFORGE_FIX_EVIDENCE_AUTO": "1"},
    )
    out = json.loads(p.stdout or "{}")
    # Block MUST stay (signal is additive, not replacement).
    assert out.get("decision") == "block"
    ctx = out.get("additional_context", "")
    m = SIGNAL_RE.search(ctx)
    assert m is not None, (
        f"Expected AUTO_FIX_TRIGGER marker in additional_context, "
        f"got: {ctx!r}"
    )
    # SHA in signal must match HEAD SHA (40 hex chars).
    assert m.group(1) == sha


# ---------------------------------------------------------------------------
# Default opt-out: AUTO=0 (or unset) -> NO signal, normal block
# ---------------------------------------------------------------------------


def test_block_regression_without_auto_emits_no_signal(tmp_path):
    _init_repo(tmp_path)
    sha = _head_sha(tmp_path)
    _write_evidence(tmp_path, sha)
    p = _run_hook(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "command": "gh pr create --title x",
        },
        tmp_path,
        # Explicit AUTO=0 ensures we exercise the disabled branch.
        extra_env={"DEVFORGE_FIX_EVIDENCE_AUTO": "0"},
    )
    out = json.loads(p.stdout or "{}")
    assert out.get("decision") == "block"
    # additional_context optional; if present, must NOT contain marker.
    ctx = out.get("additional_context", "")
    assert SIGNAL_RE.search(ctx) is None, (
        f"Did not expect AUTO_FIX_TRIGGER marker when AUTO=0, got: {ctx!r}"
    )


def test_block_regression_auto_unset_emits_no_signal(tmp_path):
    """Default behaviour: env unset == opt-out."""
    _init_repo(tmp_path)
    sha = _head_sha(tmp_path)
    _write_evidence(tmp_path, sha)
    p = _run_hook(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "command": "gh pr create --title x",
        },
        tmp_path,
        # No extra_env -> AUTO is unset (default behaviour).
    )
    out = json.loads(p.stdout or "{}")
    assert out.get("decision") == "block"
    ctx = out.get("additional_context", "")
    assert SIGNAL_RE.search(ctx) is None


# ---------------------------------------------------------------------------
# Skip conditions: hard_floor_breaches non-empty
# ---------------------------------------------------------------------------


def test_hard_floor_breaches_skips_signal(tmp_path):
    """Even with AUTO=1, non-empty hard_floor_breaches MUST skip signal."""
    _init_repo(tmp_path)
    sha = _head_sha(tmp_path)
    _write_evidence(
        tmp_path,
        sha,
        decision="BLOCK_REGRESSION",
        hard_floor_breaches=["security < 60"],
    )
    p = _run_hook(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "command": "gh pr create --title x",
        },
        tmp_path,
        extra_env={"DEVFORGE_FIX_EVIDENCE_AUTO": "1"},
    )
    out = json.loads(p.stdout or "{}")
    assert out.get("decision") == "block"
    ctx = out.get("additional_context", "")
    assert SIGNAL_RE.search(ctx) is None, (
        f"Signal MUST be skipped on hard_floor_breaches non-empty, "
        f"got: {ctx!r}"
    )


# ---------------------------------------------------------------------------
# Skip conditions: bot PR (GITHUB_ACTOR matches bot pattern)
# ---------------------------------------------------------------------------


def test_bot_actor_dependabot_skips_signal(tmp_path):
    _init_repo(tmp_path)
    sha = _head_sha(tmp_path)
    _write_evidence(tmp_path, sha)
    p = _run_hook(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "command": "gh pr create --title x",
        },
        tmp_path,
        extra_env={
            "DEVFORGE_FIX_EVIDENCE_AUTO": "1",
            "GITHUB_ACTOR": "dependabot[bot]",
        },
    )
    out = json.loads(p.stdout or "{}")
    assert out.get("decision") == "block"
    ctx = out.get("additional_context", "")
    assert SIGNAL_RE.search(ctx) is None


def test_bot_actor_renovate_skips_signal(tmp_path):
    _init_repo(tmp_path)
    sha = _head_sha(tmp_path)
    _write_evidence(tmp_path, sha)
    p = _run_hook(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "command": "gh pr create --title x",
        },
        tmp_path,
        extra_env={
            "DEVFORGE_FIX_EVIDENCE_AUTO": "1",
            "GITHUB_ACTOR": "renovate[bot]",
        },
    )
    out = json.loads(p.stdout or "{}")
    assert out.get("decision") == "block"
    ctx = out.get("additional_context", "")
    assert SIGNAL_RE.search(ctx) is None


def test_bot_actor_github_actions_skips_signal(tmp_path):
    _init_repo(tmp_path)
    sha = _head_sha(tmp_path)
    _write_evidence(tmp_path, sha)
    p = _run_hook(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "command": "gh pr create --title x",
        },
        tmp_path,
        extra_env={
            "DEVFORGE_FIX_EVIDENCE_AUTO": "1",
            "GITHUB_ACTOR": "github-actions[bot]",
        },
    )
    out = json.loads(p.stdout or "{}")
    assert out.get("decision") == "block"
    ctx = out.get("additional_context", "")
    assert SIGNAL_RE.search(ctx) is None


def test_human_actor_does_not_skip_signal(tmp_path):
    """Non-bot actor name MUST NOT trigger the bot skip path."""
    _init_repo(tmp_path)
    sha = _head_sha(tmp_path)
    _write_evidence(tmp_path, sha)
    p = _run_hook(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "command": "gh pr create --title x",
        },
        tmp_path,
        extra_env={
            "DEVFORGE_FIX_EVIDENCE_AUTO": "1",
            "GITHUB_ACTOR": "lorenzo-detomasi",
        },
    )
    out = json.loads(p.stdout or "{}")
    assert out.get("decision") == "block"
    ctx = out.get("additional_context", "")
    assert SIGNAL_RE.search(ctx) is not None


# ---------------------------------------------------------------------------
# Non-BLOCK_REGRESSION decisions do not emit the signal
# ---------------------------------------------------------------------------


def test_hard_floor_decision_no_signal_even_with_auto(tmp_path):
    """BLOCK_HARD_FLOOR uses a separate case branch and never emits signal."""
    _init_repo(tmp_path)
    sha = _head_sha(tmp_path)
    _write_evidence(tmp_path, sha, decision="BLOCK_HARD_FLOOR")
    p = _run_hook(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "command": "gh pr create --title x",
        },
        tmp_path,
        extra_env={"DEVFORGE_FIX_EVIDENCE_AUTO": "1"},
    )
    out = json.loads(p.stdout or "{}")
    assert out.get("decision") == "block"
    ctx = out.get("additional_context", "")
    assert SIGNAL_RE.search(ctx) is None


def test_severely_degraded_no_signal_even_with_auto(tmp_path):
    _init_repo(tmp_path)
    sha = _head_sha(tmp_path)
    _write_evidence(tmp_path, sha, decision="SEVERELY_DEGRADED")
    p = _run_hook(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "command": "gh pr create --title x",
        },
        tmp_path,
        extra_env={"DEVFORGE_FIX_EVIDENCE_AUTO": "1"},
    )
    out = json.loads(p.stdout or "{}")
    # SEVERELY_DEGRADED is advisory only, never blocks.
    assert out.get("decision") != "block"
    ctx = out.get("additional_context", "")
    assert SIGNAL_RE.search(ctx) is None
