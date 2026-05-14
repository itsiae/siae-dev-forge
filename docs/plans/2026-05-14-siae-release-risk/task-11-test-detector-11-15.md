# Task 11 — [TDD] test detector 11-15 + integration end-to-end

**Stato:** [PENDING]
**SP:** 1 Human / 0.5 Augmented
**Dipendenze:** task-10

## Goal

Unit test criteri 11-15 + 1 test integration end-to-end che invoca detector su fixture diff completo.

## File coinvolti

- Create: `tests/test_release_risk_detector_11_15.py`
- Create: `tests/test_release_risk_detector_integration.py`
- Create: `tests/fixtures/release_risk/diff_full_release.txt`

## Step

### Step 1 — Test criteri 11-15

Write `tests/test_release_risk_detector_11_15.py`:
```python
from lib.release_risk.detector import (
    criterion_11_coverage_stub, criterion_12_e2e_tests, criterion_13_perf_tests,
    criterion_14_user_impact, criterion_15_files_count,
)
from lib.release_risk.schema import CriterionResult


def test_c11_coverage_stub_requires_input_without_fn():
    r = criterion_11_coverage_stub()
    assert r.status == "REQUIRES_INPUT"


def test_c11_coverage_stub_delegates():
    def fake_cov(sha):
        return CriterionResult(id=11, name="Coverage < 70%", status="NO",
                               weight=2, source="evidence:coverage",
                               evidence=["overall_pct=78"])
    r = criterion_11_coverage_stub(coverage_src_fn=fake_cov, sha="abc123")
    assert r.status == "NO"
    assert "overall_pct=78" in r.evidence


def test_c12_e2e_no_ci_config():
    r = criterion_12_e2e_tests(ci_config_present=False, e2e_stage_found=False)
    assert r.status == "REQUIRES_INPUT"


def test_c12_e2e_ci_present_no_stage():
    r = criterion_12_e2e_tests(ci_config_present=True, e2e_stage_found=False)
    assert r.status == "YES"
    assert r.weight == 2


def test_c12_e2e_ci_with_stage():
    r = criterion_12_e2e_tests(ci_config_present=True, e2e_stage_found=True)
    assert r.status == "NO"


def test_c13_perf_jmeter():
    r = criterion_13_perf_tests("Run jmeter -t test.jmx")
    assert r.status == "YES"
    assert r.weight == -1


def test_c13_perf_no():
    r = criterion_13_perf_tests("just code")
    assert r.status == "NO"


def test_c14_user_impact_none():
    r = criterion_14_user_impact(None)
    assert r.status == "REQUIRES_INPUT"


def test_c14_user_impact_true():
    r = criterion_14_user_impact(True)
    assert r.status == "YES"


def test_c14_user_impact_false():
    r = criterion_14_user_impact(False)
    assert r.status == "NO"


def test_c15_files_count_yes():
    r = criterion_15_files_count(["f{}.java".format(i) for i in range(15)])
    assert r.status == "YES"
    assert r.weight == 1


def test_c15_files_count_no():
    r = criterion_15_files_count(["a.java", "b.java"])
    assert r.status == "NO"
```

### Step 2 — Fixture diff full release

Write `tests/fixtures/release_risk/diff_full_release.txt`:
```
diff --git a/pom.xml b/pom.xml
+ <dependency><groupId>org.x</groupId></dependency>
diff --git a/k8s/deployment.yaml b/k8s/deployment.yaml
kind: Deployment
strategy: Recreate
diff --git a/db/V42__add_email.sql b/db/V42__add_email.sql
+ALTER TABLE users ADD COLUMN email VARCHAR(255);
```

### Step 3 — Integration test

Write `tests/test_release_risk_detector_integration.py`:
```python
"""Integration test: invoca tutti i criteri 1-15 su fixture diff full."""
from pathlib import Path
from lib.release_risk.detector import (
    criterion_1_db_change, criterion_2_ocp_config, criterion_4_ext_deps,
    criterion_8_downtime, criterion_9_data_migration, criterion_15_files_count,
)

FIXTURE = Path(__file__).parent / "fixtures" / "release_risk" / "diff_full_release.txt"


def test_full_release_diff_multi_criteria_yes():
    diff = FIXTURE.read_text()
    files = ["pom.xml", "k8s/deployment.yaml", "db/V42__add_email.sql"]
    # Aspettati YES su: c1 (DB), c2 (K8s), c4 (deps), c8 (downtime), c9 (migration)
    assert criterion_1_db_change(files, diff).status == "YES"
    assert criterion_2_ocp_config(files, diff).status == "YES"
    assert criterion_4_ext_deps(files, diff).status == "YES"
    assert criterion_8_downtime(diff).status == "YES"
    assert criterion_9_data_migration(files, diff).status == "YES"
    assert criterion_15_files_count(files).status == "NO"  # solo 3 file
```

### Step 4 — Esegui

Run:
```bash
pytest tests/test_release_risk_detector_11_15.py tests/test_release_risk_detector_integration.py -v
```
Output atteso: 12 + 1 = 13 PASSED.

### Step 5 — Commit

```bash
git add tests/test_release_risk_detector_11_15.py tests/test_release_risk_detector_integration.py tests/fixtures/release_risk/diff_full_release.txt
git commit -m "test(release-risk): unit detector 11-15 + integration end-to-end"
```

## Criteri di accettazione

- [ ] 12 unit test PASSED + 1 integration
- [ ] Fixture diff completo con multi-criteri YES
- [ ] Test conferma criterion injection (stub coverage_src)
- [ ] Commit eseguito
