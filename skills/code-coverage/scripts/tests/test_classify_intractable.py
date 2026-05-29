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
# CRITICAL: contratto campo suggested_strategy (non suggested_action)
# ---------------------------------------------------------------------------

def test_output_has_suggested_strategy_not_suggested_action():
    """classify() deve restituire 'suggested_strategy', NON 'suggested_action'."""
    result = ci.classify("export const x = 1", "")
    assert "suggested_strategy" in result, "chiave suggested_strategy assente"
    assert "suggested_action" not in result, "chiave suggested_action non deve essere presente"


def test_suggested_strategy_not_empty_for_reflection():
    """suggested_strategy non deve essere vuoto per NEEDS_REFLECTION."""
    src = "export class D { private mapLocale(r){ return r.x ?? '' } }"
    result = ci.classify(src, "")
    assert result["suggested_strategy"] != ""


def test_suggested_strategy_not_empty_for_class_mock():
    """suggested_strategy non deve essere vuoto per NEEDS_CLASS_MOCK."""
    src = "import {Svc} from './Svc'\nclass D { f(){ const s = new Svc(); return s.go() } }"
    result = ci.classify(src, "")
    assert result["suggested_strategy"] != ""


def test_suggested_strategy_not_empty_for_tz_mock():
    """suggested_strategy non deve essere vuoto per NEEDS_TZ_MOCK."""
    src = "const f = new Intl.DateTimeFormat('it-IT', { timeZone: 'Europe/Rome' })"
    result = ci.classify(src, "")
    assert result["suggested_strategy"] != ""


def test_chain_classify_aggregate_produces_suggested_strategy(tmp_path):
    """Simula catena classify→aggregate: intractable.json ha suggested_strategy NON vuoto."""
    import aggregate_intractable as ai

    src = "export class D { private mapLocale(r){ return r.x ?? '' } }"
    classification = ci.classify(src, "")

    # Costruisci il fragment come fa il coordinatore
    fragment = [
        {
            "path": "src/dao/D.ts",
            "reason": classification["classification"],
            "suggested_strategy": classification["suggested_strategy"],
        }
    ]
    merged = ai.merge([fragment])

    assert len(merged["files"]) == 1
    entry = merged["files"][0]
    assert "suggested_strategy" in entry
    assert entry["suggested_strategy"] != "", (
        "suggested_strategy è vuoto: Block 9 mostrerebbe strategia vuota"
    )


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


# ---------------------------------------------------------------------------
# ISSUE-4: _PRIVATE_RE deve gestire modificatori static|override|abstract
# ---------------------------------------------------------------------------

def test_private_static_method_needs_reflection():
    """private static foo() deve triggerare NEEDS_REFLECTION (ISSUE-4)."""
    src = "export class D { private static compute(x: number) { return x * 2; } }"
    result = ci.classify(src, "")
    assert result["classification"] == "NEEDS_REFLECTION", (
        f"private static deve → NEEDS_REFLECTION, got {result['classification']}"
    )
    assert "compute" in result["private_methods"]


def test_private_override_method_needs_reflection():
    """private override foo() deve triggerare NEEDS_REFLECTION (ISSUE-4)."""
    src = "export class D { private override render() { return null; } }"
    result = ci.classify(src, "")
    assert result["classification"] == "NEEDS_REFLECTION", (
        f"private override deve → NEEDS_REFLECTION, got {result['classification']}"
    )


def test_private_abstract_method_needs_reflection():
    """private abstract foo() deve triggerare NEEDS_REFLECTION (ISSUE-4)."""
    src = "export abstract class D { private abstract process(): void; }"
    result = ci.classify(src, "")
    assert result["classification"] == "NEEDS_REFLECTION", (
        f"private abstract deve → NEEDS_REFLECTION, got {result['classification']}"
    )


# ---------------------------------------------------------------------------
# ISSUE-5: _TZ_RE deve avere word boundary su Intl (NotIntl.foo falso positivo)
# ---------------------------------------------------------------------------

def test_not_intl_no_tz_mock():
    """NotIntl.foo NON deve triggerare NEEDS_TZ_MOCK (ISSUE-5)."""
    src = "const x = NotIntl.foo();"
    result = ci.classify(src, "")
    assert result["classification"] != "NEEDS_TZ_MOCK", (
        "NotIntl.foo non deve causare NEEDS_TZ_MOCK: falso positivo!"
    )
    assert result["signals"]["has_tz"] is False


# ---------------------------------------------------------------------------
# ISSUE-6: _BUILTINS deve includere TextEncoder, TextDecoder e altri
# ---------------------------------------------------------------------------

def test_new_text_encoder_no_class_mock():
    """new TextEncoder() NON deve triggerare NEEDS_CLASS_MOCK (ISSUE-6)."""
    src = "function encode(s: string) { return new TextEncoder().encode(s); }"
    result = ci.classify(src, "")
    assert result["classification"] != "NEEDS_CLASS_MOCK", (
        "TextEncoder è un builtin: non deve triggerare NEEDS_CLASS_MOCK"
    )
    assert "TextEncoder" not in result["inline_classes"]


def test_new_text_decoder_no_class_mock():
    """new TextDecoder() NON deve triggerare NEEDS_CLASS_MOCK (ISSUE-6)."""
    src = "function decode(b: ArrayBuffer) { return new TextDecoder().decode(b); }"
    result = ci.classify(src, "")
    assert result["classification"] != "NEEDS_CLASS_MOCK"
    assert "TextDecoder" not in result["inline_classes"]


def test_new_url_search_params_no_class_mock():
    """new URLSearchParams() NON deve triggerare NEEDS_CLASS_MOCK (ISSUE-6)."""
    src = "const p = new URLSearchParams('a=1');"
    result = ci.classify(src, "")
    assert result["classification"] != "NEEDS_CLASS_MOCK"
    assert "URLSearchParams" not in result["inline_classes"]


def test_new_weak_map_no_class_mock():
    """new WeakMap() NON deve triggerare NEEDS_CLASS_MOCK (ISSUE-6)."""
    src = "const m = new WeakMap();"
    result = ci.classify(src, "")
    assert result["classification"] != "NEEDS_CLASS_MOCK"
    assert "WeakMap" not in result["inline_classes"]


def test_new_data_view_no_class_mock():
    """new DataView() NON deve triggerare NEEDS_CLASS_MOCK (ISSUE-6)."""
    src = "const dv = new DataView(buffer);"
    result = ci.classify(src, "")
    assert result["classification"] != "NEEDS_CLASS_MOCK"
    assert "DataView" not in result["inline_classes"]
