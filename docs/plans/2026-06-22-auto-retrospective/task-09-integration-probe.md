# Task 09 — Integration end-to-end + probe + no-regression

**Goal:** Test end-to-end del flusso DETECT (transcript sintetico → `scan` → staging record), verifica perf (<2s su 500 eventi), probe stile "compression-only" (il digest che alimenta MINE referenzia i fallimenti reali), e conferma no-regression sulla suite + `siae-retrospective` invariata.

**Dipende da:** Task 05, 06, 07, 08. **File coinvolti:** crea `tests/integration/test_retro_e2e.py`.

## Step TDD bite-sized

### Step 1 — Test fallente
Crea `tests/integration/test_retro_e2e.py`:
```python
import json
import time
from pathlib import Path

from lib.retro.scan import build_record, write_record
from lib.retro.digest import build_digest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _transcript(tmp_path, n_pairs, content="bash: ENOENT no such file", is_error=True, tool="Bash"):
    lines = []
    for i in range(n_pairs):
        lines.append(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": f"t{i}", "name": tool, "input": {}}]}}))
        lines.append(json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": f"t{i}", "content": content, "is_error": is_error}]}}))
    p = tmp_path / "transcript.jsonl"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def test_e2e_detect_to_staging(tmp_path):
    tr = _transcript(tmp_path, 4)                       # 4 errori Bash/FILE_NOT_FOUND
    rec = build_record(tr, "sidE2E")
    assert rec is not None
    out = write_record(rec, tmp_path / "retro-pending")
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["error_count"] == 4
    assert saved["top_categories"]["FILE_NOT_FOUND"] == 4
    assert saved["transcript_path"] == str(tr)
    assert "digest" not in saved                        # record leggero


def test_perf_under_2s_on_500_events(tmp_path):
    tr = _transcript(tmp_path, 250)                     # 250 pair = 500 eventi
    start = time.monotonic()
    build_record(tr, "sidPerf")
    assert time.monotonic() - start < 2.0


def test_probe_digest_references_real_failures(tmp_path):
    # Il materiale che l'LLM (MINE) vede deve contenere il fallimento reale.
    tr = _transcript(tmp_path, 2, content="cat: pippo.txt: No such file or directory")
    digest = build_digest(tr)
    assert "Bash" in digest
    assert "ERROR(FILE_NOT_FOUND)" in digest
    assert "pippo.txt" in digest                        # token reale del fallimento sopravvive


def test_no_regression_retrospective_present():
    # siae-retrospective manuale NON modificata da questo lavoro (AC8).
    assert (REPO_ROOT / "skills" / "siae-retrospective" / "SKILL.md").exists()
```

### Step 2 — Verifica fallimento
Run: `python3 -m pytest tests/integration/test_retro_e2e.py -q`
Output atteso: `FAILED` se i moduli/funzioni non sono completi (ordine task non rispettato).

### Step 3 — Implementa
Nessun codice di produzione nuovo: questo task verifica l'integrazione dei moduli dei task 1-8. Se un assert fallisce, il bug è nel modulo a monte → torna al task corrispondente (max 2 tentativi fix per errore).

### Step 4 — Verifica passa + suite completa (no-regression)
Run: `python3 -m pytest tests/integration/test_retro_e2e.py -q`
Output atteso: `4 passed`.
No-regression (delta vs baseline): `python3 -m pytest tests/ -q -p no:cacheprovider`
Output atteso: nessuna NUOVA failure rispetto alla baseline pre-feature (annota eventuali failure pre-esistenti note; vedi memory `feedback_no_regressions_directive`).

### Step 5 — Commit
`git add tests/integration/test_retro_e2e.py && git commit -m "test(retro): e2e detect→staging + perf <2s + probe digest + no-regression"`

## Criteri di accettazione
- [ ] E2E: transcript 4 errori → staging record con `error_count==4`, categorie corrette, `transcript_path`, senza `digest`.
- [ ] Perf: `build_record` su 500 eventi < 2s (AC1).
- [ ] Probe: `build_digest` contiene `Bash`, `ERROR(FILE_NOT_FOUND)` e il token reale `pippo.txt`.
- [ ] No-regression: `skills/siae-retrospective/SKILL.md` presente; suite `pytest tests/` senza nuove failure vs baseline.
- [ ] `tests/integration/test_retro_e2e.py` passa (4 test).
