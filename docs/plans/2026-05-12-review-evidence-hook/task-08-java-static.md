# Task 08 — Java collector: static analysis (checkstyle + pmd)

**SP:** 2.0 · **AC mappati:** AC #3 · **Dipendenze:** Task 07 · **Wave:** 3

## Goal

Estendere `lib/review_evidence/collectors/java.py` con parsing di `checkstyle-result.xml` (Maven plugin) e `pmd.xml` (PMD plugin). Aggregare errors+warnings nella sezione `lint`. Complexity Java NON è in MVP (delegata a Sonar via ci_fetch).

## File coinvolti

**Modificare:**
- `lib/review_evidence/collectors/java.py` (estensione)

**Creare:**
- `lib/review_evidence/collectors/_checkstyle.py`
- `lib/review_evidence/collectors/_pmd.py`
- `tests/test_review_evidence_collector_java_static.py`
- `tests/fixtures/review-evidence/checkstyle_result.xml`
- `tests/fixtures/review-evidence/pmd_report.xml`

## Step TDD

### Step 1 — Fixture

`tests/fixtures/review-evidence/checkstyle_result.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<checkstyle version="10.0.0">
  <file name="/repo/src/main/java/PaymentService.java">
    <error line="12" severity="error" message="Line too long (130 chars)" source="LineLength"/>
    <error line="45" severity="warning" message="Magic number" source="MagicNumber"/>
  </file>
  <file name="/repo/src/main/java/CatalogService.java">
    <error line="3" severity="error" message="Missing javadoc" source="MissingJavadoc"/>
  </file>
</checkstyle>
```

`tests/fixtures/review-evidence/pmd_report.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<pmd version="6.55.0">
  <file name="/repo/src/main/java/PaymentService.java">
    <violation beginline="22" rule="UnusedPrivateField" priority="3" ruleset="bestpractices"
               class="PaymentService" method="">Unused field</violation>
    <violation beginline="80" rule="CyclomaticComplexity" priority="2" ruleset="design"
               class="PaymentService" method="process">Method too complex</violation>
  </file>
</pmd>
```

### Step 2 — Test fallente

```python
"""Tests for Java collector — static analysis (checkstyle + pmd)."""
import shutil
from pathlib import Path

from lib.review_evidence.collectors.java import JavaCollector
from lib.review_evidence.collectors._checkstyle import parse_checkstyle_xml
from lib.review_evidence.collectors._pmd import parse_pmd_xml

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_parse_checkstyle_counts():
    parsed = parse_checkstyle_xml((FIX / "checkstyle_result.xml").read_text())
    assert parsed["errors"] == 2
    assert parsed["warnings"] == 1
    assert len(parsed["findings"]) == 3


def test_parse_pmd_counts_by_priority():
    parsed = parse_pmd_xml((FIX / "pmd_report.xml").read_text())
    # priority 1-2 = error, 3-5 = warning
    assert parsed["errors"] == 1
    assert parsed["warnings"] == 1


def test_collect_java_aggregates_lint(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")

    cs_target = tmp_path / "target"
    cs_target.mkdir()
    shutil.copyfile(FIX / "checkstyle_result.xml", cs_target / "checkstyle-result.xml")

    pmd_target = tmp_path / "target"
    shutil.copyfile(FIX / "pmd_report.xml", pmd_target / "pmd.xml")

    result = JavaCollector().collect(tmp_path, "main", "HEAD")
    assert result["lint"] is not None
    assert result["lint"]["errors"] == 2 + 1   # 2 checkstyle + 1 pmd
    assert result["lint"]["warnings"] == 1 + 1
    assert "checkstyle" in result["lint"]["source"]
    assert "pmd" in result["lint"]["source"]


def test_collect_only_checkstyle(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    cs_target = tmp_path / "target"
    cs_target.mkdir()
    shutil.copyfile(FIX / "checkstyle_result.xml", cs_target / "checkstyle-result.xml")

    result = JavaCollector().collect(tmp_path, "main", "HEAD")
    assert result["lint"]["errors"] == 2
    assert result["lint"]["warnings"] == 1
    assert result["lint"]["source"] == "local:checkstyle"


def test_collect_no_static_returns_lint_none(tmp_path):
    (tmp_path / "pom.xml").write_text("<project/>")
    result = JavaCollector().collect(tmp_path, "main", "HEAD")
    assert result["lint"] is None
```

