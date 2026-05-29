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
