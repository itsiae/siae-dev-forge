"""tfsec HCL/Terraform security runner."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

from lib.review_evidence.runners._registry import register
from lib.review_evidence.scoring import SecurityFindings


class TfsecRunner:
    name = "tfsec"
    category = "security"

    def is_applicable(self, repo_root: Path) -> bool:
        for _ in repo_root.rglob("*.tf"):
            return True
        return False

    def run(self, repo_root: Path) -> Optional[SecurityFindings]:
        try:
            p = subprocess.run(
                ["tfsec", "--format=json", "."],
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
            for r in data.get("results", []) or []:
                sev = str(r.get("severity", "")).upper()
                if sev == "CRITICAL":
                    critical += 1
                elif sev == "HIGH":
                    high += 1
                elif sev == "MEDIUM":
                    medium += 1
                else:
                    # LOW + UNKNOWN -> low bucket
                    low += 1
            return SecurityFindings(
                critical=critical, high=high, medium=medium, low=low
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None


register(TfsecRunner())
