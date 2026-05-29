#!/usr/bin/env python3
"""classify_intractable.py — static analysis pre-guard prima di marcare intractable.

Precedenza: REFLECTION > CLASS_MOCK > TZ_MOCK > DB_DEPENDENT > UNKNOWN.
Usage: classify_intractable.py <source_file> [<existing_spec_file>]
"""
import json
import re
import sys
from pathlib import Path

_PRIVATE_RE = re.compile(r"\bprivate\s+(?:readonly\s+)?(?:async\s+)?(\w+)\s*\(")
_NEW_RE = re.compile(r"\bnew\s+([A-Z]\w*)\s*\(")
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
