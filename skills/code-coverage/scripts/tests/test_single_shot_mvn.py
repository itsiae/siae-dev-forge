"""Test Task 09 — single-shot-mvn.

Phase 6 default strategy: single-shot (1 mvn run finale) invece di verify-each
(N mvn run intermedi). Spring Boot detected → forza single-shot. Surefire
parser identifica i fail per Phase 7 skinny repair.

TDD: scritti PRIMA dell'implementazione.
"""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))


def _spring_boot_pom():
    return """<?xml version="1.0"?>
<project>
  <groupId>x</groupId><artifactId>x</artifactId><version>1</version>
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>2.5.7</version>
  </parent>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter</artifactId>
    </dependency>
  </dependencies>
</project>
"""


def _plain_pom():
    return """<?xml version="1.0"?>
<project>
  <groupId>x</groupId><artifactId>x</artifactId><version>1</version>
</project>
"""


# ---------- mvn strategy detection ----------

def test_spring_boot_pom_emits_single_shot(tmp_path):
    """Pom Spring Boot → env.json.mvn_strategy=single-shot."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pom.xml").write_text(_spring_boot_pom())
    result = subprocess.run(
        ["python3", str(SCRIPT_DIR / "validate_env.py"), str(repo), "--framework", "junit5"],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    assert data.get("mvn_strategy") == "single-shot"
    assert data.get("is_spring_boot") is True


def test_non_spring_pom_default_single_shot(tmp_path):
    """Pom plain (no Spring Boot) → default single-shot (più veloce, raramente peggio)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pom.xml").write_text(_plain_pom())
    result = subprocess.run(
        ["python3", str(SCRIPT_DIR / "validate_env.py"), str(repo), "--framework", "junit5"],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    assert data.get("mvn_strategy") == "single-shot"
    assert data.get("is_spring_boot") is False


def test_verify_each_flag_overrides_strategy(tmp_path):
    """CLI flag --verify-each forza strategy=verify-each (opt-in legacy)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pom.xml").write_text(_spring_boot_pom())
    result = subprocess.run(
        ["python3", str(SCRIPT_DIR / "validate_env.py"), str(repo),
         "--framework", "junit5", "--verify-each"],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    assert data.get("mvn_strategy") == "verify-each"


# ---------- surefire-parser ----------

def test_surefire_parser_finds_failures(tmp_path):
    """parse_surefire_failures estrae class#method da TEST-*.xml con failure/error."""
    from surefire_parser import parse_surefire_failures
    reports = tmp_path / "surefire-reports"
    reports.mkdir()
    (reports / "TEST-it.siae.FooTest.xml").write_text("""<?xml version="1.0"?>
<testsuite name="it.siae.FooTest" tests="2" failures="1" errors="0">
  <testcase name="testHappy" classname="it.siae.FooTest"/>
  <testcase name="testFail" classname="it.siae.FooTest">
    <failure type="AssertionError">expected: A but was: B</failure>
  </testcase>
</testsuite>
""")
    failures = parse_surefire_failures(reports)
    assert "it.siae.FooTest#testFail" in failures
    assert "it.siae.FooTest#testHappy" not in failures


def test_surefire_parser_handles_errors(tmp_path):
    """Test in <error> (exception) classificati come failure."""
    from surefire_parser import parse_surefire_failures
    reports = tmp_path / "surefire-reports"
    reports.mkdir()
    (reports / "TEST-it.siae.BarTest.xml").write_text("""<?xml version="1.0"?>
<testsuite name="it.siae.BarTest" tests="1" failures="0" errors="1">
  <testcase name="testNPE" classname="it.siae.BarTest">
    <error type="NullPointerException">at line 42</error>
  </testcase>
</testsuite>
""")
    failures = parse_surefire_failures(reports)
    assert "it.siae.BarTest#testNPE" in failures


def test_surefire_parser_empty_dir(tmp_path):
    """No TEST-*.xml → lista vuota (no crash)."""
    from surefire_parser import parse_surefire_failures
    reports = tmp_path / "surefire-reports"
    reports.mkdir()
    assert parse_surefire_failures(reports) == []


def test_surefire_parser_missing_dir(tmp_path):
    """Dir non esiste → lista vuota."""
    from surefire_parser import parse_surefire_failures
    assert parse_surefire_failures(tmp_path / "nonexistent") == []
