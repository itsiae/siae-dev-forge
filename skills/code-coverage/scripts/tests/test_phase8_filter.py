"""Test Task Phase 8 — phase8_filter.

Filtra moduli `skipped_modules` (rilevati in Task 06) dal bundle coverage
post-`mvn jacoco:report`. Senza il filter i moduli con `<jacoco.skip>true</jacoco.skip>`
contano come 0% LINE → falsi FAIL.

TDD: scritti PRIMA dell'implementazione.

Compat Python 3.8+ (typing.Union/Optional, no walrus, no PEP 604 |).
"""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))


# ---------------------------------------------------------------------------
# Fixtures inline (no conftest changes) — JaCoCo XML mock minimale
# ---------------------------------------------------------------------------
def _agg_xml_two_groups():
    """JaCoCo aggregate XML con 2 group: mod-a (80% LINE) + mod-b (0% LINE)."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<report name="agg">
  <group name="mod-a">
    <package name="x/y/z">
      <counter type="LINE" missed="20" covered="80"/>
      <counter type="BRANCH" missed="5" covered="15"/>
    </package>
    <counter type="LINE" missed="20" covered="80"/>
    <counter type="BRANCH" missed="5" covered="15"/>
  </group>
  <group name="mod-b">
    <package name="x/y/skip">
      <counter type="LINE" missed="100" covered="0"/>
    </package>
    <counter type="LINE" missed="100" covered="0"/>
  </group>
</report>
"""


def _single_module_xml():
    """JaCoCo single-module XML (no <group>, direttamente <package>)."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<report name="single">
  <package name="x/y/z">
    <counter type="LINE" missed="30" covered="70"/>
    <counter type="BRANCH" missed="10" covered="10"/>
  </package>
  <counter type="LINE" missed="30" covered="70"/>
  <counter type="BRANCH" missed="10" covered="10"/>
</report>
"""


# ---------------------------------------------------------------------------
# Unit tests — funzione filter_coverage
# ---------------------------------------------------------------------------
def test_filter_excludes_skipped_module(tmp_path):
    """XML con 2 group (mod-a 80%, mod-b 0%), skipped=[mod-b]
    → bundle_line_pct calcolato solo su mod-a (80%)."""
    from phase8_filter import filter_coverage
    xml_path = tmp_path / "jacoco.xml"
    xml_path.write_text(_agg_xml_two_groups())
    result = filter_coverage(xml_path, ["mod-b"])
    assert result["error"] is None
    # mod-a: 80 covered / 100 total = 80%
    assert abs(result["bundle_line_pct"] - 80.0) < 0.01
    # mod-a branch: 15 covered / 20 total = 75%
    assert abs(result["bundle_branch_pct"] - 75.0) < 0.01
    assert result["skipped_modules_excluded"] == ["mod-b"]
    assert result["modules_included"] == ["mod-a"]


def test_filter_no_skipped_returns_full_bundle(tmp_path):
    """XML con 2 group, skipped=[] → bundle = aggregato totale (mod-a + mod-b)."""
    from phase8_filter import filter_coverage
    xml_path = tmp_path / "jacoco.xml"
    xml_path.write_text(_agg_xml_two_groups())
    result = filter_coverage(xml_path, [])
    assert result["error"] is None
    # Totale: (80 + 0) covered / (100 + 100) total = 40%
    assert abs(result["bundle_line_pct"] - 40.0) < 0.01
    # Solo mod-a ha branch: 15 / 20 = 75% (mod-b non ha BRANCH counter)
    assert abs(result["bundle_branch_pct"] - 75.0) < 0.01
    assert result["skipped_modules_excluded"] == []
    assert sorted(result["modules_included"]) == ["mod-a", "mod-b"]


