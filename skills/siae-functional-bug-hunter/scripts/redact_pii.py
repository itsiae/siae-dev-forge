#!/usr/bin/env python3
"""redact_pii.py — PII redaction for evidence excerpts.

Reads UTF-8 text from stdin (or from a file given as the only argument),
replaces every match of the regex catalog below with a typed placeholder
`<REDACTED:type>`, and writes the redacted text to stdout. The original
content is NEVER written or logged.

Regex catalog (Quality Bar #10):

- email addresses (RFC-5322 simplified)
- IPv4 literals
- IPv6 literals
- JWT tokens (three base64url segments separated by '.')
- AWS access key ids and secret-key-like tokens
- Italian Codice Fiscale (16 alphanumerics, structured)
- Italian IBAN
- Generic hex strings of length >= 32 (uppercase or lowercase)

Exit code: 0 on success.

Usage:
    python3 redact_pii.py < input.txt > output.txt
    python3 redact_pii.py path/to/input.txt > output.txt
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Order matters: more specific patterns should run first so that a JWT
# isn't shadowed by the generic-hex rule, for example.

PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "JWT",
        re.compile(r"\b[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
        "<REDACTED:JWT>",
    ),
    (
        "EMAIL",
        re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
        "<REDACTED:EMAIL>",
    ),
    (
        "IPV4",
        re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"),
        "<REDACTED:IPV4>",
    ),
    (
        "IPV6",
        re.compile(
            r"\b(?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}\b"
            r"|\b(?:[A-Fa-f0-9]{1,4}:){1,7}:(?:[A-Fa-f0-9]{1,4})?\b"
        ),
        "<REDACTED:IPV6>",
    ),
    (
        "AWS_ACCESS_KEY_ID",
        re.compile(r"\b(?:AKIA|ASIA|AIDA|AGPA|AROA|ANPA|ANVA)[0-9A-Z]{16}\b"),
        "<REDACTED:AWS_ACCESS_KEY_ID>",
    ),
    (
        "AWS_SECRET",
        re.compile(r"(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])"),
        "<REDACTED:AWS_SECRET>",
    ),
    (
        "IT_CODICE_FISCALE",
        re.compile(r"\b[A-Z]{6}\d{2}[A-EHLMPRST]\d{2}[A-Z]\d{3}[A-Z]\b"),
        "<REDACTED:IT_CF>",
    ),
    (
        "IT_IBAN",
        re.compile(r"\bIT\d{2}[A-Z]\d{10}[A-Z0-9]{12}\b"),
        "<REDACTED:IT_IBAN>",
    ),
    (
        "HEX32PLUS",
        re.compile(r"(?<![A-Fa-f0-9])[A-Fa-f0-9]{32,}(?![A-Fa-f0-9])"),
        "<REDACTED:HEX>",
    ),
]


def redact(text: str) -> str:
    redacted = text
    for _, pattern, placeholder in PATTERNS:
        redacted = pattern.sub(placeholder, redacted)
    return redacted


def main(argv: list[str]) -> int:
    if len(argv) == 0:
        src = sys.stdin.read()
    elif len(argv) == 1:
        p = Path(argv[0])
        if not p.is_file():
            raise SystemExit(f"file not found: {argv[0]}")
        src = p.read_text(encoding="utf-8")
    else:
        raise SystemExit("usage: redact_pii.py [path]")
    sys.stdout.write(redact(src))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
