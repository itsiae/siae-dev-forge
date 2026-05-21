"""Test per B4 — detect_monorepo Maven reactor + Gradle multi-module.

TDD: scritti PRIMA dell'implementazione.
"""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "detect_stack.py"
sys.path.insert(0, str(SCRIPT.parent))


def run_detect(repo_path: Path) -> dict:
    result = subprocess.run(
        ["python3", str(SCRIPT), str(repo_path)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


# ============================================================================
# detect_monorepo_workspaces — Maven
# ============================================================================

def test_maven_reactor_modules_extracted(tmp_path):
    """pom.xml con <modules><module>a</module><module>b</module></modules>
    → monorepo_workspaces == ["a", "b"]."""
    from detect_stack import detect_monorepo_workspaces
    repo = tmp_path / "maven-multi"
    repo.mkdir()
    pom = """<?xml version="1.0"?>
<project>
  <groupId>com.example</groupId>
  <artifactId>parent</artifactId>
  <packaging>pom</packaging>
  <modules>
    <module>a</module>
    <module>b</module>
  </modules>
</project>
"""
    (repo / "pom.xml").write_text(pom)
    ws = detect_monorepo_workspaces(repo)
    assert ws == ["a", "b"], f"expected ['a', 'b'], got {ws}"


def test_maven_no_modules_returns_empty(tmp_path):
    """pom.xml senza <modules> → []."""
    from detect_stack import detect_monorepo_workspaces
    repo = tmp_path / "maven-single"
    repo.mkdir()
    pom = """<?xml version="1.0"?>
<project>
  <groupId>com.example</groupId>
  <artifactId>single</artifactId>
</project>
"""
    (repo / "pom.xml").write_text(pom)
    assert detect_monorepo_workspaces(repo) == []


def test_maven_modules_dedup_and_strip(tmp_path):
    """Module entries con whitespace → trimmed; duplicate skipped."""
    from detect_stack import detect_monorepo_workspaces
    repo = tmp_path / "maven-dup"
    repo.mkdir()
    pom = """<?xml version="1.0"?>
<project>
  <modules>
    <module>  a  </module>
    <module>b</module>
    <module>a</module>
  </modules>
</project>
"""
    (repo / "pom.xml").write_text(pom)
    ws = detect_monorepo_workspaces(repo)
    assert ws == ["a", "b"], f"expected dedup+strip ['a', 'b'], got {ws}"


# ============================================================================
# detect_monorepo_workspaces — Gradle Groovy
# ============================================================================

def test_gradle_groovy_include_single_quote(tmp_path):
    """settings.gradle: include 'a', 'b:c' → ['a', 'b/c']."""
    from detect_stack import detect_monorepo_workspaces
    repo = tmp_path / "gradle-groovy"
    repo.mkdir()
    (repo / "settings.gradle").write_text(
        "rootProject.name = 'demo'\ninclude 'a', 'b:c'\n"
    )
    ws = detect_monorepo_workspaces(repo)
    assert ws == ["a", "b/c"], f"expected ['a', 'b/c'], got {ws}"


def test_gradle_groovy_leading_colon_stripped(tmp_path):
    """include ':services:api' → 'services/api' (leading ':' stripped)."""
    from detect_stack import detect_monorepo_workspaces
    repo = tmp_path / "gradle-colon"
    repo.mkdir()
    (repo / "settings.gradle").write_text("include ':services:api'\n")
    ws = detect_monorepo_workspaces(repo)
    assert ws == ["services/api"], f"got {ws}"


# ============================================================================
# detect_monorepo_workspaces — Gradle Kotlin DSL
# ============================================================================

def test_gradle_kotlin_include(tmp_path):
    """settings.gradle.kts: include('a', 'b:c') → ['a', 'b/c']."""
    from detect_stack import detect_monorepo_workspaces
    repo = tmp_path / "gradle-kts"
    repo.mkdir()
    (repo / "settings.gradle.kts").write_text(
        'rootProject.name = "demo"\ninclude("a", "b:c")\n'
    )
    ws = detect_monorepo_workspaces(repo)
    # Kotlin DSL puo' avere multiple include() invocations
    assert "a" in ws and "b/c" in ws, f"expected a + b/c in {ws}"


# ============================================================================
# detect_monorepo (boolean) — integration
# ============================================================================

def test_detect_monorepo_true_on_maven_reactor(tmp_path):
    from detect_stack import detect_monorepo
    repo = tmp_path / "maven-reactor"
    repo.mkdir()
    (repo / "pom.xml").write_text(
        "<project><modules><module>a</module><module>b</module></modules></project>"
    )
    assert detect_monorepo(repo) is True


def test_detect_monorepo_true_on_gradle_multimodule(tmp_path):
    from detect_stack import detect_monorepo
    repo = tmp_path / "gradle-multi"
    repo.mkdir()
    (repo / "settings.gradle").write_text("include 'a', 'b'\n")
    assert detect_monorepo(repo) is True


def test_detect_monorepo_false_on_single_pom(tmp_path):
    from detect_stack import detect_monorepo
    repo = tmp_path / "maven-single"
    repo.mkdir()
    (repo / "pom.xml").write_text("<project></project>")
    assert detect_monorepo(repo) is False


# ============================================================================
# Output JSON contract — monorepo_workspaces sempre presente
# ============================================================================

def test_output_includes_monorepo_workspaces_field(tmp_path):
    """Detect stack output sempre include monorepo_workspaces (anche se vuoto)."""
    repo = tmp_path / "flat"
    repo.mkdir()
    (repo / "package.json").write_text(json.dumps({"name": "flat"}))
    out = run_detect(repo)
    assert "monorepo_workspaces" in out
    assert isinstance(out["monorepo_workspaces"], list)


def test_output_monorepo_workspaces_populated_for_maven_reactor(tmp_path):
    repo = tmp_path / "maven-reactor"
    repo.mkdir()
    (repo / "pom.xml").write_text(
        "<project><modules><module>core</module><module>web</module></modules></project>"
    )
    out = run_detect(repo)
    assert out["monorepo_workspaces"] == ["core", "web"]
    assert out["monorepo"] is True
