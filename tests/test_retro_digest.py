from pathlib import Path

from lib.retro.digest import build_digest, iter_tool_events

FIX = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "retro" / "transcript_sample.jsonl"


def test_iter_tool_events_pairs_name_and_error():
    events = list(iter_tool_events(FIX))
    assert len(events) == 2                                   # 2 tool_result, riga non-json ignorata
    bash = events[0]
    assert bash.tool == "Bash" and bash.is_error is True
    assert bash.category == "FILE_NOT_FOUND"
    read = events[1]
    assert read.tool == "Read" and read.is_error is False     # content come lista di blocchi text


def test_build_digest_caps_length():
    digest = build_digest(FIX, cap=120)
    assert len(digest) <= 120
    assert "Bash" in digest


def test_iter_missing_file_returns_empty():
    assert list(iter_tool_events(Path("/non/esiste.jsonl"))) == []
