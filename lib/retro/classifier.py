"""Classificazione errori — port da headroom learn/_shared.py (Apache 2.0).

Categorie come costanti stringa per restare dependency-free.
"""
from __future__ import annotations

import re

# Categorie (15 + UNKNOWN fallback)
CATEGORIES = (
    "FILE_NOT_FOUND", "MODULE_NOT_FOUND", "COMMAND_NOT_FOUND", "PERMISSION_DENIED",
    "FILE_TOO_LARGE", "IS_DIRECTORY", "SYNTAX_ERROR", "RUNTIME_ERROR", "TIMEOUT",
    "NO_MATCHES", "USER_REJECTED", "SIBLING_ERROR", "EXIT_CODE", "CONNECTION_ERROR",
    "BUILD_FAILURE", "UNKNOWN",
)

# Pattern controllati in ordine — il primo match vince.
# NOTA: USER_REJECTED e TIMEOUT prima di PERMISSION_DENIED/RUNTIME_ERROR per evitare
# falsi match su "auto-denied" e "deadline exceeded, timed out".
_ERROR_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"No such file or directory|ENOENT|FileNotFoundError|does not exist", re.I), "FILE_NOT_FOUND"),
    (re.compile(r"ModuleNotFoundError|ImportError|No module named", re.I), "MODULE_NOT_FOUND"),
    (re.compile(r"command not found", re.I), "COMMAND_NOT_FOUND"),
    (re.compile(r"user.*reject|user.*denied|declined|didn't want to proceed|auto-denied", re.I), "USER_REJECTED"),
    (re.compile(r"timed? ?out|TimeoutError|deadline exceeded", re.I), "TIMEOUT"),
    (re.compile(r"Permission denied|EACCES|EPERM", re.I), "PERMISSION_DENIED"),
    (re.compile(r"file is too large|too many lines|exceeds.*limit", re.I), "FILE_TOO_LARGE"),
    (re.compile(r"EISDIR|Is a directory", re.I), "IS_DIRECTORY"),
    (re.compile(r"SyntaxError|IndentationError", re.I), "SYNTAX_ERROR"),
    (re.compile(r"Traceback \(most recent|Exception:|Error:", re.I), "RUNTIME_ERROR"),
    (re.compile(r"No (?:matches|files|results) found|0 matches", re.I), "NO_MATCHES"),
    (re.compile(r"[Ss]ibling tool call errored", re.I), "SIBLING_ERROR"),
    (re.compile(r"exit code|non-zero|exited with", re.I), "EXIT_CODE"),
    (re.compile(r"ConnectionError|ConnectionRefused|ECONNREFUSED|network", re.I), "CONNECTION_ERROR"),
    (re.compile(r"BUILD FAILED|compilation error|compile error", re.I), "BUILD_FAILURE"),
]

_INDICATORS = (
    "Error:", "error:", "ENOENT", "No such file", "command not found", "Permission denied",
    "ModuleNotFoundError", "Traceback (most recent", "FAILED", "EISDIR", "auto-denied",
    "Sibling tool call errored", "timed out", "exit code", "FileNotFoundError",
)


def classify_error(content: str) -> str:
    """Classifica un messaggio di errore in una categoria. Controlla i primi 2KB."""
    head = (content or "")[:2000]
    for pattern, category in _ERROR_PATTERNS:
        if pattern.search(head):
            return category
    return "UNKNOWN"


def is_error_content(content: str) -> bool:
    """Euristica: questo tool result sembra un errore? (primi 1KB)."""
    if not content or len(content) < 10:
        return False
    snippet = content[:1000]
    return any(ind in snippet for ind in _INDICATORS)
