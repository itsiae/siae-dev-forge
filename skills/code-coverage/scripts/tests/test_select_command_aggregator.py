"""Test Task 01 — select_command + maven_aggregator integration.

Verifica che con un aggregator pom in subdir (es. pae-deposito-musica/pom.xml),
select_command emetta cov_cmd con -f <aggregator_pom> + path corretto.

TDD: scritti PRIMA dell'implementazione finale.
"""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
SCRIPT = SCRIPT_DIR / "select_command.py"
sys.path.insert(0, str(SCRIPT_DIR))


_POM_AGGREGATOR_WITH_JACOCO = """<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.siae</groupId>
  <artifactId>pae-deposito-musica</artifactId>
  <version>1.0.0</version>
  <packaging>pom</packaging>
  <modules>
    <module>siae-bollettinoMusica-dao</module>
    <module>siae-bollettinoMusica-dati</module>
  </modules>
  <build>
    <plugins>
      <plugin>
        <groupId>org.jacoco</groupId>
        <artifactId>jacoco-maven-plugin</artifactId>
        <version>0.8.12</version>
      </plugin>
    </plugins>
  </build>
</project>
"""


def run_select(repo_path: Path) -> dict:
    result = subprocess.run(
        ["python3", str(SCRIPT), str(repo_path)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def test_aggregator_pom_injects_f_flag(tmp_path):
    """Aggregator in subdir → cov_cmd contiene -f <aggregator_pom>."""
    repo = tmp_path / "repo"
    sub = repo / "pae-deposito-musica"
    sub.mkdir(parents=True)
    (sub / "pom.xml").write_text(_POM_AGGREGATOR_WITH_JACOCO)
    cov_dir = repo / ".code-coverage"
    cov_dir.mkdir()
    # stack.json con maven_aggregator già popolato (simula phase 1)
    (cov_dir / "stack.json").write_text(json.dumps({
        "manifest_root": "pae-deposito-musica",
        "maven_aggregator": {
            "manifest_root": "pae-deposito-musica",
            "aggregator_pom": "pae-deposito-musica/pom.xml",
            "modules": ["a", "b"],
            "selection_reason": "packaging-pom-with-modules",
        },
        "architecture_style": "java-microservice",
    }))
    (cov_dir / "env.json").write_text(json.dumps({"required_framework": "junit5"}))

    out = run_select(repo)
    assert out.get("error") is None, f"select_command emitted error: {out.get('error')}"
    assert "-f pae-deposito-musica/pom.xml" in out["cov_cmd"], (
        f"expected -f flag in cov_cmd, got: {out['cov_cmd']}"
    )
    assert out["manifest_root"] == "pae-deposito-musica"


def test_read_maven_aggregator_missing_stack_json(tmp_path):
    """_read_maven_aggregator: ritorna None se stack.json assente."""
    from select_command import _read_maven_aggregator
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _read_maven_aggregator(repo) is None


def test_read_maven_aggregator_returns_dict(tmp_path):
    """_read_maven_aggregator: estrae dict da stack.json valido."""
    from select_command import _read_maven_aggregator
    repo = tmp_path / "repo"
    (repo / ".code-coverage").mkdir(parents=True)
    (repo / ".code-coverage" / "stack.json").write_text(json.dumps({
        "maven_aggregator": {
            "manifest_root": "sub",
            "aggregator_pom": "sub/pom.xml",
            "modules": ["a"],
            "selection_reason": "packaging-pom-with-modules",
        }
    }))
    agg = _read_maven_aggregator(repo)
    assert agg is not None
    assert agg["aggregator_pom"] == "sub/pom.xml"


def test_read_maven_aggregator_missing_field(tmp_path):
    """_read_maven_aggregator: ritorna None se stack.json non ha maven_aggregator."""
    from select_command import _read_maven_aggregator
    repo = tmp_path / "repo"
    (repo / ".code-coverage").mkdir(parents=True)
    (repo / ".code-coverage" / "stack.json").write_text(json.dumps({"languages": []}))
    assert _read_maven_aggregator(repo) is None


def test_select_fields_java_aggregator_injects_f(tmp_path):
    """select_fields con aggregator: cmd contiene -f <aggregator_pom>."""
    from select_command import select_fields
    repo = tmp_path / "repo"
    sub = repo / "agg"
    sub.mkdir(parents=True)
    (sub / "pom.xml").write_text(_POM_AGGREGATOR_WITH_JACOCO)
    aggregator = {
        "manifest_root": "agg",
        "aggregator_pom": "agg/pom.xml",
        "modules": ["m1"],
        "selection_reason": "packaging-pom-with-modules",
    }
    stack_def = {
        "coverage_command_maven": "mvn test jacoco:report",
        "coverage_report_path_maven": "target/site/jacoco/jacoco.xml",
        "coverage_report_format": "jacoco",
    }
    cmd, path, fmt, err = select_fields("java", stack_def, repo, "macos", aggregator=aggregator)
    assert err is None, f"unexpected error: {err}"
    assert "-f agg/pom.xml" in cmd
    assert fmt == "jacoco"


def test_select_fields_java_no_aggregator_no_f(tmp_path):
    """select_fields senza aggregator: cmd non contiene -f."""
    from select_command import select_fields
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pom.xml").write_text(_POM_AGGREGATOR_WITH_JACOCO)
    stack_def = {
        "coverage_command_maven": "mvn test jacoco:report",
        "coverage_report_path_maven": "target/site/jacoco/jacoco.xml",
        "coverage_report_format": "jacoco",
    }
    cmd, path, fmt, err = select_fields("java", stack_def, repo, "macos", aggregator=None)
    assert err is None
    assert "-f " not in cmd


def test_select_fields_no_pom_no_gradle_error(tmp_path):
    """select_fields java senza pom né gradle ritorna error attionable."""
    from select_command import select_fields
    repo = tmp_path / "repo"
    repo.mkdir()
    cmd, path, fmt, err = select_fields("java", {}, repo, "macos", aggregator=None)
    assert err is not None
    assert "no pom.xml" in err


def test_select_fields_aggregator_missing_jacoco_emits_snippet(tmp_path):
    """Aggregator pom senza jacoco-maven-plugin → error con snippet."""
    from select_command import select_fields
    repo = tmp_path / "repo"
    sub = repo / "agg"
    sub.mkdir(parents=True)
    # Pom aggregator MA senza jacoco-maven-plugin
    (sub / "pom.xml").write_text("""<?xml version="1.0"?>
<project><groupId>x</groupId><artifactId>x</artifactId><version>1</version>
<packaging>pom</packaging><modules><module>a</module></modules>
</project>""")
    aggregator = {
        "manifest_root": "agg",
        "aggregator_pom": "agg/pom.xml",
        "modules": ["a"],
        "selection_reason": "packaging-pom-with-modules",
    }
    cmd, path, fmt, err = select_fields("java", {}, repo, "macos", aggregator=aggregator)
    assert err is not None
    assert "jacoco-maven-plugin" in err
    assert "agg/pom.xml" in err


def test_root_pom_no_f_flag(tmp_path):
    """Repo mono-pom in root: nessun -f flag iniettato (backward compat)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pom.xml").write_text(_POM_AGGREGATOR_WITH_JACOCO.replace(
        "<packaging>pom</packaging>", "<packaging>jar</packaging>"
    ).replace(
        '<modules>\n    <module>siae-bollettinoMusica-dao</module>\n    <module>siae-bollettinoMusica-dati</module>\n  </modules>',
        ''
    ))
    cov_dir = repo / ".code-coverage"
    cov_dir.mkdir()
    (cov_dir / "stack.json").write_text(json.dumps({
        "manifest_root": ".",
        "maven_aggregator": None,
        "architecture_style": "java-microservice",
    }))
    (cov_dir / "env.json").write_text(json.dumps({"required_framework": "junit5"}))

    out = run_select(repo)
    assert out.get("error") is None
    assert "-f " not in out["cov_cmd"], (
        f"expected no -f flag for mono-pom, got: {out['cov_cmd']}"
    )
