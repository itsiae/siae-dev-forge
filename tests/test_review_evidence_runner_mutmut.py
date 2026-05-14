"""Tests for mutmut Python mutation testing adapter.

Opt-in via DEVFORGE_MUTATION_ENABLED=1; advisory metric (REVIEWER_HANDOFF,
never BLOCK). See lib/review_evidence/runners/mutmut.py.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Side-effect register() at import time.
from lib.review_evidence.runners import mutmut as mutmut_module  # noqa: E402
from lib.review_evidence.runners._registry import registry  # noqa: E402
from lib.review_evidence.runners.mutmut import MutmutRunner  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_python_project_with_cache(tmp_path: Path) -> None:
    """Minimal pyproject + .mutmut-cache layout."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    (tmp_path / ".mutmut-cache").mkdir()


def _mock_proc(stdout: str = "", returncode: int = 0) -> MagicMock:
    m = MagicMock()
    m.stdout = stdout
    m.stderr = ""
    m.returncode = returncode
    return m


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_mutmut_runner_registered():
    assert any(r.name == "mutmut" for r in registry)


# ---------------------------------------------------------------------------
# is_applicable
# ---------------------------------------------------------------------------


def test_is_applicable_disabled_returns_false(tmp_path, monkeypatch):
    monkeypatch.delenv("DEVFORGE_MUTATION_ENABLED", raising=False)
    _setup_python_project_with_cache(tmp_path)
    assert MutmutRunner().is_applicable(tmp_path) is False


