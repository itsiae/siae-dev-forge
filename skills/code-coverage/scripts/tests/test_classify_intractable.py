import classify_intractable as ci


def test_private_methods_needs_reflection():
    src = "export class D { private mapLocale(r){ return r.x ?? '' } }"
    assert ci.classify(src, "")["classification"] == "NEEDS_REFLECTION"


def test_inline_new_needs_class_mock():
    src = "import {S} from './S'\nclass D { f(){ const s = new S(); return s.go() } }"
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
    src = "import {S} from './S'\nclass D { f(){ const s = new S(); return s.go() } }"
    spec = "vi.mock('./S', () => ({ S: vi.fn() }))"
    # già mockato → non NEEDS_CLASS_MOCK; ricade su unknown (nessun altro segnale)
    assert ci.classify(src, spec)["classification"] == "INTRACTABLE_UNKNOWN"
