"""SpotBugs (+ find-sec-bugs) Java security runner.

Two modes:

1. **Fast path**: parse a pre-existing ``target/spotbugsXml.xml`` if the
   CI/build already produced it (preferred — no slow Maven invocation
   inside the orchestrator).
2. **Fallback**: invoke
   ``mvn com.github.spotbugs:spotbugs-maven-plugin:spotbugs
   -DincludeTests=false`` and parse the generated report.

Priority mapping (SpotBugs priority is 1 = highest, 5 = lowest):
    priority 1 -> critical
    priority 2 -> high
    priority 3 -> medium
    priority 4,5 -> low
"""
from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from lib.review_evidence.runners._registry import register
from lib.review_evidence.scoring import SecurityFindings

_REPORT_RELATIVE = Path("target") / "spotbugsXml.xml"


def _parse_report(xml_path: Path) -> Optional[SecurityFindings]:
    try:
        tree = ET.parse(xml_path)
    except (OSError, ET.ParseError):
        return None
    root = tree.getroot()
    critical = high = medium = low = 0
    for bug in root.iter("BugInstance"):
        priority = bug.get("priority", "3")
        try:
            p = int(priority)
        except ValueError:
            p = 3
        if p == 1:
            critical += 1
        elif p == 2:
            high += 1
        elif p == 3:
            medium += 1
        else:
            low += 1
    return SecurityFindings(critical=critical, high=high, medium=medium, low=low)


class SpotbugsRunner:
    name = "spotbugs"
    category = "security"

    def is_applicable(self, repo_root: Path) -> bool:
        if (repo_root / "pom.xml").exists():
            return True
        for pattern in ("build.gradle", "build.gradle.kts"):
            if (repo_root / pattern).exists():
                return True
        return False

    def run(self, repo_root: Path) -> Optional[SecurityFindings]:
        report = repo_root / _REPORT_RELATIVE
        if report.exists():
            parsed = _parse_report(report)
            if parsed is not None:
                return parsed
        # Fallback: invoke Maven plugin (only meaningful for Maven repos).
        if not (repo_root / "pom.xml").exists():
            return None
        try:
            subprocess.run(
                [
                    "mvn",
                    "-q",
                    "com.github.spotbugs:spotbugs-maven-plugin:spotbugs",
                    "-DincludeTests=false",
                ],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None
        if not report.exists():
            return None
        return _parse_report(report)


register(SpotbugsRunner())
