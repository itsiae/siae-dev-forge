"""Centralized lazy-loading cache for JSON reference files.

Prevents duplicate json.load() calls across modules — on Windows, each
open() triggers a Defender AV scan; the cache eliminates redundant opens.
"""
from __future__ import annotations

import json
from pathlib import Path

REFS = Path(__file__).resolve().parent.parent / "references"

_CACHE: dict[str, dict] = {}


def get(name: str) -> dict:
    """Return parsed JSON for the given filename, loading once and caching."""
    if name not in _CACHE:
        with open(REFS / name, encoding="utf-8") as f:
            _CACHE[name] = json.load(f)
    return _CACHE[name]
