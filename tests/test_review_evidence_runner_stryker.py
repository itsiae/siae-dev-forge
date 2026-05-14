"""Tests for Stryker JS/TS mutation testing adapter."""
from __future__ import annotations

import json
from pathlib import Path

# Import module directly: __init__.py auto-register integration is a
# separate task. We rely on side-effect register() at import time.
from lib.review_evidence.runners import stryker as stryker_module
from lib.review_evidence.runners._registry import registry
from lib.review_evidence.scoring import MutationFindings


SIMPLE_REPORT = {
    "schemaVersion": "1.0",
    "files": {
        "src/foo.ts": {
            "mutants": [
                {"id": "1", "status": "Killed"},
                {"id": "2", "status": "Survived"},
            ]
        }
    },
}

ALL_STATUS_REPORT = {
    "schemaVersion": "1.0",
    "files": {
        "src/foo.ts": {
            "mutants": [
                {"id": "1", "status": "Killed"},
                {"id": "2", "status": "Survived"},
                {"id": "3", "status": "Timeout"},
                {"id": "4", "status": "NoCoverage"},
                {"id": "5", "status": "RuntimeError"},
                {"id": "6", "status": "CompileError"},
                {"id": "7", "status": "Ignored"},
            ]
        }
    },
}

ALL_KILLED_REPORT = {
    "schemaVersion": "1.0",
    "files": {
        "src/foo.ts": {
            "mutants": [{"id": str(i), "status": "Killed"} for i in range(10)]
        }
    },
}

MULTIFILE_REPORT = {
    "schemaVersion": "1.0",
    "files": {
        "src/foo.ts": {
            "mutants": [
                {"id": "1", "status": "Killed"},
                {"id": "2", "status": "Survived"},
            ]
        },
        "src/bar.ts": {
            "mutants": [
                {"id": "3", "status": "Killed"},
                {"id": "4", "status": "Timeout"},
                {"id": "5", "status": "NoCoverage"},
            ]
        },
    },
}


def _write_report(tmp_path: Path, report: dict, *, with_package: bool = True) -> Path:
    rdir = tmp_path / "reports" / "mutation"
    rdir.mkdir(parents=True, exist_ok=True)
    rpath = rdir / "mutation.json"
    rpath.write_text(json.dumps(report))
    if with_package:
        (tmp_path / "package.json").write_text('{"name":"x"}')
    return rpath


def _runner() -> stryker_module.StrykerRunner:
    return stryker_module.StrykerRunner()


def test_stryker_runner_registered():
    """Import side-effect registers StrykerRunner in the global registry."""
    names = [getattr(r, "name", None) for r in registry]
    assert "stryker" in names


def test_is_applicable_disabled_returns_false(tmp_path, monkeypatch):
    monkeypatch.delenv("DEVFORGE_MUTATION_ENABLED", raising=False)
    _write_report(tmp_path, SIMPLE_REPORT)
    assert _runner().is_applicable(tmp_path) is False


