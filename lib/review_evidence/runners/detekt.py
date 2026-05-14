"""detekt Android/Kotlin static analysis runner.

Parses a pre-existing ``build/reports/detekt/detekt.xml`` (checkstyle XML
format) — detekt is typically invoked by the build, so the orchestrator does
not re-run Gradle. If the report is absent, returns ``None``.

Mapping (checkstyle severities):
    severity=error   -> high  (mapped to lint_errors so quality penalty is paid)
    severity=warning -> medium
    severity=info    -> low

Output schema is ``QualityFindings`` (lint_errors only): detekt is a code
smell / complexity tool, not a security scanner.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from lib.review_evidence.runners._registry import register
from lib.review_evidence.scoring import QualityFindings

_REPORT_RELATIVE = Path("build") / "reports" / "detekt" / "detekt.xml"


def _has_kotlin(repo_root: Path) -> bool:
    for pattern in ("*.kt", "*.kts"):
        for _ in repo_root.rglob(pattern):
            return True
    return False


def _gradle_kts_has_detekt_plugin(repo_root: Path) -> bool:
    gradle_kts = repo_root / "build.gradle.kts"
    if not gradle_kts.exists():
        return False
    try:
        content = gradle_kts.read_text(encoding="utf-8")
    except OSError:
        return False
    return 'id("io.gitlab.arturbosch.detekt")' in content


def _parse_report(xml_path: Path) -> Optional[QualityFindings]:
    try:
        tree = ET.parse(xml_path)
    except (OSError, ET.ParseError):
        return None
    root = tree.getroot()
    errors = warnings = infos = 0
    for file_el in root.iter("file"):
        for err in file_el.findall("error"):
            sev = (err.get("severity") or "").lower()
            if sev == "error":
                errors += 1
            elif sev == "warning":
                warnings += 1
            else:
                # info / unknown -> low bucket
                infos += 1
    return QualityFindings(
        lint_errors=errors + warnings + infos,
    )


class DetektRunner:
    name = "detekt"
    category = "quality"

    def is_applicable(self, repo_root: Path) -> bool:
        return _has_kotlin(repo_root) or _gradle_kts_has_detekt_plugin(repo_root)

    def run(self, repo_root: Path) -> Optional[QualityFindings]:
        report = repo_root / _REPORT_RELATIVE
        if not report.exists():
            return None
        return _parse_report(report)


register(DetektRunner())
