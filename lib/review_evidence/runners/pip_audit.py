"""pip-audit Python deps vulnerability runner."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

from lib.review_evidence.runners._registry import register
from lib.review_evidence.scoring import SecurityFindings


class PipAuditRunner:
    name = "pip-audit"
    category = "deps"

    def is_applicable(self, repo_root: Path) -> bool:
        return any(
            (repo_root / f).exists()
            for f in ("requirements.txt", "pyproject.toml", "setup.py", "Pipfile")
        )

    def run(self, repo_root: Path) -> Optional[SecurityFindings]:
        try:
            p = subprocess.run(
                ["pip-audit", "-f", "json", "--quiet"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            if not p.stdout.strip():
                return SecurityFindings()
            data = json.loads(p.stdout)
            critical = high = medium = low = 0
            for dep in data.get("dependencies", []):
                for vuln in dep.get("vulns", []):
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


register(PipAuditRunner())
