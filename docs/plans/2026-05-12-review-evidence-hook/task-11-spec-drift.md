# Task 11 — Spec-drift detector + code-fence robustness

**SP:** 1.5 · **AC mappati:** AC #5 · **Dipendenze:** Task 04 · **Wave:** 3

## Goal

Implementare `lib/review_evidence/spec_drift.py`: trova design doc (override env o ls -t), parsa markdown estraendo path validi SOLO da sezioni allowlist e stripping code-fence/inline-code/blockquote, confronta con `git diff` (rename-aware), calcola `drift_severity`.

## File coinvolti

**Creare:**
- `lib/review_evidence/spec_drift.py`
- `tests/test_review_evidence_spec_drift.py`
- `tests/fixtures/review-evidence/design_with_codefences.md`

## Step TDD

### Step 1 — Fixture design_with_codefences.md

```markdown
---
status: approved
---

# Design — Example Feature

## Contesto

Il vecchio `src/legacy/old_module.py` deve essere riscritto.

> Esempio nel quote: `src/quote_only.py` — questo NON va estratto

## File coinvolti

- `src/feature/new_module.py`
- `lib/helper.py`

## Architettura

Pseudocodice esempio (in code-fence — NON va estratto):

```python
import src.fake_path
from lib.fake_module import X
```

## Output stage

- `tests/test_new_module.py`

## Acceptance

- 1 test ok
```

In questa fixture i path "veri" del piano sono: `src/feature/new_module.py`, `lib/helper.py`, `tests/test_new_module.py`. Path da NON estrarre: `src/legacy/old_module.py` (Contesto), `src/quote_only.py` (blockquote), `src/fake_path`, `lib/fake_module` (code-fence).

### Step 2 — Test fallente

```python
"""Tests for spec-drift detector."""
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from lib.review_evidence.spec_drift import (
    extract_files_from_design,
    detect_drift,
    severity,
)

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_extract_files_strips_code_fence_and_quote():
    content = (FIX / "design_with_codefences.md").read_text()
    files = extract_files_from_design(content)
    assert "src/feature/new_module.py" in files
    assert "lib/helper.py" in files
    assert "tests/test_new_module.py" in files
    # Negatives
    assert "src/legacy/old_module.py" not in files  # in Contesto (not allowlist)
    assert "src/quote_only.py" not in files  # blockquote stripped
    assert "src/fake_path" not in files  # code-fence stripped
    assert "lib/fake_module" not in files  # code-fence stripped


def test_severity_none():
    assert severity([]) == "none"


def test_severity_low_same_dir():
    in_plan = ["src/feature/a.py"]
    unplanned = ["src/feature/b.py"]
    assert severity(unplanned, in_plan=in_plan) == "low"


def test_severity_medium_different_dir():
    in_plan = ["src/feature/a.py"]
    unplanned = ["src/other/b.py", "src/other/c.py", "src/yet_another/d.py"]
    assert severity(unplanned, in_plan=in_plan) == "medium"


def test_severity_high_many_files():
    in_plan = ["src/feature/a.py"]
    unplanned = [f"src/other/f{i}.py" for i in range(7)]
    assert severity(unplanned, in_plan=in_plan) == "high"


def test_detect_drift_uses_env_override(tmp_path, monkeypatch):
    design = tmp_path / "design.md"
    design.write_text("## File coinvolti\n- `src/a.py`\n")
    monkeypatch.setenv("DEVFORGE_EVIDENCE_DESIGN_DOC", str(design))

    def fake_run(cmd, **kwargs):
        from subprocess import CompletedProcess
        if cmd[0] == "git" and "diff" in cmd:
            return CompletedProcess(cmd, 0, stdout="src/a.py\nsrc/b.py\n", stderr="")
        return CompletedProcess(cmd, 1, stdout="", stderr="")

    with patch("lib.review_evidence.spec_drift.subprocess.run", side_effect=fake_run):
        result = detect_drift(repo_root=tmp_path, base="main", head="HEAD")

    assert result["design_doc_path"] == str(design)
    assert "src/a.py" in result["files_in_plan"]
    assert "src/b.py" in result["unplanned_files"]
    assert result["drift_severity"] in ("low", "medium")


def test_detect_drift_auto_picks_latest_design(tmp_path, monkeypatch):
    plans_dir = tmp_path / "docs" / "plans"
    plans_dir.mkdir(parents=True)
    old_design = plans_dir / "2026-01-01-old-design.md"
    old_design.write_text("## File coinvolti\n- `src/old.py`\n")
    import time
    time.sleep(0.05)
    new_design = plans_dir / "2026-05-12-new-design.md"
    new_design.write_text("## File coinvolti\n- `src/new.py`\n")

    def fake_run(cmd, **kwargs):
        from subprocess import CompletedProcess
        if "diff" in cmd:
            return CompletedProcess(cmd, 0, stdout="src/new.py\n", stderr="")
        return CompletedProcess(cmd, 1, stdout="", stderr="")

    monkeypatch.delenv("DEVFORGE_EVIDENCE_DESIGN_DOC", raising=False)
    with patch("lib.review_evidence.spec_drift.subprocess.run", side_effect=fake_run):
        result = detect_drift(repo_root=tmp_path, base="main", head="HEAD")

    assert result["design_doc_path"].endswith("2026-05-12-new-design.md")
    assert "src/new.py" in result["files_in_plan"]
    assert result["unplanned_files"] == []
    assert result["drift_severity"] == "none"


def test_detect_drift_returns_none_when_no_design(tmp_path):
    result = detect_drift(repo_root=tmp_path, base="main", head="HEAD")
    assert result is None
```

### Step 3 — Implementa spec_drift.py

```python
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
```

### Step 4 — Esegui test e commit

```bash
pytest tests/test_review_evidence_spec_drift.py -v
# 8 passed atteso

git add lib/review_evidence/spec_drift.py \
        tests/test_review_evidence_spec_drift.py \
        tests/fixtures/review-evidence/design_with_codefences.md
git commit -m "feat(review-evidence): add spec-drift detector with code-fence robustness (#task-11)"
```

## Criteri di accettazione

- [ ] `extract_files_from_design()` strippa code-fence (```), blockquote (>) e applica section allowlist
- [ ] Path estratti solo da root dir whitelist (src/lib/hooks/agents/commands/tests/skills/docs/scripts/tools)
- [ ] `severity()` mappa unplanned count + dir overlap a `none|low|medium|high`
- [ ] `detect_drift()` rispetta env override `DEVFORGE_EVIDENCE_DESIGN_DOC`
- [ ] Fallback: design più recente in `docs/plans/`
- [ ] Nessun design doc → ritorna `None` (non blocca)
- [ ] 8 test passano
