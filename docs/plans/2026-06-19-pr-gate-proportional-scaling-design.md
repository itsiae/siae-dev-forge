---
status: approved
date: 2026-06-19
topic: pr-gate-proportional-scaling
complexity: media
sp_human: 3
sp_augmented: 1
---

# Design — Scaling proporzionale dei gate PR

## 1. Contesto e problema

I hook `pr-premortem-gate` e `pr-blind-review-gate` (PreToolUse su `gh pr create|edit`)
emettono `decision:block` se la rispettiva skill non risulta validata per il task —
**identicamente** per una feature cross-module e per un PR doc-only / metadata di 2 righe.

Le **skill stesse prevedono già l'eccezione** ma i hook non la onorano:
- `siae-blind-review` §"Eccezioni": *"Modifiche esclusivamente documentali (nessun codice
  di produzione)"*.
- `siae-premortem` §"Quando si applica": *"per hotfix/bump meccanici il premortem è breve"*.

Evidenza diretta (questa sessione): un fix di 2 righe (`45 skill`→`62 skill` in
`.claude-plugin/*.json`) ha richiesto premortem + finishing-branch + blind-review +
2 PR reviewer. Attrito sproporzionato.

## 2. Obiettivo e non-obiettivi

**Obiettivo**: i gate PR scalano sul **rischio reale del diff**. Per diff a basso rischio
(doc-only / manifest non-eseguibile) il gate passa da `decision:block` ad **advisory**
(`additional_context` informativo, non bloccante).

**Non-obiettivi (floor non negoziabile)**:
- Secret scan (`pre-commit`) e security: SEMPRE attivi, mai scalati.
- `review-evidence` coverage/lint/CI hard-floor: invariati (questo design NON li tocca).
- `siae-brainstorming`/`siae-verification`: già scalati, non toccati.

## 3. Decisione architetturale

**ADR-1 — Signal basato su path/estensione, non su size (non-gameable).**
La classe di rischio è funzione esclusiva dei **path dei file cambiati** vs base branch,
NON della dimensione del diff (gonfiabile/sgonfiabile arbitrariamente). Default
conservativo: se anche UN file non è nell'allowlist low-risk → `risk=code` → gate pieno.

