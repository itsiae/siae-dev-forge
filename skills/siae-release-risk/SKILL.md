---
name: siae-release-risk
description: >
  Use when assessing pre-deploy risk of a release branch vs main before deploy to prod.
  18-criteri scoring (0-36), level LOW/MEDIUM/HIGH/CRITICAL, decision GO/POSTPONE/NO_GO.
  Trigger: pre-deploy assessment, release readiness check, /forge-release-risk,
  delivery manager review, release branch ready, CAB gate, scorecard release.
---

# SIAE Release Risk — Pre-Deploy Readiness Assessment

> **Tipo:** Rigid | **Fase SDLC:** 5. Release Management

## LA LEGGE DI FERRO

```
NESSUN DEPLOY DI RELEASE SENZA SCORECARD GENERATA
```

Una release sconosciuta è una release pericolosa. Questa skill produce evidence-based scorecard
con 18 criteri verificabili. Output: file md versionato in `docs/releases/` + PR comment automatico.

---

## Workflow 10-Step

### Step 1 — Detect repo + branch  🟢 SICURO
```bash
git rev-parse --show-toplevel
git branch --show-current
gh repo view --json name,owner
```
Salva `$REPO_ROOT`, `$BRANCH`, `$SERVICE`.

### Step 2 — Select release branch  🟢 SICURO
Se `$BRANCH` matches `release/**` → use it. Altrimenti:
```bash
git branch -r --sort=-committerdate | grep -E 'origin/release/' | head -5
```
AskUserQuestion top 5 con last-commit date.

### Step 3 — Generate diff  🟢 SICURO
```bash
git fetch origin main && git fetch origin $BRANCH
git diff origin/main...origin/$BRANCH --name-only > /tmp/diff-files.txt
git diff origin/main...origin/$BRANCH > /tmp/diff-content.txt
```
**Edge case:** diff vuoto → warning "release branch identical to main, nothing to release" + status=PARTIAL.

### Step 4 — Fill identification  🟢 SICURO
Service: from `gh repo view`. Version: from `pom.xml`/`package.json`/branch tail.
Jira tickets: `git log origin/main..origin/$BRANCH --pretty=%B | grep -oE '(SPORT|DIRITTI|OASIS|POP|TAU)-[0-9]+'`
AskUserQuestion for: release date, owner.

### Step 4c — Prefetch KG data (se servizio mappato)  🟢 SICURO

Se `$SERVICE` matcha uno dei prefix KG (`sport-*|pop-*|pae-*|ciam-*|dol-be|digital-channels-sport-*|esb-sport-*|esb-sso-*|mag-concertini-*|portal-apigateway-*|ttpp-*`):

1. Invoca MCP tool `mcp__sport-kg__describe_service` con `service_name=$SERVICE` (timeout 5s)
2. Invoca MCP tool `mcp__sport-kg__service_health` con `service_name=$SERVICE` (timeout 5s)
3. Scrivi entrambi gli output in `/tmp/release-risk-kg-${SERVICE}.json`:
   ```json
   {
     "service_name": "...",
     "describe_service": {...},
     "service_health": {...}
   }
   ```
4. Set `KG_DATA_FILE=/tmp/release-risk-kg-${SERVICE}.json` (per Step 6).

Se MCP unavailable o timeout o servizio non in prefix → skip Step 4c, KG_DATA_FILE="".

### Step 4b — GENESIS CHECK  🟡 MEDIO  (nuovo per release-risk)
```bash
git log origin/main..origin/$BRANCH --merges --pretty=format:'%h | %s' | head -30
```
Parse feature branch names. AskUserQuestion multiSelect: "Quali di queste N feature sono attese in questa release?"

**3 outcome:**
- Tutte confermate → `--genesis-confirmed=<list>`
- Subset confermato → `--genesis-confirmed=<subset>` (anomaly → Criterion 18 YES)
- Utente chiude/annulla → `--genesis-declined` (Criterion 18 REQUIRES_INPUT + warning)
- No merges (linear release) → skip Step 4b automatico

### Step 5 — Pre-flight card  🟡 MEDIO

| 🟡 MEDIO — 🔨 DevForge · siae-release-risk |
|:---|
| 📋 Service: `$SERVICE` · 🌿 Branch: `$BRANCH` |
| **▼ Azione** |
| 1. 📌 Run release-risk assessment (18 criteri) |
| 2. 💾 Output: `docs/releases/<date>-<service>-<branch>.md` (versionato) |
| 3. 📊 Activity event emit per forge-adoption |
| 💡 Perché: evaluate deploy risk + traceability audit |
| 🚫 Se NO: nessun output, nessun event emesso |

