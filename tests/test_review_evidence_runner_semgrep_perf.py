"""Wave 1 follow-up: runner perf + version check + EVIDENCE_TOOL_MISSING.

AC7: version check >=1.50.0 with EVIDENCE_TOOL_MISSING exit code.
AC8: --diff-aware via DEVFORGE_SEMGREP_BASELINE_COMMIT env.
EC-26: per-file timeout 10s (ReDoS protection).
EC-44: streaming JSON parser per output >50MB.
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from lib.review_evidence.runners.semgrep import (
    SemgrepRunner,
    _MIN_SEMGREP_VERSION,
    _TIMEOUT_PER_FILE,
)
from lib.review_evidence.scoring import SecurityFindings


def test_min_semgrep_version_constant():
    """AC7: minimum Semgrep version pinned to 1.50.0."""
    assert _MIN_SEMGREP_VERSION == "1.50.0"


def test_timeout_per_file_constant():
    """EC-26 ReDoS protection: per-file timeout=10s."""
    assert _TIMEOUT_PER_FILE == 10


def test_version_check_detects_old_semgrep(tmp_path):
    """AC7: runner returns SecurityFindings.tool_unavailable if semgrep <1.50."""
    runner = SemgrepRunner()
    with patch("subprocess.run") as mock_run:
        # First call = --version returns 1.40.0 (old)
        mock_run.return_value = MagicMock(stdout="1.40.0\n", returncode=0)
        with patch.object(runner, "_check_version") as mock_check:
            mock_check.return_value = "semgrep 1.40.0 < required 1.50.0"
            result = runner.run(tmp_path)
            assert result is not None
            assert result.tool_unavailable_reason is not None
            assert "1.50.0" in result.tool_unavailable_reason


def test_version_check_missing_semgrep(tmp_path):
    """AC7: semgrep not installed → tool_unavailable, not 0-findings."""
    runner = SemgrepRunner()
    with patch.object(runner, "_check_version", return_value="semgrep not installed"):
        result = runner.run(tmp_path)
        assert result is not None
        assert result.tool_unavailable_reason == "semgrep not installed"


def test_diff_aware_when_baseline_env_set(tmp_path):
    """AC8: DEVFORGE_SEMGREP_BASELINE_COMMIT settato → --baseline-commit aggiunto."""
    os.environ["DEVFORGE_SEMGREP_BASELINE_COMMIT"] = "abc123"
    try:
        runner = SemgrepRunner()
        with patch.object(runner, "_check_version", return_value=None), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout='{"results":[]}', returncode=0)
            runner.run(tmp_path)
            call_args = mock_run.call_args[0][0]
            assert "--baseline-commit" in call_args
            idx = call_args.index("--baseline-commit")
            assert call_args[idx + 1] == "abc123"
    finally:
        del os.environ["DEVFORGE_SEMGREP_BASELINE_COMMIT"]


def test_no_diff_aware_when_env_not_set(tmp_path):
    """AC8 negative: no --baseline-commit se env non settato."""
    runner = SemgrepRunner()
    with patch.object(runner, "_check_version", return_value=None), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout='{"results":[]}', returncode=0)
        runner.run(tmp_path)
        call_args = mock_run.call_args[0][0]
        assert "--baseline-commit" not in call_args


def test_jobs_arg_present(tmp_path):
    """Parallel jobs --jobs=N (default cpu_count via SEMGREP_JOBS or os.cpu_count)."""
    runner = SemgrepRunner()
    with patch.object(runner, "_check_version", return_value=None), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout='{"results":[]}', returncode=0)
        runner.run(tmp_path)
        call_args = mock_run.call_args[0][0]
        # At least --jobs= arg present
        assert any(a.startswith("--jobs=") for a in call_args)


def test_timeout_per_file_arg(tmp_path):
    """EC-26: --timeout=10 per-file ReDoS protection."""
    runner = SemgrepRunner()
    with patch.object(runner, "_check_version", return_value=None), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout='{"results":[]}', returncode=0)
        runner.run(tmp_path)
        call_args = mock_run.call_args[0][0]
        assert "--timeout=10" in call_args
