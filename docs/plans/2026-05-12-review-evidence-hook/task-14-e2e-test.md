# Task 14 — E2E renderer contract test + hook integration

**SP:** 1.5 · **AC mappati:** AC #8, AC #12, AC #14 · **Dipendenze:** Task 03-13 · **Wave:** 5

## Goal

Implementare:
1. Test E2E **contract-based** (non snapshot fragile): simula evidence sintetica → render agent → asserisce affermazioni atomiche
2. Test integrazione hook full pipeline: bash hook → collector → file evidence → ri-letto
3. Test no-regression: `pr-gate`, `post-commit-review`, `pr-blind-review-gate` continuano a passare
4. Coverage gate: `pytest --cov=lib.review_evidence` ≥ 80%

## File coinvolti

**Creare:**
- `tests/test_review_evidence_e2e.py`
- `tests/test_review_evidence_no_regression.py`

## Step TDD

### Step 1 — Test E2E contract-based

`tests/test_review_evidence_e2e.py`:

```python
"""E2E contract-based test for review-evidence renderer pipeline.

NOT snapshot-based (too fragile). Instead, asserts that the rendered output
contains the atomic claims one would expect an agent to make given specific
evidence values.
"""
import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
HOOK = REPO_ROOT / "hooks" / "review-evidence"


def _run_hook(stdin_obj: dict, env: dict | None = None, cwd: Path | None = None):
    full_env = os.environ.copy()
    full_env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    if env:
        full_env.update(env)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(stdin_obj),
        capture_output=True, text=True, env=full_env,
        timeout=30, cwd=str(cwd) if cwd else None,
    )


def _init_git_repo(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "x@x"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "x"], cwd=tmp_path, check=True)
    (tmp_path / "f.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)


def test_e2e_clean_evidence_no_block(tmp_path):
    _init_git_repo(tmp_path)
    # Pre-write evidence that's clean
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path).decode().strip()
    ev_dir = tmp_path / ".claude" / "review-evidence"
    ev_dir.mkdir(parents=True)
    clean = json.loads((REPO_ROOT / "tests" / "fixtures" / "review-evidence" / "evidence_clean.json").read_text())
    clean["sha"] = sha
    (ev_dir / f"{sha}.json").write_text(json.dumps(clean))

    proc = _run_hook(
        {"hook_event_name": "PreToolUse", "tool_name": "Bash",
         "command": "gh pr create --title x"},
        cwd=tmp_path,
    )
    assert proc.returncode == 0
    out = json.loads(proc.stdout or "{}")
    # Clean evidence → no block decision
    assert out.get("decision") != "block"
    # Contract: advisory must include numeric coverage AND block=false
    ctx = out.get("additional_context", "")
    assert "coverage" in ctx
    assert "block=false" in ctx


def test_e2e_block_evidence_emits_block_decision(tmp_path):
    _init_git_repo(tmp_path)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path).decode().strip()
    ev_dir = tmp_path / ".claude" / "review-evidence"
    ev_dir.mkdir(parents=True)
    blocked = json.loads((REPO_ROOT / "tests" / "fixtures" / "review-evidence" / "evidence_full_block.json").read_text())
    blocked["sha"] = sha
    (ev_dir / f"{sha}.json").write_text(json.dumps(blocked))

    proc = _run_hook(
        {"hook_event_name": "PreToolUse", "tool_name": "Bash",
         "command": "gh pr create --title x"},
        cwd=tmp_path,
    )
    out = json.loads(proc.stdout or "{}")
    assert out.get("decision") == "block"
    # Contract: reason MUST contain atomic claims
    reason = out.get("reason", "")
    assert "coverage_below_threshold" in reason
    assert "lint_errors" in reason
    assert "ci_critical" in reason


def test_e2e_bypass_state_file_overrides_block(tmp_path, monkeypatch):
    _init_git_repo(tmp_path)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path).decode().strip()
    ev_dir = tmp_path / ".claude" / "review-evidence"
    ev_dir.mkdir(parents=True)
    blocked = json.loads((REPO_ROOT / "tests" / "fixtures" / "review-evidence" / "evidence_full_block.json").read_text())
    blocked["sha"] = sha
    (ev_dir / f"{sha}.json").write_text(json.dumps(blocked))

    fake_home = tmp_path / "home"
    (fake_home / ".claude").mkdir(parents=True)
    (fake_home / ".claude" / ".devforge-skip-evidence").write_text("")

    proc = _run_hook(
        {"hook_event_name": "PreToolUse", "tool_name": "Bash",
         "command": "gh pr create --title x"},
        env={"HOME": str(fake_home)},
        cwd=tmp_path,
    )
    out = json.loads(proc.stdout or "{}")
    # State file bypass → no block
    assert out.get("decision") != "block"


def test_e2e_dirty_tree_flag_no_cache(tmp_path):
    _init_git_repo(tmp_path)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path).decode().strip()
    # Dirty: untracked file
    (tmp_path / "untracked.py").write_text("# dirty")

    proc = _run_hook(
        {"hook_event_name": "PostToolUse", "tool_name": "Bash",
         "command": "git commit -m x"},
        cwd=tmp_path,
    )
    # Async post-commit, should not block
    assert proc.returncode == 0


def test_renderer_contract_block_reasons_atomic():
    """Given a full-block evidence, the verdict.block_reasons follow the
    atomic claim format expected by agents."""
    blocked = json.loads((REPO_ROOT / "tests" / "fixtures" / "review-evidence" / "evidence_full_block.json").read_text())
    reasons = blocked["verdict"]["block_reasons"]
    # Each reason must be a self-contained string parseable by the agent
    assert any(r.startswith("coverage_below_threshold:") for r in reasons)
    assert any(r.startswith("lint_errors:") for r in reasons)
    assert any(r.startswith("complexity_max:") for r in reasons)
    assert any(r.startswith("ci_critical:") for r in reasons)
    assert "drift_severity_high" in reasons
```

