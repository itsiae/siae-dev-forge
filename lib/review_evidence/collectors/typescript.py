"""TypeScript stack collector: lcov + eslint + complexity-report."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from lib.review_evidence.collectors._lcov import parse_lcov
from lib.review_evidence.collectors.python import _walk_with_prune
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
        # E17 sibling: bounded walk for .ts/.tsx discovery so a monorepo
        # with vendored node_modules doesn't stall is_applicable.
        if next(_walk_with_prune(repo_root, ".ts", first_only=True), None) is not None:
            return True
        if next(_walk_with_prune(repo_root, ".tsx", first_only=True), None) is not None:
            return True
        return False

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
        """Run eslint and bucket findings.

        E25 mitigation — when eslint exits non-zero AND stdout is empty
        (typical of a config error: missing parser, invalid plugin,
        unresolvable extends), the previous code returned ``None`` and
        the orchestrator silently dropped the entire lint metric. Now we
        distinguish:

        * exit 0/1 + JSON stdout: normal output (1 means findings found)
        * exit 2 + empty stdout: config error → return explicit
          ``{"available": false, "reason": "eslint config error"}``
        * any error: fall back to ``None`` (tool genuinely unavailable)
        """
        try:
            p = subprocess.run(
                ["npx", "--no-install", "eslint", ".", "--format", "json"],
                cwd=repo_root, capture_output=True, text=True, timeout=15, check=False,
            )
            if not p.stdout.strip():
                if p.returncode != 0:
                    # E25: config error or invocation error — explicit signal.
                    return {
                        "available": False,
                        "errors": 0,
                        "warnings": 0,
                        "findings": [],
                        "source": "local:eslint",
                        "reason": "eslint exited non-zero with no stdout (config error?)",
                    }
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
