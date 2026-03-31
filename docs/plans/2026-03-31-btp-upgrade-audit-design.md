# Design: siae-btp-upgrade-audit

**Data:** 2026-03-31
**Autore:** mario-siae
**Status:** APPROVATO

---

## Contesto

Il repo `itsiae/liquidazione` contiene 70+ moduli SAP BTP (app SAPUI5 Fiori + workflow CAP CDS)
che devono subire un upgrade massiccio delle librerie SAP deprecate (`@ui5/cli` v2,
`sap.ui.model.odata.v2`, `@sap/cds`, ecc.).

Il rischio principale è la **regressione silente**: il nuovo codice compila e gira,
ma ha perso logica di business (condizioni mancanti, guard rimossi, side effect persi).

---

## Obiettivo

Uno strumento Claude Code (skill + hook in `siae-dev-forge`) che:

1. **Fase 1 — BASELINE**: estrae un fingerprint strutturato da ogni app sul branch vecchio
2. **Fase 2 — AUDIT**: estrae lo stesso fingerprint dal branch nuovo e produce un gap report per app

L'output è **deterministico**: nessun campo libero, nessuna interpretazione del modello.
Il modello agisce come estrattore strutturato. Il giudizio "è un bug?" rimane umano.

---

## Architettura

```
Fase 1 — BASELINE                    Fase 2 — AUDIT
─────────────────────                ──────────────────────────
Branch vecchio (es. main-alt)        Branch nuovo (feature/upgrade-*)
        │                                      │
        ▼                                      ▼
  Per ogni app (70+)               Per ogni app (70+)
  Layer 1: grep/bash         +     stesso Layer 1 + Layer 2
  Layer 2: Claude schema-locked
        │                                      │
        ▼                                      ▼
  fingerprints/old/{app}.yaml      fingerprints/new/{app}.yaml
        │                                      │
        └──────────────┬───────────────────────┘
                       ▼
               diff strutturato YAML
                       │
                       ▼
            gap-report/{app}.md  ← output finale
```

I fingerprint sono file locali generati durante la sessione Claude Code (no commit al repo).

---

## Principio di Deterministmo

Ogni campo dello schema fingerprint è uno di:
- `string` → estratto **verbatim** dal codice sorgente (mai parafrasi)
- `boolean` → presente/assente
- `integer` → conteggio
- `null` → non trovato (mai "probabilmente" o "sembra")

Il modello NON può produrre:
- Descrizioni narrative di cosa fa il codice
- Giudizi di equivalenza ("questo fa la stessa cosa")
- Valutazioni di qualità

---

## Schema YAML Fingerprint (locked)

```yaml
app: "appavvisi"
branch: "main-alt"
extracted_at: "2026-03-31T..."
schema_version: "1.0"

# ── LAYER 1: regex/bash (deterministico puro) ──

deprecated_imports:
  - file: "webapp/controller/App.controller.js"
    line: 3
    api: "sap/ui/model/odata/v2/ODataModel"   # stringa esatta dall'import

odata_v2_calls:
  - file: "webapp/controller/App.controller.js"
    line: 45
    operation: "read"          # enum: read|create|update|callFunction|remove
    entity: "/EntitySet"       # stringa esatta
    verbatim: "this.getModel().read(\"/EntitySet\","

method_signatures:
  - name: "onInit"
    file: "webapp/controller/App.controller.js"
    line: 12
  - name: "_validateForm"
    file: "webapp/controller/App.controller.js"
    line: 67

navigation_targets:
  - target: "RouteView1"
    verbatim: "this.getRouter().navTo(\"RouteView1\""
    file: "webapp/controller/App.controller.js"
    line: 89

routing_config:
  routes: ["RouteMain", "RouteDetail"]   # da manifest.json

# ── LAYER 2: Claude schema-locked ──

error_handlers:
  - method: "onInit"
    present: true
    type: "catch"              # enum: catch|attachRequestFailed|onerror|fnError
    verbatim: "oModel.attachRequestFailed(function(oEvent) {"
    file: "webapp/controller/App.controller.js"
    line: 23

logic_blocks:
  - method: "_validateForm"
    inputs: ["oData"]

    conditions:
      - line: 34
        verbatim: "if (!oData.codiceAutore)"
        branch_true:  "return false"
        branch_false: null
      - line: 38
        verbatim: "if (oData.importo <= 0 || oData.importo > 999999)"
        branch_true:  "MessageBox.error(this._getText('ERR_IMPORTO'))"
        branch_false: null

    side_effects:
      - type: "MessageBox.error"   # enum: MessageBox.error|MessageBox.success|navigation|OData.write|OData.read|BusyIndicator
        verbatim: "MessageBox.error(this._getText('ERR_IMPORTO'))"
      - type: "navigation"
        verbatim: "this.getRouter().navTo(\"RouteConferma\""
      - type: "OData.write"
        verbatim: "this.getModel().create(\"/LiquidazioniSet\","

    return_values:
      - verbatim: "return false"
      - verbatim: "return oResult"

external_calls:
  - method: "onSubmit"
    type: "callFunction"           # enum: callFunction|read|create|update|remove
    endpoint: "/FunctionImport"
    verbatim: "this.getModel().callFunction(\"/FunctionImport\","
    file: "webapp/controller/App.controller.js"
    line: 112
```

