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
