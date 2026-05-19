#!/usr/bin/env python3
"""Anti-bloat lint for CLAUDE.md files.

Validates a CLAUDE.md (or a directory tree of CLAUDE.md files) against
Anthropic best practices for large-codebase context files. Every rule is
ADVISORY: the script never blocks (always exits 0).

Rules (severity = WARN):
    line_count       file > 200 lines
    parent_overlap   > 70% textual overlap with --parent-context file
    placeholder      contains TBD, TODO, or literal <...>
    missing_import   L2/L3 file without `@<parent>/CLAUDE.md` import line
    empty_sections   `##` header with no content underneath

Usage:
    anti-bloat-lint.py <file_or_dir> [--parent-context <parent_md>]

Output (stdout): JSON object (single file) or JSON array (directory).

Co-located with the `siae-codebase-map-tiered` sub-skill. Pure stdlib so
it can run on any Python 3.9+ without additional install.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

LINE_COUNT_THRESHOLD = 200
PARENT_OVERLAP_THRESHOLD = 0.70

_PLACEHOLDER_RE = re.compile(r"(?:\bTBD\b|\bTODO\b|<\.\.\.>)")
_IMPORT_RE = re.compile(r"^\s*@[^\s]+CLAUDE\.md\s*$", re.MULTILINE)
_HEADER2_RE = re.compile(r"^##\s+.+$", re.MULTILINE)


def _warn(rule: str, msg: str) -> dict[str, str]:
    return {"rule": rule, "severity": "WARN", "msg": msg}


def _check_line_count(lines: list[str]) -> list[dict[str, str]]:
    if len(lines) > LINE_COUNT_THRESHOLD:
        return [
            _warn(
                "line_count",
                f"file has {len(lines)} lines (>{LINE_COUNT_THRESHOLD}); consider splitting via L2/L3",
            )
        ]
    return []


def _check_placeholder(text: str) -> list[dict[str, str]]:
    if _PLACEHOLDER_RE.search(text):
        return [
            _warn(
                "placeholder",
                "file contains TBD/TODO/<...> placeholder; resolve before commit",
            )
        ]
    return []


def _check_missing_import(text: str, has_parent: bool) -> list[dict[str, str]]:
    # Only meaningful when caller flagged a parent context (i.e. file is L2/L3).
    # Detection by --parent-context flag avoids brittle filename heuristics:
    # callers (siae-codebase-map Step 7, hook) know which level they're emitting
    # and pass the parent path explicitly.
    if not has_parent:
        return []
    if _IMPORT_RE.search(text):
        return []
    return [
        _warn(
            "missing_import",
            "L2/L3 CLAUDE.md missing `@<parent>/CLAUDE.md` import line",
        )
    ]


def _check_empty_sections(text: str) -> list[dict[str, str]]:
    # Walk through the file line by line; a `## ` header followed by no non-blank
    # content before EOF or the next header is considered empty.
    lines = text.splitlines()
    empties: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("## "):
            header = line.strip()
            j = i + 1
            has_content = False
            while j < len(lines):
                nxt = lines[j]
                if nxt.startswith("## ") or nxt.startswith("# "):
                    break
                if nxt.strip():
                    has_content = True
                    break
                j += 1
            if not has_content:
                empties.append(header)
            i = j
        else:
            i += 1
    if empties:
        return [
            _warn(
                "empty_sections",
                f"{len(empties)} `##` header(s) without content: {empties[:3]}",
            )
        ]
    return []


def _check_parent_overlap(text: str, parent_text: str) -> list[dict[str, str]]:
    if not parent_text:
        return []
    ratio = SequenceMatcher(a=parent_text, b=text, autojunk=False).ratio()
    if ratio > PARENT_OVERLAP_THRESHOLD:
        return [
            _warn(
                "parent_overlap",
                f"{ratio:.0%} overlap with parent CLAUDE.md (>{int(PARENT_OVERLAP_THRESHOLD * 100)}%); deduplicate",
            )
        ]
    return []


def lint_file(path: Path, parent_text: str = "") -> dict[str, Any]:
    """Return a lint payload for a single CLAUDE.md file."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {
            "file": str(path),
            "lines": 0,
            "warnings": [],
            "errors": [{"rule": "read_error", "msg": str(exc)}],
        }
    lines = text.splitlines()
    warnings: list[dict[str, str]] = []
    warnings.extend(_check_line_count(lines))
    warnings.extend(_check_placeholder(text))
    warnings.extend(_check_missing_import(text, has_parent=bool(parent_text)))
    warnings.extend(_check_empty_sections(text))
    warnings.extend(_check_parent_overlap(text, parent_text))
    return {
        "file": str(path),
        "lines": len(lines),
        "warnings": warnings,
        "errors": [],
    }


def lint_path(target: Path, parent_text: str = "") -> Any:
    """Lint a file or recursively a directory."""
    if target.is_dir():
        payloads = [
            lint_file(p, parent_text)
            for p in sorted(target.rglob("CLAUDE.md"))
        ]
        return payloads
    if target.is_file():
        return lint_file(target, parent_text)
    # Missing target — return empty list so callers can keep going.
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Anti-bloat lint for CLAUDE.md files (advisory).",
    )
    parser.add_argument("target", help="CLAUDE.md file or directory")
    parser.add_argument(
        "--parent-context",
        default=None,
        help="Path to parent CLAUDE.md (enables parent_overlap rule).",
    )
    args = parser.parse_args(argv)

    parent_text = ""
    if args.parent_context:
        parent_path = Path(args.parent_context)
        if parent_path.is_file():
            try:
                parent_text = parent_path.read_text(encoding="utf-8")
            except OSError:
                parent_text = ""

    payload = lint_path(Path(args.target), parent_text)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    # Advisory: always exit 0.
    return 0


if __name__ == "__main__":
    sys.exit(main())
