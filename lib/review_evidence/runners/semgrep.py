"""Semgrep CE multi-language SAST runner (2026 industry-leading OSS SAST)."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Optional

from lib.review_evidence.runners._registry import register
from lib.review_evidence.scoring import SecurityFindings


# Env override: allow custom config (e.g., DEVFORGE_SEMGREP_CONFIG=p/owasp-top-ten).
# Default `auto` uses Semgrep community default ruleset.
_DEFAULT_CONFIG = "auto"
_TIMEOUT_SEC = 120  # Semgrep median 10s, p95 ~60s — give it 2min headroom

_SOURCE_SUFFIXES = (
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".java",
    ".go",
    ".rb",
    ".php",
    ".kt",
    ".swift",
)


class SemgrepRunner:
    name = "semgrep"
    category = "security"

    def is_applicable(self, repo_root: Path) -> bool:
        # Applicable if repo contains any supported source file.
        # Semgrep auto-detects language; we just check for the most common.
        for p in repo_root.rglob("*"):
            if p.is_file() and p.suffix in _SOURCE_SUFFIXES:
                return True
        return False

    def run(self, repo_root: Path) -> Optional[SecurityFindings]:
        config = os.environ.get("DEVFORGE_SEMGREP_CONFIG", _DEFAULT_CONFIG)
        try:
            p = subprocess.run(
                ["semgrep", f"--config={config}", "--json", "--quiet", "."],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=_TIMEOUT_SEC,
                check=False,
            )
            if not p.stdout or not p.stdout.strip():
                return None
            data = json.loads(p.stdout)
        except (
            FileNotFoundError,
            subprocess.TimeoutExpired,
            json.JSONDecodeError,
            PermissionError,
        ):
            return None

        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for result in data.get("results", []) or []:
            extra = result.get("extra", {}) or {}
            severity = (extra.get("severity") or "").upper()
            metadata = extra.get("metadata", {}) or {}
            category = (metadata.get("category") or "").lower()
            bucket = _map_severity(severity, category)
            if bucket:
                counts[bucket] += 1

        return SecurityFindings(**counts)


def _map_severity(severity: str, category: str) -> Optional[str]:
    """Map Semgrep ERROR/WARNING/INFO + category to critical/high/medium/low."""
    if severity == "ERROR":
        return "critical" if category == "security" else "high"
    if severity == "WARNING":
        return "high" if category == "security" else "medium"
    if severity == "INFO":
        return "low"
    return None  # unknown severity — drop silently


register(SemgrepRunner())
