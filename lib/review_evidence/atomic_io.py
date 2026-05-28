"""Atomic write with iCloud-safe retry + fallback for evidence files."""
from __future__ import annotations

import errno
import hashlib
import os
import tempfile
import time
from pathlib import Path
from typing import Optional

MAX_RETRIES = 3
BACKOFF_BASE_SEC = 0.1
FALLBACK_ROOT = Path.home() / ".claude" / "review-evidence-fallback"


class DiskFullError(OSError):
    """Raised when ENOSPC is hit and even the fallback path is full.

    E41 mitigation — the hook catches this and emits decision:block on a
    blocking trigger (gh pr create/edit). Without an explicit type, the
    hook saw a generic OSError and treated it as advisory (fail-open).
    """


def _is_busy_error(exc: OSError) -> bool:
    return exc.errno in {errno.EBUSY, errno.ENOTEMPTY, errno.EAGAIN}


def _is_disk_full(exc: OSError) -> bool:
    """ENOSPC = no space left; EDQUOT = quota exceeded (NFS / iCloud)."""
    return exc.errno in {errno.ENOSPC, getattr(errno, "EDQUOT", -1)}


def _repo_hash(repo_root: Path) -> str:
    return hashlib.sha256(str(repo_root.resolve()).encode()).hexdigest()[:12]


def _atomic_write_once(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    ) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    os.replace(tmp_path, path)


def write_evidence_atomic(
    target: Path,
    content: str,
    sha: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> tuple[bool, bool, Optional[str]]:
    """Write `content` to `target` atomically. Returns (success, used_fallback, reason).

    Retries 3x on EBUSY/ENOTEMPTY (iCloud sync). Falls back to
    ~/.claude/review-evidence-fallback/<repo_hash>/<sha>.json if all retries
    fail. On ENOSPC (disk full) raises ``DiskFullError`` so the caller can
    fail-CLOSED on blocking triggers (E41). Other unexpected OSError
    propagate.
    """
    target = Path(target)

    for attempt in range(MAX_RETRIES):
        try:
            _atomic_write_once(target, content)
            return True, False, None
        except OSError as e:
            if _is_disk_full(e):
                # E41: explicit, don't keep retrying — disk is full.
                raise DiskFullError(e.errno, f"disk full / quota exceeded writing {target}") from e
            if not _is_busy_error(e):
                raise
            time.sleep(BACKOFF_BASE_SEC * (2 ** attempt))

    # All retries exhausted — fallback (outside iCloud, direct write since no
    # sync contention is expected on the fallback location)
    repo_root = repo_root or Path.cwd()
    fallback_dir = FALLBACK_ROOT / _repo_hash(repo_root)
    try:
        fallback_dir.mkdir(parents=True, exist_ok=True)
        fallback_path = fallback_dir / f"{sha or target.stem}.json"
        fallback_path.write_text(content, encoding="utf-8")
    except OSError as e:
        if _is_disk_full(e):
            raise DiskFullError(e.errno, f"disk full writing fallback {fallback_dir}") from e
        raise
    reason = f"target write failed after {MAX_RETRIES} retries (EBUSY/ENOTEMPTY) — likely iCloud sync"
    return True, True, reason
