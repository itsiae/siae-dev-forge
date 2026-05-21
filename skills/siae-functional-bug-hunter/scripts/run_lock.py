#!/usr/bin/env python3
"""run_lock.py — acquire / release .fbh/run.lock to prevent parallel runs.

Contract (per SKILL.md "Pipeline overview" lines ~102-104)
----------------------------------------------------------
- A run against `<output_dir>` is locked through `<output_dir>/.fbh/run.lock`.
- Parallel runs against the same `output_dir` are refused.
- Parallel runs against distinct `output_dir` are safe.

Usage
-----
    python3 run_lock.py acquire <output_dir> [--pid PID]
        exit 0 if acquired, 1 if locked by a live process, 2 on IO error.
    python3 run_lock.py release <output_dir>
        exit 0 if removed (or absent), 2 on IO error.

The lock file content is JSON:
    {
      "pid": <pid>,
      "started_at": "<ISO8601>",
      "hostname": "<host>"
    }

If the PID in an existing lock file is not running on this host, the lock
is treated as **stale**: it is removed automatically, a warning is
written to stderr, and acquisition proceeds.

Why not rely on fcntl/msvcrt across CLI invocations?
----------------------------------------------------
fcntl.flock / msvcrt.locking are tied to the **lifetime of the holding
process**. When this script exits after `acquire`, the OS-level lock
dies with it. The contract requires the lock to outlive the script
invocation (the orchestrator calls `acquire` early and releases hours
later). Therefore the primary exclusion mechanism is the **JSON file +
PID-liveness probe**, not the OS-level lock.

For in-process use, callers can additionally use an exclusive file
handle via fcntl/msvcrt — but the CLI form does not, on purpose.

Default PID written to the lock file is `os.getppid()` — the parent
shell of this script — which is the orchestrator process and stays
alive across the run. Pass `--pid` to override.

Cross-platform PID probe
------------------------
- POSIX: `os.kill(pid, 0)`.
- Windows: same; Python translates appropriately.

Exit codes
----------
0  acquire: lock obtained. release: lock removed (or was not present).
1  acquire: another process holds the lock (PID is live on this host).
2  argv / IO error.

Python 3.9+ standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _pid_alive(pid: int) -> bool:
    """Best-effort: True if a process with `pid` exists on this host."""
    if pid is None or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we lack rights to signal it.
        return True
    except OSError:
        return False
    return True


def _read_lock_meta(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _is_stale(meta: dict | None) -> bool:
    if not meta:
        # Empty / unreadable file — treat as stale.
        return True
    pid = meta.get("pid")
    host = meta.get("hostname")
    if not isinstance(pid, int):
        return True
    if host and host != socket.gethostname():
        # Different machine: we cannot probe; do NOT consider stale.
        return False
    return not _pid_alive(pid)


def acquire(output_dir: Path, owner_pid: int) -> int:
    fbh_dir = output_dir / ".fbh"
    try:
        fbh_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        sys.stderr.write(f"[run_lock] cannot create {fbh_dir}: {e}\n")
        return 2
    lock_path = fbh_dir / "run.lock"

    # If the lock file exists, check whether its owner is alive.
    if lock_path.exists():
        meta = _read_lock_meta(lock_path)
        if _is_stale(meta):
            sys.stderr.write(
                f"[run_lock] WARN stale lock at {lock_path} "
                f"(meta={meta!r}) — removing\n"
            )
            try:
                lock_path.unlink()
            except OSError as e:
                sys.stderr.write(f"[run_lock] cannot remove stale lock: {e}\n")
                return 2
        else:
            sys.stderr.write(
                f"[run_lock] lock held by pid={meta.get('pid') if meta else '?'} "
                f"on {meta.get('hostname') if meta else '?'} at {lock_path}\n"
            )
            return 1

    meta = {
        "pid": owner_pid,
        "started_at": _now_iso(),
        "hostname": socket.gethostname(),
    }
    try:
        lock_path.write_text(
            json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8"
        )
    except OSError as e:
        sys.stderr.write(f"[run_lock] cannot write {lock_path}: {e}\n")
        return 2
    sys.stdout.write(str(lock_path.resolve()) + "\n")
    return 0


def release(output_dir: Path) -> int:
    lock_path = output_dir / ".fbh" / "run.lock"
    if not lock_path.exists():
        return 0
    try:
        lock_path.unlink()
    except OSError as e:
        sys.stderr.write(f"[run_lock] cannot remove lock: {e}\n")
        return 2
    return 0


# Runtime mode dispatcher (Phase 0 → emit Action for STOP events).
# Single source of truth: references/runtime_modes.md.
class DispatchError(ValueError):
    """Raised when dispatch receives an unknown mode or event."""


_MODES = ("interactive", "strict", "report-only")
_EVENTS = (
    "STOP_DEPENDENCY_CLOSURE",
    "STOP_FINDING_THRESHOLD",
    "STOP_WALLCLOCK_EXCEEDED",
    "STOP_DIRTY_WORKING_TREE",
    "STOP_AMBIGUOUS_SCOPE",
)
_DISPATCH_TABLE = {
    "interactive": {ev: "PAUSE" for ev in _EVENTS},
    "strict": {ev: "CONTINUE" for ev in _EVENTS},
    "report-only": {
        "STOP_DEPENDENCY_CLOSURE": "DEGRADE",
        "STOP_FINDING_THRESHOLD": "CONTINUE",
        "STOP_WALLCLOCK_EXCEEDED": "CONTINUE",
        "STOP_DIRTY_WORKING_TREE": "CONTINUE",
        "STOP_AMBIGUOUS_SCOPE": "CONTINUE",
    },
}


def dispatch(mode: str, event: str) -> str:
    if mode not in _DISPATCH_TABLE:
        raise DispatchError(
            f"unknown mode '{mode}' (expected one of {_MODES})"
        )
    if event not in _EVENTS:
        raise DispatchError(
            f"unknown event '{event}' (expected one of {_EVENTS})"
        )
    return _DISPATCH_TABLE[mode][event]


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="action", required=True)

    for action in ("acquire", "release"):
        sp = sub.add_parser(action)
        sp.add_argument("output_dir", type=Path)
        if action == "acquire":
            sp.add_argument(
                "--pid",
                type=int,
                default=os.getppid(),
                help="PID to record as lock owner (default: parent shell pid).",
            )

    sp_dispatch = sub.add_parser(
        "dispatch",
        help="Resolve (mode, event) -> Action per runtime_modes.md matrix.",
    )
    sp_dispatch.add_argument("mode", choices=list(_MODES))
    sp_dispatch.add_argument("event", choices=list(_EVENTS))

    args = p.parse_args(argv)

    if args.action == "acquire":
        return acquire(args.output_dir, args.pid)
    if args.action == "release":
        return release(args.output_dir)
    if args.action == "dispatch":
        try:
            action = dispatch(args.mode, args.event)
        except DispatchError as e:
            sys.stderr.write(f"[run_lock] {e}\n")
            return 2
        sys.stdout.write(action + "\n")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
