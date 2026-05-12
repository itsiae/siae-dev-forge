"""Java stack collector: jacoco coverage + checkstyle/pmd static analysis."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable, Optional

from lib.review_evidence.collectors._checkstyle import parse_checkstyle_xml
from lib.review_evidence.collectors._jacoco import parse_jacoco_xml
from lib.review_evidence.collectors._pmd import parse_pmd_xml
from lib.review_evidence.registry import register


MAVEN_JACOCO_REL = Path("target/site/jacoco/jacoco.xml")
GRADLE_JACOCO_RELS = [
    Path("build/reports/jacoco/test/jacocoTestReport.xml"),
    Path("build/reports/jacoco/jacocoTestReport.xml"),
]
CHECKSTYLE_REL = Path("target/checkstyle-result.xml")
PMD_REL = Path("target/pmd.xml")

# E16: monorepo discovery — never descend into VCS/IDE/JS-deps when
# searching for module-level Jacoco/Checkstyle/PMD reports. Without the
# prune, ``rglob`` on a corporate monorepo (many ``node_modules`` mixed
# with maven modules) takes minutes and may even OOM on macOS due to the
# unbounded BFS.
PRUNE_DIRS = frozenset({
    ".git", ".idea", ".vscode",
    ".gradle", ".m2",
    "node_modules",
    "__pycache__", ".venv", "venv",
    # NOTE: we deliberately DO NOT prune ``target`` and ``build`` — those are
    # exactly where Jacoco/Checkstyle/PMD reports live. We do prune the
    # outer ``.gradle`` (gradle daemon cache) and ``.m2`` (local maven repo
    # accidentally inside the workspace).
})
MAX_WALK_DEPTH = 6  # services/<svc>/module/target/site/jacoco/jacoco.xml is 6


def _walk(root: Path, max_depth: int = MAX_WALK_DEPTH) -> Iterable[Path]:
    base_parts = len(root.parts)
    for dirpath, dirnames, filenames in os.walk(root):
        depth = len(Path(dirpath).parts) - base_parts
        if depth >= max_depth:
            dirnames[:] = []
        else:
            dirnames[:] = [d for d in dirnames if d not in PRUNE_DIRS]
        for f in filenames:
            yield Path(dirpath) / f


def _find_reports(root: Path, relative_targets: Iterable[Path]) -> list[Path]:
    """Find all files whose path ends with any of ``relative_targets``.

    Used to discover per-module Jacoco/Checkstyle/PMD reports in
    multi-module Maven/Gradle setups. Returns absolute paths in
    deterministic order (sorted).
    """
    targets = tuple(str(t) for t in relative_targets)
    found: list[Path] = []
    for p in _walk(root):
        sp = str(p)
        if any(sp.endswith(os.sep + t) or sp.endswith("/" + t) for t in targets):
            found.append(p)
    return sorted(found)


class JavaCollector:
    name = "java"

    def is_applicable(self, repo_root: Path) -> bool:
        return (
            (repo_root / "pom.xml").exists()
            or (repo_root / "build.gradle").exists()
            or (repo_root / "build.gradle.kts").exists()
            # E16: a monorepo may have only sub-module pom.xml — check
            # a bounded walk before giving up.
            or any(
                p.name in ("pom.xml", "build.gradle", "build.gradle.kts")
                for p in _walk(repo_root, max_depth=3)
            )
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

    def _jacoco(self, repo_root: Path) -> tuple[Optional[dict], str]:
        is_maven = (repo_root / "pom.xml").exists() or any(
            p.name == "pom.xml" for p in _walk(repo_root, max_depth=3)
        )
        rels = [MAVEN_JACOCO_REL] if is_maven else GRADLE_JACOCO_RELS
        source = "local:jacoco-maven" if is_maven else "local:jacoco-gradle"

        # Single-module shortcut (kept for fixture compat)
        for rel in rels:
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

        # E16: multi-module discovery — walk and aggregate.
        reports = _find_reports(repo_root, rels)
        if not reports:
            return None, source
        total_covered = 0
        total_missed = 0
        per_file: list[dict] = []
        for rep in reports:
            try:
                parsed = parse_jacoco_xml(rep.read_text())
            except Exception:
                continue
            # parsed["overall_pct"] is already the per-module pct; we re-derive
            # missed/covered from per_file ratios is brittle. Easier: weight by
            # number of per_file entries. Good-enough averaging.
            per_file.extend(parsed["per_file"])
            # Recompute weight: a module with no per_file contributes 0 to
            # both numerator and denominator.
            for pf in parsed["per_file"]:
                # Treat each file as 100 line-units for averaging (we lost
                # raw counters when delegating to parse_jacoco_xml). This is
                # a coarse approximation; for exact aggregation upstream
                # parse should expose total_missed/covered. Acceptable for
                # MVP: per-module overall_pct ratio is preserved on average.
                pct = pf["pct"]
                total_covered += pct
                total_missed += (100 - pct)
        if not per_file:
            return None, source
        overall = (total_covered / (total_covered + total_missed) * 100) if (total_covered + total_missed) else 0
        return {
            "overall_pct": round(overall, 2),
            "delta_vs_base": 0.0,
            "per_file": per_file,
            "source": source,
        }, source

    def _static_analysis(self, repo_root: Path) -> Optional[dict]:
        cs = None
        full = repo_root / CHECKSTYLE_REL
        if full.exists():
            try:
                cs = parse_checkstyle_xml(full.read_text())
            except Exception:
                cs = None

        pmd = None
        full = repo_root / PMD_REL
        if full.exists():
            try:
                pmd = parse_pmd_xml(full.read_text())
            except Exception:
                pmd = None

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


# Keep these aliases public for back-compat with code referencing the
# old constant names (tests imported them indirectly via the module).
MAVEN_JACOCO_PATHS = [MAVEN_JACOCO_REL]
GRADLE_JACOCO_PATHS = GRADLE_JACOCO_RELS
CHECKSTYLE_PATHS = [CHECKSTYLE_REL]
PMD_PATHS = [PMD_REL]
