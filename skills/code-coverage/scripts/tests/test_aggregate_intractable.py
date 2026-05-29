import json
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
    out = ai.write_intractable(tmp_path, [[{"path": "x.ts", "reason": "r", "suggested_strategy": "s"}]])
    data = json.loads((tmp_path / ".code-coverage" / "intractable.json").read_text())
    assert data["files"][0]["path"] == "x.ts"
