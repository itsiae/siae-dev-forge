"""Java stack collector: jacoco coverage + checkstyle/pmd static analysis."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from lib.review_evidence.collectors._checkstyle import parse_checkstyle_xml
from lib.review_evidence.collectors._jacoco import parse_jacoco_xml
from lib.review_evidence.collectors._pmd import parse_pmd_xml
from lib.review_evidence.registry import register


MAVEN_JACOCO_PATHS = [
    Path("target/site/jacoco/jacoco.xml"),
]
GRADLE_JACOCO_PATHS = [
    Path("build/reports/jacoco/test/jacocoTestReport.xml"),
    Path("build/reports/jacoco/jacocoTestReport.xml"),
]
CHECKSTYLE_PATHS = [Path("target/checkstyle-result.xml")]
PMD_PATHS = [Path("target/pmd.xml")]


class JavaCollector:
    name = "java"

    def is_applicable(self, repo_root: Path) -> bool:
        return (
            (repo_root / "pom.xml").exists()
            or (repo_root / "build.gradle").exists()
            or (repo_root / "build.gradle.kts").exists()
        )

    def collect(self, repo_root: Path, base_ref: str, head_ref: str) -> dict[str, Any]:
        cov, cov_src = self._jacoco(repo_root)
        result: dict[str, Any] = {
            "stack": "java",
            "coverage": cov if cov else None,
            "lint": self._static_analysis(repo_root),
            "complexity": None,  # not in MVP for Java (covered by Sonar via ci_fetch)
        }
        return result

    def _jacoco(self, repo_root: Path) -> tuple[dict | None, str]:
        is_maven = (repo_root / "pom.xml").exists()
        paths = MAVEN_JACOCO_PATHS if is_maven else GRADLE_JACOCO_PATHS
        source = "local:jacoco-maven" if is_maven else "local:jacoco-gradle"
        for rel in paths:
            full = repo_root / rel
            if full.exists():
                try:
                    parsed = parse_jacoco_xml(full.read_text())
                    return {
                        "overall_pct": parsed["overall_pct"],
                        "delta_vs_base": 0.0,
                        "per_file": parsed["per_file"],
                        "source": source,
                    }, source
                except Exception:
                    return None, source
        return None, source

    def _static_analysis(self, repo_root: Path) -> dict | None:
        cs = None
        for rel in CHECKSTYLE_PATHS:
            full = repo_root / rel
            if full.exists():
                try:
                    cs = parse_checkstyle_xml(full.read_text())
                except Exception:
                    cs = None
                break

        pmd = None
        for rel in PMD_PATHS:
            full = repo_root / rel
            if full.exists():
                try:
                    pmd = parse_pmd_xml(full.read_text())
                except Exception:
                    pmd = None
                break

        if cs is None and pmd is None:
            return None

        sources = []
        errors = 0
        warnings = 0
        findings: list[dict] = []
        if cs:
            sources.append("checkstyle")
            errors += cs["errors"]
            warnings += cs["warnings"]
            findings.extend(cs["findings"])
        if pmd:
            sources.append("pmd")
            errors += pmd["errors"]
            warnings += pmd["warnings"]
            findings.extend(pmd["findings"])
        return {
            "errors": errors,
            "warnings": warnings,
            "findings": findings,
            "source": "local:" + "+".join(sources),
        }


register(JavaCollector())
