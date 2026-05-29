# Task 10 — `scan_class_instantiations.py`

**Goal:** Scanner che trova le classi importate e istanziate inline con `new ClassFoo()` nel source-under-test, con i metodi invocati, per generare un class-mock factory. Esclude le built-in (`Date`, `Error`, `Map`, ...). Risolve gap R8 (la skill genera `vi.fn()` per funzioni, mai per classi istanziate inline — es. `new SpazioDao()` dentro `LocaleDao`).

**WS:** WS-3 · **Dipendenze:** nessuna (Task 14 lo riusa).

## File coinvolti
- Crea: `skills/code-coverage/scripts/scan_class_instantiations.py`
- Crea: `skills/code-coverage/scripts/tests/test_scan_class_instantiations.py`

## Step TDD

### Step 1 — Test fallente
Crea `skills/code-coverage/scripts/tests/test_scan_class_instantiations.py`:

```python
import scan_class_instantiations as sc


def test_finds_inline_new_with_import_path():
    src = (
        "import { SpazioDao } from '../dao/SpazioDao'\n"
        "export class LocaleDao {\n"
        "  async f() {\n"
        "    const s = new SpazioDao()\n"
        "    return s.retrieveAccertamentiApp() ?? s.findById(1)\n"
        "  }\n"
        "}\n"
    )
    res = sc.scan(src)
    assert res["SpazioDao"]["import_path"] == "../dao/SpazioDao"
    assert "retrieveAccertamentiApp" in res["SpazioDao"]["methods"]
    assert "findById" in res["SpazioDao"]["methods"]


def test_excludes_builtins():
    src = "const d = new Date(); const m = new Map(); const e = new Error('x')"
    assert sc.scan(src) == {}
```

### Step 2 — Verifica che fallisce
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_scan_class_instantiations.py -v`
Output atteso: ImportError → 2 FAILED.

### Step 3 — Implementa `scripts/scan_class_instantiations.py`

```python
#!/usr/bin/env python3
"""scan_class_instantiations.py — trova classi istanziate inline con `new`.

Per ogni classe importata e istanziata con `new ClassName(`:
  - import_path (da `import { ClassName } from 'path'`)
  - methods: metodi invocati sull'istanza (best-effort, via regex su variabile)
Esclude le built-in JS.

Usage: scan_class_instantiations.py <source_file>
Output JSON: { "ClassName": {"import_path": "...", "methods": ["m1","m2"]} }
"""
import json
import re
import sys
from pathlib import Path

_BUILTINS = {
    "Date", "Error", "Map", "Set", "Array", "Promise", "Buffer", "RegExp",
    "WeakMap", "WeakSet", "Object", "Number", "String", "Boolean", "Proxy",
    "TypeError", "RangeError", "URL", "URLSearchParams", "Int8Array",
    "Uint8Array", "Float64Array", "DataView", "TextEncoder", "TextDecoder",
}
_IMPORT_RE = re.compile(r"import\s+\{([^}]+)\}\s+from\s+['\"]([^'\"]+)['\"]")
_NEW_RE = re.compile(r"\bnew\s+([A-Z]\w+)\s*\(")
_ASSIGN_RE = re.compile(r"(?:const|let|var)\s+(\w+)\s*=\s*new\s+([A-Z]\w+)\s*\(")


def scan(text: str) -> dict:
    # mappa import: ClassName -> path
    imports: dict[str, str] = {}
    for m in _IMPORT_RE.finditer(text):
        names = [n.strip().split(" as ")[0].strip() for n in m.group(1).split(",")]
        for n in names:
            if n:
                imports[n] = m.group(2)

    result: dict[str, dict] = {}
    # var -> ClassName per estrarre i metodi invocati
    var_to_class: dict[str, str] = {}
    for m in _ASSIGN_RE.finditer(text):
        var_to_class[m.group(1)] = m.group(2)

    for m in _NEW_RE.finditer(text):
        cls = m.group(1)
        if cls in _BUILTINS:
            continue
        result.setdefault(cls, {"import_path": imports.get(cls, ""), "methods": []})

    # metodi invocati: <var>.<method>(
    for var, cls in var_to_class.items():
        if cls in result:
            for mm in re.finditer(rf"\b{re.escape(var)}\.(\w+)\s*\(", text):
                meth = mm.group(1)
                if meth not in result[cls]["methods"]:
                    result[cls]["methods"].append(meth)
    return result


def main() -> None:
    src = Path(sys.argv[1])
    text = src.read_text(encoding="utf-8", errors="ignore")
    print(json.dumps(scan(text), indent=2))


if __name__ == "__main__":
    main()
```

### Step 4 — Verifica che passa
Run: `cd skills/code-coverage && python3 -m pytest scripts/tests/test_scan_class_instantiations.py -v`
Output atteso: `2 passed`.

### Step 5 — Commit
```
git add skills/code-coverage/scripts/scan_class_instantiations.py skills/code-coverage/scripts/tests/test_scan_class_instantiations.py
git commit -m "feat(code-coverage): scan inline class instantiations for class-mock factory"
```

## Criteri di accettazione
- [ ] Trova `SpazioDao` con `import_path` e i metodi invocati (`retrieveAccertamentiApp`, `findById`).
- [ ] Esclude le built-in (`Date`/`Map`/`Error` → `{}`).
