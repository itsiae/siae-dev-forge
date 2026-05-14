# Design: siae-release-risk

**Data:** 2026-05-14
**Autore:** Lorenzo De Tomasi (lorenzo.detomasi@outlook.com)
**Status:** Ready for User Gate (spec-review PASS iter 3, fix iter 4 applicati)
**Plugin target version:** 1.57.0 (bump da 1.56.0)
**Storia esterna:** Ingestion skill `release-risk-assessment v1.0.0` (zip su ~/Desktop) + 3 controlli aggiuntivi richiesti da Lore (regression delta, security delta, release genesis confirmation)

---

## 1. Contesto

DevForge copre oggi il ciclo `brainstorm → plan → tdd → verification → finishing-branch → requesting-review → [PR merged]`. Manca un gate strutturato **pre-deploy / release-readiness**: dal merge in main al deploy in produzione non c'è una skill che valuti il rischio della release branch in modo deterministico.

Esiste una skill esterna `release-risk-assessment v1.0.0` (Delivery Manager AI) con framework 15-criteri / score 0-30 / livelli LOW-MEDIUM-HIGH-CRITICAL / decisione GO-POSTPONE-NO_GO. La skill è auto-contenuta, anti-hallucination-coded, ma agnostica rispetto a SIAE e DevForge.

Riflessione aggiuntiva di Lore: la release-risk è anche **l'ultima occasione per accorgersi di problemi prima di congelare la release**. Conviene aggiungere 3 controlli che oggi sfuggono o sono diluiti in altre skill/pipeline:
1. Regressioni funzionali (branch corrente vs precedente release)
2. Nuove vulnerabilità di sicurezza (branch corrente vs precedente release)
3. Genesi del release branch — quali feature branch sono state mergiate, da confermare all'utente

L'inclusione di questi 3 controlli porta a una skill `siae-release-risk` strutturalmente più forte di un semplice port della skill esterna.

---

## 2. Obiettivo

Una skill DevForge `siae-release-risk` che, invocata automaticamente all'apertura di una PR `release/** → main` (e on-demand via `/forge-release-risk`):

- Analizza diff release-branch vs `main`
- Compila checklist 18-criteri (15 originali + 3 nuovi) con evidence per ogni criterio
- Deriva automaticamente i criteri inferibili dal codice e dall'infrastruttura DevForge esistente (review-evidence file, MCP sport-kg, baseline_cache S3+local)
- Chiede all'utente solo le 4-5 informazioni davvero non inferibili
- Calcola score 0-36 → livello LOW/MEDIUM/HIGH/CRITICAL → decisione GO/POSTPONE/NO_GO
- Salva checklist completata in `docs/releases/<YYYY-MM-DD>-<service>-<branch>.md` (versionato in repo, audit trail)
- Posta la scorecard come comment automatico nella PR (`gh pr comment`)
- Cache by `(branch, diff-hash)` per skippare re-run su diff identici
- Emette activity event per integrazione con `forge-adoption` e futura correlazione livello-rischio ↔ incident post-deploy

---

## 3. Architettura

### 3.1 Diagramma componenti

