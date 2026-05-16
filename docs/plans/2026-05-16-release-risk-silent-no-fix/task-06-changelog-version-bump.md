# Task 06 — CHANGELOG + version bump 1.57.0 → 1.58.0

**Goal:** Documentare il fix nel CHANGELOG e bumpare la versione del plugin per invalidare la cache plugin degli altri sviluppatori SIAE.

## File coinvolti

- Modifica: `CHANGELOG.md` (append nuova sezione `[1.58.0]`)
- Modifica: `.claude-plugin/marketplace.json` (`plugins[0].version` 1.57.0 → 1.58.0)

## Step

### Step 1 — Append sezione CHANGELOG dopo intestazione

Inserisci dopo riga 5 (subito sotto "Il formato e' basato su [Keep a Changelog]...") e PRIMA della riga `## [1.57.0] - 2026-05-14`:

```markdown
## [1.58.0] - 2026-05-16

### Fixed — Release Risk silent-NO failures
- **Criterion 5** (Critical service): `mcp_invoker_from_json_file` ora propaga
  field `_kg_status="unavailable"` quando `describe_service.error` o
  `service_health.error` sono presenti nel JSON prefetch. `lookup_criticality`
  mappa il status a `REQUIRES_INPUT` invece di calcolare heuristic NO da
  valori normalizzati a zero. Risolve silent-NO su servizi non mappati nel KG
  e su VPN down.
- **Criterion 6** (First release): `_count_release_tags` ora ritorna tuple
  `(count, status)`. Subprocess failure ritorna `status="UNAVAILABLE"` →
  `criterion_6_first_release` mappa a `TOOL_UNAVAILABLE` invece di silent-YES
  da `return 0`. Default glob esteso a `release*, v*, *RELEASE*, *-RELEASE,
  RELEASE-*` per catturare pattern SIAE custom (es. `2.3.5-RELEASE`,
  `CERTIFICAZIONE`). Env override `DEVFORGE_RELEASE_RISK_TAG_GLOBS` (csv).

### Changed
- `criterion_6_first_release` accepts new optional param `tag_lookup_status: str = "OK"`
  (backwards-compatible default)
- `_count_release_tags` return type: `int` → `tuple[int, str]`
- `mcp_invoker_from_json_file` invoker output: returns `{"_kg_status": "unavailable", "_kg_error": ...}` on KG error instead of zero-normalized dict

### Tests
- +7 unit/integration tests (`test_release_risk_detector_6_10.py`,
  `test_release_risk_cli.py`, `test_release_risk_kg_lookup.py`)
- Integration verification on `pae-deposito-musica-fe release/2.3.4`: score
  8 → 4 (MEDIUM → LOW), Criterion 5 NO → REQUIRES_INPUT, Criterion 6 YES → NO

### Refs
- Design: `docs/plans/2026-05-16-release-risk-silent-no-fix-design.md`
- Plan: `docs/plans/2026-05-16-release-risk-silent-no-fix/`
- Bug discovery: test reale 2026-05-16 su pae-deposito-musica-fe

---
```

### Step 2 — Bump version in `.claude-plugin/marketplace.json` riga 13

Cambia:
```json
"version": "1.57.0",
```
in:
```json
"version": "1.58.0",
```

### Step 3 — Verifica modifiche

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && \
head -30 CHANGELOG.md && \
grep '"version"' .claude-plugin/marketplace.json
```

Output atteso:
- Prima sezione CHANGELOG: `## [1.58.0] - 2026-05-16`
- marketplace.json: `"version": "1.58.0",`

### Step 4 — Verifica suite completa

Run full test suite per conferma no-regression finale:
```bash
source .venv-analytics/bin/activate && \
pytest tests/test_release_risk_ -q 2>&1 | tail -5
```

Output atteso: `141 passed in X.YZs` (134 + 7 nuovi).

### Step 5 — Commit

```bash
git add CHANGELOG.md .claude-plugin/marketplace.json && \
git commit -m "chore(release): bump 1.57.0 → 1.58.0 with release-risk silent-NO fixes

CHANGELOG documents Criterion 5+6 silent-failure fixes.
Version bump invalidates plugin cache for SIAE devs on stale 1.57.0.

Refs: docs/plans/2026-05-16-release-risk-silent-no-fix/"
```

