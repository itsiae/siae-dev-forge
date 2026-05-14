# Task 06 — detector.py criteri 1-5

**Stato:** [DONE]
**SP:** 1.5 Human / 0.5 Augmented
**Dipendenze:** task-04 (schema)

## Goal

Implementare `lib/release_risk/detector.py` con funzioni per criteri 1-5: DB change, OCP/K8s config, breaking API, ext deps, critical service (stub che delega a kg_lookup).

## File coinvolti

- Create: `lib/release_risk/detector.py`

## Step

### Step 1 — Scrivi detector.py iniziale (criteri 1-5)

Write `lib/release_risk/detector.py`:
```python
"""Detector criteri 1-15 (criteri 16-18 hanno file dedicati)."""
import re
from pathlib import Path
from typing import Optional
from lib.release_risk.schema import CriterionResult


def criterion_1_db_change(diff_files: list[str], diff_content: str) -> CriterionResult:
    """+3 se DB change (DDL/DML) trovato."""
    file_pattern = re.compile(r"\.(sql|hql|xml)$|migration|liquibase|flyway|changelog|V\d+__", re.I)
    content_pattern = re.compile(
        r"CREATE TABLE|ALTER TABLE|DROP TABLE|INSERT INTO|UPDATE .+ SET|DELETE FROM|ADD COLUMN|DROP COLUMN",
        re.I,
    )
    matched_files = [f for f in diff_files if file_pattern.search(f)]
    has_ddl = bool(content_pattern.search(diff_content))
    if matched_files or has_ddl:
        ev = [f"file:{f}" for f in matched_files[:5]]
        if has_ddl:
            ev.append("ddl_keyword_detected")
        return CriterionResult(id=1, name="Database change (DDL/DML)", status="YES",
                               weight=3, evidence=ev, source="diff:grep")
    return CriterionResult(id=1, name="Database change (DDL/DML)", status="NO",
                           weight=3, source="diff:grep")


def criterion_2_ocp_config(diff_files: list[str], diff_content: str) -> CriterionResult:
    """+2 se OCP/K8s config change."""
    file_pattern = re.compile(r"\.(yaml|yml)$|openshift|ocp|deployment|route|configmap|secret|helm|k8s|kubernetes", re.I)
    content_pattern = re.compile(r"kind:\s*(Deployment|Route|Secret|ConfigMap)", re.I)
    matched = [f for f in diff_files if file_pattern.search(f)]
    has_kind = bool(content_pattern.search(diff_content))
    if matched or has_kind:
        ev = [f"file:{f}" for f in matched[:5]]
        return CriterionResult(id=2, name="OCP/K8s config change", status="YES",
                               weight=2, evidence=ev, source="diff:grep")
    return CriterionResult(id=2, name="OCP/K8s config change", status="NO", weight=2, source="diff:grep")


def criterion_3_breaking_api(diff_files: list[str], diff_content: str) -> CriterionResult:
    """+3 se breaking API: endpoint rimossi o firma cambiata."""
    removed_endpoint = re.compile(
        r"^-\s*.*(@(Get|Post|Put|Delete|Path)Mapping|@RequestMapping)",
        re.MULTILINE,
    )
    if removed_endpoint.search(diff_content):
        return CriterionResult(id=3, name="Breaking API changes", status="YES",
                               weight=3, evidence=["removed_mapping_annotation"],
                               source="diff:grep")
    return CriterionResult(id=3, name="Breaking API changes", status="NO", weight=3, source="diff:grep")


def criterion_4_ext_deps(diff_files: list[str], diff_content: str) -> CriterionResult:
    """+2 se nuove/modificate dipendenze esterne."""
    dep_files = {"pom.xml", "package.json", "package-lock.json", "requirements.txt",
                 "build.gradle", "Cargo.toml", "go.mod"}
    matched = [f for f in diff_files if Path(f).name in dep_files]
    if matched:
        return CriterionResult(id=4, name="External dependencies changed", status="YES",
                               weight=2, evidence=[f"file:{f}" for f in matched],
                               source="diff:files")
    return CriterionResult(id=4, name="External dependencies changed", status="NO",
                           weight=2, source="diff:files")


def criterion_5_critical_service_stub(service_name: str, kg_lookup_fn=None) -> CriterionResult:
    """+3 se servizio critico. Delega a kg_lookup_fn (vedi task-12)."""
    if kg_lookup_fn is None:
        return CriterionResult(id=5, name="Critical service", status="REQUIRES_INPUT",
                               weight=3, source="ask:user",
                               notes="kg_lookup_fn not provided")
    return kg_lookup_fn(service_name)
```

### Step 2 — Verifica import

Run:
```bash
python3 -c "from lib.release_risk.detector import criterion_1_db_change, criterion_2_ocp_config, criterion_3_breaking_api, criterion_4_ext_deps, criterion_5_critical_service_stub; print('OK')"
```
Output atteso: `OK`

### Step 3 — Commit

```bash
git add lib/release_risk/detector.py
git commit -m "feat(release-risk): detector criteri 1-5 (DB, OCP, API, deps, critical-stub)"
```

## Criteri di accettazione

- [ ] 5 funzioni implementate con regex pattern documentati
- [ ] `criterion_5` accetta `kg_lookup_fn` injectable (per testability)
- [ ] Import senza errori
- [ ] Commit eseguito
