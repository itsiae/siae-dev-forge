# Task 07 — Java collector: coverage (jacoco Maven + Gradle)

**SP:** 1.5 · **AC mappati:** AC #3 · **Dipendenze:** Task 04 · **Wave:** 3

## Goal

Implementare la prima metà del Java collector: detection (Maven `pom.xml` / Gradle `build.gradle*`) + parsing del report jacoco XML. La parte static analysis (checkstyle + pmd) è nel Task 08.

## File coinvolti

**Creare:**
- `lib/review_evidence/collectors/java.py` (parte coverage, Task 08 estende)
- `lib/review_evidence/collectors/_jacoco.py` (XML parser helper)
- `tests/test_review_evidence_collector_java_coverage.py`
- `tests/fixtures/review-evidence/jacoco_maven.xml`
- `tests/fixtures/review-evidence/jacoco_gradle.xml`

## Step TDD

### Step 1 — Fixture jacoco_maven.xml

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<!DOCTYPE report PUBLIC "-//JACOCO//DTD Report 1.1//EN" "report.dtd">
<report name="payment-service">
  <package name="it/siae/payment">
    <class name="it/siae/payment/PaymentService" sourcefilename="PaymentService.java">
      <counter type="LINE" missed="3" covered="17"/>
      <counter type="COMPLEXITY" missed="1" covered="5"/>
    </class>
    <sourcefile name="PaymentService.java">
      <counter type="LINE" missed="3" covered="17"/>
    </sourcefile>
  </package>
  <counter type="INSTRUCTION" missed="20" covered="80"/>
  <counter type="LINE" missed="3" covered="17"/>
  <counter type="COMPLEXITY" missed="1" covered="5"/>
</report>
```

`tests/fixtures/review-evidence/jacoco_gradle.xml` (identica struttura, valori diversi):

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<!DOCTYPE report PUBLIC "-//JACOCO//DTD Report 1.1//EN" "report.dtd">
<report name="catalog-service">
  <package name="it/siae/catalog">
    <sourcefile name="CatalogService.java">
      <counter type="LINE" missed="10" covered="40"/>
    </sourcefile>
  </package>
  <counter type="LINE" missed="10" covered="40"/>
</report>
```

### Step 2 — Test fallente

`tests/test_review_evidence_collector_java_coverage.py`:

```python
"""Tests for Java collector — coverage (jacoco)."""
import shutil
from pathlib import Path

import pytest

from lib.review_evidence.collectors.java import JavaCollector
from lib.review_evidence.collectors._jacoco import parse_jacoco_xml

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_parse_jacoco_overall_pct():
    xml = (FIX / "jacoco_maven.xml").read_text()
    data = parse_jacoco_xml(xml)
    # 17 / (17+3) = 85.0
    assert data["overall_pct"] == 85.0
    assert len(data["per_file"]) == 1


def test_is_applicable_maven(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    assert JavaCollector().is_applicable(tmp_path) is True


def test_is_applicable_gradle(tmp_path):
    (tmp_path / "build.gradle").write_text("plugins { id 'java' }")
    assert JavaCollector().is_applicable(tmp_path) is True


def test_is_applicable_gradle_kts(tmp_path):
    (tmp_path / "build.gradle.kts").write_text("plugins { java }")
    assert JavaCollector().is_applicable(tmp_path) is True


def test_not_applicable_otherwise(tmp_path):
    (tmp_path / "README.md").write_text("md")
    assert JavaCollector().is_applicable(tmp_path) is False


def test_collect_maven_jacoco_path(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    target = tmp_path / "target" / "site" / "jacoco"
    target.mkdir(parents=True)
    shutil.copyfile(FIX / "jacoco_maven.xml", target / "jacoco.xml")

    result = JavaCollector().collect(tmp_path, "main", "HEAD")
    assert result["stack"] == "java"
    assert result["coverage"]["overall_pct"] == 85.0
    assert result["coverage"]["source"] == "local:jacoco-maven"


def test_collect_gradle_jacoco_path(tmp_path):
    (tmp_path / "build.gradle").write_text("plugins{}")
    target = tmp_path / "build" / "reports" / "jacoco" / "test"
    target.mkdir(parents=True)
    shutil.copyfile(FIX / "jacoco_gradle.xml", target / "jacocoTestReport.xml")

    result = JavaCollector().collect(tmp_path, "main", "HEAD")
    assert result["coverage"]["overall_pct"] == 80.0
    assert result["coverage"]["source"] == "local:jacoco-gradle"


def test_collect_missing_jacoco_returns_none(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    result = JavaCollector().collect(tmp_path, "main", "HEAD")
    assert result["coverage"] is None
```

### Step 3 — Implementa _jacoco.py

```python
"""Minimal Jacoco XML parser (no external deps — xml.etree)."""
from __future__ import annotations

import xml.etree.ElementTree as ET


def parse_jacoco_xml(content: str) -> dict:
    root = ET.fromstring(content)
    # Top-level <counter type="LINE" missed=".." covered=".."/>
    overall_missed = 0
    overall_covered = 0
    for c in root.findall("counter"):
        if c.get("type") == "LINE":
            overall_missed = int(c.get("missed", 0))
            overall_covered = int(c.get("covered", 0))
    total = overall_missed + overall_covered
    pct = (overall_covered / total * 100) if total else 0.0

    per_file = []
    for pkg in root.findall("package"):
        for sf in pkg.findall("sourcefile"):
            f_missed = 0
            f_covered = 0
            for c in sf.findall("counter"):
                if c.get("type") == "LINE":
                    f_missed = int(c.get("missed", 0))
                    f_covered = int(c.get("covered", 0))
            f_total = f_missed + f_covered
            f_pct = (f_covered / f_total * 100) if f_total else 0.0
            per_file.append({
                "path": f"{pkg.get('name','')}/{sf.get('name','')}",
                "pct": round(f_pct, 2),
                "uncovered_lines": [],
            })
    return {"overall_pct": round(pct, 2), "per_file": per_file}
```

### Step 4 — Implementa java.py (parte coverage, Task 08 estenderà con static)

```python
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
```

### Step 5 — Esegui test e commit

```bash
pytest tests/test_review_evidence_collector_java_coverage.py -v
# 8 passed atteso

git add lib/review_evidence/collectors/java.py \
        lib/review_evidence/collectors/_jacoco.py \
        tests/test_review_evidence_collector_java_coverage.py \
        tests/fixtures/review-evidence/jacoco_maven.xml \
        tests/fixtures/review-evidence/jacoco_gradle.xml
git commit -m "feat(review-evidence): add Java collector coverage (jacoco maven+gradle) (#task-07)"
```

## Criteri di accettazione

- [ ] `_jacoco.parse_jacoco_xml()` calcola overall_pct + per_file
- [ ] `JavaCollector.is_applicable()` rileva Maven (pom.xml) e Gradle (build.gradle, build.gradle.kts)
- [ ] Path Maven `target/site/jacoco/jacoco.xml` riconosciuto
- [ ] Path Gradle `build/reports/jacoco/test/jacocoTestReport.xml` riconosciuto
- [ ] Missing report → coverage=None (graceful)
- [ ] 8 test passano
