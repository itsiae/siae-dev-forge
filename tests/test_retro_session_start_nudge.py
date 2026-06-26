from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "session-start"


def test_session_start_invokes_nudge_and_wires_into_context():
    src = HOOK.read_text(encoding="utf-8")
    assert "lib/retro/nudge.py" in src                 # invoca nudge.py
    assert "retro_nudge_section" in src                # definisce la sezione
    assert "${retro_nudge_section}" in src             # la interpola nel context
    # la sezione è interpolata DENTRO la stringa session_context
    ctx_line = next(l for l in src.splitlines() if l.startswith("session_context="))
    assert "${retro_nudge_section}" in ctx_line
    assert "escape_for_json" in src                    # output escapato per JSON


def test_sentinel_rm_still_present():
    src = HOOK.read_text(encoding="utf-8")
    assert 'rm -f "${HOME}/.claude/.devforge-retro-reminded"' in src   # invariato (:475)
