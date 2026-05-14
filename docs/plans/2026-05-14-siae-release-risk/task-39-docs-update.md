# Task 39 — README + CHANGELOG + ENV_VARS

**Stato:** [DONE]
**SP:** 1.5 Human / 0.5 Augmented
**Dipendenze:** task-38

## Goal

Aggiornare README.md (skill count + entry siae-release-risk), CHANGELOG.md (entry 1.57.0), `hooks/ENV_VARS.md` (sezione release-risk env var).

## File coinvolti

- Edit: `README.md`
- Edit: `CHANGELOG.md`
- Edit: `hooks/ENV_VARS.md`

## Step

### Step 1 — README.md update

Edit `README.md`:
- Trova sezione skill count "**41 skill**" o equivalente → cambia a "**42 skill**"
- Aggiungi entry tabella skill (in sezione "5. Release Management" o equivalente):
  ```markdown
  | `siae-release-risk` | Pre-deploy risk assessment release branch (18 criteri, score 0-36) | Rigid | 5. Release Management |
  ```
- Aggiungi entry tabella slash command:
  ```markdown
  | `/forge-release-risk` | On-demand release risk scorecard | siae-release-risk |
  ```

### Step 2 — CHANGELOG.md update

Edit `CHANGELOG.md` (append in cima dopo `# Changelog`):
```markdown
## [1.57.0] - 2026-05-14

### Added — Release Risk Assessment
- **siae-release-risk** skill: pre-deploy risk assessment per release branch (18 criteri, score 0-36, level LOW/MEDIUM/HIGH/CRITICAL, decision GO/POSTPONE/NO_GO)
- **/forge-release-risk** slash command on-demand
- **hooks/pr-release-gate** PostToolUse Bash hook automatic su `gh pr create --base main` con head `release/**` (advisory-only)
- 3 controlli aggiuntivi vs skill esterna originale:
  - Criterion 16: Functional regression delta vs precedente release (coverage + test disabled/deleted)
  - Criterion 17: Security vulnerability state (MVP HEAD-only via pip-audit + npm-audit)
  - Criterion 18: Unexpected feature in release (genesis confirmation Step 4b)
- Integrazione MCP sport-kg per critical service detection (Criterion 5)
- Cache `(branch, diff-hash, baseline-main-sha)` per skip re-run idempotenti
- Output versionato `docs/releases/<date>-<service>-<branch>.md` + PR comment auto
- Activity ledger event `release-risk` via `devforge_log`

### Changed
- Plugin manifest: bump 1.56.0 → 1.57.0
- Plugin description: count audit accurato (42 skill, 17 comandi, 5 agent, 24 hook)

### Reference
- Design doc: `docs/plans/2026-05-14-siae-release-risk-design.md` (13 ADR)
- Plan: `docs/plans/2026-05-14-siae-release-risk/` (42 task bite-sized)

### Out of scope (backlog futuro)
- CVE per-ID identification (v3.x)
- Criterion 17 delta vs baseline (v2.x — richiede extension EvidenceV2 schema)
- Maven security runner (estensione runners/)
- 4 controlli aggiuntivi: data migration delta, perf regression, contract breaking, OCP drift
- Auto-calibrazione weight via incident correlation
- CAB ticket auto-creation
- Dashboard release-risk in siae-dev-analytics
- Tag-creation hook + auto-block evolution
```

### Step 3 — hooks/ENV_VARS.md update

Edit `hooks/ENV_VARS.md` (append nuova sezione):
```markdown
## Release Risk Assessment

| Env var | Default | Effect |
|---|---|---|
| `DEVFORGE_RELEASE_RISK_DISABLED` | `0` | `1` → skip hook pr-release-gate + slash skill (kill switch) |
| `DEVFORGE_RELEASE_RISK_KG_TIMEOUT_SEC` | `5` | Timeout MCP sport-kg lookup (Criterion 5 critical service detection) |
| `DEVFORGE_RELEASE_RISK_SECURITY_CRITICAL_THRESHOLD` | `0` | Soglia Criterion 17 critical CVE count per trigger YES (>) |
| `DEVFORGE_RELEASE_RISK_SECURITY_HIGH_THRESHOLD` | `5` | Soglia Criterion 17 high CVE count per trigger YES (>) |

### Skip override file-based

```bash
# Disabilita hook pr-release-gate
touch ~/.claude/.devforge-skip-release-risk

# Riabilita
rm ~/.claude/.devforge-skip-release-risk
```

### Trigger automatico

Hook `pr-release-gate` (PostToolUse Bash, 30s timeout) si attiva su:
- `gh pr create --base main` AND
- branch corrente `release/**`

Posta scorecard come PR comment con idempotency marker `<!-- release-risk:<diff-hash> -->`.
```

### Step 4 — Verifica

```bash
grep -c "1.57.0\|siae-release-risk\|/forge-release-risk" README.md CHANGELOG.md hooks/ENV_VARS.md
```
Output atteso: ≥10 match totali.

### Step 5 — Commit

```bash
git add README.md CHANGELOG.md hooks/ENV_VARS.md
git commit -m "docs(release-risk): README skill count + CHANGELOG 1.57.0 + ENV_VARS release-risk section"
```

## Criteri di accettazione

- [ ] README.md skill count `42 skill`
- [ ] README.md entry siae-release-risk + /forge-release-risk
- [ ] CHANGELOG.md sezione `## [1.57.0] - 2026-05-14`
- [ ] hooks/ENV_VARS.md sezione "Release Risk Assessment" con 4 env var
- [ ] Skip override documentato
- [ ] Commit eseguito
