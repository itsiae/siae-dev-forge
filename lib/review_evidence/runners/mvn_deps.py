"""Maven OWASP dependency-check Java deps vulnerability runner.

Parses an existing ``target/dependency-check-report.json`` produced by the
``org.owasp:dependency-check-maven`` plugin. Does NOT invoke ``mvn`` itself
(too slow for the review-evidence hot path); if the report file is missing,
``run`` returns ``None`` so the orchestrator can skip the dimension.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

from lib.review_evidence.runners._registry import register
from lib.review_evidence.scoring import SecurityFindings


class MvnDepsRunner:
    name = "mvn-deps"
    category = "deps"

    def is_applicable(self, repo_root: Path) -> bool:
        return (repo_root / "pom.xml").exists()

    def run(self, repo_root: Path) -> Optional[SecurityFindings]:
        report = repo_root / "target" / "dependency-check-report.json"
        if not report.exists():
            return None
        try:
            # Use subprocess for symmetry with sibling runners (uniform mock surface)
            # but read the report file directly via `cat` so tests can patch the
            # same `subprocess.run` they patch for other runners.
            p = subprocess.run(
                ["cat", str(report)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if not p.stdout.strip():
                return SecurityFindings()
            data = json.loads(p.stdout)
            critical = high = medium = low = 0
            for dep in data.get("dependencies", []):
                for vuln in dep.get("vulnerabilities", []):
                    sev = str(vuln.get("severity", "")).upper()
                    if sev == "CRITICAL":
                        critical += 1
                    elif sev == "HIGH":
                        high += 1
                    elif sev == "MEDIUM":
                        medium += 1
                    else:
                        low += 1
            return SecurityFindings(
                critical=critical, high=high, medium=medium, low=low
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None


register(MvnDepsRunner())
