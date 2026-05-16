# Release Risk Criteria — Detection Reference

> Dettaglio implementativo per i 18 criteri di `siae-release-risk`.
> Vedi `docs/plans/2026-05-14-siae-release-risk-design.md` sez. 6 per overview.

## Criteri 1-15 (originali skill esterna, adattati)

### Criterion 1 — Database change (DDL/DML) — +3
**Detection:** `lib/release_risk/detector.py:criterion_1_db_change`
**Source:** `diff:grep`
- File regex: `\.(sql|hql|xml)$|migration|liquibase|flyway|changelog|V\d+__`
- Content regex: `CREATE TABLE|ALTER TABLE|DROP TABLE|INSERT INTO|UPDATE .+ SET|DELETE FROM|ADD COLUMN|DROP COLUMN`

**Match example:** `db/migration/V42__add_email.sql` con `ALTER TABLE users ADD COLUMN email`
**Non-match:** `src/main/App.java` puro codice senza SQL

### Criterion 2 — OCP/K8s config — +2
**Detection:** `criterion_2_ocp_config` · **Source:** `diff:grep`
- File regex: `\.(yaml|yml)$|openshift|ocp|deployment|route|configmap|secret|helm|k8s|kubernetes`
- Content regex: `kind:\s*(Deployment|Route|Secret|ConfigMap)`

**Match:** `k8s/deployment.yaml` con `kind: Deployment` · **Non-match:** Java puro

### Criterion 3 — Breaking API changes — +3
**Detection:** `criterion_3_breaking_api` · **Source:** `diff:grep`
- Content regex: `^-\s*.*(@(Get|Post|Put|Delete|Path)Mapping|@RequestMapping)` (annotation rimossa)

**Match:** rimozione di `@GetMapping("/api/v1/users")` · **Non-match:** aggiunta endpoint nuovo

### Criterion 4 — External dependencies changed — +2
**Detection:** `criterion_4_ext_deps` · **Source:** `diff:files`
- File set: `pom.xml, package.json, package-lock.json, requirements.txt, build.gradle, Cargo.toml, go.mod`

**Match:** modifica `pom.xml` · **Non-match:** modifica src puro

### Criterion 5 — Critical service — +3
**Detection:** `lib/release_risk/kg_lookup.py:lookup_criticality` · **Source:** `mcp:sport-kg` o `ask:user`

**Prefix KG match:** `sport-/pop-/pae-/ciam-/dol-be/digital-channels-sport-/esb-sport-/esb-sso-/mag-concertini-/portal-apigateway-/ttpp-`

**Heuristic 6 condizioni (YES se ≥1 true):**
1. `has_payment_chain == True`
2. `auth_chain_length >= 3`
3. `"ciam" in service_name`
4. `traffic_rps_p95 > 100`
5. `drools_rules_count > 5`
6. `called_by_count >= 3 AND traffic_rps_p95 > 10`

**Fallback:** servizio non in prefix → `REQUIRES_INPUT` (ask user). MCP timeout/error → `TOOL_UNAVAILABLE`.

**Bridge ADR-2:** SKILL.md prefetcha JSON via MCP tool e lo passa al CLI via `--kg-data-file` (vedi `mcp_invoker_from_json_file`).

### Criterion 6 — First release — +2
**Detection:** `criterion_6_first_release(git_tag_count, tag_lookup_status="OK")` · **Source:** `git:tag`
- Status `TOOL_UNAVAILABLE` quando subprocess git fallisce (no silent-YES da count=0)
- Default tag globs: `release*, v*, *RELEASE*, *-RELEASE, RELEASE-*` (env override `DEVFORGE_RELEASE_RISK_TAG_GLOBS`)
- YES se `git tag --list 'release*' 'v*'` count == 0

### Criterion 7 — Complex rollback — +2
**Detection:** `criterion_7_complex_rollback(c1_status, c9_status, diff_content)` · **Source:** `inferred`
- YES se `c1.status == "YES" OR c9.status == "YES"` (implied)
- OR diff content match `irreversible|no rollback|one[- ]way|destructive`

### Criterion 8 — Downtime required — +3
**Detection:** `criterion_8_downtime` · **Source:** `diff:grep`
- Content regex: `strategy:\s*Recreate|maxUnavailable:\s*1`

**Match:** YAML con `strategy: Recreate` · **Non-match:** `RollingUpdate maxUnavailable: 25%`

### Criterion 9 — Data migration required — +3
**Detection:** `criterion_9_data_migration` · **Source:** `diff:grep`
- File regex: `migration|migrate|V\d+__|R__`
- Content regex: `DataMigration|MigrationRunner|@Migration`

