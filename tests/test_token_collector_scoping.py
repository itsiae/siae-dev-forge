"""Test scoping per-sessione del token-collector (fix accuratezza 2026-06-16).

Copre:
- Task 01: resolve_session_dir() auto-derive da .devforge-session-id + no fallback globale
- Task 02: fail-closed (update/init/write_* no-op quando dir non risolvibile)
- Task 03: reset by_model su cambio .jsonl in update()
- Task 04: campo token_state_complete in session_fields_line (f14)

Import del modulo con trattino via importlib (pattern test_token_collector.py).
STATE_DIR viene monkeypatchato su una tmp dir per isolamento totale.
"""
import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
SCRIPT = REPO_ROOT / "lib" / "token-collector.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("token_collector_scoping", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tc = _load_module()


@pytest.fixture
def state(tmp_path, monkeypatch):
    """STATE_DIR isolato in tmp + env pulito (no DEVFORGE_SESSION_DIR)."""
    monkeypatch.setattr(tc, "STATE_DIR", tmp_path)
    monkeypatch.delenv("DEVFORGE_SESSION_DIR", raising=False)
    return tmp_path


def _write_sid(state_dir: Path, sid: str, make_dir: bool = True) -> Path:
    (state_dir / ".devforge-session-id").write_text(sid + "\n", encoding="utf-8")
    session_dir = state_dir / "devforge-state" / sid
    if make_dir:
        session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


# --- Task 01: resolve_session_dir ---

def test_resolve_from_sid_file_when_env_unset(state):
    session_dir = _write_sid(state, "abc12345")
    assert tc.resolve_session_dir() == str(session_dir)


def test_resolve_prefers_env_var_when_dir_exists(state, tmp_path, monkeypatch):
    _write_sid(state, "abc12345")
    explicit = tmp_path / "explicit-session"
    explicit.mkdir()
    monkeypatch.setenv("DEVFORGE_SESSION_DIR", str(explicit))
    assert tc.resolve_session_dir() == str(explicit)


def test_resolve_falls_back_to_sid_when_env_dir_missing(state, monkeypatch):
    session_dir = _write_sid(state, "abc12345")
    monkeypatch.setenv("DEVFORGE_SESSION_DIR", "/nonexistent/path/xyz")
    assert tc.resolve_session_dir() == str(session_dir)


def test_resolve_none_when_no_sid_file(state):
    assert tc.resolve_session_dir() is None


def test_resolve_none_when_sid_dir_missing(state):
    _write_sid(state, "abc12345", make_dir=False)
    assert tc.resolve_session_dir() is None


def test_resolve_strips_trailing_newline_crlf(state):
    (state / ".devforge-session-id").write_text("deadbeef\r\n", encoding="utf-8")
    session_dir = state / "devforge-state" / "deadbeef"
    session_dir.mkdir(parents=True)
    assert tc.resolve_session_dir() == str(session_dir)


# --- Task 01/02: NO global fallback + fail-closed ---

def test_no_global_file_created_when_unresolved(state):
    """write_stats/update non devono MAI creare il file globale per-progetto."""
    tc.write_stats(tc.empty_stats())
    tc.write_cursor("x", 0)
    tc.write_usage_index({})
    leftovers = list(state.glob(".devforge-token-*"))
    assert leftovers == [], f"stato globale creato: {leftovers}"


def test_update_noop_when_unresolved(state, monkeypatch):
    # find_session_jsonl non deve nemmeno essere raggiunto; se lo fosse, fallirebbe comunque
    monkeypatch.setattr(tc, "find_session_jsonl", lambda: (_ for _ in ()).throw(AssertionError("update non deve cercare jsonl se dir non risolvibile")))
    tc.update()  # no exception, no-op


def test_init_noop_when_unresolved(state):
    tc.init()
    assert list(state.glob(".devforge-token-*")) == []


def test_state_written_in_session_dir_when_resolved(state):
    session_dir = _write_sid(state, "abc12345")
    tc.write_stats(tc.empty_stats())
    assert (session_dir / "token-stats.json").is_file()
    assert list(state.glob(".devforge-token-*")) == []


