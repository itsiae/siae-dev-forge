# Task 09 — `scan_private_methods.py`

**Goal:** Scanner che estrae i metodi `private` di una classe TS (con conteggio branch interno), per generare test reflection-based. Risolve gap 6.9/R7 (la skill testa solo l'API public, lasciando 30+ branch privati scoperti — es. `LocaleDao.mapLocale`).

**WS:** WS-3 · **Dipendenze:** nessuna (Task 14 lo riusa).

## File coinvolti
- Crea: `skills/code-coverage/scripts/scan_private_methods.py`
- Crea: `skills/code-coverage/scripts/tests/test_scan_private_methods.py`

## Step TDD

### Step 1 — Test fallente
Crea `skills/code-coverage/scripts/tests/test_scan_private_methods.py`:

```python
import scan_private_methods as sp


def test_finds_private_methods():
    src = (
        "export class LocaleDao {\n"
        "  public searchLocali() { return 1 }\n"
        "  private mapLocale(row: Row) { return row.x ?? '' }\n"
        "  private async manipolaLocale(x) { if (x) return 1; return 2 }\n"
        "}\n"
    )
    methods = sp.scan(src)
    names = [m["name"] for m in methods]
    assert "mapLocale" in names
    assert "manipolaLocale" in names
    assert "searchLocali" not in names  # public escluso


def test_no_private_methods():
    assert sp.scan("export class A { public foo() {} }") == []
```

### Step 2 — Verifica che fallisce
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_scan_private_methods.py -v`
Output atteso: ImportError → 2 FAILED.

### Step 3 — Implementa `scripts/scan_private_methods.py`

```python
#!/usr/bin/env python3
"""scan_private_methods.py — estrae metodi private TS per test reflection-based.

Pattern: ^  private [readonly] [async] methodName(...)
Esclude getter/setter accessor. Output: lista {name, line, is_async}.

Usage: scan_private_methods.py <source_file>
Output JSON: {"file": path, "private_methods": [{"name","line","is_async"}]}
"""
import json
import re
import sys
from pathlib import Path

_PRIVATE_RE = re.compile(
    r"^\s+private\s+(?:readonly\s+)?(?:(async)\s+)?(\w+)\s*\(",
    re.M,
)


def scan(text: str) -> list[dict]:
    out = []
    for m in _PRIVATE_RE.finditer(text):
        name = m.group(2)
        if name in ("get", "set", "constructor"):
            continue
        line = text[: m.start()].count("\n") + 1
        out.append({"name": name, "line": line, "is_async": bool(m.group(1))})
    return out


def main() -> None:
    src = Path(sys.argv[1])
    text = src.read_text(encoding="utf-8", errors="ignore")
    print(json.dumps({"file": str(src), "private_methods": scan(text)}, indent=2))


if __name__ == "__main__":
    main()
```

### Step 4 — Verifica che passa
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_scan_private_methods.py -v`
Output atteso: `2 passed`.

### Step 5 — Commit
```
git add skills/code-coverage/scripts/scan_private_methods.py skills/code-coverage/scripts/tests/test_scan_private_methods.py
git commit -m "feat(code-coverage): scan private methods for reflection-based tests"
```

## Criteri di accettazione
- [ ] Estrae `mapLocale`, `manipolaLocale` (anche `async`); esclude metodi public.
- [ ] Esclude `get`/`set`/`constructor`.
- [ ] Classe senza private → lista vuota.