**ADR-2 — Allowlist per ESTENSIONE (non per path-prefix) + rename-aware.**
`risk=low` SE E SOLO SE *ogni* file cambiato matcha una di queste regole:
- estensione documentale: `*.md`, `*.txt`, `*.rst`, `*.pdf`, `*.png`, `*.jpg`, `*.svg`
  (anche sotto `docs/` — l'estensione, non il path, è il criterio)
- manifest plugin NON eseguibili, per path ESATTO: `.claude-plugin/plugin.json`,
  `.claude-plugin/marketplace.json`

Tutto il resto → `risk=code` → gate pieno. In particolare restano `code`:
qualsiasi `*.sh|*.py|*.js|*.ts|*.json` (eccetto i 2 manifest), file SENZA estensione
(es. `hooks/stop-gate`, `docs/whatever`), `hooks.json`, `settings*.json`, `*.tf`, `*.hcl`.

**Razionale anti-bypass (ISSUE review iter-1):**
- NON usiamo il prefisso `docs/`: un file `docs/evil` (script senza estensione) o
  `docs/x.json` matcherebbe il prefisso ma è eseguibile/config → ora forza `code`.
- **Rename-aware**: si usa `git diff --name-status` (NON `--name-only`). Per ogni rename
  `R` si valutano SIA il path sorgente SIA il destinazione: se ANCHE UNO è fuori
  allowlist → `code`. Blocca `git mv hooks/x docs/x.md` (sorgente `hooks/x` non-allowlist).
- `git` normalizza i path nell'output (no `..`/traversal) → no path-traversal bypass.

**ADR-3 — Downgrade ad advisory = ZERO-enforcement (scelta consapevole).**
Su `risk=low` il gate NON emette `decision:block`; emette `additional_context` che segnala
"gate X scalato ad advisory: diff doc-only/manifest, skill consigliata ma non obbligatoria".
**Esplicito (ISSUE review iter-1)**: advisory significa che l'LLM PUÒ procedere con
`gh pr create` senza invocare la skill — non c'è meccanismo di conferma né enforcement.
È intenzionale: l'obiettivo è ridurre l'attrito su cambi inerti, non forzare una skill
abbreviata. Tracciabilità: log evento `pr_gate_scaled` (`risk`/`gate`) → il downgrade è
auditabile a valle, non un bypass nascosto. Il floor security/secret resta hard.

**ADR-4 — Coerenza skill↔hook (ISSUE review iter-1).**
`siae-premortem` SKILL.md dichiara "nessun bypass discrezionale" e `siae-blind-review`
richiede "conferma umana" per l'eccezione documentale. Entrambe vanno aggiornate
contestualmente a questo design per allinearsi alla policy "diff `risk=low` → gate
advisory automatico". Senza l'update, skill e hook sarebbero in contraddizione.

## 4. Componenti

### 4.1 `lib/diff-risk-classifier.sh` (NUOVO)
Funzione `devforge_classify_diff_risk` (sourcing-safe, `set -euo pipefail`-safe):
1. Determina base branch: arg `$1` o fallback `origin/main`.
2. `STATUS=$(git diff --name-status "${BASE}...HEAD" 2>/dev/null)`. Se `git` fallisce
   (branch base assente, repo non valido) → stampa `code` e return (fail-safe).
3. **Diff vuoto → `code`** (nessuna modifica = nessun motivo di scalare; fail-safe).
4. Per ogni riga di `--name-status`:
   - rename (`R*`): la riga ha 2 path (src, dst) → valuta ENTRAMBI; se uno fuori
     allowlist → stampa `code`, return.
   - altrimenti 1 path → se fuori allowlist → stampa `code`, return.
5. Se tutti i path matchano → stampa `low`.
Allowlist (funzione `_devforge_path_is_lowrisk`): regex
`\.(md|txt|rst|pdf|png|jpe?g|svg)$` OPPURE path esatto
`.claude-plugin/(plugin|marketplace).json`.
Output su stdout: ESATTAMENTE `low` | `code` (mai vuoto: ogni ramo stampa un token).
Nessun side-effect.

### 4.2 `hooks/pr-premortem-gate` e `hooks/pr-blind-review-gate` (MODIFICA)
Dopo aver determinato `TRIGGERS=1` e PRIMA del blocco per skill-mancante:
```bash
source "${PLUGIN_ROOT}/lib/diff-risk-classifier.sh" 2>/dev/null || true
RISK=code
command -v devforge_classify_diff_risk >/dev/null 2>&1 \
    && RISK=$(devforge_classify_diff_risk "origin/main" 2>/dev/null || echo code)
# RISK inizializzato a 'code' PRIMA della chiamata (fail-safe se classifier assente
# o stdout vuoto: RISK resta 'code', mai 'low' per accidente — ISSUE review iter-1).
if [ "$RISK" = "low" ] && ! <skill validata>; then
    devforge_log "pr_gate_scaled" "info" "{\"gate\":\"<nome>\",\"risk\":\"low\"}"
    cat <<EOF
{ "additional_context": "<IMPORTANT>DevForge <Gate>: diff a basso rischio (doc-only/manifest). <skill> consigliata ma gate scalato ad advisory (non bloccante). Floor security invariato.</IMPORTANT>" }
EOF
    exit 0
fi
# else: comportamento attuale (block se skill mancante)
```
Il blocco hard resta IDENTICO per `risk=code`.

### 4.3 `skills/siae-premortem/SKILL.md` + `skills/siae-blind-review/SKILL.md` (MODIFICA — ADR-4)
- `siae-premortem`: sostituire l'asserzione "Nessun bypass discrezionale ... anche bump
  meccanici" con la policy allineata: "il gate `pr-premortem-gate` blocca per `risk=code`;
  per diff `risk=low` (doc-only/manifest, classificato da `lib/diff-risk-classifier.sh`)
  il gate è advisory automatico — premortem facoltativo".
- `siae-blind-review`: l'eccezione "modifiche esclusivamente documentali" passa da
  "chiedi al partner umano" a "advisory automatico per `risk=low` via classifier" (niente
  conferma umana manuale richiesta per doc-only).
- Coerenza count skill: le SKILL.md non cambiano di numero (modifica in-place).

## 5. Gestione errori
- Classifier non sourcabile / git fail / detached HEAD → `RISK=code` (fail-closed sul
  rischio: in dubbio, gate pieno). Mai fail-open.
- Base branch inesistente localmente → `git diff` fallisce → `code`.

## 6. Testing (TDD)
`tests/hooks/test_diff_risk_classifier.sh` (fixture: repo git temp con commit reali):
- AC-1: diff solo `*.md` → `low`.
- AC-2: diff solo `.claude-plugin/plugin.json` → `low`.
- AC-3: diff con `hooks/foo` misto a `.md` → `code`.
- AC-4: diff con `hooks.json` → `code` (config eseguibile escluso).
- AC-5: diff vuoto → `code` (fail-safe).
- AC-6: diff con `*.py`/`*.sh` → `code`.
- AC-11 (rename bypass): `git mv hooks/x.sh docs/x.md` → `code` (sorgente non-allowlist).
- AC-12 (no-extension under docs): file `docs/runme` (senza estensione) → `code`.
- AC-13 (base branch arg): classifier con base diversa da origin/main usa l'arg passato.
- AC-14 (`.claude-plugin/evil.json`): NON è manifest → `code`.

`tests/hooks/test_pr_gate_scaling.sh`:
- AC-7: `pr-premortem-gate` su `gh pr create` con diff doc-only + premortem NON validato
  → NON `decision:block` (advisory).
- AC-8: stesso ma diff con file `hooks/` → `decision:block` (no-regression).
- AC-9: `pr-blind-review-gate` idem AC-7/AC-8.
- AC-10 (no-regression): floor security/secret invariato — `pre-commit` secret scan non
  toccato (verifica strutturale: il diff non modifica `pre-commit`).

## 7. Criteri di accettazione
1. `devforge_classify_diff_risk` ritorna `low` solo per diff interamente in allowlist,
   `code` altrimenti, `code` su errore (AC-1..6).
2. `pr-premortem-gate` e `pr-blind-review-gate` su diff `low` → advisory non bloccante (AC-7,9).
3. Su diff `code` → block invariato (AC-8,9 no-regression).
4. Evento `pr_gate_scaled` loggato quando il downgrade avviene (auditabilità).
5. Nessuna modifica a secret scan / security / review-evidence floor (AC-10).
6. Rename code→doc-path classificato `code` (AC-11); manifest impostori `code` (AC-14).
7. `siae-premortem` + `siae-blind-review` SKILL.md aggiornate: nessuna contraddizione
   residua skill↔hook (grep "nessun bypass" non più assoluto in siae-premortem).
8. Suite no-regression verde (gate esistenti).

## 8. Out of scope
- `review-evidence` drift/coverage scaling (separato; drift FP su header numerati ha già
  un follow-up dedicato).
- `finishing-branch` Step 4c (richiama blind-review che ora scala da sé → effetto a cascata
  gratuito, nessuna modifica diretta necessaria).
- Estensione dell'allowlist oltre doc + manifest plugin (config eseguibile resta full-gate).
