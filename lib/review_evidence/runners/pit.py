"""PIT Java mutation testing report parser (advisory, v1.58+).

Parses pre-existing PIT XML reports — does NOT execute PIT (mutation
testing is slow; expect CI/build pipeline to run PIT separately).

Opt-in via DEVFORGE_MUTATION_ENABLED=1. Default report path:
target/pit-reports/mutations.xml (Maven plugin output). Override via
DEVFORGE_PIT_REPORT_PATH.
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from lib.review_evidence.runners._registry import register
from lib.review_evidence.scoring import MutationFindings


_DEFAULT_REPORT_PATH = "target/pit-reports/mutations.xml"


class PitRunner:
    name = "pit"
    category = "mutation"

    def is_applicable(self, repo_root: Path) -> bool:
        # Opt-in guard: skip entirely when disabled.
        if os.environ.get("DEVFORGE_MUTATION_ENABLED", "0") != "1":
            return False
        # Java project + report file present.
        if not (repo_root / "pom.xml").exists():
            return False
        report = self._report_path(repo_root)
        return report.exists()

    def run(self, repo_root: Path) -> Optional[MutationFindings]:
        if os.environ.get("DEVFORGE_MUTATION_ENABLED", "0") != "1":
            return None
        report = self._report_path(repo_root)
        if not report.exists():
            return None
        try:
            tree = ET.parse(str(report))
        except (ET.ParseError, OSError, PermissionError):
            return None
        root = tree.getroot()
        if root is None:
            return None

        killed = survived = timeout = no_coverage = 0
        total = 0
        for m in root.findall(".//mutation"):
            status = (m.get("status") or "").upper()
            total += 1
            if status == "KILLED":
                killed += 1
            elif status == "SURVIVED":
                survived += 1
            elif status in ("TIMED_OUT", "MEMORY_ERROR"):
                timeout += 1
            elif status == "NO_COVERAGE":
                no_coverage += 1
            # RUN_ERROR + any unknown status: counted in total only

        if total == 0:
            return None

        # Score = killed / (killed + survived + timeout + no_coverage).
        # Exclude RUN_ERROR / unknown from denominator (broken mutants,
        # not a coverage failure).
        scored_denom = killed + survived + timeout + no_coverage
        score_pct = (killed / scored_denom * 100.0) if scored_denom else 0.0

        return MutationFindings(
            score_pct=round(score_pct, 2),
            killed=killed,
            survived=survived,
            timeout=timeout,
            no_coverage=no_coverage,
            total_mutants=total,
            tool="pit",
        )

    @staticmethod
    def _report_path(repo_root: Path) -> Path:
        override = os.environ.get("DEVFORGE_PIT_REPORT_PATH")
        if override:
            p = Path(override)
            return p if p.is_absolute() else (repo_root / p)
        return repo_root / _DEFAULT_REPORT_PATH


register(PitRunner())
