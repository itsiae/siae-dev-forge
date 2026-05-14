"""Checkov IaC multi-cloud security runner (Terraform / k8s / Dockerfile).

Checkov exit codes vary (0 = clean, 1 = findings), but JSON output is always
emitted on stdout. Severities include CRITICAL/HIGH/MEDIUM/LOW/INFO; INFO is
mapped to ``low`` to fit the ``SecurityFindings`` 4-bucket schema.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

from lib.review_evidence.runners._registry import register
from lib.review_evidence.scoring import SecurityFindings


def _has_yaml(repo_root: Path) -> bool:
    for pat in ("*.yaml", "*.yml"):
        for _ in repo_root.rglob(pat):
            return True
    return False


def _has_dockerfile(repo_root: Path) -> bool:
    for _ in repo_root.rglob("Dockerfile"):
        return True
    return False


def _has_tf(repo_root: Path) -> bool:
    for _ in repo_root.rglob("*.tf"):
        return True
    return False


class CheckovRunner:
    name = "checkov"
    category = "security"

    def is_applicable(self, repo_root: Path) -> bool:
        return _has_tf(repo_root) or _has_yaml(repo_root) or _has_dockerfile(repo_root)

    def run(self, repo_root: Path) -> Optional[SecurityFindings]:
        try:
            p = subprocess.run(
                ["checkov", "-d", ".", "--output", "json"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            if not p.stdout.strip():
                return SecurityFindings()
            data = json.loads(p.stdout)
            # Checkov can return a list (multi-framework) or a single dict.
            if isinstance(data, list):
                blocks = data
            else:
                blocks = [data]
            critical = high = medium = low = 0
            for block in blocks:
                failed = (block.get("results") or {}).get("failed_checks", []) or []
                for chk in failed:
                    sev = str(chk.get("severity") or "").upper()
                    if sev == "CRITICAL":
                        critical += 1
                    elif sev == "HIGH":
                        high += 1
                    elif sev == "MEDIUM":
                        medium += 1
                    else:
                        # LOW + INFO + None -> low bucket
                        low += 1
            return SecurityFindings(
                critical=critical, high=high, medium=medium, low=low
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None


register(CheckovRunner())
