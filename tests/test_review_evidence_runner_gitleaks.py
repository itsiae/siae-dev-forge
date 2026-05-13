"""Tests for gitleaks runner."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from lib.review_evidence.runners.gitleaks import GitleaksRunner

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_is_applicable_any_repo(tmp_path):
    (tmp_path / ".git").mkdir()
    assert GitleaksRunner().is_applicable(tmp_path) is True


def test_run_parses_findings_as_critical(tmp_path):
    (tmp_path / ".git").mkdir()
    gl_out = (FIX / "gitleaks_output.json").read_text()

    def fake_run(cmd, **kw):
        from subprocess import CompletedProcess

        # gitleaks exits 1 when leaks found, but stdout has JSON
        return CompletedProcess(cmd, 1, stdout=gl_out, stderr="")

    with patch("lib.review_evidence.runners.gitleaks.subprocess.run", side_effect=fake_run):
        result = GitleaksRunner().run(tmp_path)
    # Both findings = critical (secrets = critical severity)
    assert result.critical == 2
    assert result.high == 0
