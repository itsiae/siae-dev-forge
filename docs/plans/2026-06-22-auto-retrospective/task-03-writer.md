# Task 03 — `lib/retro/writer.py` (marker-section dry-run/apply)

**Goal:** Port della logica marker-section di headroom `learn/writer.py`: merge idempotente dentro `<!-- devforge:retro:start/end -->`, replace-by-heading + carry-forward delle sezioni non ri-emesse, dry-run di default. Sezioni umane (fuori dai marker) mai toccate.

**Dipende da:** Task 01. **File coinvolti:** crea `lib/retro/writer.py`, `tests/test_retro_writer.py`.

## Step TDD bite-sized

### Step 1 — Test fallente
Crea `tests/test_retro_writer.py`:
```python
from lib.retro.writer import Lesson, merge_into_text, write_lessons


def L(section, content):
    return Lesson(section=section, content=content)


def test_append_block_when_absent():
    out = merge_into_text("# Mio CLAUDE\n\nregola umana.\n", [L("Bash", "- usa path assoluti")])
    assert "regola umana." in out                      # sezione umana intatta
    assert "<!-- devforge:retro:start -->" in out
    assert "### Bash" in out and "path assoluti" in out


def test_replace_by_heading_idempotent():
    base = merge_into_text("base\n", [L("Bash", "- v1")])
    once = merge_into_text(base, [L("Bash", "- v2")])
    twice = merge_into_text(once, [L("Bash", "- v2")])
    assert once.count("### Bash") == 1                 # replace, non duplica
    assert "- v2" in once and "- v1" not in once
    assert once == twice                                # idempotente


def test_carry_forward_untouched_section():
    base = merge_into_text("base\n", [L("Bash", "- b"), L("Read", "- r")])
    upd = merge_into_text(base, [L("Bash", "- b2")])   # solo Bash ri-emesso
    assert "### Read" in upd and "- r" in upd           # Read portato avanti
    assert "- b2" in upd


def test_dry_run_no_write(tmp_path):
    f = tmp_path / "CLAUDE.md"
    f.write_text("orig\n", encoding="utf-8")
    res = write_lessons(f, [L("Bash", "- x")], apply=False)
    assert f.read_text(encoding="utf-8") == "orig\n"    # NON scritto
    assert "### Bash" in res                             # ma ritorna il preview


def test_apply_writes(tmp_path):
    f = tmp_path / "CLAUDE.md"
    f.write_text("orig\n", encoding="utf-8")
    write_lessons(f, [L("Bash", "- x")], apply=True)
    assert "### Bash" in f.read_text(encoding="utf-8")   # scritto
```

### Step 2 — Verifica fallimento
Run: `python3 -m pytest tests/test_retro_writer.py -q`
Output atteso: `FAILED` — `ModuleNotFoundError: No module named 'lib.retro.writer'`.

### Step 3 — Implementa
Crea `lib/retro/writer.py` (port da headroom `learn/writer.py`, Apache-2.0 — vedi NOTICE):
```python
"""Writer marker-section idempotente — port da headroom learn/writer.py (Apache 2.0)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_MARKER_START = "<!-- devforge:retro:start -->"
_MARKER_END = "<!-- devforge:retro:end -->"
_MARKER_PATTERN = re.compile(
    re.escape(_MARKER_START) + r".*?" + re.escape(_MARKER_END), re.S
)


@dataclass
class Lesson:
    section: str          # heading (es. nome tool o tema)
    content: str          # markdown body (bullet list)


def _build_block(lessons: list[Lesson]) -> str:
    parts = [_MARKER_START, "", "## Lezioni auto-retrospective (DevForge)", ""]
    for le in lessons:
        parts.append(f"### {le.section}")
        parts.append(le.content.rstrip())
        parts.append("")
    parts.append(_MARKER_END)
    return "\n".join(parts)


def _parse_prior(text: str) -> list[Lesson]:
    m = _MARKER_PATTERN.search(text)
    if not m:
        return []
    inner = m.group(0)[len(_MARKER_START):-len(_MARKER_END)]
    out: list[Lesson] = []
    for part in re.split(r"\n### ", "\n" + inner)[1:]:
        heading, _, body = part.partition("\n")
        heading = heading.strip()
        if heading:
            out.append(Lesson(section=heading, content=body.rstrip()))
    return out


def merge_into_text(existing: str, new_lessons: list[Lesson]) -> str:
    """Merge: le sezioni nuove vincono per heading; le vecchie non ri-emesse sono portate avanti."""
    prior = _parse_prior(existing)
    new_sections = {le.section for le in new_lessons}
    carried = [p for p in prior if p.section not in new_sections]
    block = _build_block(list(new_lessons) + carried)
    if _MARKER_START in existing:
        return _MARKER_PATTERN.sub(lambda _m: block, existing)
    return existing.rstrip() + "\n\n" + block + "\n"


def write_lessons(path: Path, new_lessons: list[Lesson], apply: bool = False) -> str:
    """Ritorna il contenuto finale (preview). Scrive su disco solo se apply=True."""
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    final = merge_into_text(existing, new_lessons)
    if apply:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(final, encoding="utf-8")
    return final
```

### Step 4 — Verifica passa
Run: `python3 -m pytest tests/test_retro_writer.py -q`
Output atteso: `5 passed`.

### Step 5 — Commit
`git add lib/retro/writer.py tests/test_retro_writer.py && git commit -m "feat(retro): writer marker-section dry-run/apply (port headroom writer.py)"`

## Criteri di accettazione
- [ ] Blocco appeso se assente; sezioni umane fuori dai marker mai toccate.
- [ ] Replace-by-heading: re-merge stessa sezione non duplica; merge idempotente (`once == twice`).
- [ ] Carry-forward: sezione non ri-emessa resta nel blocco.
- [ ] `apply=False` non scrive (file invariato) ma ritorna il preview; `apply=True` scrive.
- [ ] `tests/test_retro_writer.py` passa (5 test).
