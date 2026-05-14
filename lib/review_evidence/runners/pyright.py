"""Pyright Python type errors runner.

Invokes ``pyright --outputjson .`` and parses ``summary.errorCount`` /
``summary.warningCount`` into a QualityFindings object.

Mapping:
    errorCount   -> QualityFindings.type_errors
    warningCount -> QualityFindings.lint_errors  (warnings are surface-level)

Only applicable when pyright is explicitly configured (pyrightconfig.json
or ``[tool.pyright]`` in pyproject.toml). Avoids running on every Python
repo because pyright is opt-in.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

from lib.review_evidence.runners._registry import register
from lib.review_evidence.scoring import QualityFindings


def _has_pyright_config(repo_root: Path) -> bool:
    if (repo_root / "pyrightconfig.json").exists():
        return True
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.exists():
        return False
    try:
        content = pyproject.read_text(encoding="utf-8")
    except OSError:
        return False
    return "[tool.pyright]" in content


class PyrightRunner:
    name = "pyright"
    category = "quality"

    def is_applicable(self, repo_root: Path) -> bool:
        return _has_pyright_config(repo_root)

    def run(self, repo_root: Path) -> Optional[QualityFindings]:
        try:
            p = subprocess.run(
                ["pyright", "--outputjson", "."],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            if not p.stdout.strip():
                return None
            data = json.loads(p.stdout)
            summary = data.get("summary", {})
            errors = int(summary.get("errorCount", 0) or 0)
            warnings = int(summary.get("warningCount", 0) or 0)
            return QualityFindings(type_errors=errors, lint_errors=warnings)
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None


register(PyrightRunner())