---

## Gap Report — Formato Output per App

```markdown
# Gap Analysis: appavvisi
Branch baseline: main-alt  |  Branch nuovo: feature/upgrade-ui5v3
Generato: 2026-03-31

## CRITICAL (N)
- [C1] Metodo `onSubmit` assente nel nuovo codice
- [C2] Error handler mancante in `_loadData` (presente in baseline)

## LOGIC DIFF (N)
### _validateForm — condizione #2

OLD (main-alt, riga 38):
  if (oData.importo <= 0 || oData.importo > 999999)

NEW (feature/upgrade-ui5v3, riga 41):
  if (oData.importo < 0)

⚠️  DIFFERENZA STRUTTURALE RILEVATA
    Rimossi: guard `== 0` e upper bound `> 999999`
    → REVISIONE UMANA RICHIESTA

### _validateForm — side_effect #1

OLD: MessageBox.error(this._getText('ERR_IMPORTO'))
NEW: [NON TROVATO]

⚠️  DIFFERENZA STRUTTURALE RILEVATA
    Feedback errore all'utente rimosso.
    → REVISIONE UMANA RICHIESTA

## INFO (N)
- [I1] Nuovo metodo `onRefresh` non presente in baseline — verificare

## OK (14/20 items verificati)
```

---

## Delivery: Claude Code Skill

**Nome skill:** `siae-btp-upgrade-audit`
**Trigger:** `/forge-btp-audit`
**Tipo:** Flexible
**Fase SDLC:** 4. Implementation (tool di supporto upgrade)

### Comandi skill

| Comando | Azione |
|---------|--------|
| `/forge-btp-baseline <branch>` | Fase 1: genera fingerprint per tutte le app |
| `/forge-btp-audit <old-branch> <new-branch> [--app=appname]` | Fase 2: gap analysis completa o per singola app |
| `/forge-btp-audit --app=appavvisi` | Analisi singola app (utile per iterazioni veloci) |

### Flusso operativo della skill

1. **Input validation**: verifica che i branch esistano su `itsiae/liquidazione`
2. **App discovery**: lista tutti i moduli top-level dal tree Git
3. **Per ogni app — Layer 1 (bash)**:
   - `grep` per import deprecati SAP noti
   - `grep` per OData v2 call patterns
   - `grep` per method signatures (`onXxx`, `_xxx`)
   - `grep` per navigation (`navTo`, `getRouter`)
   - `cat` manifest.json per routing config
4. **Per ogni app — Layer 2 (Claude schema-locked)**:
   - Legge i controller JS
   - Popola `error_handlers`, `logic_blocks`, `external_calls`
   - Nessun campo libero ammesso — solo verbatim + enum + boolean
5. **Diff**: confronta fingerprint old vs new struttura per struttura
6. **Report**: genera `gap-report/{app}.md` con severity CRITICAL / LOGIC DIFF / INFO / OK

---

## Criteri di Accettazione

- [ ] Fingerprint generato per 100% delle app in < 10 min (sessione Claude Code)
- [ ] Nessun campo libero nel YAML — solo verbatim, enum, boolean, null
- [ ] Gap report contiene sempre: severità, campo old (verbatim), campo new (verbatim o NON TROVATO)
- [ ] Modalità `--app` per analisi singola app funzionante
- [ ] Report identico se eseguito due volte sullo stesso input (deterministmo verificabile)

---

## Decisioni Architetturali (ADR)

| # | Decisione | Motivazione |
|---|-----------|-------------|
| 1 | Fingerprint locali (no commit) | Evitare rumore nel repo; rigenerabili in pochi minuti |
| 2 | Layer 1 bash + Layer 2 Claude | Bash per il meccanico (determinismo assoluto); Claude solo per semantica con schema locked |
| 3 | Zero campi liberi nel YAML | Il modello non interpreta — estrae. Deterministmo garantito by design. |
| 4 | Report human-readable Markdown | Il team consuma il report direttamente, senza tool aggiuntivi |
| 5 | Modalità `--app` per singola app | 70+ app = esecuzione completa lunga; iterazioni veloci su singola app |

---

## Story Points

**13 SP-Umano / 5 SP-Augmented**

- Tipo dominante: feature nuova cross-domain (skill framework + analisi codice SAP)
- Accelerazione AI: ~2.5x (logica complessa ma spec definite)
