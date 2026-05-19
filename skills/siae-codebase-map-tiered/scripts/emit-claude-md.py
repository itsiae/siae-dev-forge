#!/usr/bin/env python3
"""Emit tiered CLAUDE.md (L1 root + L2 package + L3 child) from CODEBASE_MAP.md.

Best practice Anthropic (14 May 2026): hierarchical, load-on-demand context.
Thresholds:
  - L1 root  : <= 200 lines (warn if exceeded)
  - L2 pkg   : <= 150 lines
  - L3 child : <= 100 lines, only when subdir has >=10 files AND a distinctive
               local pattern explicitly marked in CODEBASE_MAP.md.

stdlib-only (Python 3.9+).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

L1_MAX_LINES = 200
L2_MAX_LINES = 150
L3_MAX_LINES = 100
L3_MIN_FILES = 10

L1_KEEP_SECTIONS = (
    "Panoramica Sistema",
    "Stack",
    "Convenzioni SIAE Osservate",
    "Gotcha",
)


def parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """Parse leading YAML-ish frontmatter delimited by ``---`` lines.

    Supports flat key:value plus simple ``key:`` followed by ``- item`` lists.
    Returns (frontmatter_dict, body_text).
    """
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + len("\n---\n") :]
    fm: Dict[str, Any] = {}
    current_key: Optional[str] = None
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") or line.startswith("- "):
            if current_key is not None:
                fm.setdefault(current_key, [])
                if isinstance(fm[current_key], list):
                    fm[current_key].append(line.split("-", 1)[1].strip())
            continue
        m = re.match(r"^([A-Za-z0-9_]+)\s*:\s*(.*)$", line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            if value == "":
                current_key = key
                fm[key] = []
            else:
                current_key = key
                fm[key] = value
    return fm, body


def split_sections(body: str) -> Dict[str, str]:
    """Split body by H2 (``## ``) headings. Returns dict header_text -> content."""
    sections: Dict[str, str] = {}
    current_header: Optional[str] = None
    buf: List[str] = []
    for line in body.splitlines():
        if line.startswith("## ") and not line.startswith("### "):
            if current_header is not None:
                sections[current_header] = "\n".join(buf).rstrip() + "\n"
            current_header = line[3:].strip()
            buf = []
        else:
            if current_header is not None:
                buf.append(line)
    if current_header is not None:
        sections[current_header] = "\n".join(buf).rstrip() + "\n"
    return sections


def extract_modules(guida_moduli: str) -> List[Dict[str, Any]]:
    """Extract modules from 'Guida Moduli' section.

    Each module is delimited by an ``### <Name>`` header. Inside we look for
    metadata lines of the form ``**Key:** value`` and optional ``#### <subdir>``
    headers (potential L3 candidates).
    """
    modules: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    current_subdir: Optional[Dict[str, Any]] = None
    for line in guida_moduli.splitlines():
        if line.startswith("### "):
            if current is not None:
                if current_subdir is not None:
                    current["subdirs"].append(current_subdir)
                    current_subdir = None
                modules.append(current)
            current = {
                "name": line[4:].strip(),
                "path": "",
                "stack": "",
                "summary_lines": [],
                "subdirs": [],
            }
            continue
        if current is None:
            continue
        if line.startswith("#### "):
            if current_subdir is not None:
                current["subdirs"].append(current_subdir)
            current_subdir = {
                "name": line[5:].strip(),
                "files": 0,
                "pattern": "",
                "summary_lines": [],
            }
            continue
        target = current_subdir if current_subdir is not None else current
        m = re.match(r"^\*\*([A-Za-z][A-Za-z _]*):\*\*\s*(.+)$", line.rstrip())
        if m:
            key = m.group(1).strip().lower().replace(" ", "_")
            value = m.group(2).strip()
            if key == "files":
                num = re.search(r"\d+", value)
                target[key] = int(num.group(0)) if num else 0
            else:
                target[key] = value
        else:
            target["summary_lines"].append(line)
    if current is not None:
        if current_subdir is not None:
            current["subdirs"].append(current_subdir)
        modules.append(current)
    return modules


def _trim(text: str, max_lines: int) -> str:
    """Truncate text to ``max_lines`` (last line preserves trailing newline)."""
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text if text.endswith("\n") else text + "\n"
    return "\n".join(lines[:max_lines]) + "\n"


def generate_l1(
    frontmatter: Dict[str, Any],
    sections: Dict[str, str],
    modules: List[Dict[str, Any]],
    map_rel_path: str,
) -> str:
    """Build L1 root CLAUDE.md content."""
    parts: List[str] = ["# Project — Root Context\n"]
    stack = frontmatter.get("stack", "")
    if isinstance(stack, list):
        stack_text = ", ".join(stack)
    else:
        stack_text = str(stack)
    if stack_text:
        parts.append(f"> Stack: {stack_text}\n")
    parts.append("")
    for header in L1_KEEP_SECTIONS:
        if header in sections:
            content = sections[header].strip()
            if not content:
                continue
            parts.append(f"## {header}\n")
            parts.append(content)
            parts.append("")
    if len(modules) >= 2:
        parts.append("## Sub-packages\n")
        for mod in modules:
            path = mod.get("path") or mod["name"]
            parts.append(f"- @{path}/CLAUDE.md — {mod['name']}")
        parts.append("")
    parts.append("## Architettura dettagliata\n")
    parts.append(f"See @{map_rel_path} for full codebase map.\n")
    return "\n".join(parts).rstrip() + "\n"


def generate_l2(module: Dict[str, Any]) -> str:
    """Build L2 package CLAUDE.md content."""
    name = module["name"]
    parts: List[str] = [f"# {name} — Local context\n"]
    parts.append("> See @../CLAUDE.md for root context.\n")
    parts.append("")
    parts.append("## Local conventions\n")
    if module.get("stack"):
        parts.append(f"- Stack: {module['stack']}")
    summary = [s for s in module.get("summary_lines", []) if s.strip()]
    if summary:
        for s in summary[:30]:
            parts.append(s)
    parts.append("")
    if module.get("subdirs"):
        parts.append("## Files\n")
        for sd in module["subdirs"]:
            files = sd.get("files", 0)
            parts.append(f"- `{sd['name']}/` — {files} files")
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def generate_l3(module: Dict[str, Any], subdir: Dict[str, Any]) -> str:
    """Build L3 child CLAUDE.md content."""
    parts: List[str] = [f"# {subdir['name']} — Local pattern\n"]
    parts.append("> See @../../CLAUDE.md for root context.")
    parts.append("> See @../CLAUDE.md for package context.\n")
    parts.append("")
    parts.append("## Distinctive pattern\n")
    parts.append(subdir.get("pattern", "(unspecified)"))
    parts.append("")
    summary = [s for s in subdir.get("summary_lines", []) if s.strip()]
    if summary:
        parts.append("## Notes\n")
        for s in summary[:20]:
            parts.append(s)
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def should_emit_l3(subdir: Dict[str, Any]) -> bool:
    files = subdir.get("files", 0)
    pattern = (subdir.get("pattern") or "").strip()
    return files >= L3_MIN_FILES and bool(pattern)


def _line_count(text: str) -> int:
    if not text:
        return 0
    return len(text.splitlines())


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="emit-claude-md.py",
        description="Emit tiered CLAUDE.md (L1+L2+L3) from CODEBASE_MAP.md",
    )
    parser.add_argument("--root", required=True, help="Repository root path")
    parser.add_argument(
        "--map", required=True, help="Path to docs/CODEBASE_MAP.md"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute plan without writing files",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    map_path = Path(args.map).resolve()

    if not map_path.is_file():
        print("CODEBASE_MAP.md not found", file=sys.stderr)
        return 1

    try:
        text = map_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"Failed to read map: {exc}", file=sys.stderr)
        return 1

    frontmatter, body = parse_frontmatter(text)
    sections = split_sections(body)
    modules = extract_modules(sections.get("Guida Moduli", ""))

    warnings: List[str] = []
    files_written: List[str] = []

    try:
        map_rel = map_path.relative_to(root).as_posix()
    except ValueError:
        map_rel = map_path.as_posix()

    l1_text = generate_l1(frontmatter, sections, modules, map_rel)
    l1_lines = _line_count(l1_text)
    if l1_lines > L1_MAX_LINES:
        warnings.append(f"L1 exceeds {L1_MAX_LINES} lines ({l1_lines})")
        l1_text = _trim(l1_text, L1_MAX_LINES)

    l1_path = root / "CLAUDE.md"
    files_written.append("./CLAUDE.md")
    if not args.dry_run:
        l1_path.write_text(l1_text, encoding="utf-8")

    l2_count = 0
    l3_count = 0
    if len(modules) >= 2:
        for mod in modules:
            mod_rel = (mod.get("path") or mod["name"]).strip("/")
            mod_dir = root / mod_rel
            l2_text = generate_l2(mod)
            l2_lines = _line_count(l2_text)
            if l2_lines > L2_MAX_LINES:
                warnings.append(
                    f"L2 {mod_rel} exceeds {L2_MAX_LINES} lines ({l2_lines})"
                )
                l2_text = _trim(l2_text, L2_MAX_LINES)
            l2_count += 1
            files_written.append(f"./{mod_rel}/CLAUDE.md")
            if not args.dry_run:
                mod_dir.mkdir(parents=True, exist_ok=True)
                (mod_dir / "CLAUDE.md").write_text(l2_text, encoding="utf-8")

            for sd in mod.get("subdirs", []):
                if not should_emit_l3(sd):
                    continue
                sd_rel = sd["name"].strip("/")
                sd_dir = mod_dir / sd_rel
                l3_text = generate_l3(mod, sd)
                l3_lines = _line_count(l3_text)
                if l3_lines > L3_MAX_LINES:
                    warnings.append(
                        f"L3 {mod_rel}/{sd_rel} exceeds {L3_MAX_LINES} lines"
                        f" ({l3_lines})"
                    )
                    l3_text = _trim(l3_text, L3_MAX_LINES)
                l3_count += 1
                files_written.append(f"./{mod_rel}/{sd_rel}/CLAUDE.md")
                if not args.dry_run:
                    sd_dir.mkdir(parents=True, exist_ok=True)
                    (sd_dir / "CLAUDE.md").write_text(l3_text, encoding="utf-8")

    result = {
        "files_written": files_written,
        "l1_lines": _line_count(l1_text),
        "l2_count": l2_count,
        "l3_count": l3_count,
        "warnings": warnings,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
