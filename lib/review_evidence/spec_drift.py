"""Spec-drift detector — compares design doc claimed files vs git diff actual."""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any, Optional

# E38 mitigation — extended Italian header vocabulary. Real SIAE design docs
# routinely use ``Tabella file`` (file table), ``Allegato`` (attachment),
# ``Output`` (deliverable list). Without these the allowlist matched zero
# headers on production docs and `extract_files_from_design` silently
# returned []. The previous regex stopped at the bare English/Italian
# minimum; extend it to cover the actual corpus.
ALLOWLIST_HEADER_RE = re.compile(
    r"^#+\s*("
    r"file"          # English "files"
    r"|component"
    r"|piano"        # plan
    r"|tabella"      # table (Italian)
    r"|allegato"     # attachment (Italian)
    r"|output"
    r"|test"
    r"|deliverable"
    r"|acceptance"
    r"|criteri"      # criteri di accettazione (Italian)
    r"|modificare"   # "modificare"/"creare" — SIAE plan convention
    r"|creare"
    r"|manifest"     # "implementation manifest" — exhaustive file enumeration post-impl
    r"|renderer"     # "renderer integration" — agent prompt files
    r"|skill"        # "skill on-demand" — commands/forge-*.md
    r"|planning"     # "planning artifacts" — design doc + task spec files
    r"|runtime"      # "componenti runtime" — hook + lib files
    r"|root-level"   # "root-level" — .gitignore, CHANGELOG, etc.
    r"|integration"  # "renderer integration", "test integration"
    r"|fixture"      # "test fixture"
    r")",
    re.IGNORECASE | re.MULTILINE,
)
HEADER_RE = re.compile(r"^#+\s+", re.MULTILINE)
PATH_RE = re.compile(
    r"\b(src|lib|hooks|agents|commands|tests|skills|docs|scripts|tools)/[A-Za-z0-9_./-]+\.[a-z]+\b"
)

# Extensionless paths under dirs known to host scripts (bash hooks, CLI tools).
# Anchored to a small whitelist of "executable host dirs" to keep precision.
# Restricted to lowercase + digits + `_`/`-` filenames so we don't accidentally
# greedy-match prose like "in hooks/review or somewhere".
EXTENSIONLESS_PATH_RE = re.compile(
    r"\b(hooks|scripts|bin)/[a-z][a-z0-9_-]+(?=[\s`)\].,;:]|$)"
)

