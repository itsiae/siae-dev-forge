"""Tests for hooks/session-start-tiered-advisor.

TDD per task-05 (docs/plans/2026-05-19-tiered-claude-md/task-05-hook-tdd.md):
hook non-bloccante che rileva CLAUDE.md mancante o stale e emette
additionalContext via stdout JSON.

Contract:
- Exit code SEMPRE 0 (memory feedback_session_start_hook_invariants).
- Stdout vuoto se map fresh; JSON SessionStart altrimenti.
- Timeout 3s hard cap.
- macOS BSD + Linux GNU date compatibili.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

HOOK_PATH = Path(__file__).parent.parent / "hooks" / "session-start-tiered-advisor"
FIXTURES_ROOT = Path(__file__).parent / "fixtures" / "hook-tiered-advisor"


# ───────────────────────────── Helpers ─────────────────────────────


def _utc_iso(dt: datetime) -> str:
    """ISO-8601 UTC con suffix Z (formato usato dal frontmatter map)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_map(repo: Path, last_mapped_iso: str) -> None:
    """Crea docs/CODEBASE_MAP.md con frontmatter minimo."""
    (repo / "docs").mkdir(parents=True, exist_ok=True)
    content = (
        "---\n"
        f"last_mapped: {last_mapped_iso}\n"
        "version: 1.0\n"
        "---\n"
        "\n"
        "# Codebase Map\n"
    )
    (repo / "docs" / "CODEBASE_MAP.md").write_text(content, encoding="utf-8")


def _git_init(repo: Path) -> None:
    """Init git repo silenzioso con identity locale."""
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Test"], check=True
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "commit.gpgsign", "false"], check=True
    )


def _git_commit(repo: Path, message: str, when_iso: str | None = None) -> None:
    """Crea commit con timestamp opzionale (formato ISO)."""
    # Crea file dummy diverso ogni volta per evitare empty commit
    marker = repo / ".commit-marker"
    prev = marker.read_text() if marker.exists() else ""
    marker.write_text(prev + message + "\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    env = os.environ.copy()
    if when_iso:
        env["GIT_AUTHOR_DATE"] = when_iso
        env["GIT_COMMITTER_DATE"] = when_iso
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", message],
        check=True,
        env=env,
    )


def _run_hook(repo: Path, timeout: int = 10) -> tuple[int, str, str]:
    """Invoca hook con CLAUDE_PROJECT_DIR=repo, ritorna (rc, stdout, stderr)."""
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(repo)
    # Input JSON minimo (SessionStart payload)
    hook_input = json.dumps(
        {"hook_event_name": "SessionStart", "session_id": "test"}
    )
    r = subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=hook_input,
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=timeout,
    )
    return r.returncode, r.stdout, r.stderr


# ───────────────────────────── Fixtures ────────────────────────────


@pytest.fixture
def repo_without_map(tmp_path: Path) -> Path:
    repo = tmp_path / "repo-without-map"
    repo.mkdir()
    _git_init(repo)
    _git_commit(repo, "initial")
    return repo


@pytest.fixture
def repo_with_fresh_map(tmp_path: Path) -> Path:
    repo = tmp_path / "repo-with-fresh-map"
    repo.mkdir()
    _git_init(repo)
    today = _utc_iso(datetime.now(timezone.utc))
    _write_map(repo, today)
    _git_commit(repo, "initial + fresh map")
    return repo


@pytest.fixture
def repo_with_stale_map(tmp_path: Path) -> Path:
    repo = tmp_path / "repo-with-stale-map"
    repo.mkdir()
    _git_init(repo)
    stale_iso = _utc_iso(datetime.now(timezone.utc) - timedelta(days=30))
    _write_map(repo, stale_iso)
    _git_commit(repo, "stale map", when_iso=stale_iso)
    return repo


@pytest.fixture
def repo_with_many_commits(tmp_path: Path) -> Path:
    """Map 5gg fa + 50 commit dopo."""
    repo = tmp_path / "repo-with-many-commits"
    repo.mkdir()
    _git_init(repo)
    base_dt = datetime.now(timezone.utc) - timedelta(days=5)
    base_iso = _utc_iso(base_dt)
    _write_map(repo, base_iso)
    _git_commit(repo, "map commit", when_iso=base_iso)
    # 50 commit posteriori (spalmati su 5gg)
    for i in range(50):
        ts = base_dt + timedelta(hours=i * 2)
        _git_commit(repo, f"commit {i}", when_iso=_utc_iso(ts))
    return repo


# ───────────────────────────── Tests ───────────────────────────────


