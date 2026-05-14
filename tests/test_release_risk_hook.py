import subprocess
import json
import os
from pathlib import Path
import pytest

HOOK_PATH = Path(__file__).parent.parent / "hooks" / "pr-release-gate"


def _run_hook(command: str, env_extra: dict = None) -> tuple[int, str, str]:
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    hook_input = json.dumps({"command": command, "tool_input": {"command": command}})
    r = subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=hook_input, capture_output=True, text=True, env=env, check=False,
        timeout=35,
    )
    return (r.returncode, r.stdout, r.stderr)


def test_hook_executable():
    assert HOOK_PATH.exists()
    assert os.access(HOOK_PATH, os.X_OK)


def test_hook_skip_if_disabled_file(tmp_path, monkeypatch):
    # Path corretto: hook cerca in $HOME/.claude/.devforge-skip-release-risk
    skip_dir = tmp_path / ".claude"
    skip_dir.mkdir(parents=True, exist_ok=True)
    skip_file = skip_dir / ".devforge-skip-release-risk"
    skip_file.touch()
    rc, out, err = _run_hook("gh pr create --base main --head release/1.0",
                             env_extra={"HOME": str(tmp_path)})
    assert rc == 0
    assert out.strip() == ""  # silent skip


def test_hook_skip_if_disabled_env():
    rc, out, _ = _run_hook("gh pr create --base main --head release/1.0",
                          env_extra={"DEVFORGE_RELEASE_RISK_DISABLED": "1"})
    assert rc == 0
    assert out.strip() == ""


def test_hook_skip_non_gh_pr_create():
    rc, out, _ = _run_hook("git push origin main")
    assert rc == 0
    assert out.strip() == ""  # NO match → skip silenzioso


def test_hook_skip_pr_create_base_not_main():
    rc, out, _ = _run_hook("gh pr create --base release/2.0 --head feature/x")
    assert rc == 0
    assert out.strip() == ""  # base != main → skip


def test_hook_extracts_command_from_jq_input():
    # Verifica che jq parse correttamente input wrapped
    hook_input = '{"command": "gh pr create --base main --head release/1.0", "tool_input": {}}'
    r = subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=hook_input, capture_output=True, text=True, check=False, timeout=35,
        env={**os.environ, "DEVFORGE_RELEASE_RISK_DISABLED": "0"},
    )
    # Non testiamo l'output completo (richiede gh + python module + git repo),
    # solo che il hook NON crashi su input ben formato
    assert r.returncode == 0


def test_hook_fail_open_on_cli_error(monkeypatch, tmp_path):
    # Hook deve fallire-open (exit 0 + additional_context warning) se CLI errore.
    # Simulazione: invoca hook in tmp_path che NON è un git repo (rev-parse fallirà,
    # diff vuoto, CLI riceverà input invalido o subprocess.run fallirà nel fetch).
    # Hook deve uscire 0 sempre.
    env = os.environ.copy()
    env["DEVFORGE_RELEASE_RISK_DISABLED"] = "0"
    env["HOME"] = str(tmp_path)
    r = subprocess.run(
        ["bash", str(HOOK_PATH)],
        input='{"command": "gh pr create --base main --head release/1.0"}',
        capture_output=True, text=True, env=env, check=False, timeout=35,
        cwd=str(tmp_path),  # non-git directory → forza fallimento upstream
    )
    # Fail-open: exit 0 always (anche se git/gh/python3 falliscono)
    assert r.returncode == 0
