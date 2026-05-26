"""Test Task 04 — assertion-lib-probe.

Verifica detect_assertion_lib(): rileva assertj-core presente in pom o ritorna
junit5_vanilla. Persistere in env.json + permettere a phase 5 di scegliere il
template corretto (assertj vs vanilla) senza modificare pom.

TDD: scritti PRIMA dell'implementazione.
"""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))


def _pom_with_assertj():
    return """<?xml version="1.0"?>
<project>
  <groupId>x</groupId><artifactId>x</artifactId><version>1</version>
  <dependencies>
    <dependency>
      <groupId>org.junit.jupiter</groupId>
      <artifactId>junit-jupiter</artifactId>
      <version>5.10.0</version>
    </dependency>
    <dependency>
      <groupId>org.assertj</groupId>
      <artifactId>assertj-core</artifactId>
      <version>3.24.2</version>
    </dependency>
  </dependencies>
</project>
"""


def _pom_junit5_only():
    return """<?xml version="1.0"?>
<project>
  <groupId>x</groupId><artifactId>x</artifactId><version>1</version>
  <dependencies>
    <dependency>
      <groupId>org.junit.jupiter</groupId>
      <artifactId>junit-jupiter</artifactId>
      <version>5.10.0</version>
    </dependency>
  </dependencies>
</project>
"""


def _pom_mockito_no_assertj():
    return """<?xml version="1.0"?>
<project>
  <groupId>x</groupId><artifactId>x</artifactId><version>1</version>
  <dependencies>
    <dependency><groupId>org.junit.jupiter</groupId><artifactId>junit-jupiter</artifactId></dependency>
    <dependency><groupId>org.mockito</groupId><artifactId>mockito-junit-jupiter</artifactId></dependency>
  </dependencies>
</project>
"""


# ---------- detect_assertion_lib ----------

def test_assertj_present_returns_assertj(tmp_path):
    from validate_env import detect_assertion_lib
    pom = tmp_path / "pom.xml"
    pom.write_text(_pom_with_assertj())
    assert detect_assertion_lib([pom]) == "assertj"


def test_only_junit5_returns_vanilla(tmp_path):
    from validate_env import detect_assertion_lib
    pom = tmp_path / "pom.xml"
    pom.write_text(_pom_junit5_only())
    assert detect_assertion_lib([pom]) == "junit5_vanilla"


def test_mockito_without_assertj_returns_vanilla(tmp_path):
    from validate_env import detect_assertion_lib
    pom = tmp_path / "pom.xml"
    pom.write_text(_pom_mockito_no_assertj())
    assert detect_assertion_lib([pom]) == "junit5_vanilla"


def test_assertj_in_any_pom_wins(tmp_path):
    """Multi-module: AssertJ in un solo modulo → 'assertj' globalmente."""
    from validate_env import detect_assertion_lib
    pom1 = tmp_path / "mod1-pom.xml"
    pom2 = tmp_path / "mod2-pom.xml"
    pom1.write_text(_pom_junit5_only())
    pom2.write_text(_pom_with_assertj())
    assert detect_assertion_lib([pom1, pom2]) == "assertj"


def test_empty_list_returns_vanilla():
    from validate_env import detect_assertion_lib
    assert detect_assertion_lib([]) == "junit5_vanilla"


def test_nonexistent_pom_returns_vanilla(tmp_path):
    from validate_env import detect_assertion_lib
    # File non esiste — non deve crashare
    assert detect_assertion_lib([tmp_path / "missing-pom.xml"]) == "junit5_vanilla"


# ---------- env.json integration ----------

def test_env_json_contains_assertion_lib_for_java(tmp_path):
    """Eseguendo validate_env.py su repo Java con pom assertj, env.json contiene
    assertion_lib='assertj'."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pom.xml").write_text(_pom_with_assertj())

    result = subprocess.run(
        ["python3", str(SCRIPT_DIR / "validate_env.py"), str(repo), "--framework", "junit5"],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    assert data.get("assertion_lib") == "assertj"


def test_env_json_assertion_lib_vanilla_when_no_assertj(tmp_path):
    """Repo Java senza assertj-core → assertion_lib='junit5_vanilla'."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pom.xml").write_text(_pom_junit5_only())

    result = subprocess.run(
        ["python3", str(SCRIPT_DIR / "validate_env.py"), str(repo), "--framework", "junit5"],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    assert data.get("assertion_lib") == "junit5_vanilla"


def test_env_json_assertion_lib_null_for_non_java(tmp_path):
    """Repo non-Java → assertion_lib field può essere None / assente."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "package.json").write_text(json.dumps({"name": "x", "devDependencies": {"vitest": "*"}}))

    result = subprocess.run(
        ["python3", str(SCRIPT_DIR / "validate_env.py"), str(repo), "--framework", "vitest"],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    # Non Java: field può essere None (esplicito) o assente (compat)
    assert data.get("assertion_lib") in (None, "n/a")
