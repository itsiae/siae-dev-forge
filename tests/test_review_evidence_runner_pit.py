"""Tests for PIT Java mutation testing adapter."""
from __future__ import annotations

from pathlib import Path


# Import module directly: __init__.py auto-register integration is a
# separate task. We rely on side-effect register() at import time.
from lib.review_evidence.runners import pit as pit_module
from lib.review_evidence.runners._registry import registry
from lib.review_evidence.scoring import MutationFindings


SIMPLE_XML = '''<?xml version="1.0"?>
<mutations>
  <mutation detected="true" status="KILLED"><sourceFile>x.java</sourceFile></mutation>
  <mutation detected="false" status="SURVIVED"><sourceFile>x.java</sourceFile></mutation>
</mutations>'''

ALL_KILLED_XML = '''<?xml version="1.0"?>
<mutations>
{rows}
</mutations>'''.format(rows="\n".join(
    '  <mutation detected="true" status="KILLED"><sourceFile>x.java</sourceFile></mutation>'
    for _ in range(10)
))

ALL_SURVIVED_XML = '''<?xml version="1.0"?>
<mutations>
{rows}
</mutations>'''.format(rows="\n".join(
    '  <mutation detected="false" status="SURVIVED"><sourceFile>x.java</sourceFile></mutation>'
    for _ in range(5)
))

MIXED_XML = '''<?xml version="1.0"?>
<mutations>
  <mutation detected="true" status="KILLED"><sourceFile>x.java</sourceFile></mutation>
  <mutation detected="true" status="KILLED"><sourceFile>x.java</sourceFile></mutation>
  <mutation detected="true" status="KILLED"><sourceFile>x.java</sourceFile></mutation>
  <mutation detected="false" status="SURVIVED"><sourceFile>x.java</sourceFile></mutation>
  <mutation detected="false" status="TIMED_OUT"><sourceFile>x.java</sourceFile></mutation>
  <mutation detected="false" status="NO_COVERAGE"><sourceFile>x.java</sourceFile></mutation>
</mutations>'''

MEMORY_ERROR_XML = '''<?xml version="1.0"?>
<mutations>
  <mutation detected="true" status="KILLED"><sourceFile>x.java</sourceFile></mutation>
  <mutation detected="false" status="MEMORY_ERROR"><sourceFile>x.java</sourceFile></mutation>
</mutations>'''

RUN_ERROR_XML = '''<?xml version="1.0"?>
<mutations>
  <mutation detected="true" status="KILLED"><sourceFile>x.java</sourceFile></mutation>
  <mutation detected="false" status="RUN_ERROR"><sourceFile>x.java</sourceFile></mutation>
</mutations>'''

EMPTY_XML = '''<?xml version="1.0"?>
<mutations/>'''


def _write_report(tmp_path: Path, xml: str, *, with_pom: bool = True) -> Path:
    report_dir = tmp_path / "target" / "pit-reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report = report_dir / "mutations.xml"
    report.write_text(xml)
    if with_pom:
        (tmp_path / "pom.xml").write_text("<project/>")
    return report


def _runner() -> pit_module.PitRunner:
    return pit_module.PitRunner()


def test_pit_runner_registered():
    """Import side-effect registers PitRunner in the global registry."""
    names = [getattr(r, "name", None) for r in registry]
    assert "pit" in names


def test_is_applicable_disabled_returns_false(tmp_path, monkeypatch):
    monkeypatch.delenv("DEVFORGE_MUTATION_ENABLED", raising=False)
    _write_report(tmp_path, SIMPLE_XML)
    assert _runner().is_applicable(tmp_path) is False


