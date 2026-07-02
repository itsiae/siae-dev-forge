# Task 04 — `lib/retro/digest.py` (parser transcript + digest compresso)

**Goal:** Parser difensivo del transcript JSONL di Claude Code (`iter_tool_events`) + costruzione del digest compresso (`build_digest`, cap 40k char), usato nello stadio MINE. Pattern da headroom `learn/analyzer.py`.

**Dipende da:** Task 01 + Task 02 (classifier). **File coinvolti:** crea `lib/retro/digest.py`, `tests/test_retro_digest.py`, fixture `tests/fixtures/retro/transcript_sample.jsonl`.

## Step TDD bite-sized

### Step 1 — Fixture + test fallente
Crea `tests/fixtures/retro/transcript_sample.jsonl` (1 evento per riga):
```
{"type":"assistant","message":{"content":[{"type":"tool_use","id":"t1","name":"Bash","input":{"command":"cat foo"}}]}}
{"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"t1","content":"cat: foo: No such file or directory","is_error":true}]}}
{"type":"assistant","message":{"content":[{"type":"tool_use","id":"t2","name":"Read","input":{"file_path":"/ok"}}]}}
{"type":"user","message":{"content":[{"type":"tool_result","tool_use_id":"t2","content":[{"type":"text","text":"contenuto ok"}]}]}}
linea-non-json-da-ignorare
```
Crea `tests/test_retro_digest.py`:
```python
from pathlib import Path

from lib.retro.digest import build_digest, iter_tool_events

FIX = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "retro" / "transcript_sample.jsonl"


def test_iter_tool_events_pairs_name_and_error():
    events = list(iter_tool_events(FIX))
    assert len(events) == 2                                   # 2 tool_result, riga non-json ignorata
    bash = events[0]
    assert bash.tool == "Bash" and bash.is_error is True
    assert bash.category == "FILE_NOT_FOUND"
    read = events[1]
    assert read.tool == "Read" and read.is_error is False     # content come lista di blocchi text


def test_build_digest_caps_length():
    digest = build_digest(FIX, cap=120)
    assert len(digest) <= 120
    assert "Bash" in digest


def test_iter_missing_file_returns_empty():
    assert list(iter_tool_events(Path("/non/esiste.jsonl"))) == []
```

### Step 2 — Verifica fallimento
Run: `python3 -m pytest tests/test_retro_digest.py -q`
Output atteso: `FAILED` — `ModuleNotFoundError: No module named 'lib.retro.digest'`.

### Step 3 — Implementa
Crea `lib/retro/digest.py`:
```python
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
```

### Step 4 — Verifica passa
Run: `python3 -m pytest tests/test_retro_digest.py -q`
Output atteso: `3 passed`.

### Step 5 — Commit
`git add lib/retro/digest.py tests/test_retro_digest.py tests/fixtures/retro/ && git commit -m "feat(retro): parser transcript + digest compresso (pattern headroom analyzer)"`

## Criteri di accettazione
- [ ] `iter_tool_events` appaia tool_use→tool_result via id; gestisce content str e lista-blocchi; salta righe non-JSON.
- [ ] `is_error` = `is_error:true` OR euristica; categoria popolata solo sugli errori.
- [ ] `build_digest` rispetta il cap (`len(digest) <= cap`), aggiunge `… (troncato)` se taglia.
- [ ] File inesistente → iteratore vuoto (no eccezione). `tests/test_retro_digest.py` passa (3 test).
