# Task 06 — `hooks/session-end` (chiama scan.py, additivo)

**Goal:** Modifica additiva all'hook esistente `hooks/session-end`: estrarre `transcript_path` dallo stdin e invocare `lib/retro/scan.py` **per ultimo** (dopo token/adoption/flush, prima dell'`echo '{}'`), best-effort, exit 0 garantito. python-less → skip silenzioso.

**Dipende da:** Task 05 (scan.py). **File coinvolti:** modifica `hooks/session-end`; crea `tests/test_retro_session_end_hook.py`.

> Vincolo: l'hook ha già un guard at-most-once a `:39` e termina con `echo '{}'; exit 0` (`:124-125`). L'inserimento NON deve cambiare questo contratto (mai bloccare, budget 10s condiviso).

## Step TDD bite-sized

### Step 1 — Test strutturale fallente
Crea `tests/test_retro_session_end_hook.py`:
```python
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
```

### Step 2 — Verifica fallimento
Run: `python3 -m pytest tests/test_retro_session_end_hook.py -q`
Output atteso: `FAILED` — `StopIteration`/assertion (scan non ancora presente nell'hook).

### Step 3 — Implementa (2 edit additivi)
**Edit A** — estrai `transcript_path`. Dopo il blocco `REASON` (attualmente `hooks/session-end:27-31`), aggiungi:
```bash
TRANSCRIPT_PATH=""
if command -v jq >/dev/null 2>&1 && [ -n "$INPUT" ]; then
    TRANSCRIPT_PATH=$(printf '%s' "$INPUT" | jq -r '.transcript_path // ""' 2>/dev/null || echo "")
fi
```

**Edit B** — invoca lo scan **per ultimo**. Subito prima di `echo '{}'` (attualmente `hooks/session-end:124`), aggiungi:
```bash
# Auto-retrospective DETECT (best-effort, ULTIMO, exit 0 — design 2026-06-22-auto-retrospective).
# Bounded in scan.py (EVENT_CAP). python-less → skip silenzioso.
if command -v python3 >/dev/null 2>&1 && [ -n "${TRANSCRIPT_PATH:-}" ] && [ -f "$TRANSCRIPT_PATH" ]; then
    DEVFORGE_SID=$(cat "${HOME}/.claude/.devforge-session-id" 2>/dev/null || echo "unknown")
    python3 "${PLUGIN_ROOT}/lib/retro/scan.py" "$TRANSCRIPT_PATH" "$DEVFORGE_SID" >/dev/null 2>&1 || true
fi
```

### Step 4 — Verifica passa
Run: `python3 -m pytest tests/test_retro_session_end_hook.py -q`
Output atteso: `3 passed`.
Smoke shell (no blocco): `printf '{"reason":"clear","transcript_path":"/non/esiste"}' | bash hooks/session-end; echo "exit=$?"`
Output atteso: termina con `{}` ed `exit=0` (transcript inesistente → scan no-op).

### Step 5 — Commit
`git add hooks/session-end tests/test_retro_session_end_hook.py && git commit -m "feat(retro): session-end invoca DETECT scan per ultimo (additivo, best-effort)"`

## Criteri di accettazione
- [ ] `transcript_path` estratto da stdin via jq; variabile `TRANSCRIPT_PATH`.
- [ ] Chiamata a `lib/retro/scan.py` collocata DOPO il guard `:39` e PRIMA di `echo '{}'`.
- [ ] Guardia `command -v python3` + `|| true` → best-effort; python-less o transcript assente = skip.
- [ ] Usa `${HOME}/.claude/.devforge-session-id` come session id.
- [ ] Smoke: hook esce 0 con `{}` anche con transcript inesistente. `tests/test_retro_session_end_hook.py` passa (3 test).
