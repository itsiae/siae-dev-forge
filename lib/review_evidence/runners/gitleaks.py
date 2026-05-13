"""Gitleaks secret scanner (cross-stack)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

from lib.review_evidence.runners._registry import register
from lib.review_evidence.scoring import SecurityFindings


class GitleaksRunner:
    name = "gitleaks"
    category = "secret"

    def is_applicable(self, repo_root: Path) -> bool:
        return (repo_root / ".git").exists()

    def run(self, repo_root: Path) -> Optional[SecurityFindings]:
        try:
            p = subprocess.run(
                [
                    "gitleaks",
                    "detect",
                    "--no-banner",
                    "--report-format=json",
                    "--report-path=/dev/stdout",
                    "--source",
                    ".",
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            # gitleaks exit code 1 when leaks present, stdout has JSON array.
            if not p.stdout.strip():
                return SecurityFindings()  # 0 leaks
            findings = json.loads(p.stdout)
            # Every secret = CRITICAL (zero tolerance).
            return SecurityFindings(critical=len(findings))
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None


register(GitleaksRunner())
