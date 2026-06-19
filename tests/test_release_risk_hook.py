import subprocess
import json
import os
from pathlib import Path

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


# ---------------------------------------------------------------------------
# Robust trigger: l'hook deve scattare su QUALSIASI forma di `gh pr create`
# verso main (non solo `--base main` testuale), e verificare il base reale via
# GitHub. Setup: git repo fixture su branch release/** + gh mockato.
# ---------------------------------------------------------------------------

REPO_ROOT_DF = Path(__file__).parent.parent


def _make_git_repo(tmp_path):
    repo = tmp_path / "svc"
    repo.mkdir()
    sub = lambda *a: subprocess.run(list(a), cwd=repo, check=True,
                                    capture_output=True)
    sub("git", "init", "-q")
    sub("git", "config", "user.email", "t@t")
    sub("git", "config", "user.name", "t")
    (repo / "f.txt").write_text("x")
    sub("git", "add", "-A")
    sub("git", "commit", "-q", "-m", "init")
    sub("git", "checkout", "-q", "-b", "release/1.0")
    return repo


def _make_gh_mock(tmp_path, base="main"):
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    gh = bindir / "gh"
    gh.write_text(
        "#!/usr/bin/env bash\n"
        'case "$1 $2" in\n'
        '  "pr list") echo \'[{"number":7,"baseRefName":"' + base + '"}]\' ;;\n'
        '  "pr view") echo "razionale" ;;\n'
        '  "repo view") echo "itsiae/svc" ;;\n'
        '  "pr comment") exit 0 ;;\n'
        '  *) echo "" ;;\n'
        "esac\n"
        "exit 0\n"
    )
    gh.chmod(0o755)
    return bindir


def _run_in_repo(command, repo, bindir, home, extra_env=None):
    env = os.environ.copy()
    env["PATH"] = f"{bindir}:{env['PATH']}"
    env["HOME"] = str(home)
    env["PYTHONPATH"] = str(REPO_ROOT_DF)
    env["DEVFORGE_RELEASE_RISK_DISABLED"] = "0"
    # Evita tentativi di publish Confluence (timeout proxy) durante i test
    for k in list(env):
        if k.startswith("DEVFORGE_CONFLUENCE"):
            del env[k]
    if extra_env:
        env.update(extra_env)
    r = subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=json.dumps({"command": command}),
        capture_output=True, text=True, env=env, check=False, timeout=40,
        cwd=str(repo),
    )
    return r.returncode, r.stdout, r.stderr


def test_hook_triggers_on_short_flag_B_main(tmp_path):
    # `gh pr create -B main` — short flag: oggi il regex NON lo prende.
    repo = _make_git_repo(tmp_path)
    bindir = _make_gh_mock(tmp_path, base="main")
    home = tmp_path / "home"; home.mkdir()
    rc, out, _ = _run_in_repo("gh pr create -B main --head release/1.0", repo, bindir, home)
    assert rc == 0
    assert "siae-release-risk" in out  # ha superato tutti i gate → assessment


def test_hook_triggers_on_fill_default_base(tmp_path):
    # `gh pr create --fill` senza --base → base = default branch (main).
    repo = _make_git_repo(tmp_path)
    bindir = _make_gh_mock(tmp_path, base="main")
    home = tmp_path / "home"; home.mkdir()
    rc, out, _ = _run_in_repo("gh pr create --fill", repo, bindir, home)
    assert rc == 0
    assert "siae-release-risk" in out


def test_hook_triggers_on_bare_create(tmp_path):
    # `gh pr create --title x` senza base esplicito → verso main.
    repo = _make_git_repo(tmp_path)
    bindir = _make_gh_mock(tmp_path, base="main")
    home = tmp_path / "home"; home.mkdir()
    rc, out, _ = _run_in_repo("gh pr create --title x --body y", repo, bindir, home)
    assert rc == 0
    assert "siae-release-risk" in out


def test_hook_skip_when_pr_base_not_main(tmp_path):
    # Base reale != main (verificato via GitHub) → skip anche se è gh pr create.
    repo = _make_git_repo(tmp_path)
    bindir = _make_gh_mock(tmp_path, base="develop")
    home = tmp_path / "home"; home.mkdir()
    rc, out, _ = _run_in_repo("gh pr create --base develop", repo, bindir, home)
    assert rc == 0
    assert out.strip() == ""  # base != main → nessun assessment


def test_hook_skip_push_in_release_repo(tmp_path):
    # Regressione: un comando che non è gh pr create non scatta mai.
    repo = _make_git_repo(tmp_path)
    bindir = _make_gh_mock(tmp_path, base="main")
    home = tmp_path / "home"; home.mkdir()
    rc, out, _ = _run_in_repo("git push origin release/1.0", repo, bindir, home)
    assert rc == 0
    assert out.strip() == ""


def test_hook_any_pr_mode_triggers_non_main_base(tmp_path):
    # Modalità test DEVFORGE_RELEASE_RISK_ANY_PR=1: scatta su QUALSIASI PR,
    # anche base != main, per poter testare l'hook dal vivo. "Poi capiremo"
    # se restringere a release→main come default.
    repo = _make_git_repo(tmp_path)
    bindir = _make_gh_mock(tmp_path, base="develop")
    home = tmp_path / "home"; home.mkdir()
    rc, out, _ = _run_in_repo("gh pr create --base develop", repo, bindir, home,
                              extra_env={"DEVFORGE_RELEASE_RISK_ANY_PR": "1"})
    assert rc == 0
    assert "siae-release-risk" in out
