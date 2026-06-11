# siae-release-risk — Guida Operativa

Pre-deploy risk assessment di un release branch vs `main`: scorecard a **18 criteri**
verificabili, score 0-36, livello **LOW/MEDIUM/HIGH/CRITICAL** e decisione
**GO / GO_WITH_MONITORING / POSTPONE / NO_GO**. Output versionato in `docs/releases/`
e (su trigger PR) postato come commento idempotente sulla PR.

> **La Legge di Ferro:** nessun deploy di release senza scorecard generata.
> Una release sconosciuta è una release pericolosa.

---

## Quando usarla

- Prima di un deploy in produzione di un branch `release/**`.
- Come gate CAB / delivery manager review ("release readiness check").
- Automaticamente: l'hook `pr-release-gate` la invoca quando apri una PR
  `release/** → main` (`gh pr create --base main`).

## Come invocarla

| Modo | Come |
|---|---|
| **Slash command** | `/forge-release-risk` |
| **Linguaggio naturale** | "pre-deploy assessment", "release readiness check", "scorecard release", "CAB gate" |
| **Hook automatico** | apertura PR `release/** → main` (skip: `touch ~/.claude/.devforge-skip-release-risk`) |
| **CLI diretta** | `python -m lib.release_risk assess ...` (vedi [CLI Reference](#cli-reference)) |

La skill guida un workflow a 10 step (dettaglio in [SKILL.md](SKILL.md)): rileva repo/branch,
genera il diff `origin/main...origin/<release>`, estrae versione e ticket Jira, conferma con
te le feature attese nella release (**genesis check**), arricchisce con il KG sport-kg se il
servizio è mappato, e invoca la CLI deterministica che calcola i 18 criteri.

## I 18 criteri

Il calcolo è **deterministico** (codice Python in `lib/release_risk/`, non il modello).
Pesi positivi = fattori di rischio; pesi negativi = mitigazioni (sottraggono dallo score).

I pattern nella colonna "Come viene rilevato" sono regex Python (case-insensitive).

| # | Criterio | Peso | Come viene rilevato |
|---|---|---|---|
| 1 | Database change (DDL/DML) | +3 | diff: file `.sql`/`.hql`, path `migration|liquibase|flyway|changelog|V\d+__|\bdb/.*\.xml$`, keyword DDL o tag liquibase (`<createTable`, ...) |
| 2 | OCP/K8s config change | +2 | diff: file yaml/k8s/helm o `kind: Deployment\|Route\|Secret\|ConfigMap` |
| 3 | Breaking API changes | +3 | diff: righe rimosse con `@*Mapping` |
| 4 | External dependencies | +2 | diff: `pom.xml`, `package.json`, `requirements.txt`, `build.gradle`, `go.mod`, ... |
| 5 | Critical service | +3 | KG sport-kg (euristica: payment chain, auth chain ≥3, rps p95 >100, Drools >5, fan-in) |
| 6 | First release | +2 | `git tag --list` su glob release (0 tag = prima release) |
| 7 | Complex rollback | +2 | implicato da criterio 1 o 9, o keyword `irreversible|no rollback|destructive` |
| 8 | Downtime required | +3 | diff: `strategy: Recreate` o `maxUnavailable: 1` |
| 9 | Data migration | +3 | diff: file `migration|V\d+__|R__` o classi `MigrationRunner|@Migration` |
| 10 | Feature flag | **−1** | diff: pattern `featureFlag|FeatureToggle|@ConditionalOnProperty|ff4j|unleash|isEnabled` |
| 11 | Coverage < 70% | +2 | chain: evidence file → `jacoco.xml` → `lcov.info` → REQUIRES_INPUT |
| 12 | E2E tests not run | +2 | `.github/workflows/*.yml` con stage `e2e|integration|smoke` |
| 13 | Performance tests | **−1** | diff: pattern perf test presenti |
| 14 | User impact > 50% | +2 | risposta utente (non inferibile) |
| 15 | Modified > 10 files | +1 | conteggio file nel diff |
| 16 | Functional regression delta | +2 | delta coverage vs release precedente < −2pp, o test `@Disabled`/`.skip` aggiunti, o test file cancellati |
| 17 | Security vulnerability state | +2 | runner pip-audit/npm-audit su HEAD (Maven: manuale) |
| 18 | Unexpected feature in release | +2 | genesis check: feature branch mergiate non confermate dall'utente |

### Stati e visual coding

Ogni criterio ha 4 stati possibili — la skill **non indovina mai**:

- `YES` / `NO` — rilevato con evidence (es. `file:db/migration/V2__x.sql`).
- `REQUIRES_INPUT` ⚠️ — serve verifica manuale (es. KG irraggiungibile, coverage non trovata).
  Anche un solo criterio in questo stato marca la scorecard **PARTIAL**.
- `TOOL_UNAVAILABLE` ⚠️ — tool non applicabile/fallito (es. stack Maven per il criterio 17).

Emoji: per i criteri a peso positivo `YES` = rischio = ❌; per le mitigazioni (10, 13)
`YES` = mitigazione presente = ✅.

### Score → Livello → Decisione

| Score | Livello | Decisione | Next action |
|---|---|---|---|
| 0–4 | 🟢 LOW | GO | deploy standard |
| 5–9 | 🟡 MEDIUM | GO_WITH_MONITORING | notifica team + monitoring 2h post-deploy |
| 10–14 | 🟠 HIGH | POSTPONE_WITHOUT_TL | war room 4h + approval TL+Ops |
| ≥15 | 🔴 CRITICAL | NO_GO_WITHOUT_CAB | CAB approval + deploy fuori orario |

## CLI Reference

```bash
python -m lib.release_risk assess \
  --repo-root "$REPO_ROOT" \
  --branch "release/2.0.0" \
  --service "sport-licenze-service" \
  --diff-files /tmp/diff-files.txt \      # output di: git diff origin/main...origin/<branch> --name-only
  --diff-content /tmp/diff-content.txt \  # output di: git diff origin/main...origin/<branch>
  --version "2.0.0" \
  --owner "team-licenze" \
  --release-date "2026-06-12" \
  --user-impact-ge-50 true \
  --genesis-confirmed "feat/a,feat/b" \   # oppure --genesis-declined
  --kg-data-file /tmp/release-risk-kg-<service>.json \
  --trigger manual                         # pr-open | manual | cli
```

Output su stdout: JSON `{"cached", "output_path", "level", "decision", "score", "diff_hash"}`.
Exit 0 anche su scorecard CRITICAL (la decisione è informativa, non bloccante a livello CLI).

### KG prefetch (`--kg-data-file`)

Per i servizi mappati nel KG sport-kg (prefissi `sport-*`, `pop-*`, `pae-*`, `ciam-*`, ...),
la skill pre-fetcha `describe_service` + `service_health` (Step 4c) in un JSON:

```json
{
  "service_name": "sport-licenze-service",
  "describe_service": {"has_payment_chain": true, "auth_chain_length": 2, "drools_rules_count": 2, "called_by_count": 4},
  "service_health": {"traffic_rps_p95": 150}
}
```

Se il KG è irraggiungibile (campo `error` nel JSON), il criterio 5 degrada a
`REQUIRES_INPUT` con evidence esplicita — mai un silent-NO. Senza `--kg-data-file`,
i servizi mappati ottengono `TOOL_UNAVAILABLE`; i servizi fuori prefisso `REQUIRES_INPUT`.

### Cache

Chiave: `branch + diff_hash + baseline_main_sha` in `~/.claude/.cache/release-risk/`.
Stesso diff → secondo run istantaneo con `"cached": true`, niente doppio commento PR
(marker idempotenza `<!-- release-risk:<diff_hash> -->`).

**Limiti noti:**
- L'input KG **non** fa parte della chiave: se il KG torna disponibile dopo un run
  degradato, ri-esegui con `--no-cache`.
- `--no-cache` salta solo la lettura: ricalcola e **sovrascrive** comunque la entry.

### Variabili d'ambiente

| Variabile | Default | Effetto |
|---|---|---|
| `DEVFORGE_RELEASE_RISK_TAG_GLOBS` | `release*,v*,*RELEASE*,*-RELEASE,RELEASE-*` | glob tag per il criterio 6 |
| `DEVFORGE_RELEASE_RISK_SECURITY_CRITICAL_THRESHOLD` | `0` | criterio 17: trigger se critical > soglia |
| `DEVFORGE_RELEASE_RISK_SECURITY_HIGH_THRESHOLD` | `5` | criterio 17: trigger se high > soglia |
| `DEVFORGE_RELEASE_RISK_KG_TIMEOUT_SEC` | `5` | timeout lookup MCP sport-kg |

## Esempio di output

```
# 🔴 Release Risk Scorecard — sport-licenze-service
## 🔴 Level: CRITICAL | Score: 26/36 | Decision: NO_GO_WITHOUT_CAB
_score=26/36 | yes_criteria=[1, 2, 3, 4, 5, 7, 8, 9, 10, 14, 16, 18]_

| # | Criterio | Status | Peso | Evidence |
| 1 | Database change (DDL/DML) | ❌ YES | +3 | file:src/main/resources/db/migration/V2__add_rinnovo.sql; ddl_k... |
| 5 | Critical service | ❌ YES | +3 | heuristic_match=YES; traffic_rps_p95=150 |
| 18 | Unexpected feature in release | ❌ YES | +2 | unexpected_features=['feat/licenze-rinnovo'] |
...
## ➡️ Next Actions
🔴 STOP. CAB approval obbligatoria. Deploy solo fuori orario (weekend/notte).
```

## Troubleshooting

| Sintomo | Causa | Rimedio |
|---|---|---|
| `cached: true` ma il KG era giù al primo run | input KG fuori dalla chiave cache | ri-esegui con `--no-cache` |
| Criterio 17 sempre `TOOL_UNAVAILABLE` | stack Maven (no pip/npm) | `mvn dependency-check` o `trivy fs` manuale |
| Criterio 11 `REQUIRES_INPUT` | nessun artifact coverage | genera `coverage/lcov.info` o jacoco, o rispondi manualmente |
| Scorecard `PARTIAL` | ≥1 criterio `REQUIRES_INPUT` | verifica manuale dei criteri ⚠️ prima del deploy |
| Warning urllib3/boto3 su stderr | ambiente Python 3.9 + LibreSSL | innocuo: il JSON resta su stdout |
| Hook non scatta su PR | head non è `release/**` o skip file presente | rimuovi `~/.claude/.devforge-skip-release-risk` |

## Test

```bash
python3 -m pytest tests/test_release_risk_*.py --cov=lib/release_risk
# 177 test, coverage 100% (684/684 statement)
```

## Riferimenti

- [SKILL.md](SKILL.md) — workflow 10-step completo, limiti operativi, permission handling
- [reference/release-risk-criteria.md](reference/release-risk-criteria.md) — detection method dei 18 criteri
- [reference/release-criticality-checklist.md](reference/release-criticality-checklist.md) — template checklist
- `docs/plans/2026-05-14-siae-release-risk-design.md` — design doc originale