```
┌─────────────────────────────────────────────────────────────────────┐
│  Entry points                                                        │
├─────────────────────────────────────────────────────────────────────┤
│  /forge-release-risk  ───────┐                                       │
│                              │                                       │
│  hooks/pr-release-gate  ─────┼──> skills/siae-release-risk/SKILL.md  │
│   (PostToolUse Bash su          │                                    │
│    gh pr create release/**       │                                   │
│    → main)                       │                                   │
│                                  │                                   │
│  Manual prompt utente ───────────┘                                   │
│                                    │                                 │
│                                    ▼                                 │
│                         SKILL.md orchestrator (10-step)              │
│                                    │                                 │
│                                    ▼                                 │
│                       lib/release_risk/cli.py (entry)                │
│                                    │                                 │
│      ┌─────────────────────────────┼────────────────────────────┐    │
│      ▼                             ▼                            ▼    │
│  detector.py            regression_delta.py            security_delta│
│  (15 criteri 1-15)      (criterio 16)                  (criterio 17) │
│      │                             │                            │    │
│      ▼                             ▼                            ▼    │
│  kg_lookup.py           reuse baseline_cache.py        reuse runners/│
│  (criterio 5)           da review_evidence             pip-audit, npm│
│                                                                      │
│  coverage_src.py        genesis.py                                   │
│  (criterio 11)          (criterio 18 + Step 4b)                      │
│                                                                      │
│      └─────────┬────────────┬──────┴──────────┬───────────────┘     │
│                ▼            ▼                 ▼                       │
│            scoring.py   cache.py         renderer.py                  │
│            (max 36)     (diff-hash)      (template fill)              │
│                              │                                       │
│                              ▼                                       │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Output:                                                             │
│  ├─ docs/releases/<date>-<service>-<branch>.md (versionato)          │
│  ├─ ~/.claude/devforge-activity.jsonl (event)                        │
│  ├─ ~/.claude/.cache/release-risk/<branch>-<hash>.json (cache)       │
│  └─ gh pr comment <pr#> (auto-post se trigger=PR-open)               │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Mapping file → responsabilità

| File | Tipo | Responsabilità | LOC stima |
|---|---|---|---|
| `skills/siae-release-risk/SKILL.md` | Skill | Orchestrazione 10-step + pre-flight card + permission denied | 280 |
| `skills/siae-release-risk/reference/release-criticality-checklist.md` | Template | Checklist markdown (18 criteri, scorecard, decision) | 150 |
| `skills/siae-release-risk/reference/release-risk-criteria.md` | Reference | Detection method + example per ognuno dei 18 criteri | 250 |
| `commands/forge-release-risk.md` | Slash | Entry point sottile, allowed-tools, esempi uso | 90 |
| `lib/release_risk/__init__.py` | Lib | Module init | 5 |
| `lib/release_risk/schema.py` | Lib | `CriterionResult`, `ScoreCard`, `ReleaseRiskReport` dataclass | 100 |
| `lib/release_risk/detector.py` | Lib | 15 funzioni `criterion_N(diff_ctx) -> CriterionResult` | 380 |
| `lib/release_risk/regression_delta.py` | Lib | Criterion 16 (coverage delta + test disabled/deleted) | 180 |
| `lib/release_risk/security_state.py` | Lib | Criterion 17 (pip-audit + npm-audit + SARIF diff) | 220 |
| `lib/release_risk/genesis.py` | Lib | Criterion 18 (feature branch list + AskUserQuestion gate) | 130 |
| `lib/release_risk/kg_lookup.py` | Lib | Criterion 5 (MCP sport-kg describe_service + service_health) | 140 |
| `lib/release_risk/coverage_src.py` | Lib | Criterion 11 (review-evidence file → CI artifact → ask) | 110 |
| `lib/release_risk/cache.py` | Lib | Cache by `(branch, diff-hash)` | 90 |
| `lib/release_risk/scoring.py` | Lib | `compute_score(results) -> ScoreCard`, level assignment max 36 | 100 |
| `lib/release_risk/renderer.py` | Lib | Render checklist md from template + results | 170 |
| `lib/release_risk/cli.py` | Lib | CLI entry: `python -m lib.release_risk assess --branch X` | 140 |
| `hooks/pr-release-gate` | Hook | PostToolUse Bash su `gh pr create` release/** → main | 180 |
| `tests/test_release_risk_detector.py` | Test | 15 unit test (uno per criterio) con fixture diff | 430 |
| `tests/test_release_risk_regression_delta.py` | Test | Test Criterion 16 (mock baseline_cache) | 140 |
| `tests/test_release_risk_security_state.py` | Test | Test Criterion 17 (mock pip-audit/npm-audit output) | 160 |
| `tests/test_release_risk_genesis.py` | Test | Test Criterion 18 (git log mock + AskUserQuestion flow) | 110 |
| `tests/test_release_risk_kg_lookup.py` | Test | Test MCP wrapper con mock | 130 |
| `tests/test_release_risk_coverage_src.py` | Test | Test fallback chain | 100 |
| `tests/test_release_risk_cache.py` | Test | Test cache hit/miss/invalidation | 90 |
| `tests/test_release_risk_scoring.py` | Test | Test boundaries 0-4/5-9/10-14/15+ + negative weights | 110 |
| `tests/test_release_risk_renderer.py` | Test | Snapshot test output md (4 livelli) | 220 |
| `tests/test_release_risk_hook.py` | Test | Integration test hook PR-open simulato | 280 |
| `evals/release-risk/disambiguation.yaml` | Eval | 10 prompt validazione trigger vs altre skill | 80 |
| `.claude-plugin/plugin.json` | Manifest | bump 1.56.0 → 1.57.0, description "40 skill, 12 comandi" | 5 |
| `README.md` | Docs | sez. skill list, aggiorna count 39→40 | 10 |
| `CHANGELOG.md` | Docs | entry 1.57.0 | 25 |
| `hooks/ENV_VARS.md` | Docs | sezione "Release Risk Assessment" | 30 |
| **Totale stimato** | | | **~4150** |

---

## 4. Decisioni Architetturali (ADR)

### ADR-1: Skill orchestratore markdown + logica in `lib/release_risk/` Python

**Decisione:** SKILL.md è un orchestratore sottile (workflow + AskUserQuestion + pre-flight card). Tutta la logica di detection, scoring, rendering vive in `lib/release_risk/`.

**Motivo:** mirror perfetto del pattern `lib/review_evidence/` (PR mutation runners corrente). Vantaggi: unit-testable, riusabile da slash/hook/CLI, deterministico, fast (no Bash subshell per ogni criterio).

**Scartato:** SKILL.md monolitico con 15 grep nel SKILL.md → lento, non testabile, regression-prone.

### ADR-2: Critical service detection via MCP sport-kg con fallback ad AskUserQuestion

**Decisione:** Criterion 5 ("servizio critico") deriva automaticamente da `mcp__sport-kg__describe_service` + `service_health` se il repo name matcha prefix mappato nel KG (`sport-*-service`, `pop-*-service`, `pae-*`, `ciam-*`, `dol-be`, `digital-channels-sport-*`, `esb-sport-*`, `esb-sso-*`, `mag-concertini-*`, `portal-apigateway-*`, `ttpp-*-bff-service`, `sport-gestione-*`, `sport-*-drools`). Timeout 5s, fallback ad AskUserQuestion silent.

**Heuristica criticality:**
```python
if kg_data.get("has_payment_chain"): return YES
if kg_data.get("auth_chain_length", 0) >= 3: return YES
if "ciam" in service_name.lower(): return YES
if kg_data.get("traffic_rps_p95", 0) > 100: return YES
if kg_data.get("drools_rules_count", 0) > 5: return YES
if kg_data.get("called_by_count", 0) >= 3 and traffic_rps_p95 > 10: return YES
return NO
```

**Motivo:** ~80% dei repo SIAE sono mappati nel KG. Automation senza attrito utente, fallback umano per i restanti.

**Scartato:** Config-file yaml whitelist → drift continuo, non scala.

### ADR-3: Hook trigger = `gh pr create` release/** → main (PostToolUse Bash, advisory)

**Decisione:** Hook `pr-release-gate` di tipo `PostToolUse` con matcher `Bash`. Detect `gh pr create` con `--base main` e branch corrente `release/**`. NON pre-push.

**Timing scelto: PostToolUse (no PreToolUse)**

| Approccio | Pro | Contro | Decisione |
|---|---|---|---|
| **PreToolUse Bash** | Possibilità di blocking, scorecard PRIMA dell'apertura PR | Rallenta `gh pr create`, blocking implicito contro ADR-4 advisory | ❌ Scartato |
| **PostToolUse Bash** | Allineato a `post-commit-review` esistente (verificato `hooks/hooks.json`), no blocking, scorecard post-PR-open | Race con notifiche reviewer: scorecard arriva 30-60s dopo apertura PR | ✅ Scelto |

**Race condition documentata:** PostToolUse triggera dopo che PR è già aperta. Reviewer riceve email PR-open notification immediatamente, scorecard arriva come PR comment 30-60s dopo. Reviewer potrebbe iniziare review prima della scorecard. **Mitigation:** scorecard comment include header visibile `[siae-release-risk] Scorecard automatica — Level: XXX | Decision: XXX | Read before reviewing.` posto come **primo** comment della PR. Reviewer notification per comment arriva su email/Slack separatamente. Race window: ~60s — accettabile per skill advisory.

**Interazione con hook esistenti (sequenza tipica apertura PR release/**):**

```
Developer → manual run siae-finishing-branch
  ├─ Step 0b: detect parent branch = main (release/** → main)
  ├─ Step 1-3: status, test, diff
  ├─ Step 4c: Blind Review Gate (siae-blind-review)
  └─ Step 5: prompt pre-flight card → user confirms
        │
        ▼
  Developer → gh pr create --base main ...
        │
        ├─ [PreToolUse Bash] pr-gate hook (security scan) — esistente
        ├─ [Tool execution] gh creates PR
        ├─ [PostToolUse Bash] post-commit-review hook (code review) — esistente
        └─ [PostToolUse Bash] pr-release-gate hook (release-risk) — NUOVO
              ├─ Detect: --base main + head release/** → ENABLE
              ├─ Cache check: <branch>-<diff-hash>-<baseline-main-sha>
              ├─ Hit → check existing PR comment via gh api repos/{owner}/{repo}/issues/{pr#}/comments --jq ".[].body"
              │        Se already-posted con marker → skip
              │        Altrimenti → post cached scorecard
              └─ Miss → invoke python -m lib.release_risk assess
                        → write docs/releases/<...>.md
                        → gh pr comment <pr#> --body-file <...>
                        → cache write
                        → devforge_log "release-risk" "success" "$META"
```

**Skip override:** `~/.claude/.devforge-skip-release-risk` (touch). Esempio user: `touch ~/.claude/.devforge-skip-release-risk` disabilita hook fino a `rm` del file.

**Timeout hook:** 30s (allineato a `pr-gate` 15s + buffer per CLI runner). Su timeout → fail-open (no card, log warning, no PR block).

**Scartato:** pre-push hook → noioso, re-run idempotente, blocking implicito; tag-creation → developer non può più reagire.

### ADR-4: Hook severity = advisory-only (no blocking)

**Decisione:** Hook emette card + emit activity event, MAI blocca `gh pr create`. Anche su CRITICAL, output advisory.

**Motivo:** allineato a filosofia DevForge advisory-by-default (review-evidence v2 → AUTO_APPROVE non blocking). HARD-blocking pre-PR violerebbe principio "non rompere flow esistente". Decisione enforcement spetta a reviewer/CAB umano dopo lettura scorecard.

**Future:** in v2.x può evolvere a hybrid (advisory < HIGH, blocking ≥ HIGH) dopo osservazione adoption ed eventi incident correlati.

### ADR-5: Output checklist in `docs/releases/<YYYY-MM-DD>-<service>-<branch>.md` versionato

**Decisione:** File output committato in repo nella dir `docs/releases/`. Naming `<date>-<service>-<branch>.md`.

**Motivo:** audit trail traceable in git history; review post-mortem cross-team; visibile in PR diff; queryable by `git log docs/releases/`.

**Scartato:** `.devforge/releases/` untracked (si perde a switch branch); home utente (non visibile al team); current dir + flag (no convention).

### ADR-6: Activity ledger emit per `forge-adoption` correlation

**Decisione:** Emit event via API canonica `devforge_log <event_type> <status> [meta_json]` (signature verificata in `lib/logger.sh:420`). La funzione aggiunge automaticamente `event_id, ts, user, sid, branch, jira_id, project, schema_version=2, session_seq, hook_name`; il payload custom va nel campo `meta`.

Esempio chiamata:
```bash
source "${PLUGIN_ROOT}/lib/logger.sh"
devforge_init_session 2>/dev/null || true
META=$(cat <<EOF
{
  "skill": "siae-release-risk",
  "service": "sport-gestione-licenze-service",
  "release_branch": "release/2.4.0",
  "level": "MEDIUM",
  "decision": "GO",
  "score": 7,
  "score_max": 36,
  "partial": false,
  "criteria_yes_count": 3,
  "criteria_requires_input": 1,
  "trigger": "pr-open",
  "diff_hash": "abc123def456",
  "baseline_main_sha": "1a2b3c4d5e6f",
  "cached": false
}
EOF
)
devforge_log "release-risk" "success" "$META"
```

L'evento finale nel ledger avrà schema v2 standard + `meta` con i campi sopra. **Non duplicare** ts/branch/event_id fuori da `meta` (li gestisce `devforge_log`).

**Motivo:** abilita correlation futura level↔incident in `siae-dev-analytics`; abilita track adoption skill (oggi 0 baseline). Schema v2 compliant verifica `lib/logger.sh:418-420` e tutti i 10 call site esistenti.

### ADR-7: Coverage source = chain fallback (review-evidence → CI artifact → AskUserQuestion)

**Decisione:** Criterion 11 (coverage <70%) deriva da `lib/release_risk/coverage_src.py` con chain:
1. `.claude/review-evidence/<sha>.json` field `metrics.coverage.overall_pct` (se `forge-evidence` eseguito)
2. CI artifact `coverage/jacoco.xml` / `coverage/lcov.info` (parse on the fly)
3. AskUserQuestion: "Coverage > 70%?"

**Motivo:** zero re-compute se evidence già esiste; zero prompt utente per ~70% casi (rate adozione forge-evidence v1.55+).

### ADR-8: Cache by `(branch, diff-hash, baseline-main-sha)` in `~/.claude/.cache/release-risk/`

**Decisione:** Cache filename: `<branch-slug>-<diff-sha256-12chars>-<baseline-main-sha-8chars>.json`. TTL: nessuno; invalida automaticamente quando cambia il diff *o* quando avanza il baseline `main` (es. nuova release mergiata).

**Motivo:** memory `feedback_pr_gate_redundant_review.md` documenta noia di re-review su push idempotenti. MA: se solo `diff-hash` fosse cache key, lo scorecard cached resterebbe valido *anche se nel frattempo è stata mergiata una nuova release in main* (caso scoperto da spec-review BLOCK-3). Criteri 16-17 dipendono dal baseline last-release: senza includere `baseline-main-sha`, lo scorecard sarebbe stale e Criteri 16-17 ricalcolerebbero risultati diversi alla prossima invocazione no-cached.

**Diff-hash calc:** `sha256(git diff origin/main...HEAD --name-only + git diff origin/main...HEAD content) | head -12`.

**Baseline-main-sha:** `git rev-parse origin/main | head -8`. Avanza ad ogni merge in main, quindi una nuova release mergiata invalida automaticamente la cache.

**Idempotency su `gh pr comment`:** quando hook ri-triggera con cache hit, verifica con `gh api repos/{owner}/{repo}/issues/{pr#}/comments --jq ".[].body"` se esiste già un comment con marker `<!-- release-risk:<diff-hash> -->`. Se sì → skip post (no spam). Se no → post cached scorecard.

**Race con 2 PR contemporanee:** cache key è branch-specifico (`release/2.4.0` vs `release/2.4.1`), quindi file separati, no conflict. `baseline-main-sha` è atomic-read da git, no race fino al merge.

### ADR-9: Scoring framework esteso 30 → 36 con giustificazione quantitativa

**Decisione:** 3 nuovi criteri additivi con pesi **conservativi**:
- Criterion 16: Functional regression delta → **+2** (non +3)
- Criterion 17: New security vulnerabilities introduced → **+2** (non +3)
- Criterion 18: Unexpected feature in release (anomaly da genesis) → **+2**

Max totale: 30 (originale) + 6 (nuovi) = **36**.

**Giustificazione quantitativa pesi:**

| Peso | Semantica criteri originali | Allineamento nuovi criteri |
|---|---|---|
| **+3** | Impatto IRREVERSIBILE in prod: data migration (#9), DB change (#1), breaking API (#3), critical service (#5), downtime (#8) | NESSUN nuovo criterio merita +3: i 3 nuovi controlli rilevano *condizioni reversibili con patch/retest/explanation* |
| **+2** | Impatto ALTO ma reversibile/contenibile: K8s config (#2), ext deps (#4), first release (#6), rollback complex (#7), coverage <70% (#11), E2E not run (#12), user impact >50% (#14) | I 3 nuovi criteri appartengono a questa categoria: regression coverage (-2pp) è reversibile con re-test; CVE delta è reversibile con patch/lib bump; genesis anomaly è reversibile con review manuale + revert merge |
| **+1** | Impatto BASSO: >10 files modified (#15) | n/a |
| **-1** | Mitigazione: feature flag (#10), perf test eseguiti (#13) | n/a |

**Nuove soglie proporzionali (scaling 36/30 = 1.20):**

| Score | Level | Decision |
|---|---|---|
| 0–4 | 🟢 LOW | GO |
| 5–9 | 🟡 MEDIUM | GO con monitoring 2h |
| 10–14 | 🟠 HIGH | POSTPONE senza TL+Ops approval |
| 15+ | 🔴 CRITICAL | NO_GO senza CAB approval |

**Motivo scaling:** scaling proporzionale del +20% mantiene la distribuzione attesa (LOW per la maggior parte, CRITICAL solo per release pesantissime). Soglie originali 0-3/4-7/8-12/13+ traslate a 0-4/5-9/10-14/15+ con allineamento +/- 1 punto.

**Calibrazione futura:** dopo 6 mesi di adoption (Fase 4 rollout), correlazione level↔incident permetterà ri-calibrazione pesi data-driven. Documentato in sez. 14 Rollout Plan + sez. 12 backlog "auto-calibrazione weight via incident correlation".

**False positive risk explicit:** sez. 13 Risk Table contiene riga "Criterion 16/17 false positive rate > 15%" con mitigation "iterazione weight nella retrospettiva trimestrale". Soglie iniziali Criterion 16 (coverage delta < -2pp) e Criterion 17 (`critical > 0 OR high > 5`) sono conservative.

### ADR-10: Genesis check come Step 4b interattivo (con gestione user-decline)

**Decisione:** Nuovo Step 4b nel workflow SKILL.md. Estrae merge commits della release branch, presenta lista feature branch all'utente via AskUserQuestion `multiSelect=true`. Utente conferma quali sono attese.

**Implementazione:**
```bash
git log origin/main..origin/release/X --merges --pretty=format:'%h | %s' \
  | head -30
```
Parser estrae nomi feature branch da merge commit subject (pattern: `Merge.+from .+/(feature|fix)/[^ ]+` o `(#NN) feat: ...`).

**3 outcome possibili:**

| User behavior | `GenesisInfo` state | Criterion 18 status | Score contribution |
|---|---|---|---|
| Conferma tutte le feature → "tutte attese" | `user_confirmed=[all], unexpected=[], declined=False, anomaly=False` | `NO` | 0 |
| Spunta solo subset → flag unexpected | `user_confirmed=[subset], unexpected=[rest], declined=False, anomaly=True` | `YES` | +2 |
| Chiude / annulla / negazione AskUserQuestion | `user_confirmed=None, unexpected=None, declined=True, anomaly=None` | `REQUIRES_INPUT` | 0 (NOT 2) |

**Anomaly handling:**
- Se anomaly=True → Criterion 18 = YES, +2 al score
- Se declined=True → Criterion 18 = REQUIRES_INPUT, **0 al score** (NOT +2). Renderer mostra warning visibile `⚠️ Genesis non confermato dall'utente — verifica manuale richiesta prima del deploy`. Lo scorecard è marcato `partial=true` in `meta` activity event.

**Motivo:** è l'unico controllo del lifecycle che cattura "feature mergiata per errore" (es. drift release branch, conflict merge sbagliato). Pipeline non lo cattura.

**Edge case "no merges trovati":** se release branch ha solo commit diretti (no merge commits), Step 4b skip con nota "release branch built linearly, no feature-branch genesis". Criterion 18 = NO (non REQUIRES_INPUT). Documentato in `tests/test_release_risk_genesis.py`.

### ADR-11: Reuse infrastruttura review-evidence per delta detection (BASELINE-ONLY, no git-checkout)

**Decisione:**

**Criterion 16 (regression delta):**

**Risoluzione `prev_release_main_sha`:**
```bash
# Step 1: trova ref del precedente release branch (esclude branch corrente)
PREV_RELEASE_REF=$(git branch -r --sort=-committerdate \
  | grep -E 'origin/release/' \
  | grep -v "origin/${CURRENT_RELEASE_BRANCH}" \
  | head -1 \
  | xargs)

# Step 1b: strip prefisso 'origin/' per matchare il subject del merge commit
# (git merge commit subject standard: "Merge branch 'release/X.Y.Z' into main"
#  OR "Merge pull request #N from itsiae/release/X.Y.Z"
#  OR "Merge remote-tracking branch 'origin/release/X.Y.Z' into main")
PREV_RELEASE_NAME=${PREV_RELEASE_REF#origin/}

# Step 2: trova merge commit in main del precedente release (= sha baseline_cache key)
# Pattern flessibile per coprire i 3 formati merge subject sopra
PREV_RELEASE_MAIN_SHA=$(git log origin/main --merges --pretty=format:'%H %s' \
  | grep -E "Merge.+(branch '|pull request #[0-9]+ from [^/]+/|remote-tracking branch ')${PREV_RELEASE_NAME}" \
  | head -1 \
  | cut -d' ' -f1)

# Fallback: se nessuna release precedente esiste → first release scenario
if [ -z "$PREV_RELEASE_MAIN_SHA" ]; then
  STATUS="TOOL_UNAVAILABLE"
  REASON="first release, no baseline available"
fi
```

**Detection:**
- Coverage: confronto `current.metrics.coverage.overall_pct` vs `BaselineCache.get(prev_release_main_sha).coverage` letto da `lib/review_evidence/baseline_cache.py` (API verificata: `fetch_baseline(repo_full_name, main_sha) -> Optional[ScoreCard]`)
- Test disabled/deleted: grep su `git diff ${PREV_RELEASE_MAIN_SHA}...HEAD` (read-only, no checkout). Patterns: `@Disabled|@Ignore|\.skip\(|xit\(|test\.skip\(|describe\.skip`
- Test deleted: `git diff --diff-filter=D --name-only ${PREV_RELEASE_MAIN_SHA}...HEAD | grep -E "(test|spec|__tests__)"`
- Trigger condition: `coverage_delta < -2pp OR test_disabled_count > 0 OR test_deleted_count > 0`
- Se baseline non esiste (primissima release) → status `TOOL_UNAVAILABLE` con nota "no prev baseline"

**Criterion 17 (security state) — STRATEGIA HEAD-ONLY (MVP):**

Verificato schema reale post-iter2: `ScoreCard.security` è **un singolo float aggregato (0-100)** (vedi `lib/review_evidence/schema.py:110-122`), NON un sub-record con `critical/high`. Il `SecurityFindings` schema runner ha sub-count, ma viene collassato in float via `score_security(findings)` prima di entrare in baseline_cache. Estendere lo schema baseline_cache richiederebbe breaking change additiva con migration baseline esistenti su S3 (out of scope per questa PR).

**Decisione MVP**: Criterion 17 evaluation è **HEAD-only**, senza confronto delta vs baseline:
- HEAD: invoca `lib/review_evidence/runners/pip_audit.py` e `npm_audit.py` (API verificata: `class *AuditRunner` con `is_applicable(repo_root) -> bool` + `run(repo_root) -> Optional[SecurityFindings]`)
- Trigger condition: `findings.critical > 0 OR findings.high > 5` (soglia configurable via `DEVFORGE_RELEASE_RISK_SECURITY_HIGH_THRESHOLD`)
- Status YES se trigger soddisfatta su HEAD release branch
- **NON eseguire `git checkout`** (alto rischio data loss su working tree utente, contro feedback `feedback_parallel_subagent_git_race.md`)

**Limitazione esplicita MVP**:
- Criterion 17 è "absolute state" (current critical/high counts), non "delta vs precedente release". Può triggerare YES su CVE pre-esistenti che la release non introduce ma neanche rimedia → falsa percezione di "vulnerabilità nuove".
- Mitigation in scorecard rendering: nota chiarificatoria *"Criterion 17 misura lo stato corrente vulnerability, non il delta. CVE pre-esistente alla release contribuisce al trigger se conta ≥ soglia."*

**Evolution path** (sez. 12 backlog):
- v2.x: estendere `EvidenceV2` con field aggiuntivo `security_findings_raw: Optional[SecurityFindings]` (additive, no breaking change). `BaselineCache` persiste raw. Criterion 17 evolve a delta count-based con baseline.
- v3.x: `SecurityRunner.run_with_ids()` per identificazione puntuale CVE → vere "novel CVE" detection.

**Motivo:** zero duplicazione codice; zero rischio data-loss su working tree (no git checkout); allineamento con infrastructure DevForge esistente; runners `pip_audit.py`/`npm_audit.py` già mergiati nel branch corrente `feat/mutation-testing-runners` (verificato file system). Strategia MVP **non richiede modifica schema baseline_cache** → scope contenuto, implementabile in 1 PR.

**Vincolo unico:** se runner ritorna `None` (`is_applicable=False` per tech stack non Python/JS) → Criterion 17 = `TOOL_UNAVAILABLE` con messaggio "pip-audit/npm-audit non disponibili per questo tech stack; esegui scanner equivalente Maven/Trivy manualmente". Per repo Java puri (tipici in SIAE) il Criterion 17 oggi è inevitabilmente skippato — verifica in backlog estensione runner Maven (`mvn dependency-check`).

### ADR-12: SUGGESTED FOLLOW-UP su Criterion 17 HIGH (advisory-coherent)

**Decisione:** Se Criterion 17 trova `new_critical > 0` o `new_high > 5` (soglie configurable), SKILL.md include nel rendering scorecard un blocco:
```markdown
> 📌 **SUGGESTED FOLLOW-UP**: `siae-security` per deep analysis CVE
> Identificate N nuove CVE high/critical rispetto a baseline last-release.
> Esegui `/forge-security` per analisi puntuale e remediation plan.
```

**NON usare il marker `REQUIRED SUB-SKILL`** (semanticamente imperativo, in conflitto con ADR-4 advisory-only). `SUGGESTED FOLLOW-UP` mantiene la semantica advisory coerente: l'utente vede il suggerimento ma il sistema non blocca né esegue forzatamente.

**Motivo:** allineamento con principio DevForge "advisory-by-default" (ADR-4) + spec-review BLOCK-5. `REQUIRED SUB-SKILL` è un imperativo workflow usato in skill che hanno chain forzato (es. siae-finishing-branch → siae-blind-review). Per skill advisory questa semantica non si applica.

**Future:** in v2.x se la skill evolve a hybrid blocking (advisory<HIGH, blocking≥HIGH), allora la chain a `siae-security` può diventare `REQUIRED` per scorecard CRITICAL. Documentato in sez. 12 backlog.

### ADR-13: Interazione con `siae-finishing-branch` Step 4c (pre-PR vs post-PR-open)

**Decisione:** `siae-release-risk` rimane **post-PR-open advisory only** (via hook `pr-release-gate`). NON si aggancia a `siae-finishing-branch` come sub-skill. Resta tuttavia invocabile MANUALMENTE in qualsiasi momento (anche pre-PR) via slash `/forge-release-risk`.

**Sequenza esplicita per release/** → main PR:**

```
1. Developer manual: siae-finishing-branch
   ├─ Step 0b: parent_branch = main detected
   ├─ Step 1-4b (test, diff, commit hygiene, plan completion)
   ├─ Step 4c: Blind Review Gate → siae-blind-review (su design doc)
   │   └─ PASS → procedi
   ├─ (OPZIONALE manual) /forge-release-risk pre-PR per anticipare scorecard
   │   └─ Developer può vedere score, fixare red flag prima di aprire PR
   └─ Step 5: gh pr create

2. gh pr create execution:
   ├─ pr-gate (PreToolUse, existing): security scan
   ├─ PR opens (post-tool)
   ├─ post-commit-review (PostToolUse, existing): diff review
   └─ pr-release-gate (PostToolUse, NUOVO): release-risk scorecard auto-post
```

**Perché non chain hard da `siae-finishing-branch`:**
- `siae-finishing-branch` è skill per *qualsiasi* PR (feature/fix/refactor), non solo release. Forzare release-risk dentro `siae-finishing-branch` significa eseguirla anche su PR non-release (overhead, falsi trigger).
- L'utente può comunque invocare manualmente `/forge-release-risk` come "Step 4d optional" durante chiusura branch.

**Coesistenza con `siae-branching-strategy-check`:**
- `siae-branching-strategy-check` è hook SessionStart che verifica compliance branching su tutti i repo `itsiae` (default branch == main, release/** → main only PRs). Lavora a livello **org-wide governance**.
- `siae-release-risk` lavora a livello **per-PR risk assessment**. Domini ortogonali.
- Output: branching-strategy-check emette headline SessionStart su violazioni; release-risk emette PR comment su scorecard. Nessun overlap.

**Output a developer:**

Se developer ha eseguito `/forge-release-risk` PRE-PR manualmente:
- Step 4d (informal, auto-suggested by SKILL.md): se branch matches release/** AND target=main → SKILL.md suggest "Vuoi eseguire `/forge-release-risk` prima di aprire la PR? (raccomandato per release branch)". Yes → invoca skill; No → procedi.

Documentato in `skills/siae-release-risk/reference/release-risk-criteria.md` sezione "Workflow integration".

### Step 1 — Detect repo + branch (🟢 SICURO)
```bash
git rev-parse --show-toplevel  # repo root
git branch --show-current      # branch corrente
gh repo view --json name,owner # service name
```
Cache check: se `cache.get(branch, diff_hash)` → hit, salta a Step 8 con cached scorecard.

### Step 2 — Select release branch (🟢 SICURO)
Se branch corrente è `release/**` → use it. Altrimenti:
```bash
git branch -r --sort=-committerdate | grep -E 'release/' | head -5
```
AskUserQuestion top 5 con last-commit date.

### Step 3 — Generate diff (🟢 SICURO)
```bash
git fetch origin main && git fetch origin <release>
git diff origin/main...origin/<release> --stat > /tmp/diff-stat.txt
git diff origin/main...origin/<release> --name-only > /tmp/diff-files.txt
git diff origin/main...origin/<release> > /tmp/diff-content.txt
```
Calc `diff_hash = sha256(diff-files + diff-content) | head -12`.

### Step 4 — Fill identification (🟢 SICURO)
- Service: from repo name
- Version: from `pom.xml`/`package.json`/branch tail
- Jira tickets: grep `SPORT-\d+|DIRITTI-\d+|OASIS-\d+|POP-\d+|TAU-\d+` su commit messages
- Release date + owner: AskUserQuestion

### Step 4b — GENESIS CHECK (🟡 MEDIO, NUOVO)
```bash
git log origin/main..origin/<release> --merges --pretty=format:'%h | %s' | head -30
```
Parser feature branch names. AskUserQuestion multiSelect: "Quali di queste N feature sono attese in questa release?".
Set `genesis_anomaly = NOT (selected == all)`.

### Step 5 — Evaluate 18 criteria (🟢 SICURO)
Invoca `python -m lib.release_risk assess --diff-files /tmp/diff-files.txt --diff-content /tmp/diff-content.txt --branch <release> --service <name> --genesis-anomaly <bool>`.

Loop interno:
- Criteria 1-15: `detector.py` (15 funzioni con regex/grep su diff content)
- Criterion 5: `kg_lookup.py` (MCP sport-kg con timeout)
- Criterion 11: `coverage_src.py` (chain fallback)
- Criterion 16: `regression_delta.py` (baseline_cache + test disabled count)
- Criterion 17: `security_state.py` (pip-audit + npm-audit HEAD-only state, MVP)
- Criterion 18: from Step 4b output

### Step 6 — Calculate score (🟢 SICURO)
```python
score = sum(c.weight for c in criteria if c.status == YES)
```
Max teorico: 36.

### Step 7 — Assign level + decision (🟢 SICURO)
```python
# Max teorico: 36 (30 originali + 6 nuovi conservativi)
if score <= 4: level = LOW; decision = GO
elif score <= 9: level = MEDIUM; decision = GO_WITH_MONITORING
elif score <= 14: level = HIGH; decision = POSTPONE_WITHOUT_TL
else: level = CRITICAL; decision = NO_GO_WITHOUT_CAB
```

### Step 8 — Output filled checklist (🟡 MEDIO — write to repo)
```python
renderer.render(template_path, scorecard, criteria) -> markdown
write_to(f"docs/releases/{date}-{service}-{branch}.md")
cache.save(branch, diff_hash, scorecard, criteria)
```

### Step 9 — Emit activity event (🟢 SICURO)
```bash
source lib/logger.sh
devforge_log "release-risk" "success" '{"level":"MEDIUM",...}'
```

### Step 10 — Suggest next actions (🟢 SICURO)
Stampa scorecard markdown + link a `docs/releases/...` + suggested next steps per livello:
- LOW: "✅ GO standard"
- MEDIUM: "🟡 Notifica team + monitoring 2h post-deploy"
- HIGH: "🟠 War room 4h + TL+Ops approval prima di deploy"
- CRITICAL: "🔴 STOP — CAB approval + deploy fuori orario obbligatori"

Se trigger=`pr-open`: `gh pr comment <pr#> --body-file docs/releases/<...>.md`.

---

## 6. 18 Criteri — Detection Method

| # | Criterio | Weight | Source | Detection |
|---|---|---|---|---|
| 1 | Database change (DDL/DML) | +3 | diff:grep | `.sql\|.hql\|migration\|liquibase\|flyway\|V\d+__` |
| 2 | OCP/K8s config | +2 | diff:grep | `.yaml\|.yml + kind: Deployment\|Route\|Secret\|ConfigMap` |
| 3 | Breaking API | +3 | diff:grep | `^-.*@(Get\|Post\|Put\|Delete\|Path)Mapping` |
| 4 | New ext dependencies | +2 | diff:files | `pom.xml\|package.json\|requirements.txt\|build.gradle` |
| 5 | Critical service | +3 | mcp:sport-kg + fallback ask | KG describe_service + heuristic OR ask user |
| 6 | First release | +2 | git:tag | `git tag \| grep -E 'v[0-9]' \| wc -l == 0` |
| 7 | Complex rollback | +2 | inferred | Implied by criteri 1, 9 OR explicit `irreversible` |
| 8 | Downtime required | +3 | diff:grep | `strategy.*Recreate\|rollingUpdate.*maxUnavailable: 1` |
| 9 | Data migration | +3 | diff:grep | `migration\|MigrationRunner\|@Migration` |
| 10 | Feature flag disabilitabile | -1 | diff:grep | `featureFlag\|ff4j\|unleash\|@ConditionalOn` |
| 11 | Coverage < 70% | +2 | evidence:coverage | review-evidence file → CI artifact → ask |
| 12 | E2E tests not run | +2 | diff:ci + ask | `.github/workflows/*.yml` e2e stages OR ask |
| 13 | Perf tests executed | -1 | diff:grep | `jmeter\|gatling\|k6\|locust` |
| 14 | User impact > 50% | +2 | ask | AskUserQuestion |
| 15 | Modified > 10 files | +1 | diff:count | `wc -l diff-files.txt > 10` |
| **16** | **Functional regression delta** | **+2** | **baseline_cache + diff:grep** | coverage_delta < -2pp OR test_disabled_delta > 0 OR test_deleted_delta > 0 (vs prev release baseline) |
| **17** | **Security vulnerability state (MVP HEAD-only)** | **+2** | **runners** | pip-audit + npm-audit count `critical > 0 OR high > 5` su HEAD release branch (NO baseline delta in MVP, vedi ADR-11). Evoluzione delta a v2.x in backlog |
| **18** | **Unexpected feature in release** | **+2** | **genesis (Step 4b)** | User flagged unexpected feature branch in Step 4b. NB: user-decline → REQUIRES_INPUT (0 pts) + warning rendered |

Detail completo + esempi: `skills/siae-release-risk/reference/release-risk-criteria.md`.

---

## 7. Data Schema

```python
# lib/release_risk/schema.py
from dataclasses import dataclass, field
from typing import Optional, Literal
from datetime import datetime

CriterionStatus = Literal["YES", "NO", "REQUIRES_INPUT", "TOOL_UNAVAILABLE"]
Level = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
Decision = Literal["GO", "GO_WITH_MONITORING", "POSTPONE_WITHOUT_TL", "NO_GO_WITHOUT_CAB"]
TriggerSource = Literal["pr-open", "manual", "cli"]

@dataclass
class CriterionResult:
    id: int  # 1..18
    name: str
    status: CriterionStatus
    weight: int  # +3, +2, +1, -1
    evidence: list[str]  # file:line citations or commands run
    source: str  # "diff:grep", "mcp:sport-kg", "evidence:coverage", "baseline_cache", "runner:pip-audit", "genesis:user-confirm"
    notes: Optional[str] = None

@dataclass
class ScoreCard:
    total_score: int  # 0..36 (negative criteria subtract)
    level: Level
    decision: Decision
    decision_rationale: str
    suggested_followups: list[str] = field(default_factory=list)  # e.g. ["siae-security"] — NOT REQUIRED, advisory only
    partial: bool = False  # True se ≥1 criterion = REQUIRES_INPUT (es. user declined genesis)

@dataclass
class GenesisInfo:
    merge_commits: list[dict]  # [{sha, subject, feature_branch}]
    user_confirmed: Optional[list[str]] = None  # None if user declined
    unexpected: Optional[list[str]] = None  # None if user declined
    anomaly: Optional[bool] = None  # None if user declined; True if len(unexpected)>0; False if all confirmed
    declined: bool = False  # True se AskUserQuestion negato/chiuso senza risposta
    no_merges_found: bool = False  # True se linear release branch (no feature merges)

@dataclass
class ReleaseRiskReport:
    service: str
    release_branch: str
    target_branch: str  # main
    diff_hash: str
    diff_summary: dict  # files_changed, commits_count, additions, deletions
    identification: dict  # version, date, owner, jira_tickets[]
    genesis: GenesisInfo
    criteria: list[CriterionResult]
    scorecard: ScoreCard
    generated_at: str  # ISO8601
    output_path: str  # docs/releases/...
    cached: bool
    trigger: TriggerSource
```

---

## 8. Errori & Fallback

| Errore | Componente | Fallback |
|---|---|---|
| MCP sport-kg unavailable o timeout > 5s | `kg_lookup.py` | status=TOOL_UNAVAILABLE → AskUserQuestion silent |
| `.claude/review-evidence/<sha>.json` missing | `coverage_src.py` | try CI artifact → AskUserQuestion |
| `baseline_cache.py` no last-release baseline (primissima release) | `regression_delta.py` | Criterion 16 = TOOL_UNAVAILABLE con nota "first release, no baseline". **Criterion 17 (HEAD-only MVP) NON è impattato**: viene comunque eseguito su current state. |
| `pip-audit` / `npm-audit` non in PATH (runner.is_applicable=False) | `security_state.py` | Criterion 17 = TOOL_UNAVAILABLE, warning su missing dep |
| `ScoreCard.security` baseline non espone sub-counts critical/high (MVP) | `security_state.py` | MVP: Criterion 17 HEAD-only senza delta vs baseline (ADR-11). Estensione schema in v2.x backlog (sez. 12) |
| `git fetch` fails | SKILL.md Step 3 | Block step, report error |
| Release branch not found | SKILL.md Step 2 | Re-prompt user |
| Diff vuoto (release branch == main) | SKILL.md Step 3 | Emit warning "release branch identical to main, nothing to release", status=PARTIAL, esegue solo Criteri 5,6,11,14 (non-diff-based) |
| `git log --merges` ritorna 0 (linear release branch) | `genesis.py` Step 4b | GenesisInfo(no_merges_found=True), Criterion 18 = NO (non REQUIRES_INPUT) |
| AskUserQuestion Step 4b negato/chiuso | `genesis.py` | GenesisInfo(declined=True), Criterion 18 = REQUIRES_INPUT (0 pts) + warning rendered |
| `docs/releases/` non scrivibile | `renderer.py` | Fall back a `/tmp/release-risk/` + warn |
| AskUserQuestion negato (generic) | varie | TOOL_UNAVAILABLE, log gap, partial scorecard (`partial=True`) |
| `gh pr comment` fails (rate limit, permission) | hook `pr-release-gate` | Save scorecard locally + warn user via additional_context |
| `gh api repos/{owner}/{repo}/issues/{pr#}/comments --jq ".[].body"` mostra già comment con marker `<!-- release-risk:<diff-hash> -->` | hook `pr-release-gate` | Skip post (idempotency) |
| Cache file corrupted | `cache.py` | Invalidate, re-compute, log warn |
| 2 PR release contemporanee (race) | hook | Cache key è branch-specifico + baseline-main-sha atomic-read, no conflict fino al merge in main |

---

## 9. Testing Strategy

### 9.1 Unit (mock-heavy, fast)

| File | # Test | Coverage target |
|---|---|---|
| `test_release_risk_detector.py` | 15 (uno per criterio 1-15) | 100% di `detector.py` |
| `test_release_risk_regression_delta.py` | 6 (baseline missing, coverage drop, test disabled, deleted, OK, edge) | 100% di `regression_delta.py` |
| `test_release_risk_security_state.py` | 7 (no vulns, new high, new critical, runners missing, parse error, both runners, sarif) | 95% di `security_state.py` |
| `test_release_risk_genesis.py` | 5 (no merges, all confirmed, partial, none confirmed, regex edge) | 100% di `genesis.py` |
| `test_release_risk_kg_lookup.py` | 7 (KG hit, miss, timeout, error, criticality matrix branches × 3) | 95% di `kg_lookup.py` |
| `test_release_risk_coverage_src.py` | 5 (evidence hit, CI artifact hit, all fail, ask, edge) | 100% di `coverage_src.py` |
| `test_release_risk_cache.py` | 5 (hit, miss, invalidation, corruption, save+load roundtrip) | 100% di `cache.py` |
| `test_release_risk_scoring.py` | 9 (level boundaries 0-4/5-9/10-14/15+, negative weights, edge) | 100% di `scoring.py` |
| `test_release_risk_renderer.py` | 4 (snapshot LOW/MEDIUM/HIGH/CRITICAL) | 90% di `renderer.py` |

**Coverage globale target: ≥85%** (allineato a review-evidence v2 = 87%).

### 9.2 Integration

| File | # Test |
|---|---|
| `test_release_risk_hook.py` | 6 (release/**→main triggers, non-release skip, skip override, cache hit reuse, gh comment OK, gh comment fails) |
| `test_release_risk_cli.py` | 4 (e2e mock repo + fixture diff → checklist file written + activity event emitted + cache populated, idempotency) |

### 9.3 Mutation testing

Allineato a PR mutation runners corrente. Target: **mutation score ≥60%** su `lib/release_risk/`.

### 9.4 Eval set

`evals/release-risk/disambiguation.yaml`: 10 prompt per validare trigger correttamente vs:
- `siae-finishing-branch` (pre-PR feature branch, NON release branch)
- `siae-branching-strategy-check` (compliance, non risk assessment)
- `siae-security` (delegated da Criterion 17 HIGH, ma non in disambiguation)

---

## 10. Criteri di Accettazione

### 10.1 Functional

- ✅ `/forge-release-risk` invocabile produce checklist md in `docs/releases/<date>-<service>-<branch>.md`
- ✅ Skill segue 10-step workflow con AskUserQuestion solo per gap reali
- ✅ Coverage derivata da `.claude/review-evidence/<sha>.json` quando presente (zero prompt utente)
- ✅ Critical service derivata da MCP sport-kg per servizi mappati (zero prompt per ~80% repo SIAE)
- ✅ Criterion 16 (regression) confronta con baseline last-release da `lib/review_evidence/baseline_cache.py`
- ✅ Criterion 17 (security) usa pip-audit + npm-audit + diff CVE count
- ✅ Criterion 18 (genesis) basato su Step 4b interactive AskUserQuestion
- ✅ Output checklist contiene: identification, genesis info, 18 criteri con evidence, scorecard 0-36, decision GO/POSTPONE/NO_GO, link Jira
- ✅ Activity event `release-risk` emesso a `~/.claude/devforge-activity.jsonl`
- ✅ Cache by `(branch, diff-hash)` skippa re-run su diff identici
- ✅ Hook `pr-release-gate` posta scorecard come PR comment via `gh pr comment` su `gh pr create` con base=main e head=release/**
- ✅ Hook è advisory-only (no blocking)
- ✅ Skip override `~/.claude/.devforge-skip-release-risk` disabilita hook

### 10.2 Quality

- ✅ Test coverage ≥85% su `lib/release_risk/`
- ✅ Mutation score ≥60% su `lib/release_risk/`
- ✅ Eval disambiguation 10/10 PASS
- ✅ Lint: 0 errors, 0 warnings (Python ruff + bash shellcheck)
- ✅ review-evidence v2 score **PASS (non BLOCK)** per il commit di merge (AUTO_APPROVE non garantito perché PR introduce 4150 LOC nuovi + config file nuovi — REVIEWER_HANDOFF accettabile)

### 10.3 Documentation

- ✅ Plugin manifest `.claude-plugin/plugin.json` bump 1.56.0 → 1.57.0
- ✅ Plugin manifest `description` audit + recount accurati: **42 skill, 17 comandi, 5 agent, 24 hook** (counts reali post-merge — verificato file system in iter 2: skills=41+1, commands=16+1, hooks=23+1, agents=5 invariato; il manifest attuale "39 skill, 11 comandi, 3 agent, 21 hook" è già **incoerente con repo state**, l'audit è propedeutico)
- ✅ README.md skill list aggiornato (41 → 42)
- ✅ CHANGELOG.md entry 1.57.0 con sezione "Release Risk Assessment"
- ✅ `hooks/ENV_VARS.md` sezione "Release Risk Assessment" con env var opzionali (`DEVFORGE_RELEASE_RISK_DISABLED`, `DEVFORGE_RELEASE_RISK_KG_TIMEOUT_SEC`, soglie criteri 16/17)

### 10.4 Integration

- ✅ No regressione su test suite esistente (`pytest tests/` PASS)
- ✅ No regressione su hook esistenti (`siae-finishing-branch`, `siae-branching-strategy-check`)
- ✅ `forge-adoption` riconosce `release-risk` event in attività analytics

---

## 11. Stima Story Point

Scala doppia (umano vs Claude Code + DevForge augmented). Stima rivista in iter 2 spec-review (più realistica):

| Componente | Human SP | Augmented SP |
|---|---|---|
| Skill SKILL.md + reference checklist + reference criteri (10-step) | 4 | 2 |
| Slash command forge-release-risk | 1 | 0.5 |
| lib/release_risk/ detector.py (15 originali, 15 funzioni + tests fixture diff) | 5 | 2.5 |
| lib/release_risk/ regression_delta.py (Criterion 16 + baseline_cache integration + sub-count schema fix) | 3 | 1.5 |
| lib/release_risk/ security_state.py (Criterion 17 + runner integration + count-based delta) | 4 | 2 |
| lib/release_risk/ genesis.py (Criterion 18 + Step 4b + 3-outcome handling) | 2 | 1.5 |
| lib/release_risk/ kg_lookup (MCP + heuristic + 6 condizioni test) | 2 | 1 |
| lib/release_risk/ coverage_src (chain fallback evidence → CI → ask) | 1.5 | 0.5 |
| lib/release_risk/ cache.py (3-component key + idempotency check via gh api repos/{owner}/{repo}/issues/{pr#}/comments --jq ".[].body") | 2 | 1 |
| lib/release_risk/ renderer.py (template + 4 livelli output + suggested-followup block) | 2 | 1 |
| lib/release_risk/ scoring.py (max 36 + boundary edge cases) | 1 | 0.5 |
| lib/release_risk/ schema.py (5 dataclass con Optional fields + Literal types) | 1 | 0.5 |
| lib/release_risk/ cli.py (argparse + entry point) | 1.5 | 0.5 |
| Hook pr-release-gate (PostToolUse Bash + timing test + race-safe + idempotency) | 4 | 1.5 |
| Test suite unit (15 detector test (criteri 1-15) +3 nei file dedicati (regression_delta/security_state/genesis) + 6 regression + 7 security + 5 genesis + 7 kg + 5 coverage + 5 cache + 9 scoring + 4 renderer) | 6 | 2.5 |
| Test suite integration (6 hook + 4 cli) | 3 | 1 |
| Mutation testing target ≥60% su lib/release_risk/ | 1 | 0.5 |
| Eval set disambiguation (10 prompt) | 1 | 0.5 |
| Plugin manifest audit (recount skills/commands/hooks/agents) + bump 1.56→1.57 | 1 | 0.5 |
| README + CHANGELOG + hooks/ENV_VARS.md | 1.5 | 0.5 |
| **Totale** | **47** | **21.5** |

**Differenza vs iter 1:** stima iter 1 era 33/13. Iter 2 spec-review WARN-2 ha rilevato sottostima ~40%. Nuova stima 47/21.5 considera:
- Decisione MVP HEAD-only Criterion 17 (BLOCK-2): semplifica scope, scope contenuto, no breaking schema baseline_cache
- 3-outcome genesis handling (BLOCK-4)
- Race-safe idempotency su `gh pr comment` (WARN-4)
- Audit count plugin manifest pre-bump (skills/commands/hooks/agents reali != manifest)
- 15 detector test (criteri 1-15) +3 nei file dedicati (regression_delta/security_state/genesis) (non 15 — i 3 nuovi criteri non erano contati)
- Edge case diff vuoto + first release (WARN-5/6)
- Test integrazione hook stack completo (BLOCK-7)

**Rolling out come 1 PR mega:** ~3 settimane augmented (~21.5 SP / ~7 SP/week).

---

## 12. Out of Scope (backlog esplicito)

- **CAB ticket auto-creation**: integrazione con sistema CAB SIAE (richiede API CAB non disponibile)
- **Dashboard release-risk in `siae-dev-analytics`**: KPI level↔incident correlation, ROI metric
- **Integrazione `siae-finops` Criterion "cost impact"**: Infracost diff feed Criterion +1 se costo mensile > $100
- **Tag-creation hook**: trigger su `git tag v*` con last-mile gate (deferred dopo osservazione adoption)
- **Auto-block `gh pr create`**: evoluzione da advisory a hybrid (advisory < HIGH, blocking ≥ HIGH) dopo 6 mesi adoption
- **Multi-target deploy**: skill assume target=main; multi-target (sviluppo/collaudo/cert/prod) gate separato
- **Criterion 17 delta vs baseline (post-MVP)**: oggi HEAD-only (ADR-11 MVP decision). v2.x estende `EvidenceV2` schema con field `security_findings_raw: Optional[SecurityFindings]` (additive, no breaking), `BaselineCache` persiste raw, Criterion 17 evolve a delta count-based `new_critical = current.critical - baseline.critical`. SP stimato +3 augmented.
- **CVE per-ID identification (v3.x)**: estensione futura `SecurityRunner.run_with_ids() -> SecurityFindings + list[CVE]` per identificare *quali* CVE sono nuove (utile per `siae-security` follow-up automation). Richiede modifiche pip-audit/npm-audit wrapper.
- **Maven security runner**: oggi runner sono pip-audit + npm-audit (Python + JS). Repo Java puri (~60% repo SIAE) skip Criterion 17. Estensione: wrapper Maven `mvn dependency-check` o `trivy fs` con SARIF parsing.
- **Calibrazione data-driven pesi 16/17/18**: dopo 6 mesi adoption + ≥30 release con incident outcome registrato, re-pesare i 3 nuovi criteri via correlation analysis
- **3-build moving average per Criterion 16 coverage flaky**: oggi confronto puntuale; rolling window riduce false positive
- **Controllo `data migration delta` vs precedente**: criterio aggiuntivo che cattura "migration aggiunta DOPO la prev-release"; oggi Criterion 9 cattura solo "ha migration" (sì/no)
- **Controllo `performance regression`**: misura latency p95 baseline vs current via APM (Elastic ES); richiede integrazione MCP elastic
- **Controllo `contract breaking API delta`**: schema OpenAPI diff vs precedente release; richiede contract registry
- **Controllo `OCP config drift critico`**: confronto config K8s release vs config prod attuale; richiede MCP OCP cluster
- **Auto-calibrazione weight via incident correlation**: ML pipeline che ri-pesa criteri in base a incident effective vs predicted level

---

## 13. Risk & Mitigation

| Risk | Severità | Mitigation |
|---|---|---|
| MCP sport-kg latency degrada UX | M | Timeout 5s + fallback AskUserQuestion silent (ADR-2) |
| Mutation runners `pip_audit.py`/`npm_audit.py` non in PATH dev workstation | M | Feature detect via `runner.is_applicable(repo_root)`; fallback `Criterion 17 = TOOL_UNAVAILABLE` con msg "esegui pip-audit/npm-audit manualmente" |
| `ScoreCard.security` baseline non espone sub-counts critical/high | L (mitigato MVP) | MVP: Criterion 17 HEAD-only senza delta (ADR-11). Estensione schema additiva in backlog v2.x |
| Hook pr-release-gate spam su push frequenti / cache stale | L | Cache key 3-component `(branch, diff-hash, baseline-main-sha)` (ADR-8) + idempotency check via `gh api repos/{owner}/{repo}/issues/{pr#}/comments --jq ".[].body"` |
| Skill triggered erroneamente su PR non-release | M | Hook check rigoroso: `--base main` AND `head release/**` AND NOT `--draft` |
| `gh pr comment` fallisce silenziosamente (rate limit, permission) | M | Try/catch + log warning + save scorecard locally; user vede warning via additional_context |
| Race 2 PR release contemporanee | L | Cache key è branch-specifico; baseline-main-sha atomic-read da git, no race fino al merge |
| Race scorecard vs reviewer notification (60s gap) | L | Header visibile primo comment "[siae-release-risk] Read before reviewing"; reviewer ha notifica separata per comment |
| Output `docs/releases/` gonfia repo | L | File ~5-10KB ognuno; 50 release/anno = ~500KB; trascurabile |
| AskUserQuestion negato in non-interactive mode | M | Status TOOL_UNAVAILABLE + partial scorecard (`partial=True`) + warn |
| AskUserQuestion Step 4b declined → genesis silently skipped | M | Esplicito 3-outcome handling (ADR-10): declined → REQUIRES_INPUT (0 pts) + warning visibile in rendering |
| Regression Criterion 16 false positive su coverage flaky | M | Soglia delta -2pp + 3-build moving average futura (sez. 12 backlog) |
| Pesi Criterion 16/17/18 mal calibrati | M | Pesi conservativi +2 (ADR-9); calibrazione data-driven post 6 mesi rollout (Fase 4) |
| `git checkout` su working tree utente (data loss potenziale) | XL ELIMINATO | ADR-11 rivisto: NO git checkout, baseline-only via `BaselineCache.fetch_baseline()` |
| Cache collision diff-hash | XL | sha256 → 2^48 collision space, trascurabile per scope SIAE |
| Primissima release (no baseline) → Criteri 16/17 unusable | L | Esplicito fallback: TOOL_UNAVAILABLE con nota "first release, no baseline" (sez. 8) |
| Diff vuoto (release branch == main) → falso GO | L | Step 3 warning "nothing to release", status=PARTIAL, esegue solo criteri non-diff-based (sez. 8) |

---

## 14. Rollout Plan

### Fase 1 — Internal testing (settimana 1-2)
- Merge PR mega in `feat/siae-release-risk`
- Self-dogfooding su repo `siae-dev-forge` (release/N.M.0 future)
- Validazione cross-skill (no regressioni)

### Fase 2 — Pilot (settimana 3-4)
- Abilitazione su 3-5 repo target: `sport-gestione-licenze-service`, `sport-gestione-eventi-service`, `pop-be`
- Monitor activity ledger per emit event count + level distribution
- Raccolta feedback dev SIAE

### Fase 3 — General availability (settimana 5+)
- Annuncio CHANGELOG 1.57.0 release-wide
- Hook attivo di default su tutti i repo `itsiae` con DevForge installato
- Skip override documentato per opt-out per-repo

### Fase 4 — Post-launch metrics (settimana 8+)
- Correlation level↔incident rate (necessita 30+ release data points)
- Iterazione weight Criterion 16/17 se false positive rate > 15%
- Decisione evolution advisory → hybrid (ADR-4 future)

---

## 15. Test Plan References

- Pre-merge: pytest suite + mutation runners attiverà gate `forge-evidence v2` su `lib/release_risk/`
- Eval set: `evals/release-risk/disambiguation.yaml` run via `lib/evals/runner.py`
- Manual smoke test su PR `release/X` simulata su `siae-dev-forge` self-dogfood

---

## 16. References

- Skill esterna originale: `/tmp/risk-skill-inspect/release-risk-assessment/SKILL.md`
- Pattern skill DevForge: `skills/siae-finishing-branch/SKILL.md`
- Pattern slash command: `commands/forge-score.md`
- Pattern hook: `hooks/post-commit-review`, `hooks/pr-gate`
- Library reuse: `lib/review_evidence/baseline_cache.py`, `lib/review_evidence/runners/`
- Activity ledger: `lib/logger.sh`
- MCP sport-kg tools: `mcp__sport-kg__describe_service`, `mcp__sport-kg__service_health`
- Memory: `feedback_mcp_gating_conditional.md`, `feedback_pr_gate_redundant_review.md`, `mcp_sport_kg_gaps.md`
- Precedente: `docs/plans/2026-03-25-branching-strategy-check-design.md` (import skill esterna)

---

**End of design doc.**
