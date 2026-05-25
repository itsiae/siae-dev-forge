"""Test Task 07 — source-level-aware-template.

Phase 4 emette compat_profile derivato dal source level + Phase 5 (template-cache)
seleziona la variante template corretta (java8 vs modern).

TDD: scritti PRIMA dell'implementazione.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))


def _pom(source="17"):
    return f"""<?xml version="1.0"?>
<project>
  <groupId>x</groupId><artifactId>x</artifactId><version>1</version>
  <properties>
    <maven.compiler.source>{source}</maven.compiler.source>
  </properties>
</project>
"""


# ---------- compat_profile ----------

def test_compat_profile_java_legacy():
    """source 1.7 → legacy-java."""
    from validate_env import derive_compat_profile
    assert derive_compat_profile("1.7") == "legacy-java"
    assert derive_compat_profile("1.8") == "legacy-java"
    assert derive_compat_profile("8") == "legacy-java"


def test_compat_profile_modern_intermediate():
    """source 10-13 → modern-java-10."""
    from validate_env import derive_compat_profile
    assert derive_compat_profile("10") == "modern-java-10"
    assert derive_compat_profile("11") == "modern-java-10"
    assert derive_compat_profile("13") == "modern-java-10"


def test_compat_profile_modern_full():
    """source >= 14 → modern-java-14."""
    from validate_env import derive_compat_profile
    assert derive_compat_profile("14") == "modern-java-14"
    assert derive_compat_profile("17") == "modern-java-14"
    assert derive_compat_profile("21") == "modern-java-14"


def test_compat_profile_default_when_unknown():
    """source non rilevato → legacy-java (default safe)."""
    from validate_env import derive_compat_profile
    assert derive_compat_profile(None) == "legacy-java"
    assert derive_compat_profile("") == "legacy-java"


# ---------- env.json E2E ----------

def test_env_json_emits_compat_profile_legacy(tmp_path):
    """Pom source=1.7 → env.json.compat_profile=legacy-java."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pom.xml").write_text(_pom("1.7"))
    result = subprocess.run(
        ["python3", str(SCRIPT_DIR / "validate_env.py"), str(repo), "--framework", "junit5"],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    assert data.get("compat_profile") == "legacy-java"
    assert data.get("java_source_level") == "1.7"


def test_env_json_emits_compat_profile_modern(tmp_path):
    """Pom source=17 → env.json.compat_profile=modern-java-14."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pom.xml").write_text(_pom("17"))
    result = subprocess.run(
        ["python3", str(SCRIPT_DIR / "validate_env.py"), str(repo), "--framework", "junit5"],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    assert data.get("compat_profile") == "modern-java-14"


# ---------- template-cache.sh: selezione template via compat_profile ----------

def test_template_cache_selects_java8_legacy(tmp_path):
    """env.json compat_profile=legacy-java → template java8 variant selezionato."""
    skill_dir = SCRIPT_DIR.parent
    repo = tmp_path / "repo"
    cov = repo / ".code-coverage"
    cov.mkdir(parents=True)
    (cov / "env.json").write_text(json.dumps({
        "compat_profile": "legacy-java",
        "assertion_lib": "junit5_vanilla",
    }))
    # Invoca template-cache.sh get_template junit5
    result = subprocess.run(
        ["bash", "-c", f"source {skill_dir}/lib/template-cache.sh && get_template junit5 {repo}"],
        capture_output=True, text=True, check=True,
    )
    template_path = result.stdout.strip()
    content = Path(template_path).read_text()
    # No 'var ' (Java 10+ keyword) né text-blocks (""")
    assert " var " not in content, "java8 template must not use 'var' keyword"
    assert '"""' not in content, "java8 template must not use text blocks"


def test_template_cache_selects_modern_default(tmp_path):
    """No env.json (o compat_profile=modern) → template moderno con var."""
    skill_dir = SCRIPT_DIR.parent
    repo = tmp_path / "repo"
    cov = repo / ".code-coverage"
    cov.mkdir(parents=True)
    (cov / "env.json").write_text(json.dumps({
        "compat_profile": "modern-java-14",
        "assertion_lib": "assertj",
    }))
    result = subprocess.run(
        ["bash", "-c", f"source {skill_dir}/lib/template-cache.sh && get_template junit5 {repo}"],
        capture_output=True, text=True, check=True,
    )
    template_path = result.stdout.strip()
    content = Path(template_path).read_text()
    assert "var " in content, "modern template should use var keyword"
    assert "org.assertj.core.api" in content, "modern + assertj should use AssertJ imports"
