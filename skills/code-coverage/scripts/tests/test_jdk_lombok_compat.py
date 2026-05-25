"""Test Task 03 — jdk-lombok-compat-check.

Detecta JDK runtime + Lombok version + Java source level. Confronta contro
matrice compat → emette WARN/HARD-WARN con suggested fix.

TDD: scritti PRIMA dell'implementazione.
"""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))


def _pom_lombok(version="1.18.16"):
    return f"""<?xml version="1.0"?>
<project>
  <groupId>x</groupId><artifactId>x</artifactId><version>1</version>
  <properties>
    <maven.compiler.source>1.7</maven.compiler.source>
    <lombok.version>{version}</lombok.version>
  </properties>
  <dependencies>
    <dependency>
      <groupId>org.projectlombok</groupId>
      <artifactId>lombok</artifactId>
      <version>${{lombok.version}}</version>
    </dependency>
  </dependencies>
</project>
"""


def _pom_no_lombok():
    return """<?xml version="1.0"?>
<project>
  <groupId>x</groupId><artifactId>x</artifactId><version>1</version>
  <properties>
    <maven.compiler.source>17</maven.compiler.source>
  </properties>
</project>
"""


# ---------- Detection units ----------

def test_extract_lombok_version_from_property(tmp_path):
    from validate_env import extract_lombok_version
    pom = tmp_path / "pom.xml"
    pom.write_text(_pom_lombok("1.18.16"))
    assert extract_lombok_version(pom) == "1.18.16"


def test_extract_lombok_version_absent(tmp_path):
    from validate_env import extract_lombok_version
    pom = tmp_path / "pom.xml"
    pom.write_text(_pom_no_lombok())
    assert extract_lombok_version(pom) is None


def test_extract_source_level(tmp_path):
    from validate_env import extract_source_level
    pom = tmp_path / "pom.xml"
    pom.write_text(_pom_lombok())
    assert extract_source_level(pom) == "1.7"


def test_extract_source_level_modern(tmp_path):
    from validate_env import extract_source_level
    pom = tmp_path / "pom.xml"
    pom.write_text(_pom_no_lombok())
    assert extract_source_level(pom) == "17"


# ---------- Compat matrix ----------

def test_lombok_old_jdk_new_emits_hard_warn():
    """Lombok 1.18.16 + JDK 25 → HARD-WARN (TypeTag UNKNOWN)."""
    from validate_env import evaluate_jdk_lombok_compat
    result = evaluate_jdk_lombok_compat(jdk_major=25, lombok_version="1.18.16", source_level="1.7")
    assert result["severity"] == "HARD-WARN"
    assert "lombok" in result["reason"].lower() or "type" in result["reason"].lower()


def test_lombok_recent_jdk_17_passes():
    """Lombok 1.18.30 + JDK 17 + source 17 → OK."""
    from validate_env import evaluate_jdk_lombok_compat
    result = evaluate_jdk_lombok_compat(jdk_major=17, lombok_version="1.18.30", source_level="17")
    assert result["severity"] == "OK"


def test_source_1_7_jdk_25_emits_warn():
    """Source 1.7 + JDK 25 (senza Lombok) → WARN soft (plugin issues possible)."""
    from validate_env import evaluate_jdk_lombok_compat
    result = evaluate_jdk_lombok_compat(jdk_major=25, lombok_version=None, source_level="1.7")
    assert result["severity"] in ("WARN", "HARD-WARN")


def test_no_lombok_modern_source_ok():
    """No Lombok, source 17, JDK 17 → OK."""
    from validate_env import evaluate_jdk_lombok_compat
    result = evaluate_jdk_lombok_compat(jdk_major=17, lombok_version=None, source_level="17")
    assert result["severity"] == "OK"


# ---------- env.json E2E ----------

def test_env_json_emits_jdk_compat_field(tmp_path):
    """validate_env emette jdk_compat field in env.json per Java."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pom.xml").write_text(_pom_lombok("1.18.16"))
    result = subprocess.run(
        ["python3", str(SCRIPT_DIR / "validate_env.py"), str(repo), "--framework", "junit5"],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    assert "jdk_compat" in data
    assert "severity" in data["jdk_compat"]
    # i campi rilevati devono essere presenti
    assert data["jdk_compat"]["lombok_version"] == "1.18.16"
    assert data["jdk_compat"]["source_level"] == "1.7"
