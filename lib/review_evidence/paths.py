"""Evidence file path resolution across primary and fallback locations.

E42 mitigation — when atomic_write falls back to ~/.claude/review-evidence-fallback/
because iCloud sync blocked the primary path, the hook must look there too on
cache lookup, otherwise every read returns a cache miss and the collector is
re-invoked forever.

A single ``resolve_evidence_path(sha, repo_root)`` helper centralises the search
order so hook bash and python callers agree on the same convention.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

FALLBACK_ROOT = Path.home() / ".claude" / "review-evidence-fallback"


def _repo_hash(repo_root: Path) -> str:
    """Stable short hash for the absolute path of `repo_root`.

    Must match the hash used by ``atomic_io._repo_hash`` so files written
    by the collector are found by the hook on a subsequent lookup.
    """
    return hashlib.sha256(str(repo_root.resolve()).encode()).hexdigest()[:12]


def primary_path(sha: str, repo_root: Path) -> Path:
    """Return the primary evidence path (inside the repo)."""
    return repo_root / ".claude" / "review-evidence" / f"{sha}.json"


def fallback_path(sha: str, repo_root: Path) -> Path:
    """Return the fallback evidence path (outside iCloud, in ~/.claude/)."""
    return FALLBACK_ROOT / _repo_hash(repo_root) / f"{sha}.json"


def resolve_evidence_path(sha: str, repo_root: Path) -> Optional[Path]:
    """Return the path of the evidence file for ``sha``, or None if not found.

    Search order:
      1. Primary: ``<repo>/.claude/review-evidence/<sha>.json``
      2. Fallback: ``~/.claude/review-evidence-fallback/<repo_hash>/<sha>.json``

    An empty file (size==0) counts as not-found — this catches the iCloud
    ``.icloud`` placeholder edge case (E48) where the original is missing
    and only an empty stub remains.
    """
    primary = primary_path(sha, repo_root)
    if primary.exists() and primary.stat().st_size > 0:
        return primary
    fallback = fallback_path(sha, repo_root)
    if fallback.exists() and fallback.stat().st_size > 0:
        return fallback
    return None


def icloud_placeholder_for(sha: str, repo_root: Path) -> Path:
    """Return where the iCloud ``.icloud`` placeholder would live for ``sha``.

    iCloud renames offloaded files from ``foo.json`` to ``.foo.json.icloud``
    (note: dotfile + trailing ``.icloud`` suffix). The hook checks for this
    marker explicitly to know when a recompute is required (E48).
    """
    return repo_root / ".claude" / "review-evidence" / f".{sha}.json.icloud"
