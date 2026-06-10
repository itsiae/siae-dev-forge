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


def test_c1_pom_xml_alone_is_not_db_change():
    """pom.xml e' competenza del criterio 4 (ext deps), non DB change (+3)."""
    r = criterion_1_db_change(["pom.xml"], "+ <dependency>flyway-core</dependency>")
    assert r.status == "NO"


def test_c1_logback_xml_is_not_db_change():
    r = criterion_1_db_change(["src/main/resources/logback.xml"], "+ <root level=\"INFO\">")
    assert r.status == "NO"


def test_c1_db_changelog_xml_path_still_yes():
    """XML liquibase sotto path db/ resta rilevato."""
    r = criterion_1_db_change(
        ["src/main/resources/db/changelog/db.changelog-master.xml"], "")
    assert r.status == "YES"


def test_c1_liquibase_xml_content_is_db_change():
    """Changelog liquibase con nome non standard: rilevato dal contenuto XML."""
    r = criterion_1_db_change(
        ["src/main/resources/updates.xml"],
        '+    <createTable tableName="licenze">')
    assert r.status == "YES"
    assert any("ddl_keyword" in e for e in r.evidence)


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
