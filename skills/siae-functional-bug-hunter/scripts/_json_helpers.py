#!/usr/bin/env python3
"""_json_helpers.py — pure-Python fallback for environments without jq.

Provides a small subset of jq-like operations used by the other scripts
in this directory. Standard library only.

Usage examples:

    python3 _json_helpers.py get '<json-or-path>' '<dot.path[*].path>'
    python3 _json_helpers.py keys '<json-or-path>'
    python3 _json_helpers.py length '<json-or-path>'
    python3 _json_helpers.py select '<json-or-path>' '<dot.path>' '<value>'

The first argument after the verb may be either inline JSON or a path
to a file (auto-detected: starts with '{' or '[' → inline; otherwise
file).

This module is intentionally minimal — it covers exactly what the rest
of the skill's scripts need. It does NOT aim to be a jq replacement.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


def _load(arg: str) -> Any:
    s = arg.lstrip()
    if s.startswith("{") or s.startswith("["):
        return json.loads(arg)
    p = Path(arg)
    if not p.is_file():
        raise SystemExit(f"input not found and not inline JSON: {arg}")
    return json.loads(p.read_text(encoding="utf-8"))


_PATH_TOKEN = re.compile(r"\.([A-Za-z_][A-Za-z0-9_]*)|\[(\d+|\*)\]")


def _walk(value: Any, path: str) -> list[Any]:
    """Apply a dotted/bracketed path. Returns a list (may contain one
    element for non-wildcard paths or many for wildcard).
    """
    cursors: list[Any] = [value]
    if path == "." or path == "":
        return cursors
    pos = 0
    while pos < len(path):
        m = _PATH_TOKEN.match(path, pos)
        if not m:
            raise SystemExit(f"invalid path token at offset {pos}: {path!r}")
        key, idx = m.group(1), m.group(2)
        next_cursors: list[Any] = []
        for c in cursors:
            if key is not None:
                if not isinstance(c, dict):
                    continue
                if key in c:
                    next_cursors.append(c[key])
            elif idx == "*":
                if isinstance(c, list):
                    next_cursors.extend(c)
                elif isinstance(c, dict):
                    next_cursors.extend(c.values())
            else:
                i = int(idx)
                if isinstance(c, list) and 0 <= i < len(c):
                    next_cursors.append(c[i])
        cursors = next_cursors
        pos = m.end()
    return cursors


def cmd_get(argv: list[str]) -> int:
    if len(argv) != 2:
        raise SystemExit("usage: get <json|path> <dot.path>")
    value, path = _load(argv[0]), argv[1]
    results = _walk(value, path)
    if len(results) == 1:
        json.dump(results[0], sys.stdout, indent=2, sort_keys=True)
    else:
        json.dump(results, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def cmd_keys(argv: list[str]) -> int:
    if len(argv) != 1:
        raise SystemExit("usage: keys <json|path>")
    v = _load(argv[0])
    if isinstance(v, dict):
        json.dump(sorted(v.keys()), sys.stdout)
    elif isinstance(v, list):
        json.dump(list(range(len(v))), sys.stdout)
    else:
        json.dump([], sys.stdout)
    sys.stdout.write("\n")
    return 0


def cmd_length(argv: list[str]) -> int:
    if len(argv) != 1:
        raise SystemExit("usage: length <json|path>")
    v = _load(argv[0])
    if isinstance(v, (list, dict, str)):
        sys.stdout.write(str(len(v)) + "\n")
    else:
        sys.stdout.write("0\n")
    return 0


def cmd_select(argv: list[str]) -> int:
    """select <json|path> <path-to-array> <field>=<value>

    Filters elements of the array at <path-to-array> keeping those whose
    <field> equals <value> (string equality after JSON encoding).
    """
    if len(argv) != 3:
        raise SystemExit("usage: select <json|path> <array-path> <field=value>")
    v = _load(argv[0])
    arr_path = argv[1]
    cond = argv[2]
    if "=" not in cond:
        raise SystemExit("condition must be field=value")
    field, expected = cond.split("=", 1)
    candidates = _walk(v, arr_path)
    out = []
    for c in candidates:
        if isinstance(c, dict) and field in c and str(c[field]) == expected:
            out.append(c)
    json.dump(out, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


COMMANDS = {
    "get": cmd_get,
    "keys": cmd_keys,
    "length": cmd_length,
    "select": cmd_select,
}


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in COMMANDS:
        raise SystemExit(f"usage: {sys.argv[0]} <{ '|'.join(COMMANDS)}> ...")
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
