# Task 02 — `lib/retro/classifier.py` (port taxonomy errori)

**Goal:** Port dependency-free di `is_error_content()` + `classify_error()` da headroom `learn/_shared.py` (15 categorie + UNKNOWN). Nessuna dipendenza esterna (categorie come costanti stringa, non enum importato).

**Dipende da:** Task 01. **File coinvolti:** crea `lib/retro/classifier.py`, `tests/test_retro_classifier.py`.

## Step TDD bite-sized

### Step 1 — Test fallente
Crea `tests/test_retro_classifier.py`:
```python
from lib.retro.classifier import classify_error, is_error_content


def test_file_not_found():
    assert classify_error("bash: ENOENT: no such file or directory") == "FILE_NOT_FOUND"


def test_command_not_found():
    assert classify_error("zsh: command not found: foo") == "COMMAND_NOT_FOUND"


def test_user_rejected():
    assert classify_error("The user doesn't want to proceed (auto-denied)") == "USER_REJECTED"


def test_timeout():
    assert classify_error("Error: deadline exceeded, timed out after 60s") == "TIMEOUT"


def test_first_match_wins_order():
    # "No such file" deve vincere su "Error:" generico
    assert classify_error("Error: No such file or directory") == "FILE_NOT_FOUND"


def test_unknown_when_no_pattern():
    assert classify_error("tutto ok, nessun problema qui") == "UNKNOWN"


def test_is_error_true_on_indicator():
    assert is_error_content("Traceback (most recent call last): ...") is True


def test_is_error_false_on_short_or_clean():
    assert is_error_content("ok") is False
    assert is_error_content("Operazione completata con successo, 3 file scritti.") is False
```

### Step 2 — Verifica fallimento
Run: `python3 -m pytest tests/test_retro_classifier.py -q`
Output atteso: `FAILED` — `ModuleNotFoundError: No module named 'lib.retro.classifier'`.

### Step 3 — Implementa
Crea `lib/retro/classifier.py` (port da headroom `learn/_shared.py`, Apache-2.0 — vedi NOTICE):
```python
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
_ERROR_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"No such file or directory|ENOENT|FileNotFoundError|does not exist", re.I), "FILE_NOT_FOUND"),
    (re.compile(r"ModuleNotFoundError|ImportError|No module named", re.I), "MODULE_NOT_FOUND"),
    (re.compile(r"command not found", re.I), "COMMAND_NOT_FOUND"),
    (re.compile(r"Permission denied|EACCES|EPERM|auto-denied", re.I), "PERMISSION_DENIED"),
    (re.compile(r"file is too large|too many lines|exceeds.*limit", re.I), "FILE_TOO_LARGE"),
    (re.compile(r"EISDIR|Is a directory", re.I), "IS_DIRECTORY"),
    (re.compile(r"SyntaxError|IndentationError", re.I), "SYNTAX_ERROR"),
    (re.compile(r"Traceback \(most recent|Exception:|Error:", re.I), "RUNTIME_ERROR"),
    (re.compile(r"timed? ?out|TimeoutError|deadline exceeded", re.I), "TIMEOUT"),
    (re.compile(r"No (?:matches|files|results) found|0 matches", re.I), "NO_MATCHES"),
    (re.compile(r"user.*reject|user.*denied|declined|didn't want to proceed", re.I), "USER_REJECTED"),
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
```

### Step 4 — Verifica passa
Run: `python3 -m pytest tests/test_retro_classifier.py -q`
Output atteso: `8 passed`.

### Step 5 — Commit
`git add lib/retro/classifier.py tests/test_retro_classifier.py && git commit -m "feat(retro): classifier errori (port headroom _shared.py, dependency-free)"`

## Criteri di accettazione
- [ ] `classify_error` ritorna la categoria corretta per i 6 casi del test, `UNKNOWN` se nessun match.
- [ ] First-match-wins: `"Error: No such file"` → `FILE_NOT_FOUND` (non `RUNTIME_ERROR`).
- [ ] `is_error_content` True su indicatori, False su stringhe corte/pulite.
- [ ] Zero import esterni oltre `re`. `tests/test_retro_classifier.py` passa (8 test).
