# Task 04 — TDD red+green: migrate codemod + idempotency + no-rewrite tokens

**Status:** `[PENDING]`
**Depends on:** task-03
**Estimate:** 25 min
**Files:**
- `skills/code-coverage/scripts/tests/test_migrate_jest_to_vitest.py` (NEW)
- `skills/code-coverage/scripts/migrate_jest_to_vitest.py` (NEW — partial)

## Goal

Codemod parte di migrate: rewrite `jest.fn` → `vi.fn`, `jest.mock` → `vi.mock`, etc.
NO-rewrite per `jest.requireActual` / `jest.requireMock` (solo flag in manual_review).
Idempotent (run 2x stesso input = no-op).

## Steps

### A. Test file con codemod focus

Creare `scripts/tests/test_migrate_jest_to_vitest.py`:

```python
"""Test migrate_jest_to_vitest.py — codemod + idempotency."""
import json
import re
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "migrate_jest_to_vitest.py"
sys.path.insert(0, str(SCRIPT.parent))


def test_codemod_jest_fn_to_vi_fn(tmp_path):
    from migrate_jest_to_vitest import codemod_text
    src = "const m = jest.fn();\nconst spy = jest.spyOn(obj, 'foo');\n"
    out, warns, manual = codemod_text(src)
    assert "vi.fn()" in out
    assert "vi.spyOn(" in out
    assert "jest.fn" not in out
    assert "jest.spyOn" not in out


def test_codemod_jest_mock_to_vi_mock(tmp_path):
    from migrate_jest_to_vitest import codemod_text
    src = "jest.mock('./x');\njest.unmock('./y');\njest.doMock('./z');\n"
    out, _, _ = codemod_text(src)
    assert "vi.mock('./x')" in out
    assert "vi.unmock('./y')" in out
    assert "vi.doMock('./z')" in out


def test_codemod_timers(tmp_path):
    from migrate_jest_to_vitest import codemod_text
    src = "jest.useFakeTimers();\njest.advanceTimersByTime(1000);\njest.runAllTimers();\n"
    out, _, _ = codemod_text(src)
    assert "vi.useFakeTimers" in out
    assert "vi.advanceTimersByTime" in out
    assert "vi.runAllTimers" in out


def test_codemod_no_rewrite_requireActual(tmp_path):
    """Amendment-4: requireActual stays as-is, but emits manual_review."""
    from migrate_jest_to_vitest import codemod_text
    src = "const real = jest.requireActual('./foo');\n"
    out, _, manual = codemod_text(src)
    # NO rewrite — original token preserved
    assert "jest.requireActual" in out
    assert "vi.importActual" not in out
    # But flagged for manual review
    assert any("requireActual" in m for m in manual)


def test_codemod_no_rewrite_requireMock(tmp_path):
    from migrate_jest_to_vitest import codemod_text
    src = "const m = jest.requireMock('./foo');\n"
    out, _, manual = codemod_text(src)
    assert "jest.requireMock" in out
    assert "vi.importMock" not in out
    assert any("requireMock" in m for m in manual)


def test_codemod_isolate_modules_rewrites_with_warning(tmp_path):
    """isolateModules IS rewritten but also flagged for manual audit."""
    from migrate_jest_to_vitest import codemod_text
    src = "jest.isolateModules(() => { require('./x'); });\n"
    out, _, manual = codemod_text(src)
    assert "vi.isolateModules" in out
    assert any("isolateModules" in m for m in manual)


def test_codemod_injects_vi_import(tmp_path):
    from migrate_jest_to_vitest import codemod_text
    src = "const m = jest.fn();\ntest('x', () => {});\n"
    out, _, _ = codemod_text(src)
    assert "import { vi } from 'vitest'" in out or "from 'vitest'" in out


def test_codemod_does_not_double_import(tmp_path):
    """Idempotency: if vi already imported, don't add another."""
    from migrate_jest_to_vitest import codemod_text
    src = "import { vi } from 'vitest';\nconst m = vi.fn();\n"
    out, _, _ = codemod_text(src)
    # Only one vitest import line
    assert out.count("from 'vitest'") == 1


def test_codemod_idempotent(tmp_path):
    """Run codemod twice → second pass is no-op."""
    from migrate_jest_to_vitest import codemod_text
    src = "const m = jest.fn();\n"
    out1, _, _ = codemod_text(src)
    out2, _, _ = codemod_text(out1)
    assert out1 == out2


def test_codemod_strips_jest_globals_import(tmp_path):
    from migrate_jest_to_vitest import codemod_text
    src = "import { describe, it, expect, jest } from '@jest/globals';\nconst m = jest.fn();\n"
    out, _, _ = codemod_text(src)
    assert "@jest/globals" not in out
    assert "vi.fn" in out


def test_codemod_word_boundary_safe(tmp_path):
    """Don't replace `not-jest` or `mybar.jest.fn` (which doesn't exist anyway)."""
    from migrate_jest_to_vitest import codemod_text
    src = "// jest.fn doc reference\nconst notJest = 'no jest here';\n"
    out, _, _ = codemod_text(src)
    # Comments may or may not be touched — but string literals must NOT
    assert "'no jest here'" in out


def test_codemod_testing_library_jest_dom_rewritten(tmp_path):
    from migrate_jest_to_vitest import codemod_text
    src = "import '@testing-library/jest-dom';\n"
    out, _, _ = codemod_text(src)
    assert "@testing-library/jest-dom/vitest" in out


def test_codemod_testing_library_jest_dom_extend_expect(tmp_path):
    from migrate_jest_to_vitest import codemod_text
    src = "import '@testing-library/jest-dom/extend-expect';\n"
    out, _, _ = codemod_text(src)
    assert "@testing-library/jest-dom/vitest" in out
```

