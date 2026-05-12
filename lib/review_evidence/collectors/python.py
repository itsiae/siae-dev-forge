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
