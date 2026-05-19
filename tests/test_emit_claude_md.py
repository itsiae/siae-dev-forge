"""TDD tests for `skills/siae-codebase-map-tiered/scripts/emit-claude-md.py`.

Six required cases (see docs/plans/2026-05-19-tiered-claude-md/task-02):

1. L1 root from a single-repo Java fixture (no L2)
2. L2 per package on a monorepo TS fixture (3 packages)
3. L3 emitted only above the >=10 file + distinctive pattern threshold
4. Anti-bloat warning when CODEBASE_MAP forces L1 > 200 lines
5. ``--dry-run`` writes nothing
6. Missing CODEBASE_MAP exits 1 with stderr message
"""
from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills" / "siae-codebase-map-tiered" / "scripts" / "emit-claude-md.py"
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "codebase-map-samples"


def _load_module():
    """Load the hyphenated script as a Python module so coverage can hook it."""
    spec = importlib.util.spec_from_file_location("emit_claude_md", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_EMIT = _load_module()


class _CompletedLike:
    def __init__(self, returncode: int, stdout: str, stderr: str):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _run(root: Path, map_path: Path, dry_run: bool = False):
    argv = ["--root", str(root), "--map", str(map_path)]
    if dry_run:
        argv.append("--dry-run")
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = _EMIT.main(argv)
    return _CompletedLike(rc, out.getvalue(), err.getvalue())


def _payload(res):
    assert res.returncode == 0, f"stderr: {res.stderr}\nstdout: {res.stdout}"
    return json.loads(res.stdout)


@pytest.fixture
def java_root(tmp_path):
    root = tmp_path / "java-repo"
    root.mkdir()
    (root / "docs").mkdir()
    map_path = root / "docs" / "CODEBASE_MAP.md"
    map_path.write_text(
        (FIXTURES_DIR / "single-repo-java.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return root, map_path


@pytest.fixture
def monorepo_root(tmp_path):
    root = tmp_path / "ts-monorepo"
    root.mkdir()
    (root / "docs").mkdir()
    map_path = root / "docs" / "CODEBASE_MAP.md"
    map_path.write_text(
        (FIXTURES_DIR / "monorepo-ts.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return root, map_path


def test_emit_l1_root_from_single_repo_java(java_root):
    root, map_path = java_root
    res = _run(root, map_path, dry_run=True)
    data = _payload(res)
    assert data["files_written"] == ["./CLAUDE.md"]
    assert data["l1_lines"] <= 200
    assert data["l2_count"] == 0
    assert data["l3_count"] == 0
    assert data["warnings"] == []


def test_emit_l2_per_package_in_monorepo_ts(monorepo_root):
    root, map_path = monorepo_root
    res = _run(root, map_path, dry_run=False)
    data = _payload(res)
    assert data["l2_count"] == 3
    expected_l2 = {"./api/CLAUDE.md", "./web/CLAUDE.md", "./shared/CLAUDE.md"}
    assert expected_l2.issubset(set(data["files_written"]))
    for rel in expected_l2:
        body = (root / rel.lstrip("./")).read_text(encoding="utf-8")
        assert "@../CLAUDE.md" in body, f"missing parent import in {rel}"


def test_emit_l3_only_above_threshold(tmp_path):
    root = tmp_path / "l3-repo"
    root.mkdir()
    (root / "docs").mkdir()
    map_path = root / "docs" / "CODEBASE_MAP.md"
    map_path.write_text(
        """---
last_mapped: 2026-05-15T00:00:00Z
total_files: 50
stack:
  - typescript
---

# Codebase Map — l3-test

## Panoramica Sistema

Two packages, each with a candidate subdir, only one above threshold.

## Stack

- TypeScript

## Convenzioni SIAE Osservate

- Naming kebab-case

## Gotcha

- None

## Guida Moduli

### api

**Path:** api
**Stack:** Express
**Description:** REST.

#### handlers

**Files:** 8
**Pattern:** Express middleware chain (below threshold).

### web

**Path:** web
**Stack:** Vue
**Description:** SPA.

#### legacy-jquery

**Files:** 15
**Pattern:** jQuery scaffold preserved for migration, mock setup distinto.
""",
        encoding="utf-8",
    )
    res = _run(root, map_path, dry_run=False)
    data = _payload(res)
    assert data["l3_count"] == 1
    assert "./web/legacy-jquery/CLAUDE.md" in data["files_written"]
    assert "./api/handlers/CLAUDE.md" not in data["files_written"]
    l3_file = root / "web" / "legacy-jquery" / "CLAUDE.md"
    assert l3_file.is_file()
    assert "@../../CLAUDE.md" in l3_file.read_text(encoding="utf-8")


def test_emit_l1_anti_bloat_warning(tmp_path):
    root = tmp_path / "bloat-repo"
    root.mkdir()
    (root / "docs").mkdir()
    map_path = root / "docs" / "CODEBASE_MAP.md"
    huge_panoramica = "\n".join(f"Riga di descrizione numero {i}." for i in range(400))
    map_path.write_text(
        f"""---
last_mapped: 2026-05-15T00:00:00Z
total_files: 999
stack:
  - python
---

# Codebase Map — bloat-test

## Panoramica Sistema

{huge_panoramica}

## Stack

- Python

## Convenzioni SIAE Osservate

- None

## Gotcha

- None

## Guida Moduli

### sample

**Path:** .
**Stack:** Python
""",
        encoding="utf-8",
    )
    res = _run(root, map_path, dry_run=True)
    data = _payload(res)
    assert any("L1 exceeds 200 lines" in w for w in data["warnings"]), data["warnings"]


def test_dry_run_writes_nothing(monorepo_root):
    root, map_path = monorepo_root
    res = _run(root, map_path, dry_run=True)
    _payload(res)
    assert not (root / "CLAUDE.md").exists()
    for pkg in ("api", "web", "shared"):
        assert not (root / pkg / "CLAUDE.md").exists()


def test_missing_codebase_map_fails(tmp_path):
    res = _run(tmp_path, tmp_path / "nope.md")
    assert res.returncode == 1
    assert "CODEBASE_MAP.md not found" in res.stderr
    # Belt-and-suspenders: also confirm the CLI entry-point returns 1 on missing
    # map (catches breakage of ``if __name__`` wiring) — invokes via subprocess.
    cli = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--root",
            str(tmp_path),
            "--map",
            str(tmp_path / "nope.md"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert cli.returncode == 1
    assert "CODEBASE_MAP.md not found" in cli.stderr
