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

## Criteri di accettazione

- [ ] CHANGELOG.md contiene sezione `[1.58.0] - 2026-05-16`
- [ ] marketplace.json plugin version = `1.58.0`
- [ ] Suite test completa PASS (141/141)
- [ ] Commit con messaggio `chore(release):`
- [ ] Ready per push + PR su `fix/pr252-followup-drift`
