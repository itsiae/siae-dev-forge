# Task 05 — Python collector (coverage.py + ruff + radon)

**SP:** 1.0 · **AC mappati:** AC #3 · **Dipendenze:** Task 04 · **Wave:** 3

## Goal

Implementare `lib/review_evidence/collectors/python.py`: rileva repo Python (presenza di `pyproject.toml` o `*.py` files), invoca `coverage json`, `ruff check --output-format json`, `radon cc -j src/`. Tutti opzionali: missing tool → `{"available": false, "reason": "..."}`.

## File coinvolti

**Creare:**
- `lib/review_evidence/collectors/__init__.py` (vuoto)
- `lib/review_evidence/collectors/python.py`
- `tests/test_review_evidence_collector_python.py`
- `tests/fixtures/review-evidence/coverage_python.json`
- `tests/fixtures/review-evidence/ruff_output.json`
- `tests/fixtures/review-evidence/radon_cc.json`

## Step TDD

### Step 1 — Fixture

`tests/fixtures/review-evidence/coverage_python.json` (output reale di `coverage json`):

```json
{
  "meta": {"version": "7.0.0"},
  "files": {
    "src/foo.py": {"summary": {"covered_lines": 8, "num_statements": 10, "percent_covered": 80.0, "missing_lines": [12, 45]}},
    "src/bar.py": {"summary": {"covered_lines": 5, "num_statements": 10, "percent_covered": 50.0, "missing_lines": [3, 4, 7, 9, 11]}}
  },
  "totals": {"covered_lines": 13, "num_statements": 20, "percent_covered": 65.0}
}
```

`tests/fixtures/review-evidence/ruff_output.json`:

```json
[
  {"filename": "src/foo.py", "code": "E501", "message": "line too long", "location": {"row": 23, "column": 1}, "fix": null},
  {"filename": "src/foo.py", "code": "F401", "message": "unused import", "location": {"row": 5, "column": 1}, "fix": null}
]
```

`tests/fixtures/review-evidence/radon_cc.json`:

```json
{
  "src/foo.py": [{"type": "function", "name": "process", "complexity": 22, "rank": "E", "lineno": 10, "endline": 80}],
  "src/bar.py": [{"type": "function", "name": "helper", "complexity": 4, "rank": "A", "lineno": 5, "endline": 20}]
}
```

### Step 2 — Test fallente

`tests/test_review_evidence_collector_python.py`:

```python
"""Tests for Python collector."""
import json
from pathlib import Path
from unittest.mock import patch
import pytest

from lib.review_evidence.collectors.python import PythonCollector

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_is_applicable_when_pyproject_present(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool]")
    c = PythonCollector()
    assert c.is_applicable(tmp_path) is True


def test_is_applicable_when_py_files(tmp_path):
    (tmp_path / "main.py").write_text("# py")
    c = PythonCollector()
    assert c.is_applicable(tmp_path) is True


def test_not_applicable_otherwise(tmp_path):
    (tmp_path / "README.md").write_text("md")
    c = PythonCollector()
    assert c.is_applicable(tmp_path) is False


def test_collect_parses_coverage_ruff_radon(tmp_path):
    cov = (FIX / "coverage_python.json").read_text()
    ruff = (FIX / "ruff_output.json").read_text()
    radon = (FIX / "radon_cc.json").read_text()

    def fake_run(cmd, **kwargs):
        from subprocess import CompletedProcess
        if "coverage" in cmd[0] or "coverage" in (cmd[1] if len(cmd) > 1 else ""):
            return CompletedProcess(cmd, 0, stdout=cov, stderr="")
        if "ruff" in cmd[0]:
            return CompletedProcess(cmd, 0, stdout=ruff, stderr="")
        if "radon" in cmd[0]:
            return CompletedProcess(cmd, 0, stdout=radon, stderr="")
        return CompletedProcess(cmd, 1, stdout="", stderr="not found")

    (tmp_path / "pyproject.toml").write_text("[tool]")
    with patch("lib.review_evidence.collectors.python.subprocess.run", side_effect=fake_run):
        c = PythonCollector()
        result = c.collect(tmp_path, "main", "HEAD")

    assert result["stack"] == "python"
    assert result["coverage"]["overall_pct"] == 65.0
    assert result["coverage"]["source"] == "local:coverage.py"
    assert result["lint"]["errors"] + result["lint"]["warnings"] == 2
    assert result["lint"]["source"] == "local:ruff"
    assert result["complexity"]["max_cyclomatic"] == 22
    assert any(f["function"] == "process" for f in result["complexity"]["files_over_threshold"])


def test_collect_handles_missing_tools(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool]")

    def fake_run(cmd, **kwargs):
        raise FileNotFoundError(f"missing: {cmd[0]}")

    with patch("lib.review_evidence.collectors.python.subprocess.run", side_effect=fake_run):
        c = PythonCollector()
        result = c.collect(tmp_path, "main", "HEAD")

    assert result["stack"] == "python"
    # Each metric block reports availability flag
    assert result["coverage"] in (None, {}) or result["coverage"].get("overall_pct") in (None, 0.0)
    # Should not raise
```

