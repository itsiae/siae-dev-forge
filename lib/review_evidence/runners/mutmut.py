"""mutmut Python mutation testing runner (advisory, v1.58+).

Parses pre-existing mutmut cache via `mutmut results` — does NOT execute
`mutmut run` (mutation testing is slow; expect dev/CI to have populated
the .mutmut-cache SQLite already).

Strategy:
- Prefer `mutmut results --json` (mutmut >= 2.4)
- Fallback to `mutmut results` plain text + regex parse (older mutmut)

Opt-in via DEVFORGE_MUTATION_ENABLED=1. Default cache dir: ``.mutmut-cache``.
Override via DEVFORGE_MUTMUT_CACHE_PATH.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Optional

from lib.review_evidence.runners._registry import register
from lib.review_evidence.scoring import MutationFindings


_DEFAULT_CACHE_DIR = ".mutmut-cache"
_TIMEOUT_SEC = 30


class MutmutRunner:
    name = "mutmut"
    category = "mutation"

    def is_applicable(self, repo_root: Path) -> bool:
        # Opt-in guard: skip entirely when disabled.
        if os.environ.get("DEVFORGE_MUTATION_ENABLED", "0") != "1":
            return False
        # Python project marker + cache present.
        if not (
            (repo_root / "pyproject.toml").exists()
            or (repo_root / "setup.py").exists()
        ):
            return False
        return self._cache_dir(repo_root).exists()

    def run(self, repo_root: Path) -> Optional[MutationFindings]:
        if os.environ.get("DEVFORGE_MUTATION_ENABLED", "0") != "1":
            return None
        # Try JSON first (mutmut >= 2.4).
        try:
            p = subprocess.run(
                ["mutmut", "results", "--json"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=_TIMEOUT_SEC,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
            return None

        result = self._parse_json(p.stdout)
        if result is not None:
            return result

        # Fallback: older mutmut without --json support.
        try:
            p2 = subprocess.run(
                ["mutmut", "results"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=_TIMEOUT_SEC,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError):
            return None
        return self._parse_text(p2.stdout)

    @staticmethod
    def _cache_dir(repo_root: Path) -> Path:
        override = os.environ.get("DEVFORGE_MUTMUT_CACHE_PATH")
        if override:
            p = Path(override)
            return p if p.is_absolute() else (repo_root / p)
        return repo_root / _DEFAULT_CACHE_DIR

    @staticmethod
    def _parse_json(stdout: str) -> Optional[MutationFindings]:
        if not stdout.strip():
            return None
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        killed = int(data.get("killed", 0))
        survived = int(data.get("survived", 0))
        timeout = int(data.get("timeout", 0))
        no_coverage = int(data.get("no_tests", 0))
        total = int(
            data.get("total", killed + survived + timeout + no_coverage)
        )
        if total == 0:
            return None
        # Score = killed / (killed + survived + timeout + no_coverage).
        # Exclude suspicious/skipped from denominator (analogous to PIT
        # RUN_ERROR/unknown handling).
        scored_denom = killed + survived + timeout + no_coverage
        score = (killed / scored_denom * 100.0) if scored_denom else 0.0
        return MutationFindings(
            score_pct=round(score, 2),
            killed=killed,
            survived=survived,
            timeout=timeout,
            no_coverage=no_coverage,
            total_mutants=total,
            tool="mutmut",
        )

    @staticmethod
    def _parse_text(stdout: str) -> Optional[MutationFindings]:
        """Fallback parser for older mutmut text output."""
        if not stdout.strip():
            return None
        killed = MutmutRunner._extract_int(stdout, r"[Kk]illed[^\d]*(\d+)")
        survived = MutmutRunner._extract_int(stdout, r"[Ss]urvived[^\d]*(\d+)")
        timeout = MutmutRunner._extract_int(stdout, r"[Tt]imeout[^\d]*(\d+)")
        no_coverage = MutmutRunner._extract_int(
            stdout, r"[Nn]o[ _]tests[^\d]*(\d+)"
        )
        total = MutmutRunner._extract_int(stdout, r"[Tt]otal[^\d]*(\d+)")
        if total == 0 and killed == 0 and survived == 0:
            return None
        if total == 0:
            total = killed + survived + timeout + no_coverage
        scored_denom = killed + survived + timeout + no_coverage
        score = (killed / scored_denom * 100.0) if scored_denom else 0.0
        return MutationFindings(
            score_pct=round(score, 2),
            killed=killed,
            survived=survived,
            timeout=timeout,
            no_coverage=no_coverage,
            total_mutants=total,
            tool="mutmut",
        )

    @staticmethod
    def _extract_int(text: str, pattern: str) -> int:
        m = re.search(pattern, text)
        return int(m.group(1)) if m else 0


register(MutmutRunner())
