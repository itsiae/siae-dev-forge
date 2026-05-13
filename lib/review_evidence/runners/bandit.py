"""Bandit Python security runner."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

from lib.review_evidence.runners._registry import register
from lib.review_evidence.scoring import SecurityFindings


class BanditRunner:
    name = "bandit"
    category = "security"

    def is_applicable(self, repo_root: Path) -> bool:
        return (
            (repo_root / "pyproject.toml").exists()
            or (repo_root / "setup.py").exists()
            or any(repo_root.rglob("*.py"))
        )

    def run(self, repo_root: Path) -> Optional[SecurityFindings]:
        try:
            p = subprocess.run(
                ["bandit", "-r", ".", "-f", "json", "-q"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if not p.stdout.strip():
                return None
            data = json.loads(p.stdout)
            totals = data.get("metrics", {}).get("_totals", {})
            return SecurityFindings(
                critical=0,
                high=totals.get("SEVERITY.HIGH", 0),
                medium=totals.get("SEVERITY.MEDIUM", 0),
                low=totals.get("SEVERITY.LOW", 0),
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None


register(BanditRunner())
