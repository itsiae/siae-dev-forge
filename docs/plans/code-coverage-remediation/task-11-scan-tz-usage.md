# Task 11 — `scan_tz_usage.py`

**Goal:** Scanner che rileva uso di `Intl.*`, `toLocale*`, `process.env.TZ`, `getItalyOffset`/`addItalyOffset` nel source-under-test (e nelle sue dipendenze dirette), per auto-iniettare il mock TZ. Risolve gap 5.2/R12 (CI runner senza ICU full → `RangeError: Invalid time zone`).

**WS:** WS-3 · **Dipendenze:** nessuna (Task 14 lo riusa).

## File coinvolti
- Crea: `skills/code-coverage/scripts/scan_tz_usage.py`
- Crea: `skills/code-coverage/scripts/tests/test_scan_tz_usage.py`

## Step TDD

### Step 1 — Test fallente
Crea `skills/code-coverage/scripts/tests/test_scan_tz_usage.py`:

```python
import scan_tz_usage as st


def test_detects_intl():
    src = "const f = new Intl.DateTimeFormat('it-IT', { timeZone: 'Europe/Rome' })"
    res = st.scan(src)
    assert res["uses_tz"] is True
    assert "Intl" in res["signals"]


def test_detects_helpers():
    src = "import { getItalyOffset } from '../libs/utils'\nconst o = getItalyOffset()"
    res = st.scan(src)
    assert res["uses_tz"] is True
    assert "getItalyOffset" in res["signals"]


def test_no_tz():
    res = st.scan("const x = 1 + 2")
    assert res["uses_tz"] is False
    assert res["signals"] == []
```

### Step 2 — Verifica che fallisce
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_scan_tz_usage.py -v`
Output atteso: ImportError → 3 FAILED.

### Step 3 — Implementa `scripts/scan_tz_usage.py`

```python
#!/usr/bin/env python3
"""scan_tz_usage.py — rileva uso di TZ/Intl per auto-iniettare mock TZ.

Segnali: Intl., toLocaleString/toLocaleDateString/toLocaleTimeString,
process.env.TZ, getItalyOffset, addItalyOffset.

Usage: scan_tz_usage.py <source_file>
Output JSON: {"file": path, "uses_tz": bool, "signals": [...]}
"""
import json
import re
import sys
from pathlib import Path

_SIGNALS = {
    "Intl": re.compile(r"\bIntl\."),
    "toLocale": re.compile(r"\.toLocale(?:String|DateString|TimeString)\b"),
    "process.env.TZ": re.compile(r"process\.env\.TZ\b"),
    "getItalyOffset": re.compile(r"\bgetItalyOffset\b"),
    "addItalyOffset": re.compile(r"\baddItalyOffset\b"),
}


def scan(text: str) -> dict:
    found = [name for name, rx in _SIGNALS.items() if rx.search(text)]
    return {"uses_tz": bool(found), "signals": found}


def main() -> None:
    src = Path(sys.argv[1])
    text = src.read_text(encoding="utf-8", errors="ignore")
    res = scan(text)
    res["file"] = str(src)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
```

### Step 4 — Verifica che passa
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_scan_tz_usage.py -v`
Output atteso: `3 passed`.

### Step 5 — Commit
```
git add skills/code-coverage/scripts/scan_tz_usage.py skills/code-coverage/scripts/tests/test_scan_tz_usage.py
git commit -m "feat(code-coverage): scan TZ/Intl usage for mock auto-injection"
```

## Criteri di accettazione
- [ ] Rileva `Intl.`, `toLocale*`, `process.env.TZ`, `getItalyOffset`, `addItalyOffset`.
- [ ] Sorgente senza TZ → `uses_tz=false`, `signals=[]`.
