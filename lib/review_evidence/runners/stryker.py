"""Stryker JS/TS mutation testing report parser (advisory, v1.58+).

Parses pre-existing Stryker JSON reports — does NOT execute Stryker
(mutation testing is slow; expect CI/build pipeline to run Stryker
separately).

Opt-in via DEVFORGE_MUTATION_ENABLED=1. Default report path:
reports/mutation/mutation.json (Stryker default). Override via
DEVFORGE_STRYKER_REPORT_PATH.

Stryker JSON schema (v6+): top-level dict with "files" key mapping
file path → {"mutants": [{"status": <Status>}, ...]}. Status enum:
Killed, Survived, Timeout, NoCoverage, RuntimeError, CompileError,
Ignored. Score formula = killed / (killed+survived+timeout+nocoverage);
RuntimeError/CompileError/Ignored are broken mutants and are excluded
from the scored denominator (counted in total_mutants only).
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Optional

from lib.review_evidence.runners._registry import register
from lib.review_evidence.scoring import MutationFindings


_DEFAULT_REPORT_PATH = "reports/mutation/mutation.json"


class StrykerRunner:
    name = "stryker"
    category = "mutation"

    def is_applicable(self, repo_root: Path) -> bool:
        # Opt-in guard: skip entirely when disabled.
        if os.environ.get("DEVFORGE_MUTATION_ENABLED", "0") != "1":
            return False
        # Node project + report file present.
        if not (repo_root / "package.json").exists():
            return False
        return self._report_path(repo_root).exists()

    def run(self, repo_root: Path) -> Optional[MutationFindings]:
        if os.environ.get("DEVFORGE_MUTATION_ENABLED", "0") != "1":
            return None
        report = self._report_path(repo_root)
        if not report.exists():
            return None
        try:
            data = json.loads(report.read_text())
        except (json.JSONDecodeError, OSError, PermissionError):
            return None
        if not isinstance(data, dict):
            return None

        killed = survived = timeout = no_coverage = 0
        total = 0
        files = data.get("files") or {}
        if not isinstance(files, dict):
            return None
        for file_data in files.values():
            if not isinstance(file_data, dict):
                continue
            mutants = file_data.get("mutants") or []
            if not isinstance(mutants, list):
                continue
            for mutant in mutants:
                if not isinstance(mutant, dict):
                    continue
                status = (mutant.get("status") or "").strip()
                total += 1
                if status == "Killed":
                    killed += 1
                elif status == "Survived":
                    survived += 1
                elif status == "Timeout":
                    timeout += 1
                elif status == "NoCoverage":
                    no_coverage += 1
                # RuntimeError / CompileError / Ignored / unknown:
                # counted in total only, excluded from scored_denom.

        if total == 0:
            return None

        # Score = killed / (killed + survived + timeout + no_coverage).
        # Broken/ignored mutants are excluded from the denominator (they
        # are not a coverage failure).
        scored_denom = killed + survived + timeout + no_coverage
        score_pct = (killed / scored_denom * 100.0) if scored_denom else 0.0
        # NaN guard for division corner case (defensive — float math
        # above cannot produce NaN with non-negative ints, but the guard
        # protects against future refactors).
        if math.isnan(score_pct):
            return None

        return MutationFindings(
            score_pct=round(score_pct, 2),
            killed=killed,
            survived=survived,
            timeout=timeout,
            no_coverage=no_coverage,
            total_mutants=total,
            tool="stryker",
        )

    @staticmethod
    def _report_path(repo_root: Path) -> Path:
        override = os.environ.get("DEVFORGE_STRYKER_REPORT_PATH")
        if override:
            p = Path(override)
            return p if p.is_absolute() else (repo_root / p)
        return repo_root / _DEFAULT_REPORT_PATH


register(StrykerRunner())