def test_filter_single_module_xml_no_groups(tmp_path):
    """XML senza <group> (single-module) → returned without filter applied."""
    from phase8_filter import filter_coverage
    xml_path = tmp_path / "jacoco.xml"
    xml_path.write_text(_single_module_xml())
    # Anche se skipped_modules è non-vuoto, single-module non ha group → no filter
    result = filter_coverage(xml_path, ["whatever"])
    assert result["error"] is None
    # 70 covered / 100 total = 70%
    assert abs(result["bundle_line_pct"] - 70.0) < 0.01
    # 10 covered / 20 branch total = 50%
    assert abs(result["bundle_branch_pct"] - 50.0) < 0.01
    # No filter applied
    assert result["skipped_modules_excluded"] == []
    assert result["modules_included"] == []  # no group → no module names


def test_filter_missing_xml_returns_error(tmp_path):
    """Path non esiste → dict con error non-null, no crash."""
    from phase8_filter import filter_coverage
    missing = tmp_path / "does-not-exist.xml"
    result = filter_coverage(missing, [])
    assert result["error"] is not None
    assert "not found" in result["error"].lower() or "no such" in result["error"].lower()
    assert result["bundle_line_pct"] == 0.0
    assert result["bundle_branch_pct"] == 0.0


def test_filter_cli_reads_env_json(tmp_path):
    """CLI E2E: repo con .code-coverage/env.json + target/site/jacoco/jacoco.xml mock
    → stdout JSON valido con bundle calcolato."""
    repo = tmp_path / "repo"
    repo.mkdir()
    cov_dir = repo / ".code-coverage"
    cov_dir.mkdir()
    (cov_dir / "env.json").write_text(json.dumps({
        "skipped_modules": ["mod-b"],
        "framework": "junit5",
    }))
    # Mock single-shot jacoco.xml (no aggregate per questo test)
    target = repo / "target" / "site" / "jacoco"
    target.mkdir(parents=True)
    (target / "jacoco.xml").write_text(_agg_xml_two_groups())

    result = subprocess.run(
        ["python3", str(SCRIPT_DIR / "phase8_filter.py"), str(repo)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["error"] is None
    assert data["skipped_modules_excluded"] == ["mod-b"]
    assert data["modules_included"] == ["mod-a"]
    assert abs(data["bundle_line_pct"] - 80.0) < 0.01


# ---------------------------------------------------------------------------
# Extra coverage: priorita' aggregate XML over single-module
# ---------------------------------------------------------------------------
def test_filter_cli_prefers_aggregate(tmp_path):
    """Se esistono entrambi jacoco-aggregate/jacoco.xml e jacoco/jacoco.xml,
    il CLI usa aggregate."""
    repo = tmp_path / "repo"
    repo.mkdir()
    cov_dir = repo / ".code-coverage"
    cov_dir.mkdir()
    (cov_dir / "env.json").write_text(json.dumps({"skipped_modules": []}))
    # Single-module (dovrebbe essere ignorato)
    single = repo / "target" / "site" / "jacoco"
    single.mkdir(parents=True)
    (single / "jacoco.xml").write_text(_single_module_xml())
    # Aggregate (preferito)
    agg = repo / "target" / "site" / "jacoco-aggregate"
    agg.mkdir(parents=True)
    (agg / "jacoco.xml").write_text(_agg_xml_two_groups())

    result = subprocess.run(
        ["python3", str(SCRIPT_DIR / "phase8_filter.py"), str(repo)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    # Aggregate emette 2 modules (mod-a + mod-b); single emette 0 (no group)
    assert sorted(data["modules_included"]) == ["mod-a", "mod-b"]


def test_filter_cli_missing_xml_emits_error_json(tmp_path):
    """CLI con repo senza jacoco.xml → JSON con error, exit 0."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".code-coverage").mkdir()
    (repo / ".code-coverage" / "env.json").write_text(json.dumps({"skipped_modules": []}))

    result = subprocess.run(
        ["python3", str(SCRIPT_DIR / "phase8_filter.py"), str(repo)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["error"] is not None
