import subprocess
import sys

import classify_intractable as ci


def test_private_methods_needs_reflection():
    src = "export class D { private mapLocale(r){ return r.x ?? '' } }"
    assert ci.classify(src, "")["classification"] == "NEEDS_REFLECTION"


def test_inline_new_needs_class_mock():
    src = "import {Svc} from './Svc'\nclass D { f(){ const s = new Svc(); return s.go() } }"
    assert ci.classify(src, "")["classification"] == "NEEDS_CLASS_MOCK"


def test_tz_needs_tz_mock():
    src = "const f = new Intl.DateTimeFormat('it-IT', { timeZone: 'Europe/Rome' })"
    assert ci.classify(src, "")["classification"] == "NEEDS_TZ_MOCK"


def test_db_only_intractable():
    src = "class D { async f(){ return await this.db.query('SELECT 1') } }"
    assert ci.classify(src, "")["classification"] == "INTRACTABLE_DB_DEPENDENT"


def test_unknown():
    assert ci.classify("export const x = 1", "")["classification"] == "INTRACTABLE_UNKNOWN"


def test_inline_new_skipped_if_already_mocked():
    src = "import {Svc} from './Svc'\nclass D { f(){ const s = new Svc(); return s.go() } }"
    spec = "vi.mock('./Svc', () => ({ Svc: vi.fn() }))"
    # già mockato → non NEEDS_CLASS_MOCK; ricade su unknown (nessun altro segnale)
    assert ci.classify(src, spec)["classification"] == "INTRACTABLE_UNKNOWN"


# ---------------------------------------------------------------------------
# M-1/M-2: noise-strip — commenti e stringhe NON devono triggerare segnali
# ---------------------------------------------------------------------------

def test_line_comment_private_no_match():
    """// private foo() in un commento non deve triggerare NEEDS_REFLECTION."""
    src = "// private foo() is not real\nexport const x = 1"
    result = ci.classify(src, "")
    assert result["classification"] == "INTRACTABLE_UNKNOWN"
    assert result["signals"]["has_private"] is False


def test_block_comment_private_no_match():
    """/** @private bar() */ non deve triggerare NEEDS_REFLECTION."""
    src = "/** @private bar() should be ignored */\nexport const x = 1"
    result = ci.classify(src, "")
    assert result["classification"] == "INTRACTABLE_UNKNOWN"
    assert result["signals"]["has_private"] is False


def test_string_literal_new_service_no_match():
    """const x = 'new Service()' (string) non deve triggerare NEEDS_CLASS_MOCK."""
    src = "const x = 'new Service()'"
    result = ci.classify(src, "")
    assert result["classification"] == "INTRACTABLE_UNKNOWN"
    assert result["signals"]["has_inline_new"] is False


def test_template_literal_new_handler_no_match():
    """Template literal `new Handler()` non deve triggerare NEEDS_CLASS_MOCK."""
    src = "const msg = `new Handler() called`"
    result = ci.classify(src, "")
    assert result["classification"] == "INTRACTABLE_UNKNOWN"
    assert result["signals"]["has_inline_new"] is False


def test_generic_single_letter_no_match():
    """new T() (generic single-letter) non deve triggerare NEEDS_CLASS_MOCK."""
    src = "function create<T>(ctor: new () => T): T { return new T(); }"
    result = ci.classify(src, "")
    assert result["classification"] == "INTRACTABLE_UNKNOWN"
    assert result["signals"]["has_inline_new"] is False


# ---------------------------------------------------------------------------
# M-3: argv guard
# ---------------------------------------------------------------------------

def test_classify_argv_guard():
    """classify_intractable.py senza argv stampa errore su stderr ed esce con 1."""
    import classify_intractable
    script = classify_intractable.__file__
    proc = subprocess.run(
        [sys.executable, script],
        capture_output=True, text=True,
    )
    assert proc.returncode == 1
    import json
    err = json.loads(proc.stderr)
    assert "error" in err


# ---------------------------------------------------------------------------
# m-1: precedenza multi-segnale
# ---------------------------------------------------------------------------

def test_precedence_private_plus_inline_new():
    """private + inline new → NEEDS_REFLECTION (private ha precedenza)."""
    src = (
        "export class D {\n"
        "  private mapLocale(r){ return r.x ?? '' }\n"
        "  f(){ const s = new Svc(); return s.go() }\n"
        "}"
    )
    assert ci.classify(src, "")["classification"] == "NEEDS_REFLECTION"


def test_precedence_inline_new_plus_tz():
    """inline new + TZ → NEEDS_CLASS_MOCK (inline_new ha precedenza su TZ)."""
    src = (
        "import {Svc} from './Svc'\n"
        "class D {\n"
        "  f(){ const s = new Svc(); return s.go() }\n"
        "  g(){ return Intl.DateTimeFormat('it-IT') }\n"
        "}"
    )
    assert ci.classify(src, "")["classification"] == "NEEDS_CLASS_MOCK"


def test_precedence_tz_plus_db():
    """TZ + DB → NEEDS_TZ_MOCK (TZ ha precedenza su DB)."""
    src = (
        "class D {\n"
        "  async f(){ return await this.db.query('SELECT 1') }\n"
        "  g(){ return Intl.DateTimeFormat('it-IT') }\n"
        "}"
    )
    assert ci.classify(src, "")["classification"] == "NEEDS_TZ_MOCK"
