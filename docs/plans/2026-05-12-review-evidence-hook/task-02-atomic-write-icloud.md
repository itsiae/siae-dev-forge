# Task 02 — Atomic write con iCloud retry + fallback

**SP:** 1.0 · **AC mappati:** R3 mitigation · **Dipendenze:** nessuna · **Wave:** 1

## Goal

Creare `lib/review_evidence/atomic_io.py` con funzione `write_evidence_atomic(path, content)` che:
1. Usa il pattern atomic write esistente (`lib/atomic_write.py`)
2. Retry 3× con backoff esponenziale su `OSError` con errno `EBUSY` o `ENOTEMPTY` (sync iCloud)
3. Fallback fuori iCloud se tutti i retry falliscono (`~/.claude/review-evidence-fallback/<repo_hash>/<sha>.json`)
4. Emit warning visibile (return tuple `(success, used_fallback, reason)`)

## File coinvolti

**Creare:**
- `lib/review_evidence/atomic_io.py`
- `tests/test_review_evidence_atomic_io.py`

**Pattern di riferimento (non riuso diretto):**
- `lib/atomic_write.py` — espone `atomic_append(activity_file, line, lock_path)` per JSONL
  con lock + fsync. La nostra API è DIVERSA (`write_evidence_atomic(target, content, sha, repo_root)`
  per file completo non append) ma seguiamo lo stesso principio (atomic rename + lock-less,
  visto che evidence per-SHA è single-writer)

## Step TDD

### Step 1 — Verifica lib/atomic_write.py esistente (solo per pattern)

```bash
head -30 lib/atomic_write.py
```

Conferma: l'API esistente è `atomic_append(activity_file, line, lock_path)` per JSONL append.
La nostra API per evidence single-file è diversa (full-file write con retry iCloud).
Nessun riuso diretto — solo pattern (atomic rename via tempfile + os.replace).

### Step 2 — Scrivi test fallente

`tests/test_review_evidence_atomic_io.py`:

```python
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
```

### Step 3 — Esegui test (fallisce)

```bash
pytest tests/test_review_evidence_atomic_io.py -v
```

**Output atteso:** `ModuleNotFoundError: lib.review_evidence.atomic_io`.

### Step 4 — Implementa

`lib/review_evidence/atomic_io.py`:

```python
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


def _is_busy_error(exc: OSError) -> bool:
    return exc.errno in {errno.EBUSY, errno.ENOTEMPTY, errno.EAGAIN}


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
    fail. Non-busy errors propagate as exceptions.
    """
    target = Path(target)
    last_err: Optional[OSError] = None

    for attempt in range(MAX_RETRIES):
        try:
            _atomic_write_once(target, content)
            return True, False, None
        except OSError as e:
            if not _is_busy_error(e):
                raise
            last_err = e
            time.sleep(BACKOFF_BASE_SEC * (2 ** attempt))

    # All retries exhausted — fallback
    repo_root = repo_root or Path.cwd()
    fallback_dir = FALLBACK_ROOT / _repo_hash(repo_root)
    fallback_dir.mkdir(parents=True, exist_ok=True)
    fallback_path = fallback_dir / f"{sha or target.stem}.json"
    _atomic_write_once(fallback_path, content)
    reason = f"target write failed after {MAX_RETRIES} retries (EBUSY/ENOTEMPTY) — likely iCloud sync"
    return True, True, reason
```

### Step 5 — Esegui test (passa)

```bash
pytest tests/test_review_evidence_atomic_io.py -v
```

**Output atteso:** `4 passed`.

### Step 6 — Commit

```bash
git add lib/review_evidence/atomic_io.py tests/test_review_evidence_atomic_io.py
git commit -m "feat(review-evidence): add atomic write with iCloud retry + fallback (#task-02)"
```

## Criteri di accettazione

- [ ] `lib/review_evidence/atomic_io.py` definisce `write_evidence_atomic` con signature `(target, content, sha=None, repo_root=None) -> (success, used_fallback, reason)`
- [ ] Retry 3× su EBUSY/ENOTEMPTY/EAGAIN con backoff esponenziale
- [ ] Fallback in `~/.claude/review-evidence-fallback/<repo_hash>/<sha>.json` se retry esauriti
- [ ] Errori non-busy propagano come eccezione
- [ ] 4 test passano
