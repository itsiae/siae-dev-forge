# Task 07 — `hooks/session-start` nudge (additivo)

**Goal:** Mostrare un nudge una sola volta per sessione quando esistono record pending. Logica pura in `lib/retro/nudge.py` (testabile), invocata da `hooks/session-start` che ne appende l'output all'`additionalContext`. Usa il sentinel `~/.claude/.devforge-retro-reminded` (già azzerato a `hooks/session-start:475`).

**Dipende da:** Task 05 (formato staging record). **File coinvolti:** crea `lib/retro/nudge.py`, `tests/test_retro_nudge.py`; modifica `hooks/session-start`.

## Step TDD bite-sized

### Step 1 — Test fallente
Crea `tests/test_retro_nudge.py`:
```python
import json
from pathlib import Path

from lib.retro.nudge import compute_nudge


def _record(d, sid, errors):
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{sid}.json").write_text(json.dumps({"session_id": sid, "error_count": errors}), encoding="utf-8")


def test_no_pending_no_nudge(tmp_path):
    assert compute_nudge(tmp_path / "retro-pending", tmp_path / "sentinel") is None


def test_pending_and_sentinel_absent_nudges(tmp_path):
    pend = tmp_path / "retro-pending"
    _record(pend, "s1", 3)
    msg = compute_nudge(pend, tmp_path / "sentinel")
    assert msg is not None
    assert "/forge-retrospect" in msg
    assert "--dismiss" in msg


def test_sentinel_present_suppresses(tmp_path):
    pend = tmp_path / "retro-pending"
    _record(pend, "s1", 3)
    sentinel = tmp_path / "sentinel"
    sentinel.write_text("", encoding="utf-8")
    assert compute_nudge(pend, sentinel) is None     # già notificato in questa sessione
```

### Step 2 — Verifica fallimento
Run: `python3 -m pytest tests/test_retro_nudge.py -q`
Output atteso: `FAILED` — `ModuleNotFoundError: No module named 'lib.retro.nudge'`.

### Step 3 — Implementa
Crea `lib/retro/nudge.py`:
```python
"""NUDGE stage: 1 riga di promemoria se ci sono record pending e non già notificato."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def compute_nudge(pending_dir: Path, sentinel_path: Path) -> str | None:
    """Ritorna la riga di nudge se (pending non vuoto AND sentinel assente), altrimenti None."""
    pending_dir = Path(pending_dir)
    if Path(sentinel_path).exists():
        return None
    if not pending_dir.is_dir():
        return None
    records = list(pending_dir.glob("*.json"))
    if not records:
        return None
    n = len(records)
    return (
        f"⚠️ Auto-retrospective: {n} sessione/i con fallimenti ripetuti in sospeso → "
        f"lancia /forge-retrospect per estrarre lezioni (o /forge-retrospect --dismiss per ignorare)."
    )


def main() -> int:
    home = Path(os.environ.get("HOME", ""))
    pending = home / ".claude" / "devforge-state" / "retro-pending"
    sentinel = home / ".claude" / ".devforge-retro-reminded"
    try:
        msg = compute_nudge(pending, sentinel)
        if msg:
            print(msg)
            sentinel.parent.mkdir(parents=True, exist_ok=True)
            sentinel.write_text("", encoding="utf-8")   # set sentinel: nudge ≤1 per sessione
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Edit hook** — `hooks/session-start` assembla l'`additional_context` in UNA stringa letterale (`session_context`, attualmente `:319`) interpolando variabili `*_section` (pattern di `global_memory_section` `:293`/`:314`, `branching_section`, `catalog_section`; helper `escape_for_json` `:239`). NON esiste alcun `CONTEXT_BLOCK`. Segui ESATTAMENTE il pattern esistente:

**Edit A** — subito PRIMA della riga `session_context=...` (`:319`), aggiungi la sezione nudge:
```bash
# Auto-retrospective NUDGE (best-effort) — design 2026-06-22-auto-retrospective.
# nudge.py stampa la riga (con prefisso ⚠️) E imposta il sentinel come side-effect.
retro_nudge_section=""
if command -v python3 >/dev/null 2>&1; then
    _retro_nudge=$(python3 "${PLUGIN_ROOT}/lib/retro/nudge.py" 2>/dev/null || true)
    if [ -n "$_retro_nudge" ]; then
        _retro_nudge_escaped=$(escape_for_json "$_retro_nudge")
        retro_nudge_section="\\n\\n${_retro_nudge_escaped}"
    fi
fi
```

**Edit B** — nella stringa `session_context=` (`:319`), interpola `${retro_nudge_section}` subito prima di `\n</EXTREMELY_IMPORTANT>`. Cioè cambia la coda:
```
...${global_memory_section}\n</EXTREMELY_IMPORTANT>"
```
in:
```
...${global_memory_section}${retro_nudge_section}\n</EXTREMELY_IMPORTANT>"
```

(NON ri-aggiungere il prefisso `⚠️`: lo emette già `nudge.py`. Il `rm -f .devforge-retro-reminded` a `:475` azzera il sentinel a ogni nuova sessione → il nudge si ripresenta se il record è ancora pendente.)

**Test strutturale hook** — crea `tests/test_retro_session_start_nudge.py`:
```python
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "session-start"


def test_session_start_invokes_nudge_and_wires_into_context():
    src = HOOK.read_text(encoding="utf-8")
    assert "lib/retro/nudge.py" in src                 # invoca nudge.py
    assert "retro_nudge_section" in src                # definisce la sezione
    assert "${retro_nudge_section}" in src             # la interpola nel context
    # la sezione è interpolata DENTRO la stringa session_context
    ctx_line = next(l for l in src.splitlines() if l.startswith("session_context="))
    assert "${retro_nudge_section}" in ctx_line
    assert "escape_for_json" in src                    # output escapato per JSON


def test_sentinel_rm_still_present():
    src = HOOK.read_text(encoding="utf-8")
    assert 'rm -f "${HOME}/.claude/.devforge-retro-reminded"' in src   # invariato (:475)
```

### Step 4 — Verifica passa
Run: `python3 -m pytest tests/test_retro_nudge.py tests/test_retro_session_start_nudge.py -q`
Output atteso: `5 passed` (3 unit nudge + 2 strutturali hook).
Smoke: `mkdir -p /tmp/rp && echo '{}' > /tmp/rp/x.json && HOME=/tmp python3 - <<'PY'`
```python
from lib.retro.nudge import compute_nudge
from pathlib import Path
print(compute_nudge(Path("/tmp/rp"), Path("/tmp/nope")))
PY
```
Output atteso: una riga con `/forge-retrospect`.

### Step 5 — Commit
`git add lib/retro/nudge.py tests/test_retro_nudge.py tests/test_retro_session_start_nudge.py hooks/session-start && git commit -m "feat(retro): nudge session-start con sentinel (≤1 per sessione)"`

## Criteri di accettazione
- [ ] `compute_nudge`: None se pending vuoto; None se sentinel presente; stringa con `/forge-retrospect` + `--dismiss` se pending non vuoto e sentinel assente.
- [ ] `main()` stampa il nudge e imposta il sentinel; esce 0 sempre.
- [ ] `hooks/session-start` definisce `retro_nudge_section` (invocando `nudge.py`, escapato via `escape_for_json`) e lo interpola DENTRO la stringa `session_context` (`:319`) — wiring funzionale, non variabile orfana.
- [ ] Il `rm` del sentinel a `:475` resta invariato. `tests/test_retro_nudge.py` + `tests/test_retro_session_start_nudge.py` passano (5 test).
