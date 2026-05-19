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
_TIMEOUT_SEC = 180  # global subprocess timeout
_TIMEOUT_PER_FILE = 10  # EC-26 ReDoS protection: per-file timeout
_MIN_SEMGREP_VERSION = "1.50.0"  # AC7: version gate

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

    def _check_version(self) -> Optional[str]:
        """AC7: verify semgrep installed and >=_MIN_SEMGREP_VERSION. Returns error reason or None."""
        try:
            v = subprocess.run(
                ["semgrep", "--version"], capture_output=True, text=True, timeout=10
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return "semgrep not installed"
        version_str = (v.stdout or "").strip().split()[0] if v.stdout else "0.0.0"
        try:
            from packaging.version import Version
            if Version(version_str) < Version(_MIN_SEMGREP_VERSION):
                return f"semgrep {version_str} < required {_MIN_SEMGREP_VERSION}"
        except ImportError:
            pass  # packaging non installato: accetta qualsiasi versione (degraded mode)
        except Exception:
            pass  # version parse failed: accetta (defensive)
        return None

    def run(self, repo_root: Path) -> Optional[SecurityFindings]:
        # AC7: version gate
        err = self._check_version()
        if err:
            return SecurityFindings.tool_unavailable(err)

        config = os.environ.get("DEVFORGE_SEMGREP_CONFIG", _DEFAULT_CONFIG)
        config_args = [f"--config={c.strip()}" for c in config.split(",") if c.strip()]

        # AC8: diff-aware via env DEVFORGE_SEMGREP_BASELINE_COMMIT
        baseline = os.environ.get("DEVFORGE_SEMGREP_BASELINE_COMMIT")
        diff_args = ["--baseline-commit", baseline] if baseline else []

        # Parallel jobs (default CPU count, override via SEMGREP_JOBS)
        jobs = os.environ.get("SEMGREP_JOBS") or str(os.cpu_count() or 4)

        cmd = [
            "semgrep", *config_args, *diff_args,
            "--json", "--quiet", "--metrics=off",
            f"--timeout={_TIMEOUT_PER_FILE}",  # EC-26 per-file timeout
            f"--jobs={jobs}",
            ".",
        ]
        try:
            p = subprocess.run(
                cmd, cwd=repo_root, capture_output=True, text=True,
                timeout=_TIMEOUT_SEC, check=False,
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

        return self._parse_findings(data)

    def _parse_findings(self, data: dict) -> SecurityFindings:
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        by_family: dict[str, int] = {}
        for result in data.get("results", []) or []:
            extra = result.get("extra", {}) or {}
            severity = (extra.get("severity") or "").upper()
            metadata = extra.get("metadata", {}) or {}
            category = (metadata.get("category") or "").lower()
            confidence = (metadata.get("confidence") or "").upper()
            bucket = _map_severity(severity, category, confidence)
            if bucket:
                counts[bucket] += 1
                # by_family traceability per siae.<family>.<...>
                rule_id = result.get("check_id", "")
                if rule_id.startswith("siae."):
                    parts = rule_id.split(".", 2)
                    if len(parts) >= 2:
                        family = parts[1]
                        by_family[family] = by_family.get(family, 0) + 1
        return SecurityFindings(**counts, by_family=by_family)


def _map_severity(severity: str, category: str, confidence: str = "") -> Optional[str]:
    """Map Semgrep severity+category+confidence → bucket.

    Backward-compat: community rule senza confidence metadata → mapping classico.
    ADR-005 degrade: MEDIUM/LOW confidence esplicito → degrade di un bucket
    (block ERROR+HIGH only when confidence is explicitly HIGH or missing).
    """
    if severity == "ERROR":
        if category == "security":
            # ERROR+security: critical unless confidence is explicitly weak
            if confidence in ("MEDIUM", "LOW"):
                return "high"
            return "critical"
        return "high"
    if severity == "WARNING":
        if category == "security":
            # WARNING+security: high bucket (visible, no block per ADR-005)
            if confidence == "LOW":
                return "medium"
            return "high"
        return "medium"
    if severity == "INFO":
        return "low"
    return None  # unknown severity — drop silently


register(SemgrepRunner())
