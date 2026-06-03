"""E2E contract-based test for review-evidence renderer pipeline.

NOT snapshot-based (too fragile). Instead, asserts that the rendered output
contains the atomic claims one would expect an agent to make given specific
evidence values.

Fixtures used (created in Task 01):
- tests/fixtures/review-evidence/evidence_clean.json
- tests/fixtures/review-evidence/evidence_full_block.json

Each test bootstraps a tmp_path git repo, drops a synthetic evidence file
under .claude/review-evidence/<sha>.json, invokes the hook, and asserts
the contract (decision, additional_context, reason) against atomic claims.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / "hooks" / "review-evidence"


def _run_hook(stdin_obj: dict, env: dict | None = None, cwd: Path | None = None):
    """Invoke hooks/review-evidence with stdin JSON, return CompletedProcess.

    Preserves parent env (PATH/etc.) and overlays `env` on top so partial-env
    callers don't lose `bash` resolution on macOS.
    """
    full_env = os.environ.copy()
    full_env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    if env:
        full_env.update(env)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(stdin_obj),
        capture_output=True,
        text=True,
        env=full_env,
        timeout=30,
        cwd=str(cwd) if cwd else None,
    )


def _init_git_repo(tmp_path: Path) -> None:
    """Initialize a minimal git repo in tmp_path with one commit.

    Disables commit + tag gpg signing locally so machines with global
    `commit.gpgsign=true` (common on macOS dev boxes) don't break the
    initial commit.
    """
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "x@x"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "x"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "tag.gpgsign", "false"], cwd=tmp_path, check=True)
    (tmp_path / "f.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path, check=True, capture_output=True,
    )


def _load_fixture(name: str) -> dict:
    return json.loads(
        (REPO_ROOT / "tests" / "fixtures" / "review-evidence" / name).read_text()
    )


def _stage_evidence(tmp_path: Path, fixture_name: str) -> str:
    """Drop the fixture rewritten with the tmp_path HEAD sha into
    .claude/review-evidence/<sha>.json and return the sha."""
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path
    ).decode().strip()
    ev_dir = tmp_path / ".claude" / "review-evidence"
    ev_dir.mkdir(parents=True, exist_ok=True)
    payload = _load_fixture(fixture_name)
    payload["sha"] = sha
    (ev_dir / f"{sha}.json").write_text(json.dumps(payload))
    return sha


# ── E2E #1 — clean evidence: no block, advisory present ──────────────────
def test_e2e_clean_evidence_no_block(tmp_path):
    _init_git_repo(tmp_path)
    _stage_evidence(tmp_path, "evidence_clean.json")

    proc = _run_hook(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "command": "gh pr create --title x",
        },
        cwd=tmp_path,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout or "{}")
    # Clean evidence → no block decision
    assert out.get("decision") != "block"
    ctx = out.get("additional_context", "")
    # Contract: advisory must include numeric coverage AND block=false marker
    assert "coverage" in ctx
    assert "block=false" in ctx


# ── E2E #2 — full-block evidence: decision=block + atomic reasons ────────
def test_e2e_block_evidence_emits_block_decision(tmp_path):
    _init_git_repo(tmp_path)
    _stage_evidence(tmp_path, "evidence_full_block.json")

    proc = _run_hook(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "command": "gh pr create --title x",
        },
        cwd=tmp_path,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout or "{}")
    assert out.get("decision") == "block"
    # Contract: reason MUST surface atomic claims agents can parse
    reason = out.get("reason", "")
    assert "coverage_below_threshold" in reason
    assert "lint_errors" in reason
    assert "ci_critical" in reason


# ── E2E #3 — bypass state file overrides block ────────────────────────────
def test_e2e_bypass_state_file_overrides_block(tmp_path):
    _init_git_repo(tmp_path)
    _stage_evidence(tmp_path, "evidence_full_block.json")

    fake_home = tmp_path / "home"
    (fake_home / ".claude").mkdir(parents=True)
    (fake_home / ".claude" / ".devforge-skip-evidence").write_text("")

    proc = _run_hook(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "command": "gh pr create --title x",
        },
        env={"HOME": str(fake_home)},
        cwd=tmp_path,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout or "{}")
    # State-file bypass → no block decision (advisory may also be empty)
    assert out.get("decision") != "block"


# ── E2E #4 — dirty tree on PostToolUse: async path, no block ──────────────
def test_e2e_dirty_tree_flag_no_cache(tmp_path):
    _init_git_repo(tmp_path)
    # Make the tree dirty with an untracked file (not under .claude/, so it
    # passes the hook's dirty-check filter that ignores plugin output).
    (tmp_path / "untracked.py").write_text("# dirty")

    proc = _run_hook(
        {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "command": "git commit -m x",
        },
        cwd=tmp_path,
    )
    # Async post-commit path must not block; returncode 0, never decision=block.
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout or "{}")
    assert out.get("decision") != "block"


# ── E2E #5 — renderer contract: block_reasons atomic format ───────────────
def test_renderer_contract_block_reasons_atomic():
    """Given a full-block fixture, verdict.block_reasons follow the atomic
    claim format expected by downstream renderer agents (code-reviewer,
    spec-reviewer)."""
    blocked = _load_fixture("evidence_full_block.json")
    reasons = blocked["verdict"]["block_reasons"]
    # Each reason must be a self-contained string parseable by the agent
    assert any(r.startswith("coverage_below_threshold:") for r in reasons)
    assert any(r.startswith("lint_errors:") for r in reasons)
    assert any(r.startswith("complexity_max:") for r in reasons)
    assert any(r.startswith("ci_critical:") for r in reasons)
    assert "drift_severity_high" in reasons
