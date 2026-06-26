import json
from pathlib import Path

from lib.retro.scan import build_record, write_record


def _make_transcript(tmp_path, n_errors):
    lines = []
    for i in range(n_errors):
        lines.append(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": f"t{i}", "name": "Bash", "input": {}}]}}))
        lines.append(json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": f"t{i}",
             "content": "bash: ENOENT no such file", "is_error": True}]}}))
    p = tmp_path / "t.jsonl"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def test_below_threshold_returns_none(tmp_path):
    # 2 errori, nessun pattern ripetuto ≥2 di categorie diverse → sotto soglia
    p = tmp_path / "t.jsonl"
    p.write_text(
        json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "a", "name": "Bash", "input": {}}]}}) + "\n" +
        json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "a", "content": "Permission denied", "is_error": True}]}}) + "\n" +
        json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "b", "name": "Read", "input": {}}]}}) + "\n" +
        json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "b", "content": "command not found", "is_error": True}]}}),
        encoding="utf-8",
    )
    assert build_record(p, "sid1") is None     # 2 errori, categorie diverse, nessun ripetuto ≥2


def test_three_errors_triggers(tmp_path):
    p = _make_transcript(tmp_path, 3)
    rec = build_record(p, "sid2")
    assert rec is not None
    assert rec["error_count"] == 3
    assert rec["session_id"] == "sid2"
    assert rec["transcript_path"] == str(p)
    assert "digest" not in rec                  # record LEGGERO
    assert rec["top_categories"]["FILE_NOT_FOUND"] == 3


def test_repeated_pattern_triggers_under_three(tmp_path):
    p = _make_transcript(tmp_path, 2)           # 2x (Bash, FILE_NOT_FOUND) → pattern ripetuto ≥2
    rec = build_record(p, "sid3")
    assert rec is not None
    assert ["Bash", "FILE_NOT_FOUND", 2] in [list(x) for x in rec["repeated_patterns"]]


def test_write_record(tmp_path):
    rec = {"session_id": "sidW", "error_count": 3}
    out = write_record(rec, tmp_path / "retro-pending")
    assert out.name == "sidW.json"
    assert json.loads(out.read_text(encoding="utf-8"))["error_count"] == 3
