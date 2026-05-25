"""Integration tests for hooks/review-evidence (bash entry point).

Covers:
- executability + chmod +x
- non-matching command → empty-JSON no-op
- bypass via state file (~/.claude/.devforge-skip-evidence)
- bypass via env var fallback (DEVFORGE_SKIP_EVIDENCE=1)
- registration in hooks/hooks.json (PreToolUse + PostToolUse Bash matchers)
- decision=block on PreToolUse gh pr edit when verdict.block=true

The hook honors a `cwd` field in the stdin envelope (Claude Code passes this);
tests that need a controlled git HEAD use a tmp_path repo and inject cwd
into the envelope so the hook resolves SHA + evidence dir against it.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent
HOOK = REPO_ROOT / "hooks" / "review-evidence"


def _run_hook(stdin_json: dict, env: dict | None = None) -> tuple[int, str, str]:
    full_env = os.environ.copy()
    full_env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    if env:
        full_env.update(env)
    proc = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(stdin_json),
        capture_output=True,
        text=True,
        env=full_env,
        timeout=20,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_hook_is_executable():
    assert HOOK.exists()
    assert os.access(HOOK, os.X_OK)


def test_hook_emits_empty_json_on_non_matching_command():
    """PreToolUse with a non-`gh pr` command must early-return `{}`."""
    rc, out, _ = _run_hook({
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "command": "echo hello",
    })
    assert rc == 0
    parsed = json.loads(out or "{}")
    assert parsed == {}


def test_hook_blocks_on_gh_pr_edit_with_blocking_evidence(tmp_path):
    """gh pr edit must trigger the same PreToolUse blocking path as gh pr create."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "x@x"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "x"], cwd=tmp_path, check=True)
    # macOS dev boxes often have commit.gpgsign=true globally; disable locally.
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, check=True)
    (tmp_path / "f.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "x"], cwd=tmp_path, check=True, capture_output=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path).decode().strip()
    ev_dir = tmp_path / ".claude" / "review-evidence"
    ev_dir.mkdir(parents=True)
    blocked = {
        "schema_version": "1.0",
        "sha": sha,
        "verdict": {
            "block": True,
            "block_reasons": ["coverage_below_threshold:45<60"],
            "warnings": [],
        },
    }
    (ev_dir / f"{sha}.json").write_text(json.dumps(blocked))

    rc, out, _ = _run_hook({
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "command": "gh pr edit 123 --add-label review-ready",
        "cwd": str(tmp_path),
    })
    parsed = json.loads(out or "{}")
    assert parsed.get("decision") == "block"


def test_hook_bypass_state_file(tmp_path):
    """When the bypass state file exists, hook must skip processing."""
    skip_file = tmp_path / ".claude" / ".devforge-skip-evidence"
    skip_file.parent.mkdir(parents=True)
    skip_file.write_text("")
    rc, out, _ = _run_hook(
        {"command": "gh pr create --title x"},
        env={"HOME": str(tmp_path)},
    )
    parsed = json.loads(out or "{}")
    assert rc == 0
    # bypassed: no block decision
    assert parsed.get("decision") != "block"


def test_hook_bypass_env_var_fallback(tmp_path):
    """When state file is absent but DEVFORGE_SKIP_EVIDENCE=1, hook still bypasses."""
    rc, out, _ = _run_hook(
        {"command": "gh pr create --title x"},
        # Force HOME to a path without the skip file to prove env-var fallback fires.
        env={"DEVFORGE_SKIP_EVIDENCE": "1", "HOME": str(tmp_path)},
    )
    parsed = json.loads(out or "{}")
    assert rc == 0
    assert parsed.get("decision") != "block"


def test_hook_registered_in_hooks_json():
    hooks_json = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text())
    pre_bash = [
        h for entry in hooks_json["hooks"]["PreToolUse"]
        if entry["matcher"] == "Bash"
        for h in entry["hooks"]
    ]
    assert any("review-evidence" in h["command"] for h in pre_bash)
    post_bash = [
        h for entry in hooks_json["hooks"]["PostToolUse"]
        if entry["matcher"] == "Bash"
        for h in entry["hooks"]
    ]
    assert any("review-evidence" in h["command"] for h in post_bash)
