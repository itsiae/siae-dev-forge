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

## Schema YAML Fingerprint (locked) — v1.1

```yaml
app: "appavvisi"
branch: "main-alt"
extracted_at: "2026-03-31T..."
schema_version: "1.1"
module_type: "sapui5"   # enum: sapui5 | cap_cds (wf_* modules)

# ── LAYER 1-A: regex/bash — JS files ──

deprecated_imports:
  - file: "webapp/controller/App.controller.js"
    line: 3
    api: "sap/ui/model/odata/v2/ODataModel"   # verbatim dall'import

odata_v2_calls:
  - file: "webapp/controller/App.controller.js"
    line: 45
    # enum: read|create|update|remove|callFunction|submitChanges|resetChanges|
    #       setProperty|getProperty|bindElement|attachBatchRequestCompleted|attachRequestCompleted
    operation: "read"
    entity: "/EntitySet"       # verbatim
    verbatim: "this.getModel().read(\"/EntitySet\","

# ── LAYER 1-B: regex/bash — method signatures + routing ──

method_signatures:
  - name: "onInit"              # cattura: on*, _*, init, exit, onBeforeRendering, onAfterRendering, ES6 arrow
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
  routes: ["RouteMain", "RouteDetail"]   # da manifest.json sap.ui5.routing.routes

data_sources:                             # da manifest.json sap.app.dataSources — CRITICO
  - name: "mainService"
    uri: "/sap/opu/odata/siae/LIQUIDAZIONE_SRV/"
    type: "OData"

# ── LAYER 1-C: regex/bash — XMLView + Component.js ──

xmlview_bindings:                         # da *.view.xml e *.fragment.xml
  - file: "webapp/view/App.view.xml"
    line: 12
    # enum: formatter|press|change|selectionChange|liveChange|fragment
    type: "formatter"
    verbatim: "formatter='.formatStatusLabel'"
  - file: "webapp/view/App.view.xml"
    line: 34
    type: "press"
    verbatim: "press=\".onSubmit\""

component_models:                         # da webapp/Component.js
  - name: ""                              # verbatim: nome modello (stringa vuota = default)
    type: "ODataModel"                    # enum: ODataModel|JSONModel|ResourceModel
    verbatim: "this.setModel(new ODataModel(sServiceUrl), \"\");"
    file: "webapp/Component.js"
    line: 34

# ── LAYER 1-D: regex/bash — CAP CDS (solo moduli wf_*) ──

cap_handlers:                             # da srv/*.js — presente solo se module_type = cap_cds
  - file: "srv/liquidazione-service.js"
    hook: "before"                        # enum: before|on|after
    event: "CREATE"                       # enum: CREATE|READ|UPDATE|DELETE|<action_name>
    entity: "Liquidazioni"
    verbatim: "this.before('CREATE', 'Liquidazioni', async (req) => {"
    line: 12

cds_annotations:                          # da *.cds files — presente solo se module_type = cap_cds
  - file: "srv/liquidazione-service.cds"
    annotation: "@restrict"
    verbatim: "@restrict: [{ grant: 'READ', to: 'authenticated-user' }]"
    line: 8

cap_config:                               # da package.json sezione cds
  cds_version: "^6.8.0"
  services:
    - name: "db"
      kind: "hana"

# ── LAYER 2: Claude schema-locked (atomico: un file per invocazione) ──

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
      # enum: MessageBox.error|MessageBox.success|MessageBox.warning|navigation|
      #       OData.write|OData.read|BusyIndicator|Fragment
      - type: "MessageBox.error"
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
    # enum: callFunction|read|create|update|remove|batch
    type: "callFunction"
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

> **Nota metrica:** la colonna chiave è `CRITICAL`. Non usare OK% come indicatore di salute.
> Un'app con `CRITICAL=0` è sicura per il merge. Vedere SUMMARY.md per la classificazione.

---

## Delivery: Claude Code Skill

**Nome skill:** `siae-btp-upgrade-audit`
**Trigger:** `/forge-btp-audit`
**Tipo:** Rigid
**Fase SDLC:** 4. Implementation (tool di supporto upgrade)

### Comandi skill

| Comando | Azione |
|---------|--------|
| `/forge-btp-baseline <branch> [--app=nome]` | Fase 1: genera fingerprint per tutte le app o per una sola |
| `/forge-btp-audit <old-branch> <new-branch> [--app=nome]` | Fase 2: gap analysis completa o per singola app |

### Flusso operativo della skill

1. **Input validation**: risolvi branch → SHA (gh api ref/heads → commit → tree)
   - Se branch non esiste: `ERRORE: branch '<X>' non trovato`
   - Se `--app=nome` e app non trovata: `ERRORE: app '<nome>' non trovata. App disponibili: <lista>`
2. **App discovery**: lista tutti i moduli `app*` e `wf_*` dal tree root
3. **Identifica tipo modulo**: `app*` → sapui5; `wf_*` → verifica presenza `srv/` → cap_cds
4. **Per ogni app — Layer 1 (bash)**:
   - Layer 1-A: deprecated imports + OData v2 calls (tutti i metodi del modello)
   - Layer 1-B: method signatures (on*, _*, ES6, lifecycle) + navigation + routing + dataSources
   - Layer 1-C: XMLView bindings + Component.js model registration
   - Layer 1-D (solo cap_cds): CAP handlers srv/*.js + CDS annotations + cap_config
5. **Per ogni app — Layer 2 (Claude schema-locked, atomico)**:
   - Un file controller alla volta, TUTTI i metodi in una sola invocazione
   - Popola `error_handlers`, `logic_blocks`, `external_calls`
   - Zero campi liberi — solo verbatim, enum, boolean, null
6. **Checkpoint**: salva `fingerprints/old/{app}.yaml` dopo ogni app
7. **Diff con canonicalizzazione**:
   - Normalizza whitespace prima del confronto verbatim
   - Applica rename detection per suggerire possibili rinominazioni
8. **Report**: genera `gap-report/{app}.md` con CRITICAL / HIGH / LOGIC DIFF / INFO / OK
   - Metrica primaria: conteggio CRITICAL (non OK%)
   - SUMMARY.md: tabella multi-app con colonne CRITICAL, HIGH, LOGIC DIFF

---

## Criteri di Accettazione

- [ ] Fingerprint generato per 100% delle app con checkpoint su filesystem (una app alla volta)
- [ ] Nessun campo libero nel YAML — solo verbatim, enum, boolean, null
- [ ] Gap report contiene sempre: severità, campo old (verbatim), campo new (verbatim o NON TROVATO)
- [ ] Modalità `--app` per analisi singola app funzionante con exit esplicito se app non trovata
- [ ] Report identico se eseguito due volte sullo stesso input (deterministmo verificabile)
- [ ] XMLView bindings presenti nel fingerprint (`xmlview_bindings`, `component_models`)
- [ ] `data_sources` nel fingerprint (URI servizio OData tracciata)
- [ ] Negative test su `appavvisi` produce CRITICAL e LOGIC DIFF attesi
- [ ] Skill tipo `Rigid` (non `Flexible`)
- [ ] `gh api` usa sempre risoluzione branch→SHA (zero chiamate con branch name diretto)
- [ ] Layer 2 atomico: un file alla volta, tutti i metodi in una sola invocazione

---

## Decisioni Architetturali (ADR)

| # | Decisione | Motivazione |
|---|-----------|-------------|
| 1 | Fingerprint locali (no commit) | Evitare rumore nel repo; rigenerabili in pochi minuti |
| 2 | Layer 1 bash + Layer 2 Claude | Bash per il meccanico (determinismo assoluto); Claude solo per semantica con schema locked |
| 3 | Zero campi liberi nel YAML | Il modello non interpreta — estrae. Deterministmo garantito by design. |
| 4 | Report human-readable Markdown | Il team consuma il report direttamente, senza tool aggiuntivi |
| 5 | Modalità `--app` per singola app | 70+ app = esecuzione completa lunga; iterazioni veloci su singola app |
| 6 | Layer 1-C per XMLView + Component.js | Logica business (formatter, event bindings, model registration) vive nei file XML/Component tanto quanto nei controller JS |
| 7 | Canonicalizzazione verbatim prima del diff | Differenze di whitespace producono falsi positivi che erodono la fiducia nel tool |
| 8 | Rename detection best-effort | Metodi rinominati sistemicamente (es. OData v4 migration) producono alert fatigue se trattati solo come CRITICAL; il suggerimento riduce il rumore mantenendo la sicurezza |
| 9 | Layer 2 atomico (un file per invocazione) | Ambiguità dell'unità di elaborazione causa variabilità dell'output tra esecuzioni — viola il determinismo |
| 10 | CAP CDS come Layer 1-D separato | I moduli wf_* hanno una struttura radicalmente diversa (srv/, .cds) rispetto alle app SAPUI5; separarli evita falsi negativi su handler CAP e annotation di sicurezza |
| 11 | Checkpoint su filesystem dopo ogni app | Sessioni lunghe (70+ app) rischiano crash; il checkpoint permette di riprendere senza ripetere il lavoro già fatto |
| 12 | Skill tipo Rigid | Il protocollo di estrazione non ammette adattamenti: ogni variazione rompe il determinismo. Flexible permetterebbe a Claude di "ottimizzare" con verbatim parafrasati |

---

## Story Points

**15 SP-Umano / 5 SP-Augmented**

- Tipo dominante: feature nuova cross-domain (skill framework + analisi codice SAP)
- Accelerazione AI: ~3x (logica complessa ma spec definite — +2 SP per coverage CAP e XMLView)
- Rispetto alla stima originale (13 SP): +2 per Layer 1-C (XMLView/Component) e Layer 1-D (CAP CDS)
