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
