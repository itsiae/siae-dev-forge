"""Test Task 02 — maven-placeholder-inject.

Pom SIAE usano ${appVersion} iniettato dalla pipeline CI/CD ma non definito nel
pom. La skill deve scansionare i pom, rilevare placeholder non risolti, e
iniettare -D nel mvn cmd con default safe.

TDD: scritti PRIMA dell'implementazione.
"""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))


# ---------- helpers fixture ----------

def _pom_with_appversion():
    return """<?xml version="1.0"?>
<project>
  <groupId>x</groupId>
  <artifactId>x</artifactId>
  <version>${appVersion}</version>
</project>
"""


def _pom_appversion_in_properties():
    return """<?xml version="1.0"?>
<project>
  <groupId>x</groupId><artifactId>x</artifactId>
  <version>${appVersion}</version>
  <properties>
    <appVersion>2.0.0</appVersion>
  </properties>
</project>
"""


def _pom_builtin_project_version():
    return """<?xml version="1.0"?>
<project>
  <groupId>x</groupId><artifactId>x</artifactId>
  <version>1.0</version>
  <properties>
    <foo>${project.version}</foo>
  </properties>
</project>
"""


def _pom_revision_no_properties():
    return """<?xml version="1.0"?>
<project>
  <groupId>x</groupId><artifactId>x</artifactId>
  <version>${revision}</version>
</project>
"""


# ---------- scan_maven_placeholders ----------

def test_appversion_unresolved_returned(tmp_path):
    from validate_env import scan_maven_placeholders
    pom = tmp_path / "pom.xml"
    pom.write_text(_pom_with_appversion())
    result = scan_maven_placeholders([pom])
    assert "appVersion" in result
    assert result["appVersion"] == "1.0.0-SNAPSHOT"


def test_appversion_in_properties_skipped(tmp_path):
    """appVersion definito in <properties>: NON deve essere iniettato."""
    from validate_env import scan_maven_placeholders
    pom = tmp_path / "pom.xml"
    pom.write_text(_pom_appversion_in_properties())
    result = scan_maven_placeholders([pom])
    assert "appVersion" not in result


def test_builtin_project_version_skipped(tmp_path):
    """project.version è built-in Maven: NEVER injected."""
    from validate_env import scan_maven_placeholders
    pom = tmp_path / "pom.xml"
    pom.write_text(_pom_builtin_project_version())
    result = scan_maven_placeholders([pom])
    assert "project.version" not in result


def test_revision_builtin_unresolved_injected(tmp_path):
    """revision è CI-flow token (Maven 3.5+ multi-module): inject se non in properties."""
    from validate_env import scan_maven_placeholders
    pom = tmp_path / "pom.xml"
    pom.write_text(_pom_revision_no_properties())
    result = scan_maven_placeholders([pom])
    assert "revision" in result


def test_override_via_overrides_json(tmp_path):
    """overrides.json maven_placeholders ha precedenza su default."""
    from validate_env import scan_maven_placeholders, _read_overrides
    pom = tmp_path / "pom.xml"
    pom.write_text(_pom_with_appversion())
    ov_dir = tmp_path / ".code-coverage"
    ov_dir.mkdir()
    (ov_dir / "overrides.json").write_text(json.dumps({
        "maven_placeholders": {"appVersion": "2.0.0-RELEASE"}
    }))
    override_data = _read_overrides(tmp_path)
    result = scan_maven_placeholders([pom], overrides=override_data)
    assert result.get("appVersion") == "2.0.0-RELEASE"


# ---------- E2E env.json ----------

def test_select_command_injects_d_flags(tmp_path):
    """select_command propaga -D<token>=<value> nel mvn cmd quando placeholders presenti."""
    SELECT = SCRIPT_DIR / "select_command.py"
    repo = tmp_path / "repo"
    repo.mkdir()
    cov = repo / ".code-coverage"
    cov.mkdir()
    (cov / "stack.json").write_text(json.dumps({
        "manifest_root": ".", "maven_aggregator": None,
        "architecture_style": "java-microservice",
    }))
    (cov / "env.json").write_text(json.dumps({
        "required_framework": "junit5",
        "maven_placeholders": {"appVersion": "1.0.0-SNAPSHOT", "revision": "X"},
    }))
    (repo / "pom.xml").write_text("""<?xml version="1.0"?>
<project>
  <groupId>g</groupId><artifactId>a</artifactId><version>${appVersion}</version>
  <build><plugins><plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <version>0.8.12</version>
  </plugin></plugins></build>
</project>""")

    result = subprocess.run(
        ["python3", str(SELECT), str(repo)],
        capture_output=True, text=True, check=True,
    )
    out = json.loads(result.stdout)
    assert out.get("error") is None, f"unexpected error: {out.get('error')}"
    assert "-DappVersion=1.0.0-SNAPSHOT" in out["cov_cmd"]
    assert "-Drevision=X" in out["cov_cmd"]


def test_env_json_contains_maven_placeholders(tmp_path):
    """validate_env emette maven_placeholders in env.json per Java."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pom.xml").write_text(_pom_with_appversion())

    result = subprocess.run(
        ["python3", str(SCRIPT_DIR / "validate_env.py"), str(repo), "--framework", "junit5"],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    assert data.get("maven_placeholders") == {"appVersion": "1.0.0-SNAPSHOT"}
