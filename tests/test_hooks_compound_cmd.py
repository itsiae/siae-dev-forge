"""E2E: i gate token-based (pr-premortem, pr-blind-review, pre-commit) devono
scattare anche su comandi COMPOSTI (cd X && env -u P gh pr create ...), come i
gate regex-based (pr-gate/pr-release-gate), senza introdurre falsi positivi su
stringhe che contengono il comando.

Root cause coperta: _devforge_primary_cmd tagliava al primo operatore shell,
quindi il primo segmento (`cd X`) nascondeva il vero comando. Bypass realmente
avvenuto: PR #311 aperta senza premortem/blind-review (design doc
2026-06-11-hook-compound-cmd-match-design.md).
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

COMPOUND_PR = (
    'cd "/Users/x/repo" && env -u http_proxy -u https_proxy '
    "gh pr create --base main --title t --body-file /tmp/b.md"
)
ENV_PREFIX_PR = "env -u http_proxy gh pr create --base main"
PLAIN_PR = "gh pr create --base main --title t"
STRING_ONLY = "printf '{\"command\":\"gh pr create --base main\"}' > /tmp/x.json"
COMPOUND_COMMIT = 'cd "/Users/x/repo" && git commit -m "feat: x"'
PLAIN_COMMIT = 'git commit -m "feat: x"'


def run_hook(hook_name: str, command: str, tmp_home: Path,
             extra_env: dict | None = None) -> dict:
    """Pipe l'input JSON PreToolUse nell'hook reale, HOME isolata."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("DEVFORGE_SKIP")}
    env["HOME"] = str(tmp_home)
    env.pop("DEVFORGE_CURRENT_HOOK", None)
    if extra_env:
        env.update(extra_env)
    payload = json.dumps({"tool_input": {"command": command}})
    r = subprocess.run(
        ["bash", str(REPO_ROOT / "hooks" / hook_name)],
        input=payload, capture_output=True, text=True,
        cwd=REPO_ROOT, env=env, timeout=15,
    )
    out = r.stdout.strip() or "{}"
    return json.loads(out)


@pytest.fixture
def tmp_home(tmp_path):
    (tmp_path / ".claude").mkdir()
    return tmp_path


# --- pr-premortem-gate ---------------------------------------------------------

def test_premortem_gate_blocks_compound_command(tmp_home):
    out = run_hook("pr-premortem-gate", COMPOUND_PR, tmp_home)
    assert out.get("decision") == "block", f"bypass su comando composto: {out}"


def test_premortem_gate_blocks_env_prefix_command(tmp_home):
    out = run_hook("pr-premortem-gate", ENV_PREFIX_PR, tmp_home)
    assert out.get("decision") == "block", f"bypass su env -u: {out}"


def test_premortem_gate_blocks_plain_command(tmp_home):
    """Guard di regressione: il caso semplice deve continuare a bloccare."""
    out = run_hook("pr-premortem-gate", PLAIN_PR, tmp_home)
    assert out.get("decision") == "block"


def test_premortem_gate_ignores_command_inside_string(tmp_home):
    """Anti falso positivo: 'gh pr create' come STRINGA non deve bloccare."""
    out = run_hook("pr-premortem-gate", STRING_ONLY, tmp_home)
    assert out.get("decision") != "block", f"falso positivo su stringa: {out}"


def test_premortem_gate_skip_var_does_not_bypass(tmp_home):
    """DEVFORGE_SKIP_PREMORTEM rimosso: la var non deve più bypassare il gate."""
    out = run_hook("pr-premortem-gate", PLAIN_PR, tmp_home,
                   extra_env={"DEVFORGE_SKIP_PREMORTEM": "1"})
    assert out.get("decision") == "block", f"var ancora onorata (bypass): {out}"


# --- pr-blind-review-gate -------------------------------------------------------

def test_blind_review_gate_blocks_compound_command(tmp_home):
    out = run_hook("pr-blind-review-gate", COMPOUND_PR, tmp_home)
    assert out.get("decision") == "block", f"bypass su comando composto: {out}"


def test_blind_review_gate_ignores_command_inside_string(tmp_home):
    out = run_hook("pr-blind-review-gate", STRING_ONLY, tmp_home)
    assert out.get("decision") != "block"


def test_blind_review_gate_blocks_env_prefix_command(tmp_home):
    """Simmetria con il caso premortem (spec AC5: 'stessi casi')."""
    out = run_hook("pr-blind-review-gate", ENV_PREFIX_PR, tmp_home)
    assert out.get("decision") == "block", f"bypass su env -u: {out}"


def test_blind_review_gate_blocks_plain_command(tmp_home):
    out = run_hook("pr-blind-review-gate", PLAIN_PR, tmp_home)
    assert out.get("decision") == "block"


# --- pre-commit -----------------------------------------------------------------

def test_pre_commit_gate_blocks_compound_git_commit(tmp_home):
    out = run_hook("pre-commit", COMPOUND_COMMIT, tmp_home)
    assert out.get("decision") == "block", f"bypass su comando composto: {out}"


def test_pre_commit_gate_blocks_env_prefix_git_commit(tmp_home):
    """Simmetria env-prefix per il pre-commit gate."""
    out = run_hook("pre-commit", 'env -u GIT_DIR git commit -m "feat: x"', tmp_home)
    assert out.get("decision") == "block", f"bypass su env -u: {out}"


def test_pre_commit_gate_ignores_git_log_pipe_grep(tmp_home):
    """Anti falso positivo storico: `git log | grep commit` non e' un commit."""
    out = run_hook("pre-commit", "git log --oneline | grep commit", tmp_home)
    assert out.get("decision") != "block"


def test_pre_commit_gate_skip_var_does_not_bypass(tmp_home):
    """DEVFORGE_SKIP_GIT_GATE rimosso: la var non deve più bypassare il gate."""
    out = run_hook("pre-commit", PLAIN_COMMIT, tmp_home,
                   extra_env={"DEVFORGE_SKIP_GIT_GATE": "1"})
    assert out.get("decision") == "block", f"var ancora onorata (bypass): {out}"
