"""NUDGE stage: 1 riga di promemoria se ci sono record pending e non già notificato."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def compute_nudge(pending_dir: Path, sentinel_path: Path) -> str | None:
    """Ritorna la riga di nudge se (pending non vuoto AND sentinel assente), altrimenti None."""
    pending_dir = Path(pending_dir)
    if Path(sentinel_path).exists():
        return None
    if not pending_dir.is_dir():
        return None
    records = list(pending_dir.glob("*.json"))
    if not records:
        return None
    n = len(records)
    return (
        f"Auto-retrospective: {n} sessione/i con fallimenti ripetuti in sospeso -> "
        f"lancia /forge-retrospect per estrarre lezioni (o /forge-retrospect --dismiss per ignorare)."
    )


def main() -> int:
    home = Path(os.environ.get("HOME", ""))
    pending = home / ".claude" / "devforge-state" / "retro-pending"
    sentinel = home / ".claude" / ".devforge-retro-reminded"
    try:
        msg = compute_nudge(pending, sentinel)
        if msg:
            print(msg)
            sentinel.parent.mkdir(parents=True, exist_ok=True)
            sentinel.write_text("", encoding="utf-8")   # set sentinel: nudge ≤1 per sessione
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
