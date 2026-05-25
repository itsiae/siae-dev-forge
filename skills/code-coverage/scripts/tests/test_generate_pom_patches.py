"""Test Task 05 follow-up — generate_pom_patches.

Verifica la generazione del diff suggerito per pom restrittivi
(``surefire_config.restrictive=true``). Principle 1: skill NON applica patch,
solo emette diff.

TDD: scritti PRIMA dell'implementazione.
"""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

SCRIPT_PATH = SCRIPT_DIR / "generate_pom_patches.py"


def _pom_restrictive():
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


def _pom_default_includes():
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


def _pom_no_surefire():
    return """<?xml version="1.0"?>
<project>
  <groupId>x</groupId><artifactId>x</artifactId><version>1</version>
</project>
"""


def _env_json_restrictive():
    return {
        "surefire_config": {
            "includes": ["**/BollettinoMusicaServiceImplTest.java"],
            "excludes": [],
            "restrictive": True,
        }
    }


def _env_json_not_restrictive():
    return {
        "surefire_config": {
            "includes": ["**/*Test.java"],
            "excludes": [],
            "restrictive": False,
        }
    }


# ---------- API tests (generate_surefire_patch) ----------


def test_restrictive_pom_generates_diff(tmp_path):
    """Pom restrittivo + additional include => diff unified con la nuova riga."""
    from generate_pom_patches import generate_surefire_patch
    pom = tmp_path / "pom.xml"
    pom.write_text(_pom_restrictive())

    diff = generate_surefire_patch(pom, "**/model/*Test.java")

    assert diff, "Atteso diff non vuoto su pom restrittivo"
    assert "--- a/pom.xml" in diff
    assert "+++ b/pom.xml" in diff
    # La nuova riga è una add line (prefisso '+') con il pattern indicato
    assert "+" in diff
    assert "**/model/*Test.java" in diff
    # Verifica che sia una linea aggiunta, non solo testo
    added_lines = [ln for ln in diff.splitlines() if ln.startswith("+") and not ln.startswith("+++")]
    assert any("<include>**/model/*Test.java</include>" in ln for ln in added_lines), (
        f"Atteso '+        <include>**/model/*Test.java</include>' in diff, got:\n{diff}"
    )


def test_default_includes_no_patch_needed(tmp_path):
    """Pom con includes standard => diff vuoto (non restrictive)."""
    from generate_pom_patches import generate_surefire_patch
    pom = tmp_path / "pom.xml"
    pom.write_text(_pom_default_includes())

    diff = generate_surefire_patch(pom, "**/model/*Test.java")

    assert diff == "", f"Atteso diff vuoto su pom non-restrictive, got: {diff!r}"


def test_no_surefire_config_returns_empty(tmp_path):
    """Pom senza maven-surefire-plugin => diff vuoto."""
    from generate_pom_patches import generate_surefire_patch
    pom = tmp_path / "pom.xml"
    pom.write_text(_pom_no_surefire())

    diff = generate_surefire_patch(pom, "**/model/*Test.java")

    assert diff == ""


def test_missing_pom_returns_empty(tmp_path):
    """Pom inesistente => diff vuoto (no crash)."""
    from generate_pom_patches import generate_surefire_patch
    diff = generate_surefire_patch(tmp_path / "nonexistent.xml", "**/*Test.java")
    assert diff == ""


def test_diff_is_git_apply_compatible(tmp_path):
    """Verifica che il diff sia in formato unified valido (header + hunk)."""
    from generate_pom_patches import generate_surefire_patch
    pom = tmp_path / "pom.xml"
    pom.write_text(_pom_restrictive())

    diff = generate_surefire_patch(pom, "**/model/*Test.java")

    assert diff.startswith("--- a/pom.xml"), f"Header mancante: {diff[:80]!r}"
    lines = diff.splitlines()
    # Devono esserci header + almeno una hunk header @@ ... @@
    assert any(ln.startswith("@@") and ln.endswith("@@") or "@@" in ln for ln in lines), (
        f"Hunk header @@ ... @@ mancante in diff:\n{diff}"
    )


# ---------- CLI tests ----------


def _setup_repo_restrictive(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pom.xml").write_text(_pom_restrictive())
    cc_dir = repo / ".code-coverage"
    cc_dir.mkdir()
    (cc_dir / "env.json").write_text(json.dumps(_env_json_restrictive()))
    return repo


def test_cli_writes_proposed_diff_file(tmp_path):
    """E2E: CLI scrive .code-coverage/proposed-pom-patches.diff su repo restrictive."""
    repo = _setup_repo_restrictive(tmp_path)

    result = subprocess.run(
        ["python3", str(SCRIPT_PATH), str(repo)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"CLI fallita: {result.stderr}"

    diff_file = repo / ".code-coverage" / "proposed-pom-patches.diff"
    assert diff_file.is_file(), "File proposed-pom-patches.diff non creato"
    content = diff_file.read_text()
    assert "--- a/pom.xml" in content
    assert "+++ b/pom.xml" in content
    assert "**/*Test.java" in content  # default pattern (no --package)
    # Anche stdout deve contenere il diff
    assert "--- a/pom.xml" in result.stdout


def test_cli_no_op_when_not_restrictive(tmp_path):
    """CLI no-op se env.json.surefire_config.restrictive=False."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pom.xml").write_text(_pom_default_includes())
    cc_dir = repo / ".code-coverage"
    cc_dir.mkdir()
    (cc_dir / "env.json").write_text(json.dumps(_env_json_not_restrictive()))

    result = subprocess.run(
        ["python3", str(SCRIPT_PATH), str(repo)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert result.stdout == "", f"Atteso stdout vuoto, got: {result.stdout!r}"
    diff_file = repo / ".code-coverage" / "proposed-pom-patches.diff"
    assert not diff_file.exists(), "File diff non doveva essere creato"


def test_cli_cumulative_append(tmp_path):
    """Due chiamate con --package diversi => file contiene entrambi i diff."""
    repo = _setup_repo_restrictive(tmp_path)

    # Prima chiamata: --package model
    r1 = subprocess.run(
        ["python3", str(SCRIPT_PATH), str(repo), "--package", "model"],
        capture_output=True, text=True,
    )
    assert r1.returncode == 0, r1.stderr
    assert "**/model/*Test.java" in r1.stdout

    # Seconda chiamata: --package service
    r2 = subprocess.run(
        ["python3", str(SCRIPT_PATH), str(repo), "--package", "service"],
        capture_output=True, text=True,
    )
    assert r2.returncode == 0, r2.stderr
    assert "**/service/*Test.java" in r2.stdout

    diff_file = repo / ".code-coverage" / "proposed-pom-patches.diff"
    content = diff_file.read_text()
    assert "**/model/*Test.java" in content, "Primo diff perso (no append)"
    assert "**/service/*Test.java" in content, "Secondo diff mancante"
    # Almeno 2 occorrenze di header "--- a/pom.xml" => 2 diff accumulati
    assert content.count("--- a/pom.xml") >= 2, (
        f"Atteso >=2 diff accumulati, got {content.count('--- a/pom.xml')}:\n{content}"
    )


def test_cli_missing_env_json_is_noop(tmp_path):
    """Se .code-coverage/env.json manca => exit 0 silente."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pom.xml").write_text(_pom_restrictive())

    result = subprocess.run(
        ["python3", str(SCRIPT_PATH), str(repo)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert result.stdout == ""