### Step 3 — Implementa python.py

```python
"""Python stack collector: coverage.py + ruff + radon."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from lib.review_evidence.registry import register


class PythonCollector:
    name = "python"

    def is_applicable(self, repo_root: Path) -> bool:
        if (repo_root / "pyproject.toml").exists():
            return True
        if (repo_root / "setup.py").exists() or (repo_root / "requirements.txt").exists():
            return True
        return any(repo_root.rglob("*.py"))

    def collect(self, repo_root: Path, base_ref: str, head_ref: str) -> dict[str, Any]:
        return {
            "stack": "python",
            "coverage": self._coverage(repo_root),
            "lint": self._ruff(repo_root),
            "complexity": self._radon(repo_root),
        }

    def _coverage(self, repo_root: Path) -> dict[str, Any] | None:
        try:
            p = subprocess.run(
                ["coverage", "json", "--quiet", "-o", "-"],
                cwd=repo_root, capture_output=True, text=True, timeout=10, check=False,
            )
            if p.returncode != 0 or not p.stdout.strip():
                return None
            data = json.loads(p.stdout)
            per_file = [
                {"path": f, "pct": s["summary"]["percent_covered"],
                 "uncovered_lines": s["summary"].get("missing_lines", [])}
                for f, s in data.get("files", {}).items()
            ]
            return {
                "overall_pct": data["totals"]["percent_covered"],
                "delta_vs_base": 0.0,  # delta computed by orchestrator with base SHA comparison (out of scope MVP)
                "per_file": per_file,
                "source": "local:coverage.py",
            }
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None

    def _ruff(self, repo_root: Path) -> dict[str, Any] | None:
        try:
            p = subprocess.run(
                ["ruff", "check", "--output-format", "json", "."],
                cwd=repo_root, capture_output=True, text=True, timeout=10, check=False,
            )
            if not p.stdout.strip():
                return {"errors": 0, "warnings": 0, "findings": [], "source": "local:ruff"}
            findings = json.loads(p.stdout)
            errors = sum(1 for f in findings if f.get("code", "").startswith(("E", "F")))
            warnings = len(findings) - errors
            return {
                "errors": errors,
                "warnings": warnings,
                "findings": [
                    {"file": f["filename"], "line": f["location"]["row"],
                     "rule": f["code"], "severity": "error" if f["code"].startswith(("E","F")) else "warning",
                     "msg": f["message"]}
                    for f in findings
                ],
                "source": "local:ruff",
            }
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None

    def _radon(self, repo_root: Path) -> dict[str, Any] | None:
        try:
            src_dirs = ["src", "lib", "."]
            for d in src_dirs:
                target = repo_root / d
                if target.exists():
                    target_str = str(target)
                    break
            else:
                return None
            p = subprocess.run(
                ["radon", "cc", "-j", target_str],
                cwd=repo_root, capture_output=True, text=True, timeout=10, check=False,
            )
            if p.returncode != 0 or not p.stdout.strip():
                return None
            data = json.loads(p.stdout)
            files_over = []
            max_cx = 0
            for path, funcs in data.items():
                for f in funcs:
                    cx = f.get("complexity", 0)
                    if cx > max_cx:
                        max_cx = cx
                    if cx > 10:  # over-threshold = configurable, default 10 (under hard-block 15)
                        files_over.append({"path": path, "function": f.get("name", "?"),
                                           "cyclomatic": cx, "threshold": 10})
            return {
                "max_cyclomatic": max_cx,
                "files_over_threshold": files_over,
                "source": "local:radon",
            }
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None


register(PythonCollector())
```

### Step 4 — Esegui test

```bash
pytest tests/test_review_evidence_collector_python.py -v
```

**Output atteso:** 5 passed.

### Step 5 — Commit

```bash
git add lib/review_evidence/collectors/__init__.py \
        lib/review_evidence/collectors/python.py \
        tests/test_review_evidence_collector_python.py \
        tests/fixtures/review-evidence/coverage_python.json \
        tests/fixtures/review-evidence/ruff_output.json \
        tests/fixtures/review-evidence/radon_cc.json
git commit -m "feat(review-evidence): add Python collector (coverage+ruff+radon) (#task-05)"
```

## Criteri di accettazione

- [ ] `PythonCollector.is_applicable()` ritorna True su pyproject.toml o file `.py`
- [ ] `PythonCollector.collect()` parsa output di coverage/ruff/radon
- [ ] Missing tool → metric `None` (orchestrator gestisce, non solleva)
- [ ] 5 test passano
- [ ] Auto-register chiamato al module import