def test_is_applicable_no_pyproject_returns_false(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    # cache present but no pyproject.toml / setup.py
    (tmp_path / ".mutmut-cache").mkdir()
    assert MutmutRunner().is_applicable(tmp_path) is False


def test_is_applicable_no_cache_returns_false(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    assert MutmutRunner().is_applicable(tmp_path) is False


def test_is_applicable_both_present_with_setup_py(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    (tmp_path / "setup.py").write_text("from setuptools import setup\nsetup()\n")
    (tmp_path / ".mutmut-cache").mkdir()
    assert MutmutRunner().is_applicable(tmp_path) is True


def test_is_applicable_pyproject_plus_cache_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _setup_python_project_with_cache(tmp_path)
    assert MutmutRunner().is_applicable(tmp_path) is True


def test_is_applicable_env_override_cache_path(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    custom_cache = tmp_path / "custom-mutmut"
    custom_cache.mkdir()
    monkeypatch.setenv("DEVFORGE_MUTMUT_CACHE_PATH", str(custom_cache))
    # Default .mutmut-cache absent, but custom path present.
    assert MutmutRunner().is_applicable(tmp_path) is True


def test_is_applicable_env_override_cache_path_relative(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    (tmp_path / "rel-cache").mkdir()
    monkeypatch.setenv("DEVFORGE_MUTMUT_CACHE_PATH", "rel-cache")
    assert MutmutRunner().is_applicable(tmp_path) is True


# ---------------------------------------------------------------------------
# run() — env-guard
# ---------------------------------------------------------------------------


def test_run_disabled_returns_none(tmp_path, monkeypatch):
    monkeypatch.delenv("DEVFORGE_MUTATION_ENABLED", raising=False)
    _setup_python_project_with_cache(tmp_path)
    assert MutmutRunner().run(tmp_path) is None


# ---------------------------------------------------------------------------
# run() — JSON path
# ---------------------------------------------------------------------------


def test_run_json_simple(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _setup_python_project_with_cache(tmp_path)
    runner = MutmutRunner()
    payload = json.dumps(
        {"killed": 10, "survived": 5, "total": 15, "timeout": 0, "no_tests": 0}
    )
    with patch(
        "lib.review_evidence.runners.mutmut.subprocess.run",
        return_value=_mock_proc(stdout=payload),
    ):
        result = runner.run(tmp_path)
    assert result is not None
    assert result.killed == 10
    assert result.survived == 5
    assert result.total_mutants == 15
    assert result.tool == "mutmut"
    # Score = 10 / (10+5+0+0) = 66.67
    assert result.score_pct == 66.67


def test_run_json_all_killed(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _setup_python_project_with_cache(tmp_path)
    payload = json.dumps(
        {"killed": 20, "survived": 0, "total": 20, "timeout": 0, "no_tests": 0}
    )
    with patch(
        "lib.review_evidence.runners.mutmut.subprocess.run",
        return_value=_mock_proc(stdout=payload),
    ):
        result = MutmutRunner().run(tmp_path)
    assert result is not None
    assert result.score_pct == 100.0
    assert result.killed == 20
    assert result.total_mutants == 20


def test_run_json_total_missing_fallback_sum(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _setup_python_project_with_cache(tmp_path)
    # No "total" key → computed as killed+survived+timeout+no_tests.
    payload = json.dumps({"killed": 5, "survived": 3})
    with patch(
        "lib.review_evidence.runners.mutmut.subprocess.run",
        return_value=_mock_proc(stdout=payload),
    ):
        result = MutmutRunner().run(tmp_path)
    assert result is not None
    assert result.killed == 5
    assert result.survived == 3
    assert result.total_mutants == 8


def test_run_json_total_zero_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _setup_python_project_with_cache(tmp_path)
    payload = json.dumps({"killed": 0, "survived": 0, "total": 0})
    with patch(
        "lib.review_evidence.runners.mutmut.subprocess.run",
        return_value=_mock_proc(stdout=payload),
    ):
        result = MutmutRunner().run(tmp_path)
    assert result is None


def test_run_json_with_timeout_and_no_coverage(tmp_path, monkeypatch):
    """Verify timeout + no_tests propagate to fields."""
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _setup_python_project_with_cache(tmp_path)
    payload = json.dumps(
        {
            "killed": 10,
            "survived": 5,
            "timeout": 2,
            "no_tests": 3,
            "total": 20,
        }
    )
    with patch(
        "lib.review_evidence.runners.mutmut.subprocess.run",
        return_value=_mock_proc(stdout=payload),
    ):
        result = MutmutRunner().run(tmp_path)
    assert result is not None
    assert result.timeout == 2
    assert result.no_coverage == 3
    assert result.total_mutants == 20
    # Score = 10 / (10+5+2+3) = 50.0
    assert result.score_pct == 50.0


# ---------------------------------------------------------------------------
# run() — text fallback
# ---------------------------------------------------------------------------


def test_run_invalid_json_falls_back_to_text(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _setup_python_project_with_cache(tmp_path)
    # First call: --json returns garbage non-JSON. Second call (text): real
    # mutmut results-like output.
    json_stdout = "this is not json"
    text_stdout = (
        "mutmut results summary\n"
        "Killed mutants: 7\n"
        "Survived mutants: 3\n"
        "Timeout: 0\n"
        "Total mutants: 10\n"
    )
    proc_json = _mock_proc(stdout=json_stdout)
    proc_text = _mock_proc(stdout=text_stdout)
    with patch(
        "lib.review_evidence.runners.mutmut.subprocess.run",
        side_effect=[proc_json, proc_text],
    ):
        result = MutmutRunner().run(tmp_path)
    assert result is not None
    assert result.killed == 7
    assert result.survived == 3
    assert result.total_mutants == 10
    # Score = 7 / (7+3+0+0) = 70.0
    assert result.score_pct == 70.0


def test_run_empty_stdout_both_calls_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _setup_python_project_with_cache(tmp_path)
    proc_empty = _mock_proc(stdout="")
    with patch(
        "lib.review_evidence.runners.mutmut.subprocess.run",
        side_effect=[proc_empty, proc_empty],
    ):
        result = MutmutRunner().run(tmp_path)
    assert result is None


# ---------------------------------------------------------------------------
# run() — subprocess failure modes
# ---------------------------------------------------------------------------


def test_run_mutmut_not_installed(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _setup_python_project_with_cache(tmp_path)
    with patch(
        "lib.review_evidence.runners.mutmut.subprocess.run",
        side_effect=FileNotFoundError("mutmut"),
    ):
        assert MutmutRunner().run(tmp_path) is None


def test_run_timeout(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _setup_python_project_with_cache(tmp_path)
    with patch(
        "lib.review_evidence.runners.mutmut.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="mutmut", timeout=30),
    ):
        assert MutmutRunner().run(tmp_path) is None


def test_run_permission_error(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _setup_python_project_with_cache(tmp_path)
    with patch(
        "lib.review_evidence.runners.mutmut.subprocess.run",
        side_effect=PermissionError("denied"),
    ):
        assert MutmutRunner().run(tmp_path) is None


def test_run_fallback_text_call_also_fails(tmp_path, monkeypatch):
    """JSON returns garbage, then text call raises FileNotFoundError → None."""
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _setup_python_project_with_cache(tmp_path)
    proc_garbage = _mock_proc(stdout="not json")
    with patch(
        "lib.review_evidence.runners.mutmut.subprocess.run",
        side_effect=[proc_garbage, FileNotFoundError("mutmut")],
    ):
        assert MutmutRunner().run(tmp_path) is None


# ---------------------------------------------------------------------------
# subprocess invocation contract
# ---------------------------------------------------------------------------


def test_run_subprocess_called_with_correct_args(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _setup_python_project_with_cache(tmp_path)
    payload = json.dumps(
        {"killed": 1, "survived": 1, "total": 2, "timeout": 0, "no_tests": 0}
    )
    with patch(
        "lib.review_evidence.runners.mutmut.subprocess.run",
        return_value=_mock_proc(stdout=payload),
    ) as mock_run:
        MutmutRunner().run(tmp_path)
    # First (and in this scenario only) call: mutmut results --json
    first_call = mock_run.call_args_list[0]
    args, kwargs = first_call
    assert args[0] == ["mutmut", "results", "--json"]
    assert kwargs.get("cwd") == tmp_path
    assert kwargs.get("timeout") == 30
    assert kwargs.get("capture_output") is True
    assert kwargs.get("text") is True


def test_run_json_non_dict_payload_returns_none(tmp_path, monkeypatch):
    """JSON list / scalar → should not crash, just bail to text fallback."""
    monkeypatch.setenv("DEVFORGE_MUTATION_ENABLED", "1")
    _setup_python_project_with_cache(tmp_path)
    proc_list = _mock_proc(stdout=json.dumps([1, 2, 3]))
    proc_empty = _mock_proc(stdout="")
    with patch(
        "lib.review_evidence.runners.mutmut.subprocess.run",
        side_effect=[proc_list, proc_empty],
    ):
        assert MutmutRunner().run(tmp_path) is None