# --- Task 04: token_state_complete f14 ---

def test_fields_has_token_state_complete_field(state):
    line = tc.session_fields_line(tc.empty_stats())
    parts = line.split("\t")
    assert len(parts) == 14, f"attesi 14 campi, trovati {len(parts)}"
    assert parts[13] in ("true", "false")


def test_token_state_complete_false_when_unresolved(state):
    line = tc.session_fields_line(tc.empty_stats())
    assert line.split("\t")[13] == "false"


def test_token_state_complete_true_when_resolved_and_nonzero(state):
    _write_sid(state, "abc12345")
    stats = tc.empty_stats()
    stats["total"] = 12345
    line = tc.session_fields_line(stats)
    assert line.split("\t")[13] == "true"


def test_five_per_type_fields_present_with_empty_by_model(state):
    """Causa C: i 5 campi per-tipo restano presenti anche con by_model vuoto."""
    stats = tc.empty_stats()
    stats.update(input=10, output=20, cache_read=30, cache_write_5m=40, cache_write_1h=50, total=150)
    parts = tc.session_fields_line(stats).split("\t")
    # f1 total, f2 output, f5 input, f6 cache_read, f7 cw5m, f8 cw1h
    assert parts[0] == "150"
    assert parts[1] == "20"
    assert parts[4] == "10"
    assert parts[5] == "30"
    assert parts[6] == "40"
    assert parts[7] == "50"
    assert parts[8] == "{}"  # by_model vuoto


# --- Task 03: reset by_model su cambio .jsonl ---

def test_by_model_reset_on_jsonl_switch(state, tmp_path, monkeypatch):
    """update() che passa a un .jsonl diverso non deve trasportare by_model precedente."""
    session_dir = _write_sid(state, "abc12345")
    # stato con by_model "congelato" di un file precedente, cursore a EOF di file_old
    file_old = tmp_path / "old.jsonl"
    file_old.write_text("", encoding="utf-8")  # vuoto -> size 0
    stale = tc.empty_stats()
    stale["by_model"] = {"claude-opus-4-8": 703803830}
    stale["by_model_tokens"] = {"claude-opus-4-8": {"cache_read": 703803830, "input": 0, "output": 0, "cache_write_5m": 0, "cache_write_1h": 0}}
    stale["total"] = 0  # forza il ramo "newer file"
    tc.write_stats(stale)
    tc.write_cursor(str(file_old), 0)

    # un file più recente con una usage entry sonnet; l'override forza find_session_jsonl
    # a ritornarlo (simula il file di sessione più recente, diverso dal cursore).
    file_new = tmp_path / "new.jsonl"
    entry = {"message": {"model": "claude-sonnet-4-6", "id": "msg_1",
                          "usage": {"input_tokens": 100, "output_tokens": 200,
                                    "cache_read_input_tokens": 0}}}
    file_new.write_text(json.dumps(entry) + "\n", encoding="utf-8")
    monkeypatch.setenv("DEVFORGE_TOKEN_SESSION_JSONL", str(file_new))

    tc.update()
    result = json.loads((session_dir / "token-stats.json").read_text())
    assert "claude-opus-4-8" not in result.get("by_model", {}), \
        "by_model Opus congelato trasportato sul nuovo file"


# --- Task 09: cleanup file globali legacy ---

def test_init_removes_legacy_global_files(state, tmp_path, monkeypatch):
    _write_sid(state, "abc12345")
    jsonl = tmp_path / "session.jsonl"
    jsonl.write_text("", encoding="utf-8")
    monkeypatch.setenv("DEVFORGE_TOKEN_SESSION_JSONL", str(jsonl))
    ph = tc.project_hash()
    legacy = [state / f".devforge-token-{k}-{ph}" for k in ("cursor", "stats", "usage-index")]
    for f in legacy:
        f.write_text("stale", encoding="utf-8")

    tc.init()

    for f in legacy:
        assert not f.exists(), f"file legacy non rimosso: {f}"


