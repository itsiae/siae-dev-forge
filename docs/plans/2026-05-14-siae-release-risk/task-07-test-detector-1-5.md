# Task 07 — [TDD] test detector criteri 1-5

**Stato:** [PENDING]
**SP:** 1 Human / 0.5 Augmented
**Dipendenze:** task-06

## Goal

Unit test per detector criteri 1-5 con fixture diff string.

## File coinvolti

- Create: `tests/test_release_risk_detector_1_5.py`
- Create: `tests/fixtures/release_risk/diff_with_db_change.txt`
- Create: `tests/fixtures/release_risk/diff_with_breaking_api.txt`

## Step

### Step 1 — Crea fixture diff con DB change

Write `tests/fixtures/release_risk/diff_with_db_change.txt`:
```
diff --git a/db/migration/V42__add_user_email.sql b/db/migration/V42__add_user_email.sql
new file mode 100644
--- /dev/null
+++ b/db/migration/V42__add_user_email.sql
@@ -0,0 +1,3 @@
+ALTER TABLE users ADD COLUMN email VARCHAR(255);
```

### Step 2 — Crea fixture diff con breaking API

Write `tests/fixtures/release_risk/diff_with_breaking_api.txt`:
```
diff --git a/src/main/java/it/siae/UserController.java b/src/main/java/it/siae/UserController.java
--- a/src/main/java/it/siae/UserController.java
+++ b/src/main/java/it/siae/UserController.java
@@ -10,8 +10,3 @@
-    @GetMapping("/api/v1/users/{id}")
-    public ResponseEntity<User> getUser(@PathVariable Long id) { ... }
-
     @GetMapping("/api/v2/users/{id}")
     public ResponseEntity<UserDto> getUserV2(@PathVariable Long id) { ... }
```

### Step 3 — Scrivi test

Write `tests/test_release_risk_detector_1_5.py`:
```python
from pathlib import Path
from lib.release_risk.detector import (
    criterion_1_db_change, criterion_2_ocp_config, criterion_3_breaking_api,
    criterion_4_ext_deps, criterion_5_critical_service_stub,
)

FIXTURES = Path(__file__).parent / "fixtures" / "release_risk"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text()


def test_c1_db_change_yes():
    diff = _read("diff_with_db_change.txt")
    files = ["db/migration/V42__add_user_email.sql"]
    r = criterion_1_db_change(files, diff)
    assert r.status == "YES"
    assert r.weight == 3
    assert any("V42__add_user_email.sql" in e for e in r.evidence)


def test_c1_db_change_no():
    r = criterion_1_db_change(["src/main/App.java"], "// just code")
    assert r.status == "NO"


def test_c2_ocp_yaml_with_deployment_kind():
    diff = "kind: Deployment\nspec:\n  replicas: 3"
    r = criterion_2_ocp_config(["deployment.yaml"], diff)
    assert r.status == "YES"
    assert r.weight == 2


def test_c2_ocp_no():
    r = criterion_2_ocp_config(["src/App.java"], "")
    assert r.status == "NO"


def test_c3_breaking_api_yes():
    diff = _read("diff_with_breaking_api.txt")
    r = criterion_3_breaking_api(["src/main/java/UserController.java"], diff)
    assert r.status == "YES"
    assert r.weight == 3


def test_c3_breaking_api_no():
    diff_additive = "+    @GetMapping(\"/api/v3/users\") public ... { }"
    r = criterion_3_breaking_api(["src/main/UserController.java"], diff_additive)
    assert r.status == "NO"


def test_c4_ext_deps_pom_xml():
    r = criterion_4_ext_deps(["pom.xml"], "")
    assert r.status == "YES"
    assert "pom.xml" in str(r.evidence)


def test_c4_ext_deps_package_json():
    r = criterion_4_ext_deps(["frontend/package.json"], "")
    assert r.status == "YES"


def test_c4_ext_deps_no():
    r = criterion_4_ext_deps(["src/App.java"], "")
    assert r.status == "NO"


def test_c5_stub_requires_input_without_kg_fn():
    r = criterion_5_critical_service_stub("sport-test-service")
    assert r.status == "REQUIRES_INPUT"


def test_c5_stub_delegates_to_kg_fn():
    from lib.release_risk.schema import CriterionResult

    def fake_kg(name: str) -> CriterionResult:
        return CriterionResult(id=5, name="Critical service", status="YES",
                               weight=3, source="mcp:sport-kg")

    r = criterion_5_critical_service_stub("sport-test-service", kg_lookup_fn=fake_kg)
    assert r.status == "YES"
    assert r.source == "mcp:sport-kg"
```

### Step 4 — Esegui test

Run:
```bash
pytest tests/test_release_risk_detector_1_5.py -v
```
Output atteso: 11 PASSED.

### Step 5 — Commit

```bash
git add tests/test_release_risk_detector_1_5.py tests/fixtures/release_risk/
git commit -m "test(release-risk): unit test detector criteri 1-5 + fixture diff"
```

## Criteri di accettazione

- [ ] 11 test PASSED
- [ ] Fixture diff salvate (DB change + breaking API)
- [ ] Test `c5_stub` valida injection pattern
- [ ] Commit eseguito