### Step 3 — Implementa parser

`lib/review_evidence/collectors/_checkstyle.py`:

```python
"""Minimal checkstyle XML parser."""
import xml.etree.ElementTree as ET


def parse_checkstyle_xml(content: str) -> dict:
    root = ET.fromstring(content)
    errors = 0
    warnings = 0
    findings = []
    for f in root.findall("file"):
        for e in f.findall("error"):
            sev = e.get("severity", "error")
            if sev == "error":
                errors += 1
            else:
                warnings += 1
            findings.append({
                "file": f.get("name"),
                "line": int(e.get("line", 0)),
                "rule": e.get("source", "?"),
                "severity": sev,
                "msg": e.get("message", ""),
            })
    return {"errors": errors, "warnings": warnings, "findings": findings}
```

`lib/review_evidence/collectors/_pmd.py`:

```python
"""Minimal PMD XML parser."""
import xml.etree.ElementTree as ET


def parse_pmd_xml(content: str) -> dict:
    root = ET.fromstring(content)
    errors = 0
    warnings = 0
    findings = []
    for f in root.findall("file"):
        for v in f.findall("violation"):
            priority = int(v.get("priority", 5))
            sev = "error" if priority <= 2 else "warning"
            if sev == "error":
                errors += 1
            else:
                warnings += 1
            findings.append({
                "file": f.get("name"),
                "line": int(v.get("beginline", 0)),
                "rule": v.get("rule", "?"),
                "severity": sev,
                "msg": (v.text or "").strip(),
            })
    return {"errors": errors, "warnings": warnings, "findings": findings}
```

### Step 4 — Estendi `JavaCollector.collect`

Aggiungi metodo `_static_analysis` e wire-up:

```python
# Aggiungere a JavaCollector

CHECKSTYLE_PATHS = [Path("target/checkstyle-result.xml")]
PMD_PATHS = [Path("target/pmd.xml")]

def _static_analysis(self, repo_root: Path) -> dict | None:
    from lib.review_evidence.collectors._checkstyle import parse_checkstyle_xml
    from lib.review_evidence.collectors._pmd import parse_pmd_xml

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
    findings = []
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
    return {"errors": errors, "warnings": warnings, "findings": findings,
            "source": "local:" + "+".join(sources)}
```

E nel `collect()`:

```python
def collect(self, repo_root: Path, base_ref: str, head_ref: str) -> dict[str, Any]:
    cov, _ = self._jacoco(repo_root)
    return {
        "stack": "java",
        "coverage": cov,
        "lint": self._static_analysis(repo_root),
        "complexity": None,
    }
```

### Step 5 — Esegui test e commit

```bash
pytest tests/test_review_evidence_collector_java_static.py -v
# 5 passed atteso

git add lib/review_evidence/collectors/java.py \
        lib/review_evidence/collectors/_checkstyle.py \
        lib/review_evidence/collectors/_pmd.py \
        tests/test_review_evidence_collector_java_static.py \
        tests/fixtures/review-evidence/checkstyle_result.xml \
        tests/fixtures/review-evidence/pmd_report.xml
git commit -m "feat(review-evidence): add Java static analysis (checkstyle+pmd) (#task-08)"
```

## Criteri di accettazione

- [ ] `_checkstyle.parse_checkstyle_xml()` aggrega errors+warnings+findings
- [ ] `_pmd.parse_pmd_xml()` mappa priority 1-2 → error, 3-5 → warning
- [ ] `JavaCollector._static_analysis()` aggrega checkstyle+pmd se presenti
- [ ] Source label include i tool effettivamente usati
- [ ] 5 test passano
