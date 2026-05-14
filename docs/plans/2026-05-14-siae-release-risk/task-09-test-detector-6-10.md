# Task 09 — [TDD] test detector criteri 6-10

**Stato:** [DONE]
**SP:** 1 Human / 0.5 Augmented
**Dipendenze:** task-08

## Goal

Unit test per detector criteri 6-10.

## File coinvolti

- Create: `tests/test_release_risk_detector_6_10.py`

## Step

### Step 1 — Scrivi test

Write `tests/test_release_risk_detector_6_10.py`:
```python
from lib.release_risk.detector import (
    criterion_6_first_release, criterion_7_complex_rollback,
    criterion_8_downtime, criterion_9_data_migration, criterion_10_feature_flag,
)


def test_c6_first_release_yes():
    r = criterion_6_first_release(0)
    assert r.status == "YES"
    assert r.weight == 2


def test_c6_first_release_no():
    r = criterion_6_first_release(5)
    assert r.status == "NO"


def test_c7_rollback_implied_by_c1():
    r = criterion_7_complex_rollback("YES", "NO", "no destructive keyword")
    assert r.status == "YES"
    assert "implied" in r.evidence[0]


def test_c7_rollback_implied_by_c9():
    r = criterion_7_complex_rollback("NO", "YES", "")
    assert r.status == "YES"


def test_c7_rollback_irreversible_keyword():
    r = criterion_7_complex_rollback("NO", "NO", "this is irreversible operation")
    assert r.status == "YES"


def test_c7_rollback_no():
    r = criterion_7_complex_rollback("NO", "NO", "regular code")
    assert r.status == "NO"


def test_c8_downtime_recreate():
    r = criterion_8_downtime("strategy: Recreate\n  selector: {}")
    assert r.status == "YES"
    assert r.weight == 3


def test_c8_downtime_maxunavailable():
    r = criterion_8_downtime("rollingUpdate:\n    maxUnavailable: 1")
    assert r.status == "YES"


def test_c8_downtime_no():
    r = criterion_8_downtime("strategy: RollingUpdate\nmaxUnavailable: 25%")
    assert r.status == "NO"


def test_c9_migration_file():
    r = criterion_9_data_migration(["db/V42__migrate_users.sql"], "")
    assert r.status == "YES"


def test_c9_migration_class():
    r = criterion_9_data_migration(["src/MigrationRunner.java"], "public class DataMigration { }")
    assert r.status == "YES"


def test_c9_migration_no():
    r = criterion_9_data_migration(["src/App.java"], "")
    assert r.status == "NO"


def test_c10_feature_flag_yes_ff4j():
    r = criterion_10_feature_flag("ff4j.check(\"feature.x\")")
    assert r.status == "YES"
    assert r.weight == -1  # mitigation


def test_c10_feature_flag_yes_conditional():
    r = criterion_10_feature_flag("@ConditionalOnProperty(\"feature.enabled\")")
    assert r.status == "YES"


def test_c10_feature_flag_no():
    r = criterion_10_feature_flag("if (true) { doStuff(); }")
    assert r.status == "NO"
```

### Step 2 — Esegui

Run:
```bash
pytest tests/test_release_risk_detector_6_10.py -v
```
Output atteso: 14 PASSED.

### Step 3 — Commit

```bash
git add tests/test_release_risk_detector_6_10.py
git commit -m "test(release-risk): unit test detector criteri 6-10"
```

## Criteri di accettazione

- [ ] 14 test PASSED
- [ ] Test su 3 path inference per Criterion 7 (c1, c9, keyword)
- [ ] Test weight negative (-1) per Criterion 10
- [ ] Commit eseguito
