"""Test Task 01 — detect-aggregator-pom.

Verifica detect_maven_aggregator(): identifica pom aggregator in subdir, priorità
selection (packaging-pom > fallback jacoco+junit5), no false positive su mono-pom.

TDD: scritti PRIMA dell'implementazione.
"""
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))


# ---------- helpers fixture ----------

def _aggregator_pom(group="com.siae", artifact="aggregator", modules=("a", "b")):
    mod_xml = "\n".join(f"    <module>{m}</module>" for m in modules)
    return f"""<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>{group}</groupId>
  <artifactId>{artifact}</artifactId>
  <version>1.0.0</version>
  <packaging>pom</packaging>
  <modules>
{mod_xml}
  </modules>
</project>
"""


def _jacoco_junit5_pom(group="com.siae", artifact="leaf"):
    return f"""<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>{group}</groupId>
  <artifactId>{artifact}</artifactId>
  <version>1.0.0</version>
  <dependencies>
    <dependency>
      <groupId>org.junit.jupiter</groupId>
      <artifactId>junit-jupiter-api</artifactId>
      <version>5.10.0</version>
    </dependency>
  </dependencies>
  <build>
    <plugins>
      <plugin>
        <groupId>org.jacoco</groupId>
        <artifactId>jacoco-maven-plugin</artifactId>
      </plugin>
    </plugins>
  </build>
</project>
"""


def _plain_pom(group="com.siae", artifact="single"):
    return f"""<?xml version="1.0"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>{group}</groupId>
  <artifactId>{artifact}</artifactId>
  <version>1.0.0</version>
</project>
"""


# ---------- AC 1: aggregator pom in subdir → detection corretta ----------

def test_aggregator_pom_in_subdir(tmp_path):
    """Layout pae-deposito-musica-be: aggregator pom in subdir, no pom in root."""
    from detect_stack import detect_maven_aggregator
    repo = tmp_path / "repo"
    sub = repo / "pae-deposito-musica"
    sub.mkdir(parents=True)
    (sub / "pom.xml").write_text(_aggregator_pom(modules=("mod-a", "mod-b", "mod-c")))

    result = detect_maven_aggregator(repo)
    assert result is not None, "aggregator pom not detected"
    assert result["manifest_root"] == "pae-deposito-musica"
    assert result["aggregator_pom"] == "pae-deposito-musica/pom.xml"
    assert sorted(result["modules"]) == ["mod-a", "mod-b", "mod-c"]
    assert result["selection_reason"] == "packaging-pom-with-modules"


# ---------- AC 3: single-pom root → no aggregator (manifest_root resta ".") ----------

def test_no_aggregator_returns_none_on_single_pom(tmp_path):
    """Pom root senza <packaging>pom</packaging> e senza <modules>: no aggregator."""
    from detect_stack import detect_maven_aggregator
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pom.xml").write_text(_plain_pom())
    result = detect_maven_aggregator(repo)
    assert result is None, f"expected None, got {result}"


# ---------- Priority: packaging-pom batte fallback ----------

def test_packaging_pom_priority_over_fallback(tmp_path):
    """2 pom: uno aggregator vero (packaging=pom + modules), uno fallback (jacoco+junit5).
    L'aggregator vero vince a priorità."""
    from detect_stack import detect_maven_aggregator
    repo = tmp_path / "repo"
    real_agg = repo / "real-aggregator"
    fallback = repo / "fallback-leaf"
    real_agg.mkdir(parents=True)
    fallback.mkdir(parents=True)
    (real_agg / "pom.xml").write_text(_aggregator_pom(modules=("x",)))
    (fallback / "pom.xml").write_text(_jacoco_junit5_pom())

    result = detect_maven_aggregator(repo)
    assert result is not None
    assert result["manifest_root"] == "real-aggregator"
    assert result["selection_reason"] == "packaging-pom-with-modules"


# ---------- Fallback: solo jacoco+junit5 pom presente ----------

def test_jacoco_junit5_fallback(tmp_path):
    """Nessun packaging=pom, ma un pom con jacoco+junit5 → fallback selection."""
    from detect_stack import detect_maven_aggregator
    repo = tmp_path / "repo"
    leaf = repo / "module-leaf"
    leaf.mkdir(parents=True)
    (leaf / "pom.xml").write_text(_jacoco_junit5_pom())

    result = detect_maven_aggregator(repo)
    assert result is not None
    assert result["manifest_root"] == "module-leaf"
    assert result["selection_reason"] == "jacoco-junit5-fallback"
    assert result["modules"] == []


# ---------- AC 4: no pom dentro maxdepth → None ----------

def test_no_pom_at_all_returns_none(tmp_path):
    """Repo senza pom: ritorna None."""
    from detect_stack import detect_maven_aggregator
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# Empty")
    assert detect_maven_aggregator(repo) is None


# ---------- AC 4: override via overrides.json ----------

def test_overrides_json_takes_precedence(tmp_path):
    """`.code-coverage/overrides.json` { aggregator_pom: ... } batte la detection."""
    from detect_stack import detect_maven_aggregator
    repo = tmp_path / "repo"
    auto_sub = repo / "auto-detected"
    custom_sub = repo / "custom-dir"
    auto_sub.mkdir(parents=True)
    custom_sub.mkdir(parents=True)
    (auto_sub / "pom.xml").write_text(_aggregator_pom(modules=("auto",)))
    (custom_sub / "pom.xml").write_text(_aggregator_pom(modules=("user",)))
    cov = repo / ".code-coverage"
    cov.mkdir()
    import json as _json
    (cov / "overrides.json").write_text(_json.dumps({
        "manifest_root": "custom-dir",
        "aggregator_pom": "custom-dir/pom.xml",
    }))
    result = detect_maven_aggregator(repo)
    assert result is not None
    assert result["manifest_root"] == "custom-dir"
    assert result["selection_reason"] == "user-override"


# ---------- AC 2: discovery-summary.json conserva manifest_root + reason ----------

def test_main_emits_maven_aggregator_field(tmp_path):
    """Eseguendo detect_stack.py su repo SIAE-like, l'output JSON ha campo
    maven_aggregator non-null + manifest_root override."""
    import json, subprocess
    repo = tmp_path / "repo"
    sub = repo / "pae-deposito-musica"
    sub.mkdir(parents=True)
    (sub / "pom.xml").write_text(_aggregator_pom(modules=("a", "b")))
    # Aggiungo un file java per registrare il linguaggio (altrimenti _walk
    # potrebbe non emettere "java" se nessun .java è nei moduli)
    (sub / "a").mkdir()
    (sub / "a" / "src").mkdir()
    (sub / "a" / "src" / "Dummy.java").write_text("class Dummy {}")

    result = subprocess.run(
        ["python3", str(SCRIPT_DIR / "detect_stack.py"), str(repo)],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    assert "maven_aggregator" in data, "stack.json must contain maven_aggregator field"
    assert data["maven_aggregator"] is not None
    assert data["maven_aggregator"]["manifest_root"] == "pae-deposito-musica"
    assert data["maven_aggregator"]["selection_reason"] == "packaging-pom-with-modules"
    # manifest_root top-level deve riflettere l'aggregator dir
    assert data["manifest_root"] == "pae-deposito-musica"
