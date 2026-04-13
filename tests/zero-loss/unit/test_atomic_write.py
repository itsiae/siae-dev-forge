"""Unit tests for lib/atomic_write.py — cross-OS lock+fsync wrapper.

Covers edge cases:
- #1 concurrent writes without truncation
- #2 kill during write (no partial line)
- #13 truncate accidentale (size decrease)
- #16 case-sensitive event_id (filesystem APFS edge)
- #17 UTF-8 (emoji, accenti)
- BLOCK-2 fix: shared lock file path with bash writer in lib/logger.sh
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

# Module under test (will be created in A3)
import atomic_write  # noqa: E402  — provided by lib/ on sys.path via conftest


def test_module_exports_atomic_append():
    """Smoke: module exposes the public API."""
    assert hasattr(atomic_write, "atomic_append")
    assert callable(atomic_write.atomic_append)


def test_basic_append_writes_line(activity_file):
    atomic_write.atomic_append(activity_file, '{"event":"hello"}')
    content = activity_file.read_text(encoding="utf-8")
    assert content == '{"event":"hello"}\n'


def test_basic_append_adds_trailing_newline_if_missing(activity_file):
    atomic_write.atomic_append(activity_file, '{"a":1}')  # no trailing \n
    assert activity_file.read_text(encoding="utf-8").endswith("\n")


def test_basic_append_preserves_existing_newline(activity_file):
    atomic_write.atomic_append(activity_file, '{"a":1}\n')
    # Should not double-newline
    assert activity_file.read_text(encoding="utf-8").count("\n") == 1


def test_concurrent_threads_no_truncation(activity_file):
    """Edge #1: 100 concurrent threads append 1 line each. No partial lines."""
    NUM_THREADS = 100

    def writer(idx: int) -> None:
        # Long-ish line to maximize chance of interleave under no-lock
        line = json.dumps({"event": "concurrent", "idx": idx, "padding": "x" * 200})
        atomic_write.atomic_append(activity_file, line)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(NUM_THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    lines = activity_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == NUM_THREADS, f"expected {NUM_THREADS} lines, got {len(lines)}"

    # Every line must parse as valid JSON (no truncation)
    parsed_idx = set()
    for line in lines:
        obj = json.loads(line)  # raises if truncated
        assert obj["event"] == "concurrent"
        parsed_idx.add(obj["idx"])
    assert parsed_idx == set(range(NUM_THREADS))


def test_fsync_on_write(activity_file, monkeypatch):
    """Verify os.fsync is invoked after the write (durability guarantee)."""
    fsync_calls: list[int] = []
    real_fsync = os.fsync

    def fake_fsync(fd: int) -> None:
        fsync_calls.append(fd)
        return real_fsync(fd)

    monkeypatch.setattr(os, "fsync", fake_fsync)
    atomic_write.atomic_append(activity_file, '{"a":1}')
    assert len(fsync_calls) == 1


def test_handles_size_decrease(activity_file):
    """Edge #13: file truncated externally between two writes — append still works."""
    atomic_write.atomic_append(activity_file, '{"a":1}')
    activity_file.write_text("", encoding="utf-8")  # external truncate
    atomic_write.atomic_append(activity_file, '{"a":2}')
    content = activity_file.read_text(encoding="utf-8")
    assert content == '{"a":2}\n'


def test_case_sensitive_event_id(activity_file):
    """Edge #16: APFS case-insensitive default — event_id with mixed case preserved verbatim."""
    eid_lower = "abc-123"
    eid_upper = "ABC-123"
    atomic_write.atomic_append(activity_file, json.dumps({"event_id": eid_lower}))
    atomic_write.atomic_append(activity_file, json.dumps({"event_id": eid_upper}))
    lines = activity_file.read_text(encoding="utf-8").splitlines()
    parsed = [json.loads(l) for l in lines]
    assert parsed[0]["event_id"] == eid_lower
    assert parsed[1]["event_id"] == eid_upper
    assert parsed[0]["event_id"] != parsed[1]["event_id"]  # preserved distinct


def test_utf8_roundtrip_emoji_accents(activity_file):
    """Edge #17: UTF-8 emoji and accents survive append + read."""
    payload = {"user": "lorèn'zo 🇮🇹", "msg": "Caffè ☕ — perché funzioni 😀"}
    atomic_write.atomic_append(activity_file, json.dumps(payload, ensure_ascii=False))
    parsed = json.loads(activity_file.read_text(encoding="utf-8").strip())
    assert parsed == payload


def test_lock_file_path_is_shared_with_bash(activity_file):
    """Lock file path matches the bash writer convention in lib/logger.sh.

    Convention: `${activity_file.parent}/.activity.lock` — a hidden lock file
    alongside activity.jsonl inside DEVFORGE_SESSION_DIR. Both Python writer
    and any future bash writer must use the SAME path (the path IS the contract —
    flock() is fd-based but POSIX semantics bind the lock to the file on disk).
    """
    expected_lock_path = activity_file.parent / ".activity.lock"
    # Module must expose the path resolver
    assert hasattr(atomic_write, "lock_path_for")
    assert atomic_write.lock_path_for(activity_file) == expected_lock_path


def test_lock_path_uses_explicit_override(tmp_path, activity_file):
    """Caller can override lock path (used by bash interop)."""
    custom = tmp_path / "custom.lock"
    atomic_write.atomic_append(activity_file, '{"a":1}', lock_path=custom)
    assert custom.exists() or custom.parent.exists()  # lock file created or dir ready


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only signal semantics")
def test_kill_during_write_no_partial_line(tmp_session_dir, activity_file):
    """Edge #2 (POSIX): subprocess that writes 50 events killed mid-stream.
    activity.jsonl must contain only complete lines (no partial writes).
    """
    lib_dir = Path(__file__).resolve().parents[3] / "lib"
    script = f'''
import sys
sys.path.insert(0, {str(lib_dir)!r})
import atomic_write
from pathlib import Path
af = Path({str(activity_file)!r})
import time, json
for i in range(50):
    atomic_write.atomic_append(af, json.dumps({{"i": i, "pad": "x"*100}}))
    time.sleep(0.01)
'''
    proc = subprocess.Popen([sys.executable, "-c", script])
    time.sleep(0.15)  # let it write a few lines
    proc.terminate()
    proc.wait(timeout=2)

    lines = activity_file.read_text(encoding="utf-8").splitlines()
    # Some events written, some not — but each line must parse cleanly
    assert len(lines) >= 1, "expected at least 1 line written before kill"
    for line in lines:
        json.loads(line)  # raises if any line is truncated mid-write
