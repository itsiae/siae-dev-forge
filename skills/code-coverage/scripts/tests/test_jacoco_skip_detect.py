"""Test Task 06 — jacoco-skip-detect.

Identifica moduli con <jacoco.skip>true</jacoco.skip> per filtrarli dal bundle
coverage in Phase 8 (no falsi 0% LINE su moduli by-design senza tests).

TDD: scritti PRIMA dell'implementazione.
"""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))


def _pom_jacoco_skip(skip=True):
    return f"""<?xml version="1.0"?>
<project>
  <groupId>x</groupId><artifactId>x</artifactId><version>1</version>
  <properties>
    <jacoco.skip>{str(skip).lower()}</jacoco.skip>
  </properties>
</project>
"""


def _pom_no_skip():
    return """<?xml version="1.0"?>
<project>
  <groupId>x</groupId><artifactId>x</artifactId><version>1</version>
</project>
"""


def test_detect_skip_returns_module_name(tmp_path):
    """Modulo con jacoco.skip=true → entry in skipped_modules."""
    from validate_env import detect_jacoco_skipped_modules
    base = tmp_path
    sub = base / "skipped-mod"
    sub.mkdir()
    (sub / "pom.xml").write_text(_pom_jacoco_skip(True))
    result = detect_jacoco_skipped_modules(base, ["skipped-mod"])
    assert result == ["skipped-mod"]


def test_detect_skip_false_not_returned(tmp_path):
    """Modulo con jacoco.skip=false → NON in skipped_modules."""
    from validate_env import detect_jacoco_skipped_modules
    base = tmp_path
    sub = base / "ready-mod"
    sub.mkdir()
    (sub / "pom.xml").write_text(_pom_jacoco_skip(False))
    assert detect_jacoco_skipped_modules(base, ["ready-mod"]) == []


def test_detect_skip_missing_returns_empty(tmp_path):
    """Modulo senza property jacoco.skip → NON in skipped_modules."""
    from validate_env import detect_jacoco_skipped_modules
    base = tmp_path
    sub = base / "normal-mod"
    sub.mkdir()
    (sub / "pom.xml").write_text(_pom_no_skip())
    assert detect_jacoco_skipped_modules(base, ["normal-mod"]) == []


def test_detect_multi_module_mixed(tmp_path):
    """Multi-module: solo i moduli con skip=true ritornano."""
    from validate_env import detect_jacoco_skipped_modules
    base = tmp_path
    for name, content in [
        ("svc1", _pom_no_skip()),
        ("svc2", _pom_jacoco_skip(True)),
        ("svc3", _pom_jacoco_skip(False)),
        ("svc4", _pom_jacoco_skip(True)),
    ]:
        d = base / name
        d.mkdir()
        (d / "pom.xml").write_text(content)
    result = detect_jacoco_skipped_modules(base, ["svc1", "svc2", "svc3", "svc4"])
    assert sorted(result) == ["svc2", "svc4"]


def test_detect_missing_pom_handled(tmp_path):
    """Modulo dichiarato ma pom mancante: skip non rilevato (return empty), no crash."""
    from validate_env import detect_jacoco_skipped_modules
    result = detect_jacoco_skipped_modules(tmp_path, ["nonexistent"])
    assert result == []


def test_env_json_emits_skipped_modules_field(tmp_path):
    """validate_env.py emette skipped_modules in env.json quando aggregator + moduli rilevati."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pom.xml").write_text("""<?xml version="1.0"?>
<project>
  <groupId>x</groupId><artifactId>agg</artifactId><version>1</version>
  <packaging>pom</packaging>
  <modules><module>real-mod</module><module>skipped-mod</module></modules>
  <dependencies>
    <dependency><groupId>org.junit.jupiter</groupId><artifactId>junit-jupiter</artifactId></dependency>
  </dependencies>
</project>
""")
    (repo / "real-mod").mkdir()
    (repo / "real-mod" / "pom.xml").write_text(_pom_no_skip())
    (repo / "skipped-mod").mkdir()
    (repo / "skipped-mod" / "pom.xml").write_text(_pom_jacoco_skip(True))

    # Simulo stack.json con aggregator (normalmente da detect_stack.py)
    cov = repo / ".code-coverage"
    cov.mkdir()
    (cov / "stack.json").write_text(json.dumps({
        "manifest_root": ".",
        "maven_aggregator": {
            "manifest_root": ".",
            "aggregator_pom": "pom.xml",
            "modules": ["real-mod", "skipped-mod"],
            "selection_reason": "packaging-pom-with-modules",
        },
    }))

    result = subprocess.run(
        ["python3", str(SCRIPT_DIR / "validate_env.py"), str(repo), "--framework", "junit5"],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    assert data.get("skipped_modules") == ["skipped-mod"]
