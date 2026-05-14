"""Vulture Python dead code runner.

Parses ``vulture .`` stdout findings (one per line, format:
``path:line:col: <type> '<name>' (XX% confidence)``).

Exit codes (vulture convention):
    0 = no findings
    3 = findings present (still parseable from stdout)

All findings map to QualityFindings.dead_code_blocks (dead code is a
quality signal, not a security one).
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from lib.review_evidence.runners._registry import register
from lib.review_evidence.scoring import QualityFindings


class VultureRunner:
    name = "vulture"
    category = "quality"

    def is_applicable(self, repo_root: Path) -> bool:
        if (repo_root / "pyproject.toml").exists():
            return True
        for _ in repo_root.rglob("*.py"):
            return True
        return False

    def run(self, repo_root: Path) -> Optional[QualityFindings]:
        try:
            p = subprocess.run(
                ["vulture", "."],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            # vulture exit 0 = no findings, exit 3 = findings, other = error
            if p.returncode not in (0, 3):
                return None
            dead = 0
            for line in p.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                # Heuristic: a valid finding line contains ":" path:line:col:
                # and ends with "% confidence)". Avoid counting tool errors.
                if "% confidence)" in line:
                    dead += 1
            return QualityFindings(dead_code_blocks=dead)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None


register(VultureRunner())
