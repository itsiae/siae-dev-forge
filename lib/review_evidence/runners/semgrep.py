"""Semgrep CE multi-language SAST runner (2026 industry-leading OSS SAST)."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Optional

from lib.review_evidence.runners._registry import register
from lib.review_evidence.scoring import SecurityFindings


# Env override: allow custom config (e.g., DEVFORGE_SEMGREP_CONFIG=p/owasp-top-ten,...).
# Default = community "auto" + SIAE custom registry (Wave 1 Vulnerability Prevention Library).
# Multiple configs accepted as CSV; Semgrep accetta multiple --config args.
_REPO_ROOT = Path(__file__).parents[3]
# SIAE custom rules live as individual YAML files under rules/semgrep/siae/.
# Semgrep accepts a DIR as --config and auto-discovers rule yaml files
# recursively. `registry.yaml` is a documentation manifest, NOT a Semgrep
# ruleset schema — we skip it via Semgrep's natural --config dir behavior
# (yaml files at any depth get loaded; we ensure only real rule files exist).
_SIAE_RULES_DIR = _REPO_ROOT / "rules" / "semgrep" / "siae"
_DEFAULT_CONFIGS = ["auto"]
if _SIAE_RULES_DIR.is_dir():
    # Include dir only if at least one rule yaml is present.
    # (Skip empty scaffold dir to avoid Semgrep "no rules found" error.)
    _siae_rule_files = [
        p for p in _SIAE_RULES_DIR.rglob("*.yaml")
        if p.name not in {"registry.yaml", "suppressions.yaml"}
    ]
    if _siae_rule_files:
        _DEFAULT_CONFIGS.append(str(_SIAE_RULES_DIR))
_DEFAULT_CONFIG = ",".join(_DEFAULT_CONFIGS)
_TIMEOUT_SEC = 180  # Wave 1: ext timeout for layered config + diff-aware (Task 09/10 follow-up)

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
        # Semgrep accetta multipli --config args; CSV viene splittato.
        config_args = [f"--config={c.strip()}" for c in config.split(",") if c.strip()]
        try:
            p = subprocess.run(
                ["semgrep", *config_args, "--json", "--quiet", "."],
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
