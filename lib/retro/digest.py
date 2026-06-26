"""Parser transcript Claude Code + digest compresso — pattern headroom analyzer.py (Apache 2.0)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from lib.retro.classifier import classify_error, is_error_content


@dataclass
class ToolEvent:
    tool: str
    is_error: bool
    category: str          # "UNKNOWN" se non-errore
    preview: str           # primi ~200 char dell'output


def _content_to_text(content) -> str:
    """content può essere str o lista di blocchi {type:text,text:...}."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


def iter_tool_events(transcript_path: Path) -> Iterator[ToolEvent]:
    """Itera i tool_result del transcript, appaiati al nome del tool via tool_use_id.

    Difensivo: salta righe non-JSON e blocchi malformati. Ritorna [] se il file non esiste.
    """
    p = Path(transcript_path)
    if not p.exists():
        return
    id_to_name: dict[str, str] = {}
    with p.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except (ValueError, TypeError):
                continue
            msg = evt.get("message") if isinstance(evt, dict) else None
            blocks = msg.get("content") if isinstance(msg, dict) else None
            if not isinstance(blocks, list):
                continue
            for b in blocks:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use":
                    if b.get("id"):
                        id_to_name[b["id"]] = b.get("name", "?")
                elif b.get("type") == "tool_result":
                    text = _content_to_text(b.get("content"))
                    is_err = bool(b.get("is_error")) or is_error_content(text)
                    name = id_to_name.get(b.get("tool_use_id", ""), "?")
                    yield ToolEvent(
                        tool=name,
                        is_error=is_err,
                        category=classify_error(text) if is_err else "UNKNOWN",
                        preview=text[:200].replace("\n", " "),
                    )


def build_digest(transcript_path: Path, cap: int = 40000) -> str:
    """Digest compresso: una riga per tool event, troncato a `cap` caratteri."""
    lines: list[str] = []
    total = 0
    for i, e in enumerate(iter_tool_events(transcript_path)):
        status = f"ERROR({e.category})" if e.is_error else "OK"
        row = f"[{i}] {e.tool}: {status}: {e.preview}"
        if total + len(row) + 1 > cap:
            lines.append("… (troncato)")
            break
        lines.append(row)
        total += len(row) + 1
    return "\n".join(lines)
