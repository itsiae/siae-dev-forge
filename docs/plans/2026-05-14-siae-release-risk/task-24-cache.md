# Task 24 — cache.py 3-key + idempotency

**Stato:** [PENDING]
**SP:** 2 Human / 1 Augmented
**Dipendenze:** task-04

## Goal

Implementare `lib/release_risk/cache.py` con: (1) cache key 3-component `(branch, diff-hash, baseline-main-sha)`, (2) get/put atomic, (3) idempotency marker per PR comment.

## File coinvolti

- Create: `lib/release_risk/cache.py`

## Step

### Step 1 — Write cache.py

Write `lib/release_risk/cache.py`:
```python
"""Cache 3-key per release-risk scorecard."""
import json
import os
import hashlib
from pathlib import Path
from typing import Optional
from lib.release_risk.schema import ReleaseRiskReport

CACHE_DIR = Path.home() / ".claude" / ".cache" / "release-risk"


def _slug(s: str) -> str:
    return s.replace("/", "_").replace(":", "_")[:80]


def compute_diff_hash(diff_files: list[str], diff_content: str) -> str:
    """sha256(files + content) | head -12."""
    h = hashlib.sha256()
    h.update("\n".join(sorted(diff_files)).encode("utf-8"))
    h.update(b"\n---\n")
    h.update(diff_content.encode("utf-8"))
    return h.hexdigest()[:12]


def cache_key(branch: str, diff_hash: str, baseline_main_sha: str) -> Path:
    """Returns cache file path."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{_slug(branch)}-{diff_hash}-{baseline_main_sha[:8]}.json"


def get(branch: str, diff_hash: str, baseline_main_sha: str) -> Optional[ReleaseRiskReport]:
    """Return cached report or None."""
    p = cache_key(branch, diff_hash, baseline_main_sha)
    if not p.exists():
        return None
    try:
        return ReleaseRiskReport.from_json(p.read_text())
    except Exception:
        return None  # corrupted cache, treat as miss


def put(branch: str, diff_hash: str, baseline_main_sha: str, report: ReleaseRiskReport) -> bool:
    """Atomic save report. Returns True on success."""
    p = cache_key(branch, diff_hash, baseline_main_sha)
    tmp = p.with_suffix(".tmp")
    try:
        tmp.write_text(report.to_json())
        os.replace(tmp, p)
        return True
    except Exception:
        return False


def idempotency_marker(diff_hash: str) -> str:
    """HTML comment marker per PR comment idempotency check."""
    return f"<!-- release-risk:{diff_hash} -->"


def already_posted_in_pr(pr_comments_bodies: list[str], diff_hash: str) -> bool:
    """Check if any comment body contains the idempotency marker."""
    marker = idempotency_marker(diff_hash)
    return any(marker in body for body in pr_comments_bodies)
```

### Step 2 — Verifica

```bash
python3 -c "from lib.release_risk.cache import compute_diff_hash, cache_key, get, put, CACHE_DIR; print(CACHE_DIR)"
```

### Step 3 — Commit

```bash
git add lib/release_risk/cache.py
git commit -m "feat(release-risk): cache 3-key (branch, diff-hash, baseline) + idempotency marker"
```

## Criteri di accettazione

- [ ] 6 funzioni: compute_diff_hash, cache_key, get, put (atomic), idempotency_marker, already_posted_in_pr
- [ ] Cache dir `~/.claude/.cache/release-risk/`
- [ ] Atomic write tramite os.replace
- [ ] Marker `<!-- release-risk:<hash> -->`
- [ ] Commit eseguito