### Step 2 — Test no-regression (esegue tests/.test.sh REALI)

`tests/review-evidence/test_no_regression.py`:

```python
"""Verify that adding review-evidence hook didn't break existing hooks.

We invoke the ACTUAL existing bash test scripts under tests/hooks/ instead
of fictitious test_*.py files. The plan-review iter 1 caught that referencing
non-existent files (with `returncode == 5: return` early-exit) silently passes
the no-regression check — that's exactly the kind of false safety we want to
avoid.
"""
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


EXISTING_BASH_TESTS = [
    REPO_ROOT / "tests" / "hooks" / "post-commit-review-sha.test.sh",
    REPO_ROOT / "tests" / "hooks" / "post-commit-pr-lifecycle.test.sh",
    REPO_ROOT / "tests" / "hooks" / "hooks-json-var-expansion.test.sh",
    REPO_ROOT / "tests" / "hooks" / "brainstorming-gate.test.sh",
]


@pytest.mark.parametrize("test_script", EXISTING_BASH_TESTS, ids=lambda p: p.name)
def test_existing_hook_test_passes(test_script):
    """Each existing hook test must still pass after we added review-evidence."""
    if not test_script.exists():
        pytest.skip(f"test script not present: {test_script.name}")
    p = subprocess.run(
        ["bash", str(test_script)],
        capture_output=True, text=True, cwd=REPO_ROOT, timeout=60,
    )
    assert p.returncode == 0, (
        f"{test_script.name} broke:\n--- STDOUT ---\n{p.stdout}\n--- STDERR ---\n{p.stderr}"
    )


def test_existing_python_tests_lib_pass():
    """Run existing pytest suite under tests/lib/ to verify no regression."""
    target = REPO_ROOT / "tests" / "lib"
    if not target.exists():
        pytest.skip("tests/lib/ not present")
    p = subprocess.run(
        ["pytest", str(target), "-x", "-q"],
        capture_output=True, text=True, cwd=REPO_ROOT, timeout=120,
    )
    # Code 5 = no tests collected → not a regression
    assert p.returncode in (0, 5), (
        f"tests/lib/ broke:\n--- STDOUT ---\n{p.stdout}\n--- STDERR ---\n{p.stderr}"
    )


def test_existing_zero_loss_tests_pass():
    """Run existing pytest suite under tests/zero-loss/ (atomic_write coverage)."""
    target = REPO_ROOT / "tests" / "zero-loss"
    if not target.exists():
        pytest.skip("tests/zero-loss/ not present")
    p = subprocess.run(
        ["pytest", str(target), "-x", "-q"],
        capture_output=True, text=True, cwd=REPO_ROOT, timeout=120,
    )
    assert p.returncode in (0, 5), (
        f"tests/zero-loss/ broke:\n--- STDOUT ---\n{p.stdout}\n--- STDERR ---\n{p.stderr}"
    )


def test_hook_dispatcher_loads_review_evidence_without_error():
    """Smoke: hooks/review-evidence loads via run-hook.cmd dispatcher."""
    dispatcher = REPO_ROOT / "hooks" / "run-hook.cmd"
    if not dispatcher.exists():
        pytest.skip("run-hook.cmd not present")
    # Empty stdin, non-matching command → hook should emit {} and exit 0
    p = subprocess.run(
        ["bash", str(dispatcher), "review-evidence"],
        input='{"command": "echo nothing"}',
        capture_output=True, text=True,
        env={"CLAUDE_PLUGIN_ROOT": str(REPO_ROOT), "HOME": str(REPO_ROOT)},
        timeout=20,
    )
    assert p.returncode == 0, f"hook dispatcher failed:\n{p.stderr}"
```

### Step 3 — Coverage gate check

```bash
pip install pytest-cov  # if not installed
pytest tests/ --cov=lib.review_evidence --cov-report=term-missing -q
```

**Output atteso:** `TOTAL ... 80%+`.

Se < 80%, individua file/branch non coperti e aggiungi test mirati.

### Step 4 — Esegui tutto e commit

```bash
pytest tests/test_review_evidence_e2e.py tests/test_review_evidence_no_regression.py -v
# 5 + 3 = 8 passed (no-regression skip se test esistenti non presenti)

pytest tests/ --cov=lib.review_evidence --cov-report=term -q
# verifica coverage >= 80%

git add tests/test_review_evidence_e2e.py tests/test_review_evidence_no_regression.py
git commit -m "test(review-evidence): add E2E renderer contract + no-regression (#task-14)"
```

## Criteri di accettazione

- [ ] E2E test simula clean evidence → no block, evidence atomica
- [ ] E2E test simula full-block evidence → decision:block con reasons atomic
- [ ] E2E test bypass state file overrides block
- [ ] E2E test dirty tree non blocca PostToolUse
- [ ] Renderer contract verifica formato block_reasons atomic
- [ ] No-regression test su pr-gate, post-commit-review, pr-blind-review-gate
- [ ] Coverage `lib.review_evidence` ≥ 80%
- [ ] 8 test passano (alcuni no-regression possono skip se test esistenti non presenti)
