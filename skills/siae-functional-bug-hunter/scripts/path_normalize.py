#!/usr/bin/env python3
"""path_normalize.py — canonical path form for cross-stack bridge matching.

Implements the Path Normalization Rules section of
`references/cross_stack_bridges.md`. The rules are:

- Strip query string (everything after `?`).
- Replace Express/Koa `:name` segments with `{name}`.
- Replace Flask `<name>` and `<name:converter>` segments with `{name}`.
- Replace FastAPI/OAS `{name:type}` segments with `{name}` (strip type).

Stdlib-only.

Used by
-------
- `scripts/generate_payloads.py` (when building per-entry-point payloads).
- Future dependency-closure resolver (Phase 2).

Tests
-----
See `tests/test_path_normalization.py`.
"""
from __future__ import annotations

import re

_EXPRESS_PARAM = re.compile(r":([A-Za-z_][A-Za-z0-9_]*)")
# Flask: keep the FIRST identifier inside angle brackets; discard any type
# annotation that follows a colon. Matches per the table in
# references/cross_stack_bridges.md ("<id:int>" -> "{id}").
_FLASK_PARAM = re.compile(r"<\s*([A-Za-z_][A-Za-z0-9_]*)(?:\s*:\s*[^>]+)?\s*>")
# FastAPI typed: {name:type} -> {name}; the type after the colon is stripped.
_FASTAPI_TYPED = re.compile(r"\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*[^}]+\s*\}")


def normalize_path(path: str) -> str:
    """Normalize a stack-specific path template to canonical form.

    Returns the canonical form `/v1/users/{id}` for any of the documented
    input shapes. Inputs that contain neither parameters nor query string
    are returned unchanged.
    """
    if not isinstance(path, str):
        raise TypeError(f"path must be str, got {type(path).__name__}")

    # Strip query string from the bridge key.
    qmark = path.find("?")
    if qmark >= 0:
        path = path[:qmark]

    # Flask must run BEFORE FastAPI-typed because Flask may also use
    # `<name:type>` shape (e.g. `<id:int>`). The FastAPI-typed regex
    # only matches curly braces so they do not conflict, but ordering
    # is documented as a contract.
    path = _FLASK_PARAM.sub(r"{\1}", path)
    path = _FASTAPI_TYPED.sub(r"{\1}", path)
    path = _EXPRESS_PARAM.sub(r"{\1}", path)
    return path


if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        sys.stdout.write(normalize_path(arg) + "\n")
