"""ktlint Kotlin formatter/linter runner.

Invokes ``ktlint --reporter=json`` and parses the JSON array of files, each
containing a list of style errors. ktlint is style-only so all findings map
to QualityFindings.lint_errors with a low-severity flavour (the scoring
weight is still applied uniformly via lint_errors — caller decides).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

from lib.review_evidence.runners._registry import register
from lib.review_evidence.scoring import QualityFindings


def _has_kotlin(repo_root: Path) -> bool:
    for _ in repo_root.rglob("*.kt"):
        return True
    return False


class KtlintRunner:
    name = "ktlint"
    category = "quality"

    def is_applicable(self, repo_root: Path) -> bool:
        return _has_kotlin(repo_root)

    def run(self, repo_root: Path) -> Optional[QualityFindings]:
        try:
            p = subprocess.run(
                ["ktlint", "--reporter=json"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            if not p.stdout.strip():
                return QualityFindings()
            data = json.loads(p.stdout)
            if not isinstance(data, list):
                return QualityFindings()
            total = 0
            for entry in data:
                errs = entry.get("errors") or []
                if isinstance(errs, list):
                    total += len(errs)
            return QualityFindings(lint_errors=total)
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None


register(KtlintRunner())
