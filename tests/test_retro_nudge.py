import json
from pathlib import Path

from lib.retro.nudge import compute_nudge


def _record(d, sid, errors):
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{sid}.json").write_text(json.dumps({"session_id": sid, "error_count": errors}), encoding="utf-8")


def test_no_pending_no_nudge(tmp_path):
    assert compute_nudge(tmp_path / "retro-pending", tmp_path / "sentinel") is None


def test_pending_and_sentinel_absent_nudges(tmp_path):
    pend = tmp_path / "retro-pending"
    _record(pend, "s1", 3)
    msg = compute_nudge(pend, tmp_path / "sentinel")
    assert msg is not None
    assert "/forge-retrospect" in msg
    assert "--dismiss" in msg


def test_sentinel_present_suppresses(tmp_path):
    pend = tmp_path / "retro-pending"
    _record(pend, "s1", 3)
    sentinel = tmp_path / "sentinel"
    sentinel.write_text("", encoding="utf-8")
    assert compute_nudge(pend, sentinel) is None     # già notificato in questa sessione