def test_is_applicable_no_pom_returns_false(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    # Write report only, no pom.xml
    _write_report(tmp_path, SIMPLE_XML, with_pom=False)
    assert _runner().is_applicable(tmp_path) is False


def test_is_applicable_no_report_returns_false(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    (tmp_path / "pom.xml").write_text("<project/>")
    assert _runner().is_applicable(tmp_path) is False


def test_is_applicable_pom_plus_report_returns_true(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _write_report(tmp_path, SIMPLE_XML)
    assert _runner().is_applicable(tmp_path) is True


def test_run_disabled_returns_none(tmp_path, monkeypatch):
    monkeypatch.delenv("DEVFORGE_MUTATION_ENABLED", raising=False)
    _write_report(tmp_path, SIMPLE_XML)
    assert _runner().run(tmp_path) is None


def test_run_parses_simple_report(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _write_report(tmp_path, SIMPLE_XML)
    out = _runner().run(tmp_path)
    assert isinstance(out, MutationFindings)
    assert out.killed == 1
    assert out.survived == 1
    assert out.total_mutants == 2
    assert out.score_pct == 50.0
    assert out.tool == "pit"


def test_run_all_killed(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _write_report(tmp_path, ALL_KILLED_XML)
    out = _runner().run(tmp_path)
    assert out is not None
    assert out.killed == 10
    assert out.survived == 0
    assert out.total_mutants == 10
    assert out.score_pct == 100.0


def test_run_all_survived(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _write_report(tmp_path, ALL_SURVIVED_XML)
    out = _runner().run(tmp_path)
    assert out is not None
    assert out.killed == 0
    assert out.survived == 5
    assert out.total_mutants == 5
    assert out.score_pct == 0.0


def test_run_with_timeout_and_no_coverage(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _write_report(tmp_path, MIXED_XML)
    out = _runner().run(tmp_path)
    assert out is not None
    assert out.killed == 3
    assert out.survived == 1
    assert out.timeout == 1
    assert out.no_coverage == 1
    assert out.total_mutants == 6
    # scored_denom = 6, killed=3 → 50%
    assert out.score_pct == 50.0


def test_run_memory_error_counted_as_timeout(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _write_report(tmp_path, MEMORY_ERROR_XML)
    out = _runner().run(tmp_path)
    assert out is not None
    assert out.killed == 1
    assert out.timeout == 1
    assert out.total_mutants == 2
    # scored_denom = 2 (killed+timeout), killed=1 → 50%
    assert out.score_pct == 50.0


def test_run_invalid_xml_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    report_dir = tmp_path / "target" / "pit-reports"
    report_dir.mkdir(parents=True)
    (report_dir / "mutations.xml").write_text("not xml at all <<<")
    (tmp_path / "pom.xml").write_text("<project/>")
    assert _runner().run(tmp_path) is None


def test_run_empty_mutations_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _write_report(tmp_path, EMPTY_XML)
    assert _runner().run(tmp_path) is None


def test_run_env_override_report_path(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    # Java project (pom.xml) but custom absolute report path.
    (tmp_path / "pom.xml").write_text("<project/>")
    custom = tmp_path / "custom-report.xml"
    custom.write_text(SIMPLE_XML)
    monkeypatch.setenv("DEVFORGE_PIT_REPORT_PATH", str(custom))
    out = _runner().run(tmp_path)
    assert out is not None
    assert out.killed == 1
    assert out.survived == 1
    assert out.score_pct == 50.0


def test_run_relative_override_path(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    (tmp_path / "pom.xml").write_text("<project/>")
    rel_dir = tmp_path / "pit-out"
    rel_dir.mkdir()
    (rel_dir / "m.xml").write_text(ALL_KILLED_XML)
    monkeypatch.setenv("DEVFORGE_PIT_REPORT_PATH", "pit-out/m.xml")
    out = _runner().run(tmp_path)
    assert out is not None
    assert out.killed == 10
    assert out.score_pct == 100.0


def test_run_run_error_excluded_from_score_denom(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _write_report(tmp_path, RUN_ERROR_XML)
    out = _runner().run(tmp_path)
    assert out is not None
    assert out.killed == 1
    assert out.survived == 0
    assert out.timeout == 0
    assert out.no_coverage == 0
    # total counts RUN_ERROR, but scored_denom excludes it.
    assert out.total_mutants == 2
    # scored_denom = killed + survived + timeout + no_coverage = 1
    # → score = 1/1 = 100%
    assert out.score_pct == 100.0
