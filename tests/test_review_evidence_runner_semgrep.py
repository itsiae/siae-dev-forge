"""Tests for Semgrep CE cross-stack SAST runner."""
from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

from lib.review_evidence.runners.semgrep import SemgrepRunner
from lib.review_evidence.scoring import SecurityFindings


# ---------- registry ----------


def test_semgrep_runner_registered():
    """Importing the runners package must auto-register SemgrepRunner."""
    import lib.review_evidence.runners as runners_pkg  # noqa: F401

    assert any(r.name == "semgrep" for r in runners_pkg.registry)


# ---------- is_applicable ----------


def test_is_applicable_python_repo(tmp_path):
    (tmp_path / "x.py").write_text("pass")
    assert SemgrepRunner().is_applicable(tmp_path) is True


def test_is_applicable_java_repo(tmp_path):
    (tmp_path / "App.java").write_text("class App {}")
    assert SemgrepRunner().is_applicable(tmp_path) is True


def test_is_applicable_empty_repo(tmp_path):
    assert SemgrepRunner().is_applicable(tmp_path) is False


def test_is_applicable_only_md(tmp_path):
    (tmp_path / "README.md").write_text("# hi")
    (tmp_path / "NOTES.md").write_text("notes")
    assert SemgrepRunner().is_applicable(tmp_path) is False


# ---------- run / severity mapping ----------


def _mock_proc(payload) -> MagicMock:
    stdout = payload if isinstance(payload, str) else json.dumps(payload)
    return MagicMock(stdout=stdout, returncode=0)


def test_run_no_findings(tmp_path):
    (tmp_path / "x.py").write_text("pass")
    with patch(
        "lib.review_evidence.runners.semgrep.subprocess.run",
        return_value=_mock_proc({"results": []}),
    ):
        result = SemgrepRunner().run(tmp_path)
    assert result == SecurityFindings(0, 0, 0, 0)


def test_run_error_security_critical(tmp_path):
    payload = {
        "results": [
            {
                "check_id": "py.sql-injection",
                "path": "src/db.py",
                "extra": {
                    "severity": "ERROR",
                    "metadata": {"category": "security"},
                },
            }
        ]
    }
    with patch(
        "lib.review_evidence.runners.semgrep.subprocess.run",
        return_value=_mock_proc(payload),
    ):
        result = SemgrepRunner().run(tmp_path)
    assert result == SecurityFindings(critical=1, high=0, medium=0, low=0)


def test_run_error_other_high(tmp_path):
    payload = {
        "results": [
            {
                "check_id": "py.bad-pattern",
                "path": "src/x.py",
                "extra": {
                    "severity": "ERROR",
                    "metadata": {"category": "correctness"},
                },
            }
        ]
    }
    with patch(
        "lib.review_evidence.runners.semgrep.subprocess.run",
        return_value=_mock_proc(payload),
    ):
        result = SemgrepRunner().run(tmp_path)
    assert result == SecurityFindings(critical=0, high=1, medium=0, low=0)


def test_run_warning_security_high(tmp_path):
    payload = {
        "results": [
            {
                "check_id": "py.weak-crypto",
                "path": "src/x.py",
                "extra": {
                    "severity": "WARNING",
                    "metadata": {"category": "security"},
                },
            }
        ]
    }
    with patch(
        "lib.review_evidence.runners.semgrep.subprocess.run",
        return_value=_mock_proc(payload),
    ):
        result = SemgrepRunner().run(tmp_path)
    assert result == SecurityFindings(critical=0, high=1, medium=0, low=0)


def test_run_warning_other_medium(tmp_path):
    payload = {
        "results": [
            {
                "check_id": "py.style",
                "path": "src/x.py",
                "extra": {
                    "severity": "WARNING",
                    "metadata": {"category": "best-practice"},
                },
            }
        ]
    }
    with patch(
        "lib.review_evidence.runners.semgrep.subprocess.run",
        return_value=_mock_proc(payload),
    ):
        result = SemgrepRunner().run(tmp_path)
    assert result == SecurityFindings(critical=0, high=0, medium=1, low=0)


