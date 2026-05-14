# Task 31 — reference 18 criteri detail

**Stato:** [PENDING]
**SP:** 1 Human / 0.5 Augmented
**Dipendenze:** task-30

## Goal

Creare `skills/siae-release-risk/reference/release-risk-criteria.md` con detection method dettagliato per ogni criterio + esempi diff + soglie.

## File coinvolti

- Create: `skills/siae-release-risk/reference/release-risk-criteria.md`

## Step

### Step 1 — Write reference criteri

Write `skills/siae-release-risk/reference/release-risk-criteria.md` (~250 righe). Per ogni criterio include:
- Detection method (regex/grep/lib function)
- Source (diff:grep, mcp:sport-kg, evidence:coverage, baseline_cache, runners, genesis)
- Soglie
- Esempio match + non-match
- Edge case + fallback

Struttura:
```markdown
# Release Risk Criteria — Detection Reference

> Dettaglio implementativo per i 18 criteri di `siae-release-risk`.
> Vedi `docs/plans/2026-05-14-siae-release-risk-design.md` sez. 6 per overview.

## Criteri 1-15 (originali skill esterna, adattati)

### Criterion 1 — Database change (DDL/DML) — +3
**Detection:** file pattern + content pattern via `lib/release_risk/detector.py:criterion_1_db_change`
- File regex: `\.(sql|hql|xml)$|migration|liquibase|flyway|changelog|V\d+__`
- Content regex: `CREATE TABLE|ALTER TABLE|DROP TABLE|INSERT INTO|UPDATE .+ SET|DELETE FROM|ADD COLUMN|DROP COLUMN`

**Match example:** `db/migration/V42__add_email.sql` con `ALTER TABLE users ADD COLUMN email`
**Non-match:** `src/main/App.java` puro codice senza SQL

### Criterion 2 — OCP/K8s config — +2
**Detection:** `criterion_2_ocp_config`
- File regex: `\.(yaml|yml)$|openshift|ocp|deployment|route|configmap|secret|helm`
- Content regex: `kind:\s*(Deployment|Route|Secret|ConfigMap)`

[... continua per criteri 3-15 con stesso pattern ...]

## Criteri 16-18 (nuovi controlli SIAE)

### Criterion 16 — Functional regression delta — +2
**Detection:** `lib/release_risk/regression_delta.py:evaluate_criterion_16`
**Source:** baseline_cache (last release) + diff grep test disabled

**Trigger condition:**
- `coverage_delta < -2pp` (vs baseline ScoreCard.coverage)
- OR `test_disabled_count > 0` (added @Disabled/@Ignore/.skip()/xit() patterns)
- OR `test_deleted_count > 0` (file *.test|spec|__tests__ deletions)

**Prev release resolution:** `git branch -r --sort=-committerdate | grep release/` + `git log --merges` su origin/main (3 formati merge subject).

**Fallback:** primissima release o baseline non in cache → `TOOL_UNAVAILABLE`.

### Criterion 17 — Security vulnerability state (MVP HEAD-only) — +2
**Detection:** `lib/release_risk/security_state.py:evaluate_criterion_17`
**Source:** `lib/review_evidence/runners/pip_audit.py` + `npm_audit.py`

**Trigger condition (HEAD-only, NO baseline delta):**
- `findings.critical > 0` (env override: `DEVFORGE_RELEASE_RISK_SECURITY_CRITICAL_THRESHOLD`)
- OR `findings.high > 5` (env override: `DEVFORGE_RELEASE_RISK_SECURITY_HIGH_THRESHOLD`)

**Suggested follow-up `siae-security`:** se `critical > 0 OR high > 10`.

**Limitazione MVP:** count "absolute state" non "delta vs prev release". CVE pre-esistenti contribuiscono al trigger. Vedi design sez. 12 backlog v2.x per evolution.

**Fallback:** repo non Python/JS (es. Maven puri) → `TOOL_UNAVAILABLE` con nota "esegui mvn dependency-check manualmente".

### Criterion 18 — Unexpected feature in release — +2
**Detection:** `lib/release_risk/genesis.py:evaluate_criterion_18`
**Source:** Step 4b workflow + AskUserQuestion multiSelect

**3-outcome handling:**
| User behavior | Criterion 18 status | Score |
|---|---|---|
| Conferma tutte le feature | NO | 0 |
| Spunta subset (anomaly) | YES | +2 |
| Chiude / annulla (declined) | REQUIRES_INPUT | 0 + warning |
| Linear release (no merges) | NO | 0 + note |

**Parser regex feature branch:** 3 formati merge subject (`Merge branch '...'`, `Merge pull request #N from .../...`, `Merge remote-tracking branch '...'`).

---

## Soglie e configurazione

| Env var | Default | Effect |
|---|---|---|
| `DEVFORGE_RELEASE_RISK_DISABLED` | `0` | `1` → skip hook + skill |
| `DEVFORGE_RELEASE_RISK_KG_TIMEOUT_SEC` | `5` | Timeout MCP sport-kg lookup (Criterion 5) |
| `DEVFORGE_RELEASE_RISK_SECURITY_CRITICAL_THRESHOLD` | `0` | Soglia Criterion 17 critical |
| `DEVFORGE_RELEASE_RISK_SECURITY_HIGH_THRESHOLD` | `5` | Soglia Criterion 17 high |

## Skip override

```bash
touch ~/.claude/.devforge-skip-release-risk
```
File-based override del hook automatico. Rimuovi per riattivare:
```bash
rm ~/.claude/.devforge-skip-release-risk
```
```

### Step 2 — Commit

```bash
git add skills/siae-release-risk/reference/release-risk-criteria.md
git commit -m "docs(release-risk): reference 18 criteri detection method + env config"
```

## Criteri di accettazione

- [ ] Detection method per ogni criterio 1-18
- [ ] Match + non-match examples
- [ ] Env var documentation
- [ ] Skip override pattern
- [ ] Reference a design doc sez. 12 per evolution
- [ ] Commit eseguito
