# Task 01 — NOTICE Apache-2.0 + scaffold package `lib/retro/`

**Goal:** Creare il package Python `lib/retro/` e registrare l'attribuzione Apache-2.0 di headroom in `NOTICE` (AC7).

## File coinvolti
- Crea: `lib/retro/__init__.py`
- Crea o aggiorna: `NOTICE` (root repo)

## Step TDD bite-sized

### Step 1 — Test strutturale (attribuzione presente)
Crea `tests/test_retro_notice.py`:
```python
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_notice_attributes_headroom_apache2():
    notice = (REPO_ROOT / "NOTICE").read_text(encoding="utf-8")
    assert "headroom" in notice.lower()
    assert "Apache" in notice and "2.0" in notice
    assert "chopratejas/headroom" in notice


def test_retro_is_python_package():
    assert (REPO_ROOT / "lib" / "retro" / "__init__.py").exists()
```

### Step 2 — Esegui e verifica che fallisce
Run: `python3 -m pytest tests/test_retro_notice.py -q`
Output atteso: `FAILED` — `FileNotFoundError: .../NOTICE` (o assertion su package mancante).

### Step 3 — Implementa
Crea `lib/retro/__init__.py`:
```python
"""DevForge auto-retrospective (forge-retrospect).

Port del failure-learning di headroom (https://github.com/chopratejas/headroom),
licenza Apache 2.0. Vedi NOTICE per l'attribuzione.
"""
```
Crea/append `NOTICE` (root). Se il file esiste, appendi il blocco; altrimenti crealo:
```
DevForge — NOTICE

Questo progetto include codice derivato da:

  headroom — https://github.com/chopratejas/headroom
  Copyright the headroom authors.
  Licensed under the Apache License, Version 2.0.

  File derivati: lib/retro/classifier.py (port di headroom/learn/_shared.py),
  lib/retro/writer.py (port della logica marker-section di headroom/learn/writer.py),
  lib/retro/digest.py (pattern di headroom/learn/analyzer.py).

  Una copia della licenza Apache 2.0: http://www.apache.org/licenses/LICENSE-2.0
```

### Step 4 — Esegui e verifica che passa
Run: `python3 -m pytest tests/test_retro_notice.py -q`
Output atteso: `2 passed`.

### Step 5 — Commit
`git add lib/retro/__init__.py NOTICE tests/test_retro_notice.py && git commit -m "chore(retro): scaffold lib/retro package + NOTICE attribuzione headroom Apache-2.0"`

## Criteri di accettazione
- [ ] `lib/retro/__init__.py` esiste e il package è importabile (`from lib import retro`).
- [ ] `NOTICE` contiene `headroom`, `Apache`, `2.0`, `chopratejas/headroom`.
- [ ] `tests/test_retro_notice.py` passa (2 test).
