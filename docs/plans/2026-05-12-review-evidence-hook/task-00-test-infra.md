# Task 00 — Test infrastructure bootstrap

**SP:** 0.5 · **AC mappati:** prerequisite for AC #2-15 · **Dipendenze:** nessuna · **Wave:** 0

## Goal

Bootstrap di `tests/conftest.py` **root-level** che inietta `REPO_ROOT` in `sys.path`, abilitando `from lib.review_evidence.<module>` da qualsiasi file di test. Pattern allineato a `tests/zero-loss/conftest.py` ma esteso a tutta la suite (decisione plan-review iter 2 opzione b: semplifica e copre anche W2-Task14 path inconsistency).

## Razionale (gap rilevato dal plan-reviewer iter 1)

Il repo NON ha un `conftest.py` root né `pyproject.toml` con `[tool.pytest.ini_options]` per `pythonpath`. I test Python sono per-suite con `conftest.py` locale (vedi `tests/zero-loss/conftest.py:11-20`). Senza Task 00 i test scritti nei task 01-15 fallirebbero con `ModuleNotFoundError: No module named 'lib.review_evidence'`.

**Iter 2 update:** scelto root-level conftest invece di `tests/review-evidence/conftest.py`. Beneficio: i task 01-15 mantengono i path test `tests/test_review_evidence_*.py` come scritti (no path correction massiva) E `tests/fixtures/review-evidence/` come fixture root.

## File coinvolti

**Creare:**
- `tests/conftest.py` (root)
- `tests/fixtures/__init__.py` (vuoto — se non esiste già)
- `tests/fixtures/review-evidence/.gitkeep` (placeholder dir per fixture)

**NON modificare:**
- `tests/zero-loss/conftest.py` resta com'è. Il suo `sys.path.insert(0, str(LIB_DIR))` resta locale al suo scope.

## Step

### Step 1 — Crea directory fixture

```bash
mkdir -p "tests/fixtures/review-evidence"
touch "tests/fixtures/review-evidence/.gitkeep"
```

### Step 2 — Scrivi root conftest

`tests/conftest.py`:

```python
"""Root-level pytest conftest for siae-devforge.

Mutuated from `tests/zero-loss/conftest.py` pattern (sys.path injection)
but scoped to the entire `tests/` tree so any test_*.py can do:

    from lib.review_evidence.schema import Evidence

without per-suite conftest.

Co-exists with `tests/zero-loss/conftest.py` which has its own fixtures.
This file MUST stay minimal — suite-specific helpers belong to suite-local
conftest.

Naming convention:
- `lib/review_evidence/` (underscore) is a Python module
- `.claude/review-evidence/` (dash) is a filesystem dir (not Python)
- Both are intentional; this conftest only handles the Python path.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def repo_root() -> Path:
    """Path to repository root (where lib/ and hooks/ live)."""
    return REPO_ROOT


@pytest.fixture
def review_evidence_fixtures_dir() -> Path:
    """Path to tests/fixtures/review-evidence/."""
    return REPO_ROOT / "tests" / "fixtures" / "review-evidence"
```

### Step 3 — Smoke test

```bash
cd "$(git rev-parse --show-toplevel)"
pytest tests/ --collect-only -q 2>&1 | head -20
```

**Output atteso:** zero `error` in collection. Eventuali test esistenti listati senza ImportError. (Se vedi qualche `error in test_foo` non legato a `lib.review_evidence`, è pre-esistente — non bloccare Task 00 su quello, è fuori scope.)

Smoke import:

```bash
python3 -c "
import sys
sys.path.insert(0, '.')
# Pre-Task 01: il modulo non esiste ancora, ma il path injection funziona
import os
assert os.path.exists('lib'), 'lib/ not found from REPO_ROOT'
print('PASS')
"
```

**Output atteso:** `PASS`.

### Step 4 — Commit

```bash
git add tests/conftest.py tests/fixtures/review-evidence/.gitkeep
git commit -m "test(review-evidence): bootstrap root conftest with sys.path injection (#task-00)"
```

## Criteri di accettazione

- [ ] `tests/conftest.py` esiste e inietta `REPO_ROOT` in `sys.path`
- [ ] Fixtures `repo_root` e `review_evidence_fixtures_dir` disponibili globalmente
- [ ] `tests/fixtures/review-evidence/` directory creata (anche se vuota, `.gitkeep`)
- [ ] `pytest tests/ --collect-only` non solleva ImportError nuovi
- [ ] `tests/zero-loss/conftest.py` NON modificato (no regressione zero-loss tests)

## Conseguenze sui task 01-15

**Path test usati nei task:** `tests/test_review_evidence_<scope>.py` (root flat, coerente con `tests/lib/test_adoption_analyzer.py`).
**Path fixture:** `tests/fixtures/review-evidence/<file>.{json,xml,md}`.
**Path import:** `from lib.review_evidence.<module> import ...` — funziona grazie al conftest root.

Nessuna correzione path massiva richiesta nei task 01-15 (decisione consapevole post plan-review iter 2 W1).