def test_run_info_low(tmp_path):
    payload = {
        "results": [
            {
                "check_id": "py.info",
                "path": "src/x.py",
                "extra": {
                    "severity": "INFO",
                    "metadata": {"category": "best-practice"},
                },
            }
        ]
    }
    with patch(
        "lib.review_evidence.runners.semgrep.subprocess.run",
        return_value=_mock_proc(payload),
    ):
        result = SemgrepRunner().run(tmp_path)
    assert result == SecurityFindings(critical=0, high=0, medium=0, low=1)


# ---------- error paths ----------


def test_run_semgrep_not_installed(tmp_path):
    with patch(
        "lib.review_evidence.runners.semgrep.subprocess.run",
        side_effect=FileNotFoundError("semgrep"),
    ):
        assert SemgrepRunner().run(tmp_path) is None


def test_run_semgrep_timeout(tmp_path):
    with patch(
        "lib.review_evidence.runners.semgrep.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="semgrep", timeout=120),
    ):
        assert SemgrepRunner().run(tmp_path) is None


def test_run_invalid_json(tmp_path):
    with patch(
        "lib.review_evidence.runners.semgrep.subprocess.run",
        return_value=_mock_proc("not json at all"),
    ):
        assert SemgrepRunner().run(tmp_path) is None


def test_run_empty_stdout(tmp_path):
    with patch(
        "lib.review_evidence.runners.semgrep.subprocess.run",
        return_value=_mock_proc(""),
    ):
        assert SemgrepRunner().run(tmp_path) is None


def test_run_permission_error(tmp_path):
    with patch(
        "lib.review_evidence.runners.semgrep.subprocess.run",
        side_effect=PermissionError("denied"),
    ):
        assert SemgrepRunner().run(tmp_path) is None


# ---------- env override ----------


def test_run_custom_config_env(tmp_path, monkeypatch):
    monkeypatch.setenv("DEVFORGE_SEMGREP_CONFIG", "p/owasp-top-ten")
    captured = {}

    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        return _mock_proc({"results": []})

    with patch(
        "lib.review_evidence.runners.semgrep.subprocess.run",
        side_effect=fake_run,
    ):
        SemgrepRunner().run(tmp_path)
    assert "--config=p/owasp-top-ten" in captured["cmd"]


def test_run_default_config_auto(tmp_path, monkeypatch):
    """Without env override, default config is 'auto'."""
    monkeypatch.delenv("DEVFORGE_SEMGREP_CONFIG", raising=False)
    captured = {}

    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        return _mock_proc({"results": []})

    with patch(
        "lib.review_evidence.runners.semgrep.subprocess.run",
        side_effect=fake_run,
    ):
        SemgrepRunner().run(tmp_path)
    assert "--config=auto" in captured["cmd"]


# ---------- mixed findings ----------


def test_run_mixed_findings(tmp_path):
    payload = {
        "results": [
            {
                "check_id": "py.sql-inj",
                "path": "a.py",
                "extra": {"severity": "ERROR", "metadata": {"category": "security"}},
            },
            {
                "check_id": "py.bad",
                "path": "b.py",
                "extra": {"severity": "ERROR", "metadata": {"category": "correctness"}},
            },
            {
                "check_id": "py.weak",
                "path": "c.py",
                "extra": {"severity": "WARNING", "metadata": {"category": "security"}},
            },
            {
                "check_id": "py.info",
                "path": "d.py",
                "extra": {"severity": "INFO", "metadata": {"category": "best-practice"}},
            },
        ]
    }
    with patch(
        "lib.review_evidence.runners.semgrep.subprocess.run",
        return_value=_mock_proc(payload),
    ):
        result = SemgrepRunner().run(tmp_path)
    assert result == SecurityFindings(critical=1, high=2, medium=0, low=1)
