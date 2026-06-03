"""Test Task 05 — surefire-includes-detect.

Rileva configurazione restrittiva di maven-surefire-plugin <includes> che
impedirebbe l'esecuzione dei nuovi test generati. Persistere in env.json;
Phase 5 deve allineare naming o generare proposed-pom-patches.diff.

TDD: scritti PRIMA dell'implementazione.
"""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))


def _pom_with_restrictive_surefire():
    return """<?xml version="1.0"?>
<project>
  <groupId>x</groupId><artifactId>x</artifactId><version>1</version>
  <build>
    <plugins>
      <plugin>
        <artifactId>maven-surefire-plugin</artifactId>
        <configuration>
          <includes>
            <include>**/BollettinoMusicaServiceImplTest.java</include>
          </includes>
        </configuration>
      </plugin>
    </plugins>
  </build>
</project>
"""


def _pom_with_default_includes():
    return """<?xml version="1.0"?>
<project>
  <groupId>x</groupId><artifactId>x</artifactId><version>1</version>
  <build>
    <plugins>
      <plugin>
        <artifactId>maven-surefire-plugin</artifactId>
        <configuration>
          <includes>
            <include>**/*Test.java</include>
          </includes>
        </configuration>
      </plugin>
    </plugins>
  </build>
</project>
"""


def _pom_no_surefire_config():
    return """<?xml version="1.0"?>
<project>
  <groupId>x</groupId><artifactId>x</artifactId><version>1</version>
</project>
"""


def _pom_with_excludes():
    return """<?xml version="1.0"?>
<project>
  <groupId>x</groupId><artifactId>x</artifactId><version>1</version>
  <build><plugins>
    <plugin>
      <artifactId>maven-surefire-plugin</artifactId>
      <configuration>
        <excludes>
          <exclude>**/IT*.java</exclude>
        </excludes>
      </configuration>
    </plugin>
  </plugins></build>
</project>
"""


def test_restrictive_includes_detected(tmp_path):
    from validate_env import detect_surefire_config
    pom = tmp_path / "pom.xml"
    pom.write_text(_pom_with_restrictive_surefire())
    cfg = detect_surefire_config(pom)
    assert cfg["restrictive"] is True
    assert "**/BollettinoMusicaServiceImplTest.java" in cfg["includes"]


def test_default_includes_not_restrictive(tmp_path):
    """Wildcard standard **/*Test.java NON è restrittivo."""
    from validate_env import detect_surefire_config
    pom = tmp_path / "pom.xml"
    pom.write_text(_pom_with_default_includes())
    cfg = detect_surefire_config(pom)
    assert cfg["restrictive"] is False
    assert cfg["includes"] == ["**/*Test.java"]


def test_no_surefire_config_returns_empty(tmp_path):
    """Pom senza maven-surefire-plugin config: cfg defaults, restrictive=False."""
    from validate_env import detect_surefire_config
    pom = tmp_path / "pom.xml"
    pom.write_text(_pom_no_surefire_config())
    cfg = detect_surefire_config(pom)
    assert cfg["includes"] == []
    assert cfg["excludes"] == []
    assert cfg["restrictive"] is False


def test_excludes_only_extracted(tmp_path):
    """Pom con solo excludes: cfg con lista excludes + restrictive=False."""
    from validate_env import detect_surefire_config
    pom = tmp_path / "pom.xml"
    pom.write_text(_pom_with_excludes())
    cfg = detect_surefire_config(pom)
    assert "**/IT*.java" in cfg["excludes"]
    assert cfg["includes"] == []
    assert cfg["restrictive"] is False


def test_env_json_emits_surefire_config(tmp_path):
    """validate_env.py emette surefire_config field in env.json per Java."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pom.xml").write_text(_pom_with_restrictive_surefire())
    result = subprocess.run(
        ["python3", str(SCRIPT_DIR / "validate_env.py"), str(repo), "--framework", "junit5"],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    assert "surefire_config" in data
    # restrictive=True per aggregator pom (collezionato come root pom)
    cfg = data["surefire_config"]
    assert cfg.get("restrictive") is True
