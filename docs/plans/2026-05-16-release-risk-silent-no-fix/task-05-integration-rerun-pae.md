# Task 05 — Integration test: re-run scorecard pae-deposito-musica-fe

**Goal:** Verificare end-to-end che il fix produca scorecard corretto su repo reale.
Score atteso: **8 → 4 LOW** (Criterion 6 NO + Criterion 5 REQUIRES_INPUT).

## File coinvolti

- Lettura: `/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/pae-deposito-musica-fe/` (repo target)
- Output (temporaneo, non commit): scorecard rigenerata in `docs/releases/` del repo target

## Step

### Step 1 — Rigenera JSON prefetch KG per pae-deposito-musica-fe

I dati MCP raccolti durante il test originale sono già in `/tmp/release-risk-kg-pae-deposito-musica-fe.json`. Verifica che esistano i field `describe_service.error` e `service_health.error`:

```bash
cat /tmp/release-risk-kg-pae-deposito-musica-fe.json | python3 -m json.tool
```

Output atteso:
```json
{
  "service_name": "pae-deposito-musica-fe",
  "describe_service": {
    "error": "Service 'pae-deposito-musica-fe' not found",
    ...
  },
  "service_health": {
    "status": "CRITICO",
    "error": "ES non raggiungibile — VPN non attiva",
    ...
  }
}
```

Se il file è stato cancellato, ricrealo con:
```bash
cat > /tmp/release-risk-kg-pae-deposito-musica-fe.json <<'EOF'
{
  "service_name": "pae-deposito-musica-fe",
  "describe_service": {"error": "Service 'pae-deposito-musica-fe' not found"},
  "service_health": {"status": "CRITICO", "error": "ES non raggiungibile — VPN non attiva", "sample_size": 0}
}
EOF
```

### Step 2 — Verifica diff fixtures ancora validi

```bash
ls -la /tmp/pae-diff-files.txt /tmp/pae-diff-content.txt
wc -l /tmp/pae-diff-files.txt /tmp/pae-diff-content.txt
```

Output atteso: `5` files, `143` lines content. Se diversi, rigenera:
```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/pae-deposito-musica-fe" && \
git diff origin/main...origin/release/2.3.4 --name-only > /tmp/pae-diff-files.txt && \
git diff origin/main...origin/release/2.3.4 > /tmp/pae-diff-content.txt
```

### Step 3 — Re-run CLI con `--no-cache`

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && \
source .venv-analytics/bin/activate && \
python -m lib.release_risk assess \
  --repo-root "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/pae-deposito-musica-fe" \
  --branch "release/2.3.4" \
  --service "pae-deposito-musica-fe" \
  --diff-files /tmp/pae-diff-files.txt \
  --diff-content /tmp/pae-diff-content.txt \
  --version "2.3.4" \
  --owner "lorenzo.detomasi" \
  --release-date "2026-05-16" \
  --user-impact-ge-50 "false" \
  --kg-data-file /tmp/release-risk-kg-pae-deposito-musica-fe.json \
  --no-cache \
  --trigger manual
```

Output atteso (JSON ultima riga):
```json
{"cached": false, "output_path": "...", "level": "LOW", "decision": "GO", "score": 4, "diff_hash": "..."}
```

**Asserzioni:**
- `score` deve essere ≤ 4 (era 8)
- `level` deve essere `LOW` (era MEDIUM)
- `decision` deve essere `GO` (era GO_WITH_MONITORING)

### Step 4 — Verifica scorecard contenuto

```bash
cat "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/pae-deposito-musica-fe/docs/releases/2026-05-16-pae-deposito-musica-fe-release_2.3.4.md" | grep -E '^\| (5|6) \|'
```

Output atteso:
```
| 5 | **Critical service** | ⚠️ REQUIRES_INPUT | +3 | kg_unavailable: Service 'pae-deposito-musica-fe' not found
| 6 | **First release** | ✅ NO | +2 | git_tag_count=N (where N>=2 per i tag *-RELEASE)
```

### Step 5 — Documenta esito nel design doc

Append a `docs/plans/2026-05-16-release-risk-silent-no-fix-design.md` sezione 12:

```markdown
## 12. Integration verification (task-05)

Re-run scorecard su `pae-deposito-musica-fe release/2.3.4` post-fix:

| Metric | Pre-fix (PR #252) | Post-fix |
|---|---|---|
| Score | 8/36 | ≤4/36 |
| Level | MEDIUM | LOW |
| Decision | GO_WITH_MONITORING | GO |
| Criterion 5 | ❌ NO (silent) | ⚠️ REQUIRES_INPUT |
| Criterion 6 | ❌ YES (false positive) | ✅ NO (`2.3.5-RELEASE` matched) |

Output JSON CLI: `{"score": 4, "level": "LOW", "decision": "GO", ...}` ✅
```

### Step 6 — Commit documentazione

Il file in `docs/releases/` del repo target NON va commitato qui (è repo separato). Solo aggiornamento del design doc nel repo dev-forge:

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && \
git add docs/plans/2026-05-16-release-risk-silent-no-fix-design.md && \
git commit -m "docs(release-risk): integration verification post-fix on pae

Score 8 → 4 (MEDIUM → LOW) confirmed on pae-deposito-musica-fe release/2.3.4
Criterion 5: NO → REQUIRES_INPUT (KG miss explicit)
Criterion 6: YES → NO (tag pattern 2.3.5-RELEASE matched)

Refs: docs/plans/2026-05-16-release-risk-silent-no-fix/task-05"
```

## Criteri di accettazione

- [ ] CLI ritorna `level=LOW` + `decision=GO` + `score<=4`
- [ ] Criterion 5 evidence contiene `kg_unavailable:`
- [ ] Criterion 6 evidence contiene `git_tag_count=` con N≥2
- [ ] Design doc aggiornato con sezione 12 integration verification
- [ ] Commit `docs(release-risk):` creato