# Common root-level config / docs files that have no leading directory but are
# legitimate part of any repo manifest. Explicit whitelist (no wildcards) to
# avoid matching arbitrary words inside paragraphs.
ROOT_FILES = (
    ".gitignore", "README.md", "CHANGELOG.md", "LICENSE", "Makefile",
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    "requirements-test.txt", "package.json", "tsconfig.json", ".mcp.json",
    ".shellcheckrc", "install.sh",
)
ROOT_FILE_RE = re.compile(
    r"(?<![\w/])(" + "|".join(re.escape(f) for f in ROOT_FILES) + r")(?![\w/.-])"
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

    Three regex families are combined:
      1. PATH_RE — dir/file.ext under known root dirs
      2. EXTENSIONLESS_PATH_RE — dir/file under hooks/scripts/bin (bash scripts)
      3. ROOT_FILE_RE — known root-level files (.gitignore, README.md, etc.)

    Note: PATH_RE has a capture group (root dir whitelist), so we must use
    finditer + match.group(0) to get the full path, not just the group.
    """
    stripped = _strip_code_fences(content)
    stripped = _strip_blockquotes(stripped)
    section_content = _allowlisted_sections(stripped)
    paths: set[str] = set()
    paths.update(m.group(0) for m in PATH_RE.finditer(section_content))
    paths.update(m.group(0) for m in EXTENSIONLESS_PATH_RE.finditer(section_content))
    paths.update(m.group(0) for m in ROOT_FILE_RE.finditer(section_content))
    return sorted(paths)


def _top_part(p: Path) -> str:
    """Return the first path component, or '.' if the path is empty/root-level."""
    return p.parts[0] if p.parts else "."


def severity(unplanned: list[str], in_plan: list[str] | None = None) -> str:
    if not unplanned:
        return "none"
    n = len(unplanned)
    if n > 5:
        return "high"
    in_plan = in_plan or []
    plan_dirs = {Path(p).parent for p in in_plan}
    unplanned_dirs = {Path(p).parent for p in unplanned}
    new_top_levels = {_top_part(p) for p in unplanned_dirs} - {_top_part(p) for p in plan_dirs}
    if new_top_levels:
        return "medium"
    same_dir = all(d in plan_dirs for d in unplanned_dirs)
    if same_dir and n <= 2:
        return "low"
    if n >= 3:
        return "medium"
    return "low"


def _design_candidates(plans_dir: Path) -> list[Path]:
    """Q11-M1 mitigation — match both legacy and SIAE-canonical layouts.

    SIAE convention (see ``docs/plans/<topic>/design.md``) places one
    ``design.md`` inside each topic subdir. The previous glob
    ``*-design.md`` only matched the *legacy* flat layout
    (``docs/plans/2026-05-12-foo-design.md``), so on production repos
    coverage was effectively 0. We now accept BOTH and merge them, sorted
    by mtime so newer designs win — with a deterministic tiebreaker on the
    filename prefix (E34: iCloud can rewrite mtime when a file is
    re-materialised, so a lexicographic prefix ``YYYY-MM-DD-*`` tiebreaker
    keeps selection stable).
    """
    if not plans_dir.exists():
        return []
    # Legacy: docs/plans/YYYY-MM-DD-foo-design.md
    legacy = list(plans_dir.glob("*-design.md"))
    # SIAE-canonical: docs/plans/<topic>/design.md
    canonical = list(plans_dir.rglob("design.md"))
    # Drop any legacy entries that would also show up via rglob (rglob
    # returns top-level matches too, so dedup by resolved path).
    seen: set[Path] = set()
    merged: list[Path] = []
    for p in legacy + canonical:
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        merged.append(p)
    # Sort: mtime DESC primary, name DESC secondary (lexicographic; for
    # YYYY-MM-DD-* prefixed dirs this keeps the most recent date wins).
    merged.sort(key=lambda p: (p.stat().st_mtime, p.name), reverse=True)
    return merged


def _find_design_doc(repo_root: Path) -> Optional[Path]:
    override = os.environ.get("DEVFORGE_EVIDENCE_DESIGN_DOC")
    if override:
        p = Path(override)
        return p if p.exists() else None
    plans_dir = repo_root / "docs" / "plans"
    candidates = _design_candidates(plans_dir)
    return candidates[0] if candidates else None


def _safe_read_design(path: Path) -> Optional[str]:
    """E36: read design doc tolerating binary / non-UTF8 content.

    A renamed PDF (``.pdf`` → ``.md``) would otherwise raise
    UnicodeDecodeError deep inside ``extract_files_from_design`` and the
    orchestrator would swallow it silently. Better: explicit ``None``
    return so the caller can mark ``drift_severity="unknown"``.
    """
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def _is_planning_artifact(path: str) -> bool:
    """Files under ``docs/plans/`` ARE the plan — they cannot drift FROM it.

    A commit that only adds/updates design docs and task spec files is a
    planning act, not implementation. Treating those paths as "unplanned
    implementation" produced false-positive ``drift_severity:high`` blocks
    on docs-only PRs (e.g. brainstorming + writing-plans output committed
    before any code lands).
    """
    return path.startswith("docs/plans/")


def detect_drift(repo_root: Path, base: str, head: str) -> Optional[dict[str, Any]]:
    design = _find_design_doc(repo_root)
    if design is None:
        return None
    content = _safe_read_design(design)
    if content is None:
        # E36: binary / non-UTF8 design doc — drift cannot be computed but
        # we must not pretend everything is fine. Mark severity unknown.
        return {
            "design_doc_path": str(design),
            "files_in_plan": [],
            "files_changed": [],
            "unplanned_files": [],
            "drift_severity": "unknown",
            "reason": "design_doc_unreadable_or_binary",
        }
    files_in_plan = extract_files_from_design(content)
    try:
        p = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=AMR", "-M", f"{base}...{head}"],
            cwd=repo_root, capture_output=True, text=True, timeout=5, check=False,
        )
        changed = [l.strip() for l in p.stdout.splitlines() if l.strip()]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        changed = []
    # Planning artifacts (docs/plans/*) ARE the plan and cannot drift FROM
    # it. Keep them visible in ``files_changed`` for transparency, but
    # exclude from ``unplanned_files`` / severity. Implementation files
    # outside docs/plans/ still count toward drift.
    impl_changed = [f for f in changed if not _is_planning_artifact(f)]
    unplanned = sorted(set(impl_changed) - set(files_in_plan))
    return {
        "design_doc_path": str(design),
        "files_in_plan": files_in_plan,
        "files_changed": changed,
        "unplanned_files": unplanned,
        "drift_severity": severity(unplanned, in_plan=files_in_plan),
    }
