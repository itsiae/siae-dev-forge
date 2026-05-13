"""npm audit TS/JS deps vulnerability runner."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

from lib.review_evidence.runners._registry import register
from lib.review_evidence.scoring import SecurityFindings


class NpmAuditRunner:
    name = "npm-audit"
    category = "deps"

    def is_applicable(self, repo_root: Path) -> bool:
        return (repo_root / "package.json").exists()

    def run(self, repo_root: Path) -> Optional[SecurityFindings]:
        try:
            p = subprocess.run(
                ["npm", "audit", "--json"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            if not p.stdout.strip():
                return SecurityFindings()
            data = json.loads(p.stdout)
            counts = data.get("metadata", {}).get("vulnerabilities", {})
            # npm audit uses "moderate" instead of "medium"
            return SecurityFindings(
                critical=counts.get("critical", 0),
                high=counts.get("high", 0),
                medium=counts.get("moderate", 0),
                low=counts.get("low", 0),
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None


register(NpmAuditRunner())
