"""Spec-drift detector — compares design doc claimed files vs git diff actual."""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

ALLOWLIST_HEADER_RE = re.compile(
    r"^#+\s*(file|component|output|acceptance|test|deliverable|piano)",
    re.IGNORECASE | re.MULTILINE,
)
HEADER_RE = re.compile(r"^#+\s+", re.MULTILINE)
PATH_RE = re.compile(
    r"\b(src|lib|hooks|agents|commands|tests|skills|docs|scripts|tools)/[A-Za-z0-9_./-]+\.[a-z]+\b"
)


def _strip_code_fences(text: str) -> str:
    # Triple backtick or tilde fences
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"~~~.*?~~~", "", text, flags=re.DOTALL)
    # Inline code (single backtick) — we KEEP single backtick paths in bullet
    # lists, those are legitimate claims. Stripping inline globally would lose
    # actual paths. Instead strip ONLY inline code in blockquotes (next pass).
    return text


def _strip_blockquotes(text: str) -> str:
    # Remove any line starting with `>` (after optional whitespace)
    return re.sub(r"^\s*>.*$", "", text, flags=re.MULTILINE)


def _allowlisted_sections(text: str) -> str:
    """Return only content under headers matching the allowlist regex."""
    # Find all headers + their positions
    matches = list(HEADER_RE.finditer(text))
    if not matches:
        return ""
    keep = []
    for i, m in enumerate(matches):
        header_line_start = m.start()
        line_end = text.find("\n", header_line_start)
        header_line = text[header_line_start: line_end if line_end != -1 else len(text)]
        if not ALLOWLIST_HEADER_RE.match(header_line):
            continue
        # Section spans up to next header (any level)
        next_start = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        keep.append(text[header_line_start: next_start])
    return "\n".join(keep)


def extract_files_from_design(content: str) -> list[str]:
    """Extract file paths from design doc, restricted to allowlist sections,
    with code-fence and blockquote stripping.

    Note: PATH_RE has a capture group (root dir whitelist), so we must use
    finditer + match.group(0) to get the full path, not just the group.
    """
    stripped = _strip_code_fences(content)
    stripped = _strip_blockquotes(stripped)
    section_content = _allowlisted_sections(stripped)
    return sorted({m.group(0) for m in PATH_RE.finditer(section_content)})


def severity(unplanned: list[str], in_plan: list[str] | None = None) -> str:
    if not unplanned:
        return "none"
    n = len(unplanned)
    if n > 5:
        return "high"
    in_plan = in_plan or []
    plan_dirs = {Path(p).parent for p in in_plan}
    unplanned_dirs = {Path(p).parent for p in unplanned}
    new_top_levels = {p.parts[0] for p in unplanned_dirs} - {p.parts[0] for p in plan_dirs}
    if new_top_levels:
        return "medium"
    same_dir = all(d in plan_dirs for d in unplanned_dirs)
    if same_dir and n <= 2:
        return "low"
    if n >= 3:
        return "medium"
    return "low"


def _find_design_doc(repo_root: Path) -> Path | None:
    override = os.environ.get("DEVFORGE_EVIDENCE_DESIGN_DOC")
    if override:
        p = Path(override)
        return p if p.exists() else None
    plans_dir = repo_root / "docs" / "plans"
    if not plans_dir.exists():
        return None
    candidates = sorted(plans_dir.glob("*-design.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def detect_drift(repo_root: Path, base: str, head: str) -> dict[str, Any] | None:
    design = _find_design_doc(repo_root)
    if design is None:
        return None
    files_in_plan = extract_files_from_design(design.read_text())
    try:
        p = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=AMR", "-M", f"{base}...{head}"],
            cwd=repo_root, capture_output=True, text=True, timeout=5, check=False,
        )
        changed = [l.strip() for l in p.stdout.splitlines() if l.strip()]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        changed = []
    unplanned = sorted(set(changed) - set(files_in_plan))
    return {
        "design_doc_path": str(design),
        "files_in_plan": files_in_plan,
        "files_changed": changed,
        "unplanned_files": unplanned,
        "drift_severity": severity(unplanned, in_plan=files_in_plan),
    }
