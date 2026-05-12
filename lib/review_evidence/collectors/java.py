"""Java stack collector: jacoco (this task) + checkstyle/pmd (Task 08)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from lib.review_evidence.collectors._jacoco import parse_jacoco_xml
from lib.review_evidence.registry import register


MAVEN_JACOCO_PATHS = [
    Path("target/site/jacoco/jacoco.xml"),
]
GRADLE_JACOCO_PATHS = [
    Path("build/reports/jacoco/test/jacocoTestReport.xml"),
    Path("build/reports/jacoco/jacocoTestReport.xml"),
]


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
            "lint": None,        # populated by Task 08
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


register(JavaCollector())
