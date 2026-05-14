"""cfn-lint AWS CloudFormation security/correctness runner.

Invokes ``cfn-lint --format json`` and parses the JSON array. Each entry has
a ``Level`` field (Error / Warning / Informational) which maps to the
SecurityFindings buckets.

Applicability heuristic: scan ``*.yml``/``*.yaml``/``*.json`` for either an
``AWSTemplateFormatVersion`` tag or a top-level ``Resources:`` key (the two
markers of a CloudFormation template). This keeps the runner inert on
generic YAML/JSON repos (CI configs, package.json, etc).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

from lib.review_evidence.runners._registry import register
from lib.review_evidence.scoring import SecurityFindings

# Cap on files inspected to keep is_applicable cheap on large monorepos.
_MAX_FILES_SCANNED = 200


def _looks_like_cfn(text: str) -> bool:
    if "AWSTemplateFormatVersion" in text:
        return True
    # Top-level Resources: marker — accept both YAML key and JSON key.
    for line in text.splitlines():
        stripped = line.rstrip()
        if stripped.startswith("Resources:") or stripped.startswith('"Resources"'):
            return True
    return False


def _has_cfn_template(repo_root: Path) -> bool:
    scanned = 0
    for pattern in ("*.yml", "*.yaml", "*.json"):
        for path in repo_root.rglob(pattern):
            scanned += 1
            if scanned > _MAX_FILES_SCANNED:
                return False
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if _looks_like_cfn(text):
                return True
    return False


class CfnLintRunner:
    name = "cfn-lint"
    category = "security"

    def is_applicable(self, repo_root: Path) -> bool:
        return _has_cfn_template(repo_root)

    def run(self, repo_root: Path) -> Optional[SecurityFindings]:
        try:
            p = subprocess.run(
                ["cfn-lint", "--format", "json"],
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
            high = medium = low = 0
            for entry in data:
                level = str(entry.get("Level", "")).lower()
                if level == "error":
                    high += 1
                elif level == "warning":
                    medium += 1
                else:
                    # Informational / unknown -> low bucket
                    low += 1
            return SecurityFindings(high=high, medium=medium, low=low)
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None


register(CfnLintRunner())
