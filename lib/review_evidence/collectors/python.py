"""Python stack collector: coverage.py + ruff + radon."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Iterator, Optional

from lib.review_evidence.registry import register


# E17 mitigation — never walk into these directories. Vendored third-party
# code or build artefacts can trivially contain 50k+ .py files (e.g. .venv,
# node_modules) and an unbounded ``Path.rglob("*.py")`` on a monorepo can
# stall ``is_applicable`` for minutes. PRUNE_DIRS is the union of: virtualenvs,
# JS deps, build outputs, VCS, Python caches, vendoring conventions.
PRUNE_DIRS = frozenset(
    {
        ".venv",
        "venv",
        ".tox",
        ".nox",
        "node_modules",
        "__pycache__",
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "vendor",
        "target",   # Maven / Rust / Cargo
        "build",    # Gradle / setuptools
        "dist",
        ".gradle",
        ".idea",
        ".vscode",
    }
)

# Depth cap to bound walk time even when PRUNE_DIRS misses a custom-named
# vendor folder. 5 levels is enough for nearly all real repos
# (e.g. ``services/<svc>/src/main/python/<pkg>``).
MAX_WALK_DEPTH = 5


def _walk_with_prune(
    root: Path,
    suffix: str,
    max_depth: int = MAX_WALK_DEPTH,
    first_only: bool = False,
) -> Iterator[Path]:
    """Yield files under ``root`` ending in ``suffix``, pruning noise dirs.

    Stops early when ``first_only=True`` and one file has been found — this
    lets ``is_applicable`` answer in O(1) on monorepos. Depth is computed
    relative to ``root`` so a max_depth=5 means we never descend beyond
    ``root/a/b/c/d/e``.
    """
    root = Path(root)
    base_parts = len(root.parts)
    for dirpath, dirnames, filenames in os.walk(root):
        depth = len(Path(dirpath).parts) - base_parts
        if depth >= max_depth:
            # Prevent any further descent
            dirnames[:] = []
        else:
            # Mutate dirnames in-place so os.walk skips pruned subtrees
            dirnames[:] = [d for d in dirnames if d not in PRUNE_DIRS]
        for f in filenames:
            if f.endswith(suffix):
                yield Path(dirpath) / f
                if first_only:
                    return


class PythonCollector:
    name = "python"

    def is_applicable(self, repo_root: Path) -> bool:
        if (repo_root / "pyproject.toml").exists():
            return True
        if (repo_root / "setup.py").exists() or (repo_root / "requirements.txt").exists():
            return True
        # E17: bounded walk — first hit short-circuits.
        return next(_walk_with_prune(repo_root, ".py", first_only=True), None) is not None

    def collect(self, repo_root: Path, base_ref: str, head_ref: str) -> dict[str, Any]:
        return {
            "stack": "python",
            "coverage": self._coverage(repo_root),
            "lint": self._ruff(repo_root),
            "complexity": self._radon(repo_root),
        }

    def _coverage(self, repo_root: Path) -> Optional[dict[str, Any]]:
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

    def _ruff(self, repo_root: Path) -> Optional[dict[str, Any]]:
        """Run ruff and bucket findings into errors vs warnings.

        Q05-M1 mitigation — the previous severity rule classified every
        ``E`` and ``F`` rule as ``error``. ``E1-E7`` are style issues
        (pep8) and inflate ``lint_errors`` past the hard-block threshold
        for repos that simply have not run ``ruff format``. Restrict
        ``error`` to genuine syntactic / pyflakes / static-analysis bugs:

        * ``F*`` (pyflakes: unused import, undefined name, etc.)
        * ``E9*`` (syntax errors: E999 IndentationError, …)
        * ``B*`` (flake8-bugbear: mutable default args, …)

        Everything else is a warning.
        """
        try:
            p = subprocess.run(
                ["ruff", "check", "--output-format", "json", "."],
                cwd=repo_root, capture_output=True, text=True, timeout=10, check=False,
            )
            if not p.stdout.strip():
                return {"errors": 0, "warnings": 0, "findings": [], "source": "local:ruff"}
            findings = json.loads(p.stdout)

            def _is_error(code: str) -> bool:
                if not code:
                    return False
                if code.startswith("F"):
                    return True
                if code.startswith("E9"):
                    return True
                if code.startswith("B"):
                    return True
                return False

            errors = sum(1 for f in findings if _is_error(f.get("code", "")))
            warnings = len(findings) - errors
            return {
                "errors": errors,
                "warnings": warnings,
                "findings": [
                    {"file": f["filename"], "line": f["location"]["row"],
                     "rule": f["code"],
                     "severity": "error" if _is_error(f.get("code", "")) else "warning",
                     "msg": f["message"]}
                    for f in findings
                ],
                "source": "local:ruff",
            }
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None

    def _radon(self, repo_root: Path) -> Optional[dict[str, Any]]:
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
