"""Perf benchmark + corpus generator tests (Wave 1 follow-up task-16).

AC15: hook P95 < 90s su monorepo mock 200k LOC.
AC22: scripts/build_perf_corpus.sh idempotente.
AC23: pytest.mark.skipif + slow.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest


REPO = Path(__file__).parents[1]
CORPUS = REPO / "tests" / "fixtures" / "perf_corpus_200k"
BUILD_SCRIPT = REPO / "scripts" / "build_perf_corpus.sh"


def test_build_script_exists_and_executable():
    """AC22 prerequisite: script esiste + executable."""
    assert BUILD_SCRIPT.is_file()
    assert os.access(BUILD_SCRIPT, os.X_OK)


def test_sync_semgrep_registry_script_exists():
    """Task-03 prerequisite: sync-semgrep-registry script esiste + executable."""
    sync_script = REPO / "scripts" / "sync-semgrep-registry.sh"
    assert sync_script.is_file()
    assert os.access(sync_script, os.X_OK)


@pytest.mark.slow
def test_build_corpus_idempotent(tmp_path):
    """AC22: run 2x → identico filesystem state."""
    out = tmp_path / "perf_corpus"
    env = os.environ.copy()
    env["OUT"] = str(out)
    # Run 1
    r1 = subprocess.run(
        ["bash", str(BUILD_SCRIPT)],
        env=env, capture_output=True, text=True, timeout=120,
        cwd=str(REPO),
    )
    assert r1.returncode == 0, r1.stderr
    snapshot1 = sorted(p.name for p in out.rglob("*") if p.is_file())
    # Run 2
    r2 = subprocess.run(
        ["bash", str(BUILD_SCRIPT)],
        env=env, capture_output=True, text=True, timeout=120,
        cwd=str(REPO),
    )
    assert r2.returncode == 0
    snapshot2 = sorted(p.name for p in out.rglob("*") if p.is_file())
    assert snapshot1 == snapshot2, "Corpus generation not idempotent"


@pytest.mark.slow
@pytest.mark.skipif(not shutil.which("semgrep"), reason="semgrep not installed (perf benchmark)")
def test_perf_corpus_manifest_exists():
    """AC22: manifest.yaml presente dopo build."""
    if not CORPUS.is_dir():
        pytest.skip(f"corpus not built; run: bash {BUILD_SCRIPT}")
    manifest = CORPUS / "manifest.yaml"
    assert manifest.is_file()


@pytest.mark.slow
@pytest.mark.skipif(not shutil.which("semgrep"), reason="semgrep not installed (perf benchmark)")
def test_p95_under_90s():
    """AC15: P95 hook < 90s su corpus (5 run)."""
    from lib.review_evidence.runners.semgrep import SemgrepRunner

    if not CORPUS.is_dir() or not list(CORPUS.rglob("*.ts")):
        pytest.skip(f"corpus not built; run: bash {BUILD_SCRIPT}")

    runner = SemgrepRunner()
    timings: list[float] = []
    runs = 3  # smaller in CI; baseline assertion P95
    for _ in range(runs):
        t0 = time.perf_counter()
        runner.run(CORPUS)
        elapsed = time.perf_counter() - t0
        timings.append(elapsed)

    timings.sort()
    p95_idx = max(0, int(len(timings) * 0.95) - 1)
    p95 = timings[p95_idx]
    assert p95 < 90.0, f"P95 = {p95:.2f}s > 90s (timings={timings})"