## Carry-over follow-up da review task-02 (3 issue MINOR/INFO)

Includi nella stessa unit-of-change di CHANGELOG+bump:

### A) Reference doc drift (MINOR-1)
**File:** `skills/siae-release-risk/reference/release-risk-criteria.md:54`
**Fix:** aggiorna firma documentata + nota status TOOL_UNAVAILABLE.
Cambia:
```
**Detection:** `criterion_6_first_release(git_tag_count)` · **Source:** `git:tag`
```
in:
```
**Detection:** `criterion_6_first_release(git_tag_count, tag_lookup_status="OK")` · **Source:** `git:tag`
- Status `TOOL_UNAVAILABLE` quando subprocess git fallisce (no silent-YES da count=0)
- Default tag globs: `release*, v*, *RELEASE*, *-RELEASE, RELEASE-*` (env override `DEVFORGE_RELEASE_RISK_TAG_GLOBS`)
```

### B) Exception specificity (MINOR-2)
**File:** `lib/release_risk/cli.py:186`
**Fix:** specializza bare `except Exception` per evitare silent-mask di programmer-bug:
```python
except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
        FileNotFoundError, OSError):
    return (0, "UNAVAILABLE")
```
Rationale: coerente con principio zero-silent del piano. Una `TypeError` programmatic verrebbe mascherata da UNAVAILABLE altrimenti.

### C) Env-override coverage (INFO-1)
**File:** `tests/test_release_risk_cli.py` (append)
**Fix:** aggiungi 2 test:
```python
def test_count_release_tags_uses_env_override_globs(tmp_path, monkeypatch):
    """Env DEVFORGE_RELEASE_RISK_TAG_GLOBS override usato."""
    import subprocess
    subprocess.check_call(["git", "init", "-q"], cwd=tmp_path)
    subprocess.check_call(["git", "config", "user.email", "t@t"], cwd=tmp_path)
    subprocess.check_call(["git", "config", "user.name", "t"], cwd=tmp_path)
    (tmp_path / "f").write_text("x")
    subprocess.check_call(["git", "add", "."], cwd=tmp_path)
    subprocess.check_call(["git", "commit", "-q", "-m", "init"], cwd=tmp_path)
    subprocess.check_call(["git", "tag", "custom-prod-tag"], cwd=tmp_path)
    monkeypatch.setenv("DEVFORGE_RELEASE_RISK_TAG_GLOBS", "custom-*,prod-*")
    from lib.release_risk.cli import _count_release_tags
    count, status = _count_release_tags(tmp_path)
    assert status == "OK"
    assert count >= 1, "Expected custom-prod-tag matched by custom-* env override"


def test_count_release_tags_malformed_env_falls_back_default(tmp_path, monkeypatch):
    """Env malformata (solo virgole/spazi) → fallback a default globs."""
    monkeypatch.setenv("DEVFORGE_RELEASE_RISK_TAG_GLOBS", " , , , ")
    from lib.release_risk.cli import _count_release_tags
    count, status = _count_release_tags(tmp_path)
    # tmp_path non-git → UNAVAILABLE (verifica che almeno il fallback default non crashi)
    assert status == "UNAVAILABLE"
```

## Step aggiunti

### Step 0 — Apply review follow-up A+B+C (prima di CHANGELOG)

Esegui i fix A (reference doc), B (exception specificity), C (2 nuovi test env).
Run `pytest tests/test_release_risk_ -v` per confermare 143 test PASS (138 + 2 nuovi + ... ricalcola dopo task 03+04).

## Criteri di accettazione

- [ ] CHANGELOG.md contiene sezione `[1.58.0] - 2026-05-16`
- [ ] marketplace.json plugin version = `1.58.0`
- [ ] Suite test completa PASS (141+2 = 143/143)
- [ ] **Carry-over A: reference-doc firma aggiornata**
- [ ] **Carry-over B: exception specificity in `_count_release_tags`**
- [ ] **Carry-over C: 2 nuovi test env-var override coverage**
- [ ] Commit con messaggio `chore(release):` (con carry-over note nel body)
- [ ] Ready per push + PR su `fix/pr252-followup-drift`