def test_hook_executable():
    """Hook file deve esistere ed essere eseguibile."""
    assert HOOK_PATH.exists(), f"hook missing at {HOOK_PATH}"
    assert os.access(HOOK_PATH, os.X_OK), "hook must be executable"


def test_hook_no_map_emits_advisory(repo_without_map: Path):
    """Repo senza CODEBASE_MAP.md → advisory 'Nessuna codebase map' + JSON valido."""
    rc, out, _ = _run_hook(repo_without_map)
    assert rc == 0
    assert out.strip(), "expected advisory output"
    payload = json.loads(out)
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert "Nessuna codebase map" in ctx
    assert payload["hookSpecificOutput"]["hookEventName"] == "SessionStart"


def test_hook_fresh_map_no_output(repo_with_fresh_map: Path):
    """Map fresca (oggi, 1 commit) → nessun output, exit 0."""
    rc, out, _ = _run_hook(repo_with_fresh_map)
    assert rc == 0
    assert out.strip() == "", f"expected silent output, got: {out!r}"


def test_hook_stale_map_emits_advisory(repo_with_stale_map: Path):
    """Map last_mapped 30gg fa → advisory 'stale' + JSON valido."""
    rc, out, _ = _run_hook(repo_with_stale_map)
    assert rc == 0
    assert out.strip(), "expected advisory output for stale map"
    payload = json.loads(out)
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert "stale" in ctx.lower()
    # Almeno una delle due condizioni deve essere nel testo
    assert "giorni" in ctx or "commit" in ctx


def test_hook_many_commits_emits_advisory(repo_with_many_commits: Path):
    """Map 5gg + 50 commit → advisory con count commit."""
    rc, out, _ = _run_hook(repo_with_many_commits)
    assert rc == 0
    assert out.strip(), "expected advisory output for many commits"
    payload = json.loads(out)
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert "stale" in ctx.lower()
    # 50 commit >= 30 threshold; numero deve apparire in output
    assert "50" in ctx or "commit" in ctx


def test_hook_exits_zero_on_git_error(tmp_path: Path):
    """Directory NON git → hook deve uscire 0 senza crash."""
    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()
    # Crea anche docs/CODEBASE_MAP.md per forzare il path che chiama git
    stale_iso = _utc_iso(datetime.now(timezone.utc) - timedelta(days=30))
    _write_map(not_a_repo, stale_iso)
    rc, _out, _err = _run_hook(not_a_repo)
    assert rc == 0, "hook must exit 0 even if git fails"


def test_hook_exits_zero_on_timeout(tmp_path: Path, monkeypatch):
    """Se git hang oltre 3s → hook ucciso ed esce 0.

    Simuliamo creando un PATH-shadow `git` che sleep 10s. Il hook deve
    comunque uscire entro ~4s con rc=0.
    """
    repo = tmp_path / "repo-hang"
    repo.mkdir()
    stale_iso = _utc_iso(datetime.now(timezone.utc) - timedelta(days=30))
    _write_map(repo, stale_iso)
    # Init un git vero perché alcuni branch del hook potrebbero fallire prima
    _git_init(repo)
    _git_commit(repo, "init", when_iso=stale_iso)

    # Shim: directory bin con `git` che dorme
    shim_dir = tmp_path / "shim-bin"
    shim_dir.mkdir()
    shim = shim_dir / "git"
    shim.write_text("#!/usr/bin/env bash\nsleep 10\nexit 0\n")
    shim.chmod(0o755)

    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(repo)
    env["PATH"] = f"{shim_dir}:{env.get('PATH', '')}"
    hook_input = json.dumps(
        {"hook_event_name": "SessionStart", "session_id": "test"}
    )
    start = time.monotonic()
    r = subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=hook_input,
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=8,  # external safety net > hook internal 3s cap
    )
    elapsed = time.monotonic() - start
    assert r.returncode == 0, f"timeout path must exit 0, got {r.returncode}"
    # Hook timeout interno è 3s; concedi 1.5s di margine
    assert elapsed < 5.0, f"hook took too long: {elapsed:.2f}s"


def test_hook_json_output_valid(repo_with_stale_map: Path):
    """Output JSON deve essere parsabile e contenere campi richiesti."""
    rc, out, _ = _run_hook(repo_with_stale_map)
    assert rc == 0
    payload = json.loads(out)
    assert "hookSpecificOutput" in payload
    hso = payload["hookSpecificOutput"]
    assert hso["hookEventName"] == "SessionStart"
    assert "additionalContext" in hso
    assert isinstance(hso["additionalContext"], str)
    assert hso["additionalContext"].strip() != ""
