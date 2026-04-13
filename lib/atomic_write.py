"""Cross-OS atomic append for activity.jsonl with shared lock + fsync.

Purpose:
    Single source of truth for appending JSONL lines to DevForge activity logs.
    Replaces the raw `printf >> file` in lib/logger.sh (which had no lock and
    no fsync, causing the 6,612 parse errors observed in S3 pre-PR #187).

Lock contract:
    The lock file path is `${activity_file.parent}/.activity.lock` by default.
    Any writer (Python or future bash caller of this module) must use the same
    path for mutual exclusion. On POSIX, both `fcntl.flock` and `flock(1)` bind
    to the file on disk — compatible.

Windows behavior:
    `msvcrt.locking` on the same lock file path. Bash on Windows runs via Git
    Bash (POSIX-compat layer); if bash ever writes directly (currently it does
    not — bash delegates to this module via `python3 atomic_write.py append`),
    callers must route through Python to share the lock correctly.

Durability:
    Each append flushes Python buffers + calls `os.fsync(fd)` before releasing
    the lock. Guarantees the data is on disk (modulo SSD firmware) even on
    immediate kernel panic.

CLI usage (called by lib/logger.sh):
    python3 lib/atomic_write.py append <file> <line>
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

if sys.platform == "win32":  # pragma: no cover — exercised by windows-smoke CI job
    import msvcrt

    def _acquire(lockfd) -> None:
        msvcrt.locking(lockfd.fileno(), msvcrt.LK_LOCK, 1)

    def _release(lockfd) -> None:
        try:
            msvcrt.locking(lockfd.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
else:
    import fcntl

    def _acquire(lockfd) -> None:
        fcntl.flock(lockfd.fileno(), fcntl.LOCK_EX)

    def _release(lockfd) -> None:
        try:
            fcntl.flock(lockfd.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass


def _rotate_if_needed(activity_path: Path, rotate_at_bytes: int) -> None:
    """Rotate activity_path to archived if size > threshold. MUST hold lock.

    Fix post-PR-A review: rotation OUTSIDE the lock creates race where a
    concurrent writer can write into a file about to be renamed. Keeping
    rotation inside makes rename atomic w.r.t. other writers.
    """
    if rotate_at_bytes <= 0:
        return
    try:
        size = activity_path.stat().st_size
    except FileNotFoundError:
        return
    if size <= rotate_at_bytes:
        return
    import time
    ts = int(time.time())
    archived = activity_path.parent / f"{activity_path.stem}-{ts}.archived.jsonl"
    if archived.exists():
        for i in range(1, 1000):
            candidate = activity_path.parent / f"{activity_path.stem}-{ts}-{i}.archived.jsonl"
            if not candidate.exists():
                archived = candidate
                break
    os.rename(str(activity_path), str(archived))


def lock_path_for(activity_file) -> Path:
    """Resolve the canonical lock file path for an activity.jsonl.

    Convention: a hidden `.activity.lock` file placed alongside activity.jsonl
    in DEVFORGE_SESSION_DIR. This is the single lock path shared across all
    writers.
    """
    return Path(activity_file).parent / ".activity.lock"


def atomic_append(activity_file, line: str, lock_path=None,
                  rotate_at_bytes: int = 0) -> None:
    """Append `line` to `activity_file` under exclusive lock + fsync.

    Args:
        activity_file: Path-like to the JSONL file to append to.
        line: The line to append. A trailing newline is added if missing.
            Already-terminated lines are preserved (no double \\n).
        lock_path: Override for the lock file path. Defaults to
            `lock_path_for(activity_file)`.

    Raises:
        OSError: if file cannot be opened, written, or fsync fails.
    """
    activity_path = Path(activity_file)
    lp = Path(lock_path) if lock_path is not None else lock_path_for(activity_path)

    lp.parent.mkdir(parents=True, exist_ok=True)

    if not line.endswith("\n"):
        line = line + "\n"

    with open(lp, "a") as lockfd:
        _acquire(lockfd)
        try:
            _rotate_if_needed(activity_path, rotate_at_bytes)
            with open(activity_path, "a", encoding="utf-8") as af:
                af.write(line)
                af.flush()
                os.fsync(af.fileno())
        finally:
            _release(lockfd)


def _main(argv) -> int:
    """CLI: `python3 atomic_write.py append <file> <line> [rotate_at_bytes]`."""
    if len(argv) < 4 or argv[1] != "append":
        print("usage: atomic_write.py append <file> <line> [rotate_at_bytes]",
              file=sys.stderr)
        return 2
    file_arg = argv[2]
    line_arg = argv[3]
    rotate_at = 0
    if len(argv) >= 5 and argv[4].isdigit():
        rotate_at = int(argv[4])
    try:
        atomic_append(file_arg, line_arg, rotate_at_bytes=rotate_at)
    except OSError as e:
        print(f"atomic_write error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
