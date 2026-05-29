# Task 14 — `classify_intractable.py`

**Goal:** Script che, prima di marcare un file come `intractable` in Phase 7, esegue static analysis e classifica `NEEDS_REFLECTION | NEEDS_CLASS_MOCK | NEEDS_TZ_MOCK | INTRACTABLE_DB_DEPENDENT | INTRACTABLE_UNKNOWN`. Marca `intractable` solo per DB-only/unknown. Risolve gap 6.3 (la skill marcava intractable file in realtà trattabili con reflection/class-mock/TZ-mock). Unifica le proposte cieche di Agent B (Step 0 pre-abort) e Agent C (C2).

**WS:** WS-4 · **Dipendenze:** Task 09/10/11 (riusa la stessa logica regex degli scanner).

## File coinvolti
- Crea: `skills/code-coverage/scripts/classify_intractable.py`
- Crea: `skills/code-coverage/scripts/tests/test_classify_intractable.py`

## Step TDD

### Step 1 — Test fallente
Crea `skills/code-coverage/scripts/tests/test_classify_intractable.py`:

```python
import classify_intractable as ci


def test_private_methods_needs_reflection():
    src = "export class D { private mapLocale(r){ return r.x ?? '' } }"
    assert ci.classify(src, "")["classification"] == "NEEDS_REFLECTION"


def test_inline_new_needs_class_mock():
    src = "import {S} from './S'\nclass D { f(){ const s = new S(); return s.go() } }"
    assert ci.classify(src, "")["classification"] == "NEEDS_CLASS_MOCK"


def test_tz_needs_tz_mock():
    src = "const f = new Intl.DateTimeFormat('it-IT', { timeZone: 'Europe/Rome' })"
    assert ci.classify(src, "")["classification"] == "NEEDS_TZ_MOCK"


def test_db_only_intractable():
    src = "class D { async f(){ return await this.db.query('SELECT 1') } }"
    assert ci.classify(src, "")["classification"] == "INTRACTABLE_DB_DEPENDENT"


def test_unknown():
    assert ci.classify("export const x = 1", "")["classification"] == "INTRACTABLE_UNKNOWN"


def test_inline_new_skipped_if_already_mocked():
    src = "import {S} from './S'\nclass D { f(){ const s = new S(); return s.go() } }"
    spec = "vi.mock('./S', () => ({ S: vi.fn() }))"
    # già mockato → non NEEDS_CLASS_MOCK; ricade su unknown (nessun altro segnale)
    assert ci.classify(src, spec)["classification"] == "INTRACTABLE_UNKNOWN"
```

### Step 2 — Verifica che fallisce
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_classify_intractable.py -v`
Output atteso: ImportError → 6 FAILED.

### Step 3 — Implementa `scripts/classify_intractable.py`

```python
#!/usr/bin/env python3
"""classify_intractable.py — static analysis pre-guard prima di marcare intractable.

Precedenza: REFLECTION > CLASS_MOCK > TZ_MOCK > DB_DEPENDENT > UNKNOWN.
Usage: classify_intractable.py <source_file> [<existing_spec_file>]
"""
import json
import re
import sys
from pathlib import Path

_PRIVATE_RE = re.compile(r"^\s+private\s+(?:readonly\s+)?(?:async\s+)?(\w+)\s*\(", re.M)
_NEW_RE = re.compile(r"\bnew\s+([A-Z]\w+)\s*\(")
_TZ_RE = re.compile(r"Intl\.|\.toLocale(?:String|DateString|TimeString)\b|process\.env\.TZ\b|getItalyOffset|addItalyOffset")
_DB_RE = re.compile(r"await\s+this\.(?:db|pool|knex|client|pgClient)\.(?:query|execute|raw)|\.prepare\s*\(|createConnection\s*\(", re.M)
_MOCK_RE = re.compile(r"vi\.mock|jest\.mock")
_BUILTINS = {"Date", "Error", "Map", "Set", "Array", "Promise", "Buffer", "RegExp",
             "Object", "Number", "String", "TypeError", "RangeError", "URL"}


def classify(src_text: str, spec_text: str = "") -> dict:
    private_methods = [m.group(1) for m in _PRIVATE_RE.finditer(src_text)
                       if m.group(1) not in ("get", "set", "constructor")]
    inline_classes = [c for c in dict.fromkeys(_NEW_RE.findall(src_text)) if c not in _BUILTINS]
    has_tz = bool(_TZ_RE.search(src_text))
    has_db = bool(_DB_RE.search(src_text))
    has_mock = bool(_MOCK_RE.search(spec_text))

    if private_methods:
        cls, action = "NEEDS_REFLECTION", \
            "Reflection: (inst as unknown as {m:Fn}).m.call(inst, fixture)"
    elif inline_classes and not has_mock:
        cls, action = "NEEDS_CLASS_MOCK", \
            f"vi.mock for {', '.join(inline_classes)}: vi.fn().mockImplementation(() => ({{...}}))"
    elif has_tz:
        cls, action = "NEEDS_TZ_MOCK", \
            "vi.mock utils with importOriginal: getItalyOffset/addItalyOffset"
    elif has_db:
        cls, action = "INTRACTABLE_DB_DEPENDENT", \
            "Requires real DB fixture / integration test; skip in unit coverage"
    else:
        cls, action = "INTRACTABLE_UNKNOWN", "Manual investigation: no automatable pattern"

    return {
        "classification": cls,
        "suggested_action": action,
        "private_methods": private_methods,
        "inline_classes": inline_classes,
        "signals": {"has_private": bool(private_methods), "has_inline_new": bool(inline_classes),
                    "has_tz": has_tz, "has_db": has_db, "has_existing_mock": has_mock},
    }


def main() -> None:
    src = Path(sys.argv[1]).read_text(encoding="utf-8", errors="ignore")
    spec = ""
    if len(sys.argv) > 2 and Path(sys.argv[2]).exists():
        spec = Path(sys.argv[2]).read_text(encoding="utf-8", errors="ignore")
    print(json.dumps(classify(src, spec), indent=2))


if __name__ == "__main__":
    main()
```

### Step 4 — Verifica che passa
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_classify_intractable.py -v`
Output atteso: `6 passed`.

### Step 5 — Commit
```
git add skills/code-coverage/scripts/classify_intractable.py skills/code-coverage/scripts/tests/test_classify_intractable.py
git commit -m "feat(code-coverage): classify_intractable gate (reflection/class-mock/tz vs genuine intractable)"
```

## Criteri di accettazione
- [ ] private → NEEDS_REFLECTION; inline new → NEEDS_CLASS_MOCK; Intl → NEEDS_TZ_MOCK; db-only → INTRACTABLE_DB_DEPENDENT; nessuno → INTRACTABLE_UNKNOWN.
- [ ] inline new già mockato nel spec → non NEEDS_CLASS_MOCK.
- [ ] Precedenza rispettata (private vince su tutto).
