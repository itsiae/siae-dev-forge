from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "session-end"


def test_extracts_transcript_path_from_stdin():
    src = HOOK.read_text(encoding="utf-8")
    assert ".transcript_path" in src          # estrae transcript_path da INPUT (jq)
    assert "TRANSCRIPT_PATH" in src


def test_invokes_scan_best_effort_after_guard():
    src = HOOK.read_text(encoding="utf-8")
    lines = src.splitlines()
    guard_idx = next(i for i, l in enumerate(lines) if "SESSION_END_GUARD" in l and "mkdir" in l)
    scan_idx = next(i for i, l in enumerate(lines) if "lib/retro/scan.py" in l)
    echo_idx = next(i for i, l in enumerate(lines) if l.strip() == "echo '{}'")
    assert guard_idx < scan_idx < echo_idx     # scan dopo il guard, prima dell'echo finale
    # best-effort: guardia python3 + || true sulla stessa zona
    block = "\n".join(lines[scan_idx - 3:scan_idx + 1])
    assert "command -v python3" in block
    assert "|| true" in lines[scan_idx] or "|| true" in lines[scan_idx + 1] if scan_idx + 1 < len(lines) else True


def test_uses_devforge_session_id():
    src = HOOK.read_text(encoding="utf-8")
    assert ".devforge-session-id" in src