### B. Implementation — `migrate_jest_to_vitest.py` (codemod core)

Solo la funzione `codemod_text(text: str) -> tuple[str, list[str], list[str]]`:
- Carica `assets/vitest-jest-compat.json` per `rewrites`, `no_rewrite_tokens`, `manual_review_triggers`.
- Per ogni rewrite: `re.sub(r"\b" + re.escape(from_token), to_token, text)`.
- SALTA pattern in `no_rewrite_tokens`.
- Per `manual_review_triggers`: applica rewrite MA emette riga in `manual` list con info.
- Inject `import { vi } from 'vitest';` se `vi.` usato e nessun `from 'vitest'` esistente.
- Strip `@jest/globals` imports.
- Rewrite `@testing-library/jest-dom` → `@testing-library/jest-dom/vitest`.
- Returns: `(transformed_text, warnings, manual_review_entries)`.

Skeleton:

```python
import json
import re
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "vitest-jest-compat.json"

def _load_compat():
    return json.loads(ASSETS.read_text(encoding="utf-8"))


def codemod_text(text: str) -> tuple[str, list[str], list[str]]:
    compat = _load_compat()
    rewrites = compat["api_migration_map"]["rewrites"]
    no_rewrite = set(compat["api_migration_map"]["no_rewrite_tokens"])
    manual_triggers = compat["api_migration_map"]["manual_review_triggers"]

    warnings: list[str] = []
    manual: list[str] = []

    # Detect manual review triggers BEFORE rewriting (so no_rewrite tokens stay logged)
    for trig in manual_triggers:
        if trig in text:
            manual.append(f"manual-review:{trig}")

    out = text
    # Strip @jest/globals import (line-level)
    out = re.sub(
        r"^import\s+[^;]+from\s+['\"]@jest/globals['\"];\s*\n",
        "",
        out,
        flags=re.MULTILINE,
    )
    # @testing-library/jest-dom rewrites
    out = re.sub(
        r"@testing-library/jest-dom(?:/extend-expect)?(?!/vitest)",
        "@testing-library/jest-dom/vitest",
        out,
    )

    # Token rewrites (skip no_rewrite)
    for rule in rewrites:
        from_tok = rule["from"]
        if from_tok.rstrip("(") in no_rewrite:
            continue
        pat = r"(?<![\w.$])" + re.escape(from_tok)
        out = re.sub(pat, rule["to"], out)

    # Inject vi import if needed (idempotent)
    if re.search(r"(?<![\w.$])vi\.", out) and not re.search(r"from\s+['\"]vitest['\"]", out):
        out = "import { vi } from 'vitest';\n" + out

    return out, warnings, manual
```

### C. Run

```bash
python3 -m pytest skills/code-coverage/scripts/tests/test_migrate_jest_to_vitest.py -v
```

## Acceptance

- [ ] 12 test pass
- [ ] `codemod_text` esposta come funzione importabile
- [ ] Idempotency verificata (test esplicito)
- [ ] No_rewrite tokens NON modificati
- [ ] Manual review entries emessi per trigger
