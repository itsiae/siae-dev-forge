# Task 29 — [TDD] test cli.py e2e

**Stato:** [PENDING]
**SP:** 1.5 Human / 0.5 Augmented
**Dipendenze:** task-28

## Goal

Test end-to-end CLI con fixture repo + diff. Verify output file + cache + idempotency.

## File coinvolti

- Create: `tests/test_release_risk_cli.py`

## Step

### Step 1 — Write test

Write `tests/test_release_risk_cli.py`:
```python
import subprocess
import json
from pathlib import Path
import pytest


@pytest.fixture
def fake_git_repo(tmp_path):
    """Crea un repo git fake con minimal struttura."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)
    # Simulate origin/main
    subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True)
    return tmp_path


@pytest.fixture
def diff_fixtures(tmp_path, fake_git_repo):
    diff_files = tmp_path / "diff_files.txt"
    diff_files.write_text("pom.xml\nsrc/App.java\n")
    diff_content = tmp_path / "diff_content.txt"
    diff_content.write_text("+ <dependency>x</dependency>\n+ public class App { }")
    return (str(diff_files), str(diff_content))


def test_cli_help():
    r = subprocess.run(
        ["python3", "-m", "lib.release_risk", "assess", "--help"],
        capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0
    assert "Release Risk" in r.stdout
    assert "--branch" in r.stdout
    assert "--service" in r.stdout


def test_cli_assess_minimal_run(fake_git_repo, diff_fixtures, monkeypatch):
    diff_files_path, diff_content_path = diff_fixtures
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", "/tmp/nonexistent")  # skip event emit gracefully
    r = subprocess.run(
        ["python3", "-m", "lib.release_risk", "assess",
         "--repo-root", str(fake_git_repo),
         "--branch", "release/1.0.0",
         "--service", "sport-test-service",
         "--diff-files", diff_files_path,
         "--diff-content", diff_content_path,
         "--no-cache"],
        capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0, f"stderr: {r.stderr}"
    output = json.loads(r.stdout.strip().split("\n")[-1])
    assert "level" in output
    assert "decision" in output
    assert "score" in output


def test_cli_writes_output_file(fake_git_repo, diff_fixtures):
    diff_files_path, diff_content_path = diff_fixtures
    subprocess.run(
        ["python3", "-m", "lib.release_risk", "assess",
         "--repo-root", str(fake_git_repo),
         "--branch", "release/1.0.0",
         "--service", "test-service",
         "--diff-files", diff_files_path,
         "--diff-content", diff_content_path,
         "--no-cache"],
        capture_output=True, text=True, check=True,
    )
    output_dir = fake_git_repo / "docs" / "releases"
    files = list(output_dir.glob("*.md"))
    assert len(files) == 1
    content = files[0].read_text()
    assert "Release Risk Scorecard" in content
    assert "<!-- release-risk:" in content  # idempotency marker


def test_cli_cache_idempotent_second_run(fake_git_repo, diff_fixtures):
    diff_files_path, diff_content_path = diff_fixtures
    args = ["python3", "-m", "lib.release_risk", "assess",
            "--repo-root", str(fake_git_repo),
            "--branch", "release/1.0.0",
            "--service", "test-service",
            "--diff-files", diff_files_path,
            "--diff-content", diff_content_path]
    r1 = subprocess.run(args, capture_output=True, text=True, check=True)
    r2 = subprocess.run(args, capture_output=True, text=True, check=True)
    out2 = json.loads(r2.stdout.strip().split("\n")[-1])
    assert out2.get("cached") is True
```

### Step 2 — Esegui

```bash
pytest tests/test_release_risk_cli.py -v
```
Output atteso: 4 PASSED (richiede `python3` + `git` disponibili).

### Step 3 — Commit

```bash
git add tests/test_release_risk_cli.py
git commit -m "test(release-risk): cli e2e (help + assess + output file + cache idempotent)"
```

## Criteri di accettazione

- [ ] 4 test PASSED
- [ ] Fixture git repo isolata via tmp_path
- [ ] Cache hit verificato su seconda run
- [ ] Idempotency marker in output file
- [ ] Commit eseguito
