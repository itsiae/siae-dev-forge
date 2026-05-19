"""Test estensione select_command.py — supporto Java multi-module Maven.

Audit blind ha rilevato che ~70% dei repo SIAE sport-* sono Spring Boot multi-module Maven.
La logica attuale emette path single-module che fallisce su questi repo.

Fix: per Java/JaCoCo, emettere:
1. jacoco-aggregate report se presente (single XML certificato)
2. Path single-module se file effettivamente presente
3. Repo root come directory (parse_coverage.py aggrega via rglob) come fallback
"""
import json
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "select_command.py"


def run_select(repo_path: Path) -> dict:
    result = subprocess.run(
        ["python3", str(SCRIPT), str(repo_path)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


_POM_WITH_JACOCO = (
    "<?xml version='1.0'?><project>"
    "<build><plugins><plugin>"
    "<groupId>org.jacoco</groupId>"
    "<artifactId>jacoco-maven-plugin</artifactId>"
    "<version>0.8.12</version>"
    "<executions>"
    "<execution><id>prepare-agent</id><goals><goal>prepare-agent</goal></goals></execution>"
    "<execution><id>report</id><phase>test</phase><goals><goal>report</goal></goals></execution>"
    "</executions>"
    "</plugin></plugins></build>"
    "</project>"
)


def _bootstrap_maven_repo(repo: Path) -> None:
    (repo / ".code-coverage").mkdir(parents=True, exist_ok=True)
    (repo / ".code-coverage" / "env.json").write_text(
        json.dumps({"required_framework": "junit5"})
    )
    # Task 06: pom DEVE includere jacoco-maven-plugin altrimenti select_fields
    # ritorna actionable error invece di cov_cmd/path.
    (repo / "pom.xml").write_text(_POM_WITH_JACOCO)


def test_maven_mono_module_returns_single_path(tmp_path):
    """Mono-module con jacoco.xml esistente → path single-module standard."""
    repo = tmp_path / "maven-mono"
    repo.mkdir()
    _bootstrap_maven_repo(repo)
    jacoco_dir = repo / "target" / "site" / "jacoco"
    jacoco_dir.mkdir(parents=True)
    (jacoco_dir / "jacoco.xml").write_text("<?xml version='1.0'?><report/>")

    out = run_select(repo)
    assert out["error"] is None, out
    assert out["report_path"] == "target/site/jacoco/jacoco.xml"
    assert out["format"] == "jacoco"


def test_maven_multimodule_with_aggregate_prefers_aggregate(tmp_path):
    """Multi-module con jacoco-aggregate → preferisce aggregate XML."""
    repo = tmp_path / "maven-multi"
    repo.mkdir()
    _bootstrap_maven_repo(repo)
    agg_dir = repo / "coverage-aggregate" / "target" / "site" / "jacoco-aggregate"
    agg_dir.mkdir(parents=True)
    (repo / "coverage-aggregate" / "pom.xml").write_text("<project/>")
    (agg_dir / "jacoco.xml").write_text("<?xml version='1.0'?><report/>")

    out = run_select(repo)
    assert out["error"] is None, out
    assert out["report_path"] == "coverage-aggregate/target/site/jacoco-aggregate/jacoco.xml"
    assert out["format"] == "jacoco"


def test_maven_multimodule_no_aggregate_falls_back_to_repo_root(tmp_path):
    """Multi-module senza aggregate → ritorna '.' (rglob via parse_coverage)."""
    repo = tmp_path / "maven-multi-noagg"
    repo.mkdir()
    _bootstrap_maven_repo(repo)
    # Multi-module: pom root deve contenere <modules> + jacoco-plugin (Task 06)
    (repo / "pom.xml").write_text(
        "<?xml version='1.0'?><project>"
        "<modules><module>mod-a</module><module>mod-b</module></modules>"
        "<build><plugins><plugin>"
        "<groupId>org.jacoco</groupId>"
        "<artifactId>jacoco-maven-plugin</artifactId>"
        "<version>0.8.12</version>"
        "<executions><execution><goals><goal>report</goal></goals></execution></executions>"
        "</plugin></plugins></build>"
        "</project>"
    )
    for mod in ("mod-a", "mod-b"):
        jdir = repo / mod / "target" / "site" / "jacoco"
        jdir.mkdir(parents=True)
        (repo / mod / "pom.xml").write_text("<project/>")
        (jdir / "jacoco.xml").write_text("<?xml version='1.0'?><report/>")

    out = run_select(repo)
    assert out["error"] is None, out
    assert out["report_path"] == "."
    assert out["format"] == "jacoco"


def test_single_module_maven_emits_canonical_path(tmp_path):
    """Repo Maven single-module senza <modules> tag → emit target/site/jacoco/jacoco.xml."""
    repo = tmp_path / "single-mvn"
    repo.mkdir()
    (repo / ".code-coverage").mkdir()
    (repo / "pom.xml").write_text(
        "<?xml version='1.0'?><project><artifactId>x</artifactId>"
        "<build><plugins><plugin>"
        "<groupId>org.jacoco</groupId>"
        "<artifactId>jacoco-maven-plugin</artifactId>"
        "<version>0.8.12</version>"
        "<executions><execution><goals><goal>report</goal></goals></execution></executions>"
        "</plugin></plugins></build>"
        "</project>"
    )
    (repo / ".code-coverage" / "env.json").write_text('{"required_framework":"junit5"}')

    import subprocess, json
    out = subprocess.run(
        ["python3", "skills/code-coverage/scripts/select_command.py", str(repo)],
        capture_output=True, text=True, cwd="/Users/mazzacuv/Git/siae-dev-forge",
    )
    d = json.loads(out.stdout)
    assert d["report_path"] == "target/site/jacoco/jacoco.xml", f"got {d['report_path']}"


def test_multi_module_maven_falls_back_to_dot(tmp_path):
    """Repo Maven multi-module con <modules> → fallback "." per rglob."""
    repo = tmp_path / "multi-mvn"
    repo.mkdir()
    (repo / ".code-coverage").mkdir()
    (repo / "pom.xml").write_text(
        "<?xml version='1.0'?><project>"
        "<modules><module>a</module><module>b</module></modules>"
        "<build><plugins><plugin>"
        "<groupId>org.jacoco</groupId>"
        "<artifactId>jacoco-maven-plugin</artifactId>"
        "<version>0.8.12</version>"
        "<executions><execution><goals><goal>report</goal></goals></execution></executions>"
        "</plugin></plugins></build>"
        "</project>"
    )
    (repo / ".code-coverage" / "env.json").write_text('{"required_framework":"junit5"}')

    import subprocess, json
    out = subprocess.run(
        ["python3", "skills/code-coverage/scripts/select_command.py", str(repo)],
        capture_output=True, text=True, cwd="/Users/mazzacuv/Git/siae-dev-forge",
    )
    d = json.loads(out.stdout)
    assert d["report_path"] == ".", f"got {d['report_path']}"


# --- Task 06 — JaCoCo plugin pre-check + manifest_root surfacing ----------


def test_jacoco_plugin_missing_emits_actionable_error(tmp_path):
    """pom.xml senza <artifactId>jacoco-maven-plugin</artifactId> → error con snippet pronto."""
    repo = tmp_path / "no-jacoco-plugin"
    repo.mkdir()
    _bootstrap_maven_repo(repo)
    # pom dichiara solo la version property, niente plugin wired in <plugins>
    (repo / "pom.xml").write_text(
        "<?xml version='1.0'?><project>"
        "<properties><jacoco.version>0.8.12</jacoco.version></properties>"
        "</project>"
    )

    out = run_select(repo)
    assert out["error"] is not None
    assert "jacoco-maven-plugin" in out["error"]
    assert "<executions>" in out["error"]
    assert "<goal>prepare-agent</goal>" in out["error"]


def test_jacoco_plugin_present_returns_command(tmp_path):
    """pom.xml con plugin correttamente wired → cov_cmd risolto, error None."""
    repo = tmp_path / "jacoco-wired"
    repo.mkdir()
    _bootstrap_maven_repo(repo)
    (repo / "pom.xml").write_text(
        "<?xml version='1.0'?><project>"
        "<build><plugins><plugin>"
        "<groupId>org.jacoco</groupId>"
        "<artifactId>jacoco-maven-plugin</artifactId>"
        "<version>0.8.12</version>"
        "<executions>"
        "<execution><id>prepare-agent</id><goals><goal>prepare-agent</goal></goals></execution>"
        "<execution><id>report</id><phase>test</phase><goals><goal>report</goal></goals></execution>"
        "</executions>"
        "</plugin></plugins></build>"
        "</project>"
    )

    out = run_select(repo)
    assert out["error"] is None, out
    assert "mvn" in out["cov_cmd"]
    assert "jacoco:report" in out["cov_cmd"]


def test_manifest_root_surfaced_in_output(tmp_path):
    """stack.json con manifest_root nested → emit() include il field nel JSON."""
    repo = tmp_path / "monorepo-vitest"
    repo.mkdir()
    (repo / ".code-coverage").mkdir()
    (repo / ".code-coverage" / "env.json").write_text('{"required_framework":"vitest"}')
    (repo / ".code-coverage" / "stack.json").write_text(json.dumps({
        "manifest_root": "modules/service/lambda",
        "architecture_style": "serverless",
    }))
    # package.json di facciata per non far esplodere downstream check (no asserzioni qui)
    (repo / "package.json").write_text('{"name":"x","devDependencies":{"vitest":"^1.0.0"}}')

    out = run_select(repo)
    assert "manifest_root" in out
    assert out["manifest_root"] == "modules/service/lambda"


def test_manifest_root_defaults_to_dot_when_stack_json_missing(tmp_path):
    """stack.json assente → manifest_root='.' (default, no error)."""
    repo = tmp_path / "no-stack-json"
    repo.mkdir()
    _bootstrap_maven_repo(repo)
    (repo / "pom.xml").write_text(
        "<?xml version='1.0'?><project>"
        "<build><plugins><plugin>"
        "<groupId>org.jacoco</groupId>"
        "<artifactId>jacoco-maven-plugin</artifactId>"
        "<version>0.8.12</version>"
        "<executions><execution><goals><goal>report</goal></goals></execution></executions>"
        "</plugin></plugins></build>"
        "</project>"
    )

    out = run_select(repo)
    assert out["manifest_root"] == "."