⏸️ **ATTENDI CONFERMA UTENTE** ("sì, procedi" / "no, annulla").

### Step 6 — Invoke CLI  🟢 SICURO

```bash
python -m lib.release_risk assess \
  --repo-root "$REPO_ROOT" \
  --branch "$BRANCH" \
  --service "$SERVICE" \
  --diff-files /tmp/diff-files.txt \
  --diff-content /tmp/diff-content.txt \
  --version "$VERSION" \
  --owner "$OWNER" \
  --release-date "$RELEASE_DATE" \
  --user-impact-ge-50 "$USER_IMPACT" \
  --genesis-confirmed "$GENESIS_CONFIRMED" \
  ${KG_DATA_FILE:+--kg-data-file "$KG_DATA_FILE"} \
  --trigger manual
```

### Step 7 — Cache check  🟢 SICURO
CLI gestisce internamente. Se cache hit + `gh pr comment --list` mostra marker `<!-- release-risk:<diff-hash> -->` già presente → skip post.

**Limiti cache (chiave = branch + diff_hash + baseline_main_sha):**
- L'input KG (Step 4c) NON fa parte della chiave: se il prefetch KG cambia (es. VPN ripristinata dopo un run con KG unavailable) la scorecard cachata resta quella vecchia → ri-esegui con `--no-cache`.
- `--no-cache` salta solo la lettura: il run ricalcola e sovrascrive comunque la entry in cache.

### Step 8 — Display scorecard  🟢 SICURO
Output CLI mostra scorecard markdown. Path file: `docs/releases/<date>-<service>-<branch>.md`.

### Step 9 — Emit activity event  🟢 SICURO
CLI già esegue `devforge_log "release-risk" "success" "$META"` internamente.

### Step 10 — Suggest next actions  🟢 SICURO
Per livello:
- **LOW**: "✅ GO deploy standard"
- **MEDIUM**: "🟡 Notifica team + monitoring 2h post-deploy"
- **HIGH**: "🟠 War room 4h + TL+Ops approval prima di deploy"
- **CRITICAL**: "🔴 STOP — CAB approval + deploy fuori orario obbligatori"

Se `suggested_followups` non vuoto → mostra "📌 SUGGESTED FOLLOW-UP: `$SKILL`" per ogni skill.

---

## Trigger automatico (PR-open)

Hook `pr-release-gate` (PostToolUse Bash su `gh pr create --base main` con head `release/**`)
invoca questa skill con `--trigger pr-open`. Scorecard postata come PR comment auto.

**Skip override:** `touch ~/.claude/.devforge-skip-release-risk`.

---

## Sub-skill richieste

| Trigger | Sub-skill |
|---|---|
| Criterion 17 critical CVE | `siae-security` (SUGGESTED FOLLOW-UP) |
| Pre-PR self-assessment | `siae-finishing-branch` (manual chain) |

---

## Reference

- `reference/release-criticality-checklist.md` — template checklist
- `reference/release-risk-criteria.md` — 18 criteri detection method + env config
- Design doc: `docs/plans/2026-05-14-siae-release-risk-design.md`

---

## Limiti Operativi

| Vincolo | Limite | Se superato |
|---|---|---|
| Tentativi per criterio | 2 | TOOL_UNAVAILABLE + log gap |
| MCP sport-kg timeout | 5s | Fallback ad AskUserQuestion |
| Hook timeout totale | 30s | Fail-open, no card |
| Output max | 200 righe scorecard | Già limitato dal renderer |

---

## Permission Denied

- Write `docs/releases/` negato → fallback `/tmp/release-risk/` + warn
- `gh pr comment` negato → save scorecard local + warn additional_context
- Bash negato → presenta comandi, chiedi output utente
- AskUserQuestion negato → status TOOL_UNAVAILABLE, partial scorecard

---

## Visual Coding scorecard

**Positive-weight criteria (1-9, 11-12, 14-18):** YES=risk-present=❌
**Negative-weight criteria (10, 13):** YES=mitigation-present=✅
**REQUIRES_INPUT / TOOL_UNAVAILABLE:** ⚠️
