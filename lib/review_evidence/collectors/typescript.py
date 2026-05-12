"""TypeScript stack collector: lcov + eslint + complexity-report."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from lib.review_evidence.collectors._lcov import parse_lcov
from lib.review_evidence.registry import register


class TypeScriptCollector:
    name = "typescript"

    def is_applicable(self, repo_root: Path) -> bool:
        pj = repo_root / "package.json"
        if pj.exists():
            try:
                data = json.loads(pj.read_text())
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                if "typescript" in deps:
                    return True
            except json.JSONDecodeError:
                pass
        return any(repo_root.rglob("*.ts")) or any(repo_root.rglob("*.tsx"))

    def collect(self, repo_root: Path, base_ref: str, head_ref: str) -> dict[str, Any]:
        return {
            "stack": "typescript",
            "coverage": self._coverage(repo_root),
            "lint": self._eslint(repo_root),
            "complexity": self._complexity(repo_root),
        }

    def _coverage(self, repo_root: Path) -> dict[str, Any] | None:
        lcov = repo_root / "coverage" / "lcov.info"
        if not lcov.exists():
            return None
        try:
            parsed = parse_lcov(lcov.read_text())
            return {
                "overall_pct": round(parsed["pct"], 2),
                "delta_vs_base": 0.0,
                "per_file": parsed["per_file"],
                "source": "local:lcov",
            }
        except Exception:
            return None

    def _eslint(self, repo_root: Path) -> dict[str, Any] | None:
        try:
            p = subprocess.run(
                ["npx", "--no-install", "eslint", ".", "--format", "json"],
                cwd=repo_root, capture_output=True, text=True, timeout=15, check=False,
            )
            if not p.stdout.strip():
                return None
            data = json.loads(p.stdout)
            errors = sum(f.get("errorCount", 0) for f in data)
            warnings = sum(f.get("warningCount", 0) for f in data)
            findings = []
            for f in data:
                for m in f.get("messages", []):
                    findings.append({
                        "file": f.get("filePath"),
                        "line": m.get("line"),
                        "rule": m.get("ruleId"),
                        "severity": "error" if m.get("severity") == 2 else "warning",
                        "msg": m.get("message"),
                    })
            return {"errors": errors, "warnings": warnings, "findings": findings, "source": "local:eslint"}
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None

    def _complexity(self, repo_root: Path) -> dict[str, Any] | None:
        try:
            p = subprocess.run(
                ["npx", "--no-install", "complexity-report", "--format", "json", "src/"],
                cwd=repo_root, capture_output=True, text=True, timeout=15, check=False,
            )
            if p.returncode != 0 or not p.stdout.strip():
                return None
            data = json.loads(p.stdout)
            max_cx = 0
            over = []
            for report in data.get("reports", []):
                for fn in report.get("functions", []):
                    cx = fn.get("cyclomatic", 0)
                    if cx > max_cx:
                        max_cx = cx
                    if cx > 10:
                        over.append({"path": report.get("path"),
                                     "function": fn.get("name"),
                                     "cyclomatic": cx, "threshold": 10})
            return {"max_cyclomatic": max_cx, "files_over_threshold": over, "source": "local:complexity-report"}
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None


register(TypeScriptCollector())