def test_is_applicable_no_package_json_returns_false(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    # Write report only, no package.json.
    _write_report(tmp_path, SIMPLE_REPORT, with_package=False)
    assert _runner().is_applicable(tmp_path) is False


def test_is_applicable_no_report_returns_false(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    (tmp_path / "package.json").write_text('{"name":"x"}')
    assert _runner().is_applicable(tmp_path) is False


def test_is_applicable_all_present_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _write_report(tmp_path, SIMPLE_REPORT)
    assert _runner().is_applicable(tmp_path) is True


def test_run_disabled_returns_none(tmp_path, monkeypatch):
    monkeypatch.delenv("DEVFORGE_MUTATION_ENABLED", raising=False)
    _write_report(tmp_path, SIMPLE_REPORT)
    assert _runner().run(tmp_path) is None


def test_run_simple_killed_survived(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _write_report(tmp_path, SIMPLE_REPORT)
    out = _runner().run(tmp_path)
    assert isinstance(out, MutationFindings)
    assert out.killed == 1
    assert out.survived == 1
    assert out.timeout == 0
    assert out.no_coverage == 0
    assert out.total_mutants == 2
    assert out.score_pct == 50.0
    assert out.tool == "stryker"


def test_run_all_status_types(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _write_report(tmp_path, ALL_STATUS_REPORT)
    out = _runner().run(tmp_path)
    assert out is not None
    assert out.killed == 1
    assert out.survived == 1
    assert out.timeout == 1
    assert out.no_coverage == 1
    # total counts all 7 (including RuntimeError, CompileError, Ignored).
    assert out.total_mutants == 7
    # scored_denom = killed+survived+timeout+no_coverage = 4 → 1/4 = 25%.
    assert out.score_pct == 25.0


def test_run_all_killed(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _write_report(tmp_path, ALL_KILLED_REPORT)
    out = _runner().run(tmp_path)
    assert out is not None
    assert out.killed == 10
    assert out.survived == 0
    assert out.total_mutants == 10
    assert out.score_pct == 100.0


def test_run_invalid_json_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    rdir = tmp_path / "reports" / "mutation"
    rdir.mkdir(parents=True)
    (rdir / "mutation.json").write_text("not json")
    (tmp_path / "package.json").write_text('{"name":"x"}')
    assert _runner().run(tmp_path) is None


def test_run_no_files_in_report_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _write_report(tmp_path, {"schemaVersion": "1.0", "files": {}})
    # total = 0 (no mutants at all) → None.
    assert _runner().run(tmp_path) is None


def test_run_empty_mutants_list_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _write_report(
        tmp_path,
        {"schemaVersion": "1.0", "files": {"x.ts": {"mutants": []}}},
    )
    assert _runner().run(tmp_path) is None


def test_run_env_override_report_path(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    # Node project (package.json) but custom absolute report path.
    (tmp_path / "package.json").write_text('{"name":"x"}')
    custom = tmp_path / "custom-stryker.json"
    custom.write_text(json.dumps(SIMPLE_REPORT))
    monkeypatch.setenv("DEVFORGE_STRYKER_REPORT_PATH", str(custom))
    out = _runner().run(tmp_path)
    assert out is not None
    assert out.killed == 1
    assert out.survived == 1
    assert out.score_pct == 50.0


def test_run_relative_override_path(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    (tmp_path / "package.json").write_text('{"name":"x"}')
    rel_dir = tmp_path / "custom"
    rel_dir.mkdir()
    (rel_dir / "m.json").write_text(json.dumps(ALL_KILLED_REPORT))
    monkeypatch.setenv("DEVFORGE_STRYKER_REPORT_PATH", "custom/m.json")
    out = _runner().run(tmp_path)
    assert out is not None
    assert out.killed == 10
    assert out.score_pct == 100.0


def test_run_multifile_aggregation(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _write_report(tmp_path, MULTIFILE_REPORT)
    out = _runner().run(tmp_path)
    assert out is not None
    # foo.ts: 1 Killed + 1 Survived; bar.ts: 1 Killed + 1 Timeout + 1 NoCoverage.
    assert out.killed == 2
    assert out.survived == 1
    assert out.timeout == 1
    assert out.no_coverage == 1
    assert out.total_mutants == 5
    # scored_denom = 5, killed=2 → 40%.
    assert out.score_pct == 40.0


def test_run_non_dict_report_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    rdir = tmp_path / "reports" / "mutation"
    rdir.mkdir(parents=True)
    (rdir / "mutation.json").write_text(json.dumps([]))
    (tmp_path / "package.json").write_text('{"name":"x"}')
    assert _runner().run(tmp_path) is None


def test_run_missing_files_key_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _write_report(tmp_path, {"schemaVersion": "1.0"})
    # No files key → total=0 → None.
    assert _runner().run(tmp_path) is None