def test_cleanup_legacy_idempotent_when_absent(state, tmp_path, monkeypatch):
    _write_sid(state, "abc12345")
    jsonl = tmp_path / "session.jsonl"
    jsonl.write_text("", encoding="utf-8")
    monkeypatch.setenv("DEVFORGE_TOKEN_SESSION_JSONL", str(jsonl))
    tc.init()  # nessun file legacy presente: nessuna eccezione


# --- Task 06: semantica delta primo/secondo commit (Causa B) ---

def _append_usage(path: Path, msg_id: str, output: int, inp: int = 0):
    entry = {"message": {"model": "claude-opus-4-8", "id": msg_id,
                         "usage": {"input_tokens": inp, "output_tokens": output,
                                   "cache_read_input_tokens": 0}}}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def test_delta_first_commit_equals_cum_second_is_genuine(state, tmp_path, monkeypatch):
    """E2E: init reset per-sessione → 1° commit delta==cum (corretto), 2° commit delta<cum.

    Replica la formula di hooks/post-commit-review (dt = curr.total - prev.total,
    cum = curr.total) sopra lo stato per-sessione prodotto da token-collector update().
    """
    _write_sid(state, "abc12345")
    jsonl = tmp_path / "session.jsonl"
    jsonl.write_text("", encoding="utf-8")
    monkeypatch.setenv("DEVFORGE_TOKEN_SESSION_JSONL", str(jsonl))

    tc.init()  # offset a inizio sessione, stats azzerate

    # --- primo commit: una usage entry, poi snapshot ---
    _append_usage(jsonl, "msg_1", output=1000)
    tc.update()
    curr1 = tc.read_stats()
    prev = {}  # token-at-last-commit.json non esiste al primo commit
    dt1 = curr1["total"] - prev.get("total", 0)
    cum1 = curr1["total"]
    assert dt1 == cum1, "al primo commit delta deve uguagliare il cumulativo (intera sessione)"
    assert dt1 == 1000

    # snapshot post-commit-1 = curr1
    prev = curr1

    # --- secondo commit: altra usage entry ---
    _append_usage(jsonl, "msg_2", output=500)
    tc.update()
    curr2 = tc.read_stats()
    dt2 = curr2["total"] - prev["total"]
    cum2 = curr2["total"]
    assert dt2 == 500, "delta del 2° commit deve essere l'incremento reale"
    assert dt2 < cum2, "delta del 2° commit deve essere < cumulativo (non ambiguo)"
    assert cum2 == 1500


def test_token_state_complete_true_via_full_pipeline(state, tmp_path, monkeypatch):
    """E2E completo init→update→fields: token_state_complete=true quando ci sono token reali."""
    _write_sid(state, "abc12345")
    jsonl = tmp_path / "session.jsonl"
    jsonl.write_text("", encoding="utf-8")
    monkeypatch.setenv("DEVFORGE_TOKEN_SESSION_JSONL", str(jsonl))
    tc.init()
    _append_usage(jsonl, "msg_1", output=700)
    tc.update()
    line = tc.session_fields_line(tc.read_stats())
    assert line.split("\t")[13] == "true"


def test_truncation_resets_breakdowns(state, tmp_path, monkeypatch):
    """File troncato (file_size < offset): lo stato è riletto da 0, niente carry-forward."""
    session_dir = _write_sid(state, "abc12345")
    jsonl = tmp_path / "session.jsonl"
    jsonl.write_text("", encoding="utf-8")
    monkeypatch.setenv("DEVFORGE_TOKEN_SESSION_JSONL", str(jsonl))
    # stato stale con cursore oltre la dimensione attuale del file (simula truncation)
    stale = tc.empty_stats()
    stale["by_model"] = {"claude-opus-4-8": 703803830}
    stale["input"] = 703803830
    stale["total"] = 703803830
    tc.write_stats(stale)
    tc.write_cursor(str(jsonl), 999999)  # offset > file_size (0) → ramo truncation
    _append_usage(jsonl, "msg_new", output=300)
    tc.update()
    result = json.loads((session_dir / "token-stats.json").read_text())
    assert result["by_model"] == {"claude-opus-4-8": 300}, "carry-forward su truncation"
    assert result["total"] == 300
