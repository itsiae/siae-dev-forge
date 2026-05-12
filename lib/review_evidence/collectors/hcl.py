"""HCL stack collector: tflint + terraform validate."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from lib.review_evidence.collectors.python import _walk_with_prune
from lib.review_evidence.registry import register


class HCLCollector:
    name = "hcl"

    def is_applicable(self, repo_root: Path) -> bool:
        # E17 sibling: bounded walk for .tf discovery.
        return next(_walk_with_prune(repo_root, ".tf", first_only=True), None) is not None

    def collect(self, repo_root: Path, base_ref: str, head_ref: str) -> dict[str, Any]:
        return {
            "stack": "hcl",
            "coverage": None,  # N/A for HCL
            "lint": self._aggregate_lint(repo_root),
            "complexity": None,
        }

    def _aggregate_lint(self, repo_root: Path) -> dict[str, Any] | None:
        tflint = self._tflint(repo_root)
        tfval = self._tf_validate(repo_root)
        if tflint is None and tfval is None:
            return None

        errors = 0
        warnings = 0
        findings: list[dict[str, Any]] = []
        sources: list[str] = []
        if tflint:
            sources.append("tflint")
            errors += tflint["errors"]
            warnings += tflint["warnings"]
            findings.extend(tflint["findings"])
        if tfval:
            sources.append("terraform-validate")
            errors += tfval["errors"]
            warnings += tfval["warnings"]
            findings.extend(tfval["findings"])

        return {"errors": errors, "warnings": warnings, "findings": findings,
                "source": "local:" + "+".join(sources)}

    def _tflint(self, repo_root: Path) -> dict | None:
        try:
            p = subprocess.run(
                ["tflint", "--format", "json"],
                cwd=repo_root, capture_output=True, text=True, timeout=10, check=False,
            )
            data = json.loads(p.stdout or "{}")
            errors = 0
            warnings = 0
            findings = []
            for issue in data.get("issues", []):
                sev = issue.get("rule", {}).get("severity", "warning")
                if sev == "error":
                    errors += 1
                else:
                    warnings += 1
                findings.append({
                    "file": issue.get("range", {}).get("filename"),
                    "line": issue.get("range", {}).get("start", {}).get("line", 0),
                    "rule": issue.get("rule", {}).get("name", "?"),
                    "severity": sev,
                    "msg": issue.get("message", ""),
                })
            return {"errors": errors, "warnings": warnings, "findings": findings}
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return None

    def _tf_validate(self, repo_root: Path) -> dict | None:
        """Run ``terraform validate -json``.

        E27 mitigation — ``terraform validate`` errors out with
        ``Initialization required.`` when ``.terraform/`` is missing.
        The default stderr message is human-readable but not in JSON,
        so the legacy code silently treated it as JSONDecodeError and
        returned None — masking the real cause (no init run). We now
        detect the init-required hint and surface it as an explicit
        ``reason`` field so the renderer can tell the user what to do.
        """
        try:
            p = subprocess.run(
                ["terraform", "validate", "-json"],
                cwd=repo_root, capture_output=True, text=True, timeout=10, check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

        stderr_lower = (p.stderr or "").lower()
        if "initialization required" in stderr_lower or "please run 'terraform init'" in stderr_lower:
            return {
                "errors": 0,
                "warnings": 0,
                "findings": [],
                "reason": "terraform validate requires 'terraform init' to be run first",
            }
        try:
            data = json.loads(p.stdout or "{}")
        except json.JSONDecodeError:
            return None
        errors = data.get("error_count", 0)
        warnings = data.get("warning_count", 0)
        findings = []
        for d in data.get("diagnostics", []):
            sev = d.get("severity", "warning")
            findings.append({
                "file": d.get("range", {}).get("filename"),
                "line": d.get("range", {}).get("start", {}).get("line", 0),
                "rule": d.get("summary", "?"),
                "severity": sev,
                "msg": d.get("detail", ""),
            })
        return {"errors": errors, "warnings": warnings, "findings": findings}


register(HCLCollector())
