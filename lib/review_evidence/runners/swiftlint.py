"""SwiftLint iOS quality + security runner.

Invokes ``swiftlint --quiet --reporter json`` and parses the JSON array of
violations. SwiftLint emits security-relevant rules (e.g. ``force_cast``,
``force_try``, ``force_unwrapping``) alongside style rules, so the category
is ``security`` for consistency with the other native-platform runners that
surface unsafe-cast/IO issues.

Mapping:
    severity=error   -> SecurityFindings.high
    severity=warning -> SecurityFindings.medium
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

from lib.review_evidence.runners._registry import register
from lib.review_evidence.scoring import SecurityFindings


def _has_swift(repo_root: Path) -> bool:
    if (repo_root / "Package.swift").exists():
        return True
    if (repo_root / ".swiftlint.yml").exists():
        return True
    for _ in repo_root.rglob("*.swift"):
        return True
    return False


class SwiftlintRunner:
    name = "swiftlint"
    category = "security"

    def is_applicable(self, repo_root: Path) -> bool:
        return _has_swift(repo_root)

    def run(self, repo_root: Path) -> Optional[SecurityFindings]:
        try:
            p = subprocess.run(
                ["swiftlint", "--quiet", "--reporter", "json"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            if not p.stdout.strip():
                return SecurityFindings()
            data = json.loads(p.stdout)
            if not isinstance(data, list):
                return SecurityFindings()
            high = medium = 0
            for v in data:
                sev = str(v.get("severity", "")).lower()
                if sev == "error":
                    high += 1
                elif sev == "warning":
                    medium += 1
            return SecurityFindings(high=high, medium=medium)
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None


register(SwiftlintRunner())
