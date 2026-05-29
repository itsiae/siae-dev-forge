#!/usr/bin/env python3
"""classify_intractable.py — static analysis pre-guard prima di marcare intractable.

Precedenza: REFLECTION > CLASS_MOCK > TZ_MOCK > DB_DEPENDENT > UNKNOWN.
Usage: classify_intractable.py <source_file> [<existing_spec_file>]
"""
import json
import re
import sys
from pathlib import Path

_PRIVATE_RE = re.compile(r"\bprivate\s+(?:(?:static|override|abstract|readonly)\s+)*(?:async\s+)?(\w+)\s*\(")
_NEW_RE = re.compile(r"\bnew\s+([A-Z]\w+)\s*\(")  # ≥2 chars: esclude generics single-letter
_TZ_RE = re.compile(r"\bIntl\.|\.toLocale(?:String|DateString|TimeString)\b|process\.env\.TZ\b|getItalyOffset|addItalyOffset")
_DB_RE = re.compile(r"await\s+this\.(?:db|pool|knex|client|pgClient)\.(?:query|execute|raw)|\.prepare\s*\(|createConnection\s*\(", re.M)
_MOCK_RE = re.compile(r"vi\.mock|jest\.mock")
_BUILTINS = {"Date", "Error", "Map", "Set", "Array", "Promise", "Buffer", "RegExp",
             "WeakMap", "WeakSet", "Object", "Number", "String", "Boolean", "Proxy",
             "TypeError", "RangeError", "URL", "URLSearchParams", "Int8Array",
             "Uint8Array", "Float64Array", "DataView", "TextEncoder", "TextDecoder"}

# Regex per lo stripping del "noise" (commenti e stringhe)
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")
_STRING_SQ_RE = re.compile(r"'(?:[^'\\]|\\.)*'")
_STRING_DQ_RE = re.compile(r'"(?:[^"\\]|\\.)*"')
_TEMPLATE_LITERAL_RE = re.compile(r"`(?:[^`\\]|\\.)*`", re.DOTALL)


def _strip_noise(text: str) -> str:
    """Rimuove commenti e stringhe dal sorgente per evitare falsi positivi nelle regex.

    Ordine: block comments, line comments, template literals, double-quoted strings,
    single-quoted strings. Ogni match viene sostituito con spazi per preservare gli
    offset (non necessario per la logica, ma mantiene la leggibilità dei log).
    """
    text = _BLOCK_COMMENT_RE.sub(lambda m: " " * len(m.group()), text)
    text = _LINE_COMMENT_RE.sub(lambda m: " " * len(m.group()), text)
    text = _TEMPLATE_LITERAL_RE.sub(lambda m: " " * len(m.group()), text)
    text = _STRING_DQ_RE.sub(lambda m: " " * len(m.group()), text)
    text = _STRING_SQ_RE.sub(lambda m: " " * len(m.group()), text)
    return text


def classify(src_text: str, spec_text: str = "") -> dict:
    """Classifica un sorgente TypeScript/JavaScript per tipo di intractability.

    Applica _strip_noise prima di eseguire le regex in modo da ignorare segnali
    presenti solo in commenti, JSDoc o stringhe letterali.

    Args:
        src_text: contenuto del file sorgente da analizzare.
        spec_text: contenuto del file di test esistente (opzionale).

    Returns:
        dict con chiavi: classification, suggested_strategy, private_methods,
        inline_classes, signals.
    """
    clean = _strip_noise(src_text)
    private_methods = [m.group(1) for m in _PRIVATE_RE.finditer(clean)
                       if m.group(1) not in ("get", "set", "constructor")]
    inline_classes = [c for c in dict.fromkeys(_NEW_RE.findall(clean)) if c not in _BUILTINS]
    has_tz = bool(_TZ_RE.search(clean))
    has_db = bool(_DB_RE.search(clean))
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
        "suggested_strategy": action,
        "private_methods": private_methods,
        "inline_classes": inline_classes,
        "signals": {"has_private": bool(private_methods), "has_inline_new": bool(inline_classes),
                    "has_tz": has_tz, "has_db": has_db, "has_existing_mock": has_mock},
    }


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: classify_intractable.py <source_file> [<spec_file>]"}),
              file=sys.stderr)
        sys.exit(1)
    src = Path(sys.argv[1]).read_text(encoding="utf-8", errors="ignore")
    spec = ""
    if len(sys.argv) > 2 and Path(sys.argv[2]).exists():
        spec = Path(sys.argv[2]).read_text(encoding="utf-8", errors="ignore")
    print(json.dumps(classify(src, spec), indent=2))


if __name__ == "__main__":
    main()
