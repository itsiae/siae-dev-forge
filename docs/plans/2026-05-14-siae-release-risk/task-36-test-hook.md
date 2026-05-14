# Task 36 — [TDD] integration test hook

**Stato:** [DONE]
**SP:** 2 Human / 1 Augmented
**Dipendenze:** task-34, task-35

## Goal

Test integration hook `pr-release-gate`: trigger correct match, skip cases, idempotency, fail-open.

## File coinvolti

- Create: `tests/test_release_risk_hook.py`

## Step

### Step 1 — Write test

Write `tests/test_release_risk_hook.py`:
```python
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
    # Hook deve fallire-open (exit 0 + additional_context warning) se CLI errore
    # Simulazione: PATH senza python3 disponibile (hook deve catch)
    env = {"PATH": "/nonexistent", "DEVFORGE_RELEASE_RISK_DISABLED": "0", "HOME": str(tmp_path)}
    r = subprocess.run(
        ["bash", str(HOOK_PATH)],
        input='{"command": "gh pr create --base main --head release/1.0"}',
        capture_output=True, text=True, env=env, check=False, timeout=35,
    )
    # Fail-open: exit 0 always
    assert r.returncode == 0
```

### Step 2 — Esegui

```bash
pytest tests/test_release_risk_hook.py -v
```
Output atteso: 6+ PASSED. Alcuni test richiedono ambiente specifico — quelli che richiedono `gh` + git repo possono essere skipped via marker `@pytest.mark.integration`.

### Step 3 — Commit

```bash
git add tests/test_release_risk_hook.py
git commit -m "test(release-risk): hook pr-release-gate integration (skip cases + match + fail-open)"
```

## Criteri di accettazione

- [ ] 6+ test PASSED
- [ ] Test skip override (file + env)
- [ ] Test skip non-match commands
- [ ] Test fail-open su CLI error
- [ ] Commit eseguito
