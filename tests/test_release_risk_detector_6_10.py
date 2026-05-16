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


def test_c6_tool_unavailable_on_subprocess_fail():
    """Quando _count_release_tags fallisce, criterion 6 propaga TOOL_UNAVAILABLE invece di YES."""
    r = criterion_6_first_release(0, tag_lookup_status="UNAVAILABLE")
    assert r.status == "TOOL_UNAVAILABLE"
    assert r.weight == 2
    assert "git_tag_lookup_failed" in r.evidence


def test_c6_no_with_explicit_ok_status():
    """Tag count positivo + status OK → NO esplicito."""
    r = criterion_6_first_release(5, tag_lookup_status="OK")
    assert r.status == "NO"
    assert "git_tag_count=5" in r.evidence
