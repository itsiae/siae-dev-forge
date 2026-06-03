import json
import subprocess
import sys

import aggregate_intractable as ai


def test_merge_dedup(tmp_path):
    fragments = [
        [{"path": "a.ts", "reason": "private", "suggested_strategy": "reflection"}],
        [{"path": "a.ts", "reason": "private", "suggested_strategy": "reflection"},  # dup
         {"path": "b.ts", "reason": "db", "suggested_strategy": "skip"}],
    ]
    merged = ai.merge(fragments)
    paths = sorted(f["path"] for f in merged["files"])
    assert paths == ["a.ts", "b.ts"]  # dedup su path


def test_write_file(tmp_path):
    ai.write_intractable(tmp_path, [[{"path": "x.ts", "reason": "r", "suggested_strategy": "s"}]])
    data = json.loads((tmp_path / ".code-coverage" / "intractable.json").read_text())
    assert data["files"][0]["path"] == "x.ts"


# ---------------------------------------------------------------------------
# MAJOR-3: robustezza — fragment malformato, item senza path, argv guard
# ---------------------------------------------------------------------------

def test_malformed_fragment_produces_no_spurious_entries():
    """Fragment non-lista (es. dict) non deve produrre entry spurie."""
    # merge() riceve il risultato del parsing JSON: un dict invece di una lista
    # viene passato come elemento di fragments; il codice fa `for item in frag or []`
    # su una dict che itera sulle chiavi → non deve produrre entry valide
    # (le chiavi di una dict non hanno il campo 'path' come stringa di file).
    bad_fragment = {"error": "not a list"}  # dict, non lista
    merged = ai.merge([[{"path": "ok.ts", "reason": "r", "suggested_strategy": "s"}], bad_fragment])
    paths = [f["path"] for f in merged["files"]]
    # Nessuna chiave del dict bad_fragment deve diventare una entry valida
    assert "error" not in paths
    assert "not a list" not in paths
    # L'entry valida deve esserci
    assert "ok.ts" in paths


def test_item_missing_path_is_silently_ignored():
    """Item senza campo 'path' (o path=None) non produce entry nel result."""
    fragments = [
        [
            {"reason": "private", "suggested_strategy": "reflection"},  # path assente
            {"path": None, "reason": "db", "suggested_strategy": "skip"},  # path=None
            {"path": "valid.ts", "reason": "tz", "suggested_strategy": "mock"},
        ]
    ]
    merged = ai.merge(fragments)
    paths = [f["path"] for f in merged["files"]]
    assert paths == ["valid.ts"]
    assert len(merged["files"]) == 1


def test_no_args_exits_1_with_json_on_stderr():
    """Invocazione senza argomenti → exit code 1 + JSON con chiave 'error' su stderr."""
    import aggregate_intractable
    script = aggregate_intractable.__file__
    proc = subprocess.run(
        [sys.executable, script],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1, f"atteso exit 1, ottenuto {proc.returncode}"
    err_data = json.loads(proc.stderr)
    assert "error" in err_data, f"chiave 'error' assente in stderr JSON: {proc.stderr}"