### Criterion 10 — Feature flag (mitigation) — -1
**Detection:** `criterion_10_feature_flag` · **Source:** `diff:grep`
- Content regex: `featureFlag|feature\.flag|FeatureToggle|@ConditionalOnProperty|ff4j|unleash|LaunchDarkly|isEnabled`

**Mitigation:** YES → score -1. Visual coding nel report = ✅ (inverted per negative weight).

### Criterion 11 — Coverage < 70% — +2
**Detection:** `lib/release_risk/coverage_src.py:get_coverage` · **Source:** `evidence:coverage | ci:jacoco | ci:lcov | ask:user`

**Chain priority:**
1. `.claude/review-evidence/<sha>.json` → `metrics.coverage.overall_pct`
2. `coverage/jacoco.xml` o `target/site/jacoco/jacoco.xml` (counter LINE missed+covered)
3. `coverage/lcov.info` (aggregato LH/LF)
4. Nessun source → `REQUIRES_INPUT`

**Threshold:** 70% (configurabile via `COVERAGE_THRESHOLD_PCT` constant).

### Criterion 12 — E2E tests not run — +2
**Detection:** `criterion_12_e2e_tests(ci_config_present, e2e_stage_found)` · **Source:** `diff:ci | ask:user`
- No CI config → `REQUIRES_INPUT`
- CI presente ma no stage E2E (grep `e2e|integration|smoke` in `.github/workflows/*.yml`) → YES
- Stage trovato → NO

### Criterion 13 — Performance tests (mitigation) — -1
**Detection:** `criterion_13_perf_tests` · **Source:** `diff:grep`
- Content regex: `jmeter|gatling|locust|k6|performance\.test|load\.test`

### Criterion 14 — User impact > 50% — +2
**Detection:** `criterion_14_user_impact(user_impact_ge_50pct)` · **Source:** `ask:user`
- `None` → `REQUIRES_INPUT` (caller deve passare risposta da AskUserQuestion)
- `True` → YES · `False` → NO

### Criterion 15 — Modified > 10 files — +1
**Detection:** `criterion_15_files_count(diff_files)` · **Source:** `diff:count`

---

## Criteri 16-18 (nuovi controlli SIAE)

### Criterion 16 — Functional regression delta — +2
**Detection:** `lib/release_risk/regression_delta.py:evaluate_criterion_16`
**Source:** `baseline_cache` (last release ScoreCard) + diff grep test disabled

**Trigger condition (qualsiasi):**
- `coverage_delta < -2pp` (vs baseline `ScoreCard.coverage`)
- `test_disabled_count > 0` (added `@Disabled|@Ignore|.skip(|.xskip(|xit(|test.skip|describe.skip` patterns in diff)
- `test_deleted_count > 0` (file `test|spec|__tests__|.test.|.spec.` deletions)

**Prev release resolution:** `git branch -r --sort=-committerdate` + `git log origin/main --merges` con regex 3 formati merge subject (`Merge branch '...'`, `Merge pull request #N from .../...`, `Merge remote-tracking branch '...'`).

**Fallback:** primissima release o baseline non in cache → `TOOL_UNAVAILABLE`.

### Criterion 17 — Security vulnerability state (MVP HEAD-only) — +2
**Detection:** `lib/release_risk/security_state.py:evaluate_criterion_17`
**Source:** `runners` (`lib/review_evidence/runners/pip_audit.py` + `npm_audit.py`)

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

## Levels & Decisions

| Score | Level | Decision | Visual |
|---|---|---|---|
| 0-4 | LOW | `GO` | 🟢 Deploy standard |
| 5-9 | MEDIUM | `GO_WITH_MONITORING` | 🟡 2h post-deploy monitoring |
| 10-14 | HIGH | `POSTPONE_WITHOUT_TL` | 🟠 War room 4h + TL+Ops approval |
| 15+ | CRITICAL | `NO_GO_WITHOUT_CAB` | 🔴 CAB approval + deploy fuori orario |

## Negative weight visual inversion

Criteri 10 e 13 hanno `weight = -1` (mitigation). Nel renderer:
- Status `YES` (mitigation presente) → `✅` (verde, riduce score)
- Status `NO` (mitigation assente) → `❌`

Per criteri positive weight (1-9, 11-12, 14-18):
- Status `YES` (rischio presente) → `❌`
- Status `NO` → `✅`

`REQUIRES_INPUT` e `TOOL_UNAVAILABLE` → `⚠️` (entrambi i sign).
