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
    # mappa import: ClassName -> path, con supporto alias (import { X as Y } -> sia X che Y mappano al path)
    imports: dict[str, str] = {}
    for m in _IMPORT_RE.finditer(text):
        path = m.group(2)
        for spec in m.group(1).split(","):
            spec = spec.strip()
            if not spec:
                continue
            parts = [p.strip() for p in spec.split(" as ")]
            # parts[0] = nome originale, parts[1] = alias (se presente)
            for name in parts:
                if name:
                    imports[name] = path

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
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: scan_class_instantiations.py <source_file>"}), file=sys.stderr)
        sys.exit(1)
    src = Path(sys.argv[1])
    text = src.read_text(encoding="utf-8", errors="ignore")
    print(json.dumps({"file": str(src), "classes": scan(text)}, indent=2))


if __name__ == "__main__":
    main()
