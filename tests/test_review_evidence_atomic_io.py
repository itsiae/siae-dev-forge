"""Tests for lib/review_evidence/atomic_io.py."""
import errno
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from lib.review_evidence.atomic_io import write_evidence_atomic


def test_normal_write_to_target(tmp_path):
    target = tmp_path / "evidence.json"
    success, used_fallback, reason = write_evidence_atomic(target, '{"k":"v"}')
    assert success is True
    assert used_fallback is False
    assert reason is None
    assert target.read_text() == '{"k":"v"}'


def test_retry_on_ebusy(tmp_path):
    target = tmp_path / "evidence.json"
    call_count = {"n": 0}
    real_replace = os.replace

    def flaky_replace(src, dst):
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise OSError(errno.EBUSY, "icloud busy")
        return real_replace(src, dst)

    with patch("lib.review_evidence.atomic_io.os.replace", side_effect=flaky_replace):
        success, used_fallback, reason = write_evidence_atomic(target, '{"k":"v"}')
    assert success is True
    assert used_fallback is False
    assert call_count["n"] == 3


def test_fallback_after_max_retries(tmp_path, monkeypatch):
    target = tmp_path / "evidence.json"

    def always_busy(src, dst):
        raise OSError(errno.EBUSY, "icloud busy")

    fallback_root = tmp_path / "fallback" / ".claude" / "review-evidence-fallback"
    # Only override FALLBACK_ROOT; no need to manipulate HOME (FALLBACK_ROOT is
    # the single source of truth in the implementation)
    monkeypatch.setattr("lib.review_evidence.atomic_io.FALLBACK_ROOT", fallback_root)

    with patch("lib.review_evidence.atomic_io.os.replace", side_effect=always_busy):
        success, used_fallback, reason = write_evidence_atomic(target, '{"k":"v"}', sha="abc123")

    assert success is True
    assert used_fallback is True
    assert "EBUSY" in reason or "icloud" in reason.lower()
    fallback_files = list(fallback_root.rglob("abc123.json"))
    assert len(fallback_files) == 1


def test_non_busy_error_propagates(tmp_path):
    target = tmp_path / "evidence.json"
    with patch("lib.review_evidence.atomic_io.os.replace",
               side_effect=PermissionError("denied")):
        with pytest.raises(PermissionError):
            write_evidence_atomic(target, '{"k":"v"}')
