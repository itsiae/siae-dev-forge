"""Test C1 fix: clean_template_placeholders post-render normalization.

Esercita la funzione bash `clean_template_placeholders` definita in
`lib/template-cache.sh` simulando il pipeline di rendering: template →
sostituzione naïve (lascia placeholder vuoti) → cleanup script → output valido.

Coverage:
  - Vitest/Jest/TS:  `import { foo,  } from '...'`   → `import { foo } from '...'`
  - Vitest/Jest/TS:  `import {  ,  } from '...'`      → riga rimossa (sintassi pulita)
  - Vitest/Jest/TS:  `import { , foo } from '...'`    → `import { foo } from '...'`
  - Python:          `from x import Foo,  `           → `from x import Foo`
  - Python:          `from x import , `               → riga rimossa
  - Java:            `import ;`                       → riga rimossa
  - Idempotenza: applicare 2 volte == 1 volta
"""
from __future__ import annotations

import subprocess
from pathlib import Path

LIB_SCRIPT = Path(__file__).resolve().parents[2] / "lib" / "template-cache.sh"


def _run_cleanup(input_text: str, tmp_path: Path, fname: str) -> str:
    """Scrive input_text su file, invoca clean_template_placeholders, ritorna risultato."""
    f = tmp_path / fname
    f.write_text(input_text, encoding="utf-8")
    cmd = (
        f"source {LIB_SCRIPT} && clean_template_placeholders '{f}'"
    )
    result = subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"cleanup failed: stderr={result.stderr}"
    return f.read_text(encoding="utf-8")


# ─── Vitest / TS / JS ────────────────────────────────────────────────────────


def test_vitest_trailing_empty_symbol_removed(tmp_path):
    """C1: SUT esporta solo foo (no class) → import { foo,  } from '...'
    deve diventare import { foo } from '...'."""
    inp = "import { foo,  } from './sut'\n"
    out = _run_cleanup(inp, tmp_path, "x.ts")
    assert "import { foo } from './sut'" in out
    assert ",  }" not in out
    assert ", }" not in out


def test_vitest_leading_empty_symbol_removed(tmp_path):
    inp = "import { , bar } from './sut'\n"
    out = _run_cleanup(inp, tmp_path, "x.ts")
    assert "import { bar } from './sut'" in out


def test_vitest_empty_import_line_dropped(tmp_path):
    """import {  } from '...' (entrambi placeholder vuoti) → riga rimossa."""
    inp = "import { describe } from 'vitest'\nimport {  } from './sut'\nconst x = 1\n"
    out = _run_cleanup(inp, tmp_path, "x.ts")
    assert "import {  } from './sut'" not in out
    assert "import { } from './sut'" not in out
    assert "import { describe } from 'vitest'" in out
    assert "const x = 1" in out


def test_vitest_residual_placeholder_treated_as_empty(tmp_path):
    """Sostituzione naïve fallita lascia {{ExportedClass}} letterale:
    cleanup deve trattarlo come simbolo vuoto."""
    inp = "import { foo, {{ExportedClass}} } from './sut'\n"
    out = _run_cleanup(inp, tmp_path, "x.ts")
    assert "{{" not in out
    assert "import { foo } from './sut'" in out


def test_vitest_valid_two_symbols_unchanged(tmp_path):
    """Regression: import con 2 simboli validi non viene alterato."""
    inp = "import { foo, BarClass } from './sut'\n"
    out = _run_cleanup(inp, tmp_path, "x.ts")
    # whitespace normalizzato a ' ' tra simboli
    assert "import { foo, BarClass } from './sut'" in out


def test_vitest_syntax_valid_after_cleanup(tmp_path):
    """C1 acceptance: after cleanup, l'output deve essere TS sintatticamente
    plausibile (no `, }` trailing). Test grep-based per evitare dipendenza da
    node/tsc nel CI runner."""
    inp = (
        "import { describe, it, expect } from 'vitest'\n"
        "import { foo, {{ExportedClass}} } from './sut'\n"
        "describe('foo', () => { it('works', () => expect(foo()).toBe(1)) })\n"
    )
    out = _run_cleanup(inp, tmp_path, "x.ts")
    # nessuna virgola trailing prima di '}'
    import re as _re
    assert _re.search(r",\s*\}", out) is None, f"trailing comma found in:\n{out}"
    # nessun placeholder residuo
    assert "{{" not in out


# ─── Python / pytest ─────────────────────────────────────────────────────────


def test_pytest_trailing_empty_symbol_removed(tmp_path):
    inp = "from src.sut import Foo, \n"
    out = _run_cleanup(inp, tmp_path, "x.py")
    assert "from src.sut import Foo" in out
    assert "import Foo, " not in out


def test_pytest_empty_import_line_dropped(tmp_path):
    """from x import {{ClassName}}, {{function_name}} → entrambi vuoti → riga rimossa."""
    inp = "import pytest\nfrom src.sut import , \nx = 1\n"
    out = _run_cleanup(inp, tmp_path, "x.py")
    assert "from src.sut import" not in out
    assert "import pytest" in out
    assert "x = 1" in out


def test_pytest_residual_placeholder(tmp_path):
    inp = "from src.sut import Foo, {{function_name}}\n"
    out = _run_cleanup(inp, tmp_path, "x.py")
    assert "from src.sut import Foo" in out
    assert "{{" not in out


# ─── Java / junit5 ───────────────────────────────────────────────────────────


def test_java_empty_import_dropped(tmp_path):
    inp = "package com.foo;\nimport ;\nimport com.bar.Baz;\nclass X {}\n"
    out = _run_cleanup(inp, tmp_path, "x.java")
    assert "import ;" not in out
    assert "import com.bar.Baz;" in out
    assert "package com.foo;" in out


def test_java_residual_placeholder_dropped(tmp_path):
    """import {{full_dep_import}} con placeholder vuoto → diventa `import ;` → drop."""
    inp = "import com.foo.Bar;\nimport {{full_dep_import}};\nclass X {}\n"
    out = _run_cleanup(inp, tmp_path, "x.java")
    assert "{{" not in out
    assert "import com.foo.Bar;" in out
    # la riga import vuota generata dal placeholder eliminato deve sparire
    assert "import ;" not in out


# ─── Idempotenza ─────────────────────────────────────────────────────────────


def test_cleanup_idempotent(tmp_path):
    """C1 invariante: clean(clean(x)) == clean(x)."""
    inp = "import { foo, {{X}} } from './a'\nfrom b import Y, {{Z}}\n"
    out1 = _run_cleanup(inp, tmp_path, "first.ts")
    out2 = _run_cleanup(out1, tmp_path, "second.ts")
    assert out1 == out2, f"cleanup non idempotente:\nout1={out1!r}\nout2={out2!r}"
