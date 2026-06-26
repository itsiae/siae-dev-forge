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
