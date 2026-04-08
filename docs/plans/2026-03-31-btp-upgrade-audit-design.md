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

## Schema YAML Fingerprint (locked) — v1.3

```yaml
app: "appavvisi"
branch: "main-alt"
extracted_at: "2026-03-31T..."
schema_version: "1.3"
module_type: "sapui5"   # enum: sapui5 | cap_cds
# NOTA: module_type=cap_cds si applica SOLO al modulo liquidazione ROOT (che ha srv/)
# I moduli wf_* sono SAP BPM workflow (YAML/XML) — NON sono CAP services. Saltarli sempre.

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

eventbus_calls:                           # v1.3: EventBus publish/subscribe inter-controller
  - file: "webapp/controller/App.controller.js"
    line: 78
    type: "subscribe"                     # enum: subscribe | publish | unsubscribe
    channel: "sap.ui.core.EventBus"
    event: "dataLoaded"
    verbatim: "EventBus.getInstance().subscribe(\"sap.ui.core.EventBus\", \"dataLoaded\","

model_lifecycle_handlers:                 # v1.3: attachMetadataLoaded / attachMetadataFailed
  - file: "webapp/controller/App.controller.js"
    line: 34
    # enum: attachMetadataLoaded | attachMetadataFailed | attachRequestCompleted
    type: "attachMetadataLoaded"
    verbatim: "oModel.attachMetadataLoaded(function() {"

fragment_loads:                           # v1.3: Fragment.load() o sap.ui.xmlfragment()
  - file: "webapp/controller/App.controller.js"
    line: 56
    style: "Fragment.load"                # enum: Fragment.load | sap.ui.xmlfragment
    name: "siae.liquidazione.view.DetailDialog"
    verbatim: "Fragment.load({ name: \"siae.liquidazione.view.DetailDialog\","

dialog_lifecycle:                         # v1.3: dialog.open() / dialog.close() + side effects
  - file: "webapp/controller/App.controller.js"
    line: 67
    # enum: open | close | destroy
    event: "close"
    verbatim: "this._oDialog.close();"

external_formatters:                      # v1.3: import di formatter esterni
  - file: "webapp/controller/App.controller.js"
    line: 8
    formatter_path: "siae/liquidazione/formatter/StatusFormatter"
    verbatim: "\"siae/liquidazione/formatter/StatusFormatter\""

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

model_bindings:                           # v1.3: come viene ottenuto il model OData
  - file: "webapp/controller/App.controller.js"
    line: 23
    binding_type: "getModel"             # enum: getModel | component_property | owner_component
    verbatim: "const oModel = this.getModel(\"main\");"

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

# ── LAYER 1-D: regex/bash — CAP CDS (solo liquidazione root srv/) ──
# ARCHITETTURA: wf_* = SAP BPM workflow, NON CAP services. Non processarli.

cap_handlers:                             # da srv/*.js — solo se module_type = cap_cds
  - file: "srv/liquidazione-service.js"
    hook: "before"                        # enum: before|on|after
    event: "CREATE"                       # enum: CREATE|READ|UPDATE|DELETE|<action_name>
    entity: "Liquidazioni"
    verbatim: "this.before('CREATE', 'Liquidazioni', async (req) => {"
    line: 12

cap_security_checks:                      # v1.3: req.reject() nei handlers
  - file: "srv/liquidazione-service.js"
    line: 15
    method_context: "CREATE"
    http_code: 403
    verbatim: "req.reject(403, 'Accesso negato: utente non autorizzato');"

cap_lib_modules:                          # v1.3: helper di business logic in srv/lib/
  - file: "srv/lib/validation.js"
    line: 1
    verbatim: "module.exports = { validateLiquidazione, checkAutore }"

cap_context_accesses:                     # v1.3: req.user/tenant/data nei handlers
  - file: "srv/liquidazione-service.js"
    line: 18
    access_type: "user"                   # enum: user | tenant | data | params
    verbatim: "if (req.user.is('admin')) { req.reject(403); }"

cds_annotations:                          # da *.cds files — solo se module_type = cap_cds
  - file: "srv/liquidazione-service.cds"
    annotation: "@restrict"
    verbatim: "@restrict: [{ grant: 'READ', to: 'authenticated-user' }]"
    line: 8

cap_config:                               # da package.json sezione cds
  cds_version: "^6.8.0"
  odata_version: "v4"                     # v1.3: da cds.odata.version
  feature_lean_draft: true                # v1.3: da cds.features (breaking v6→v7)
  sql_native_hana_associations: null      # v1.3: da cds.sql (breaking v7)
  requires:
    - service: "db"
      kind: "hana"

# ── LAYER 1-E: bash pre-location (hint per Layer 2) ──
# data_transforms_hints e timing_hints sono SOLO per Layer 2 — non nel fingerprint finale

# ── LAYER 2: Claude schema-locked (atomico: un file per invocazione) ──

layer2_completeness:                      # v1.3: validation gate post-estrazione
  - file: "webapp/controller/App.controller.js"
    methods_expected: 8                   # da method_signatures Layer 1-B
    methods_extracted: 8
    completeness_ratio: 1.0
    status: "OK"                          # enum: OK | INCOMPLETE

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
        nesting_depth: 0               # v1.3: 0=top-level, 1=inside one if, 2=inside two if
        branch_true:                   # v1.2+: lista ORDINATA di TUTTE le azioni nel ramo true
          - "return false"
        branch_false: []               # lista vuota se ramo assente
        nested: []                     # v1.2+: condizioni annidate (max depth 2)
      - line: 38
        verbatim: "if (oData.importo <= 0 || oData.importo > 999999)"
        nesting_depth: 0
        branch_true:
          - "MessageBox.error(this._getText('ERR_IMPORTO'))"
        branch_false: []
        nested: []

    side_effects:
      # enum: MessageBox.error|MessageBox.success|MessageBox.warning|navigation|
      #       OData.write|OData.read|BusyIndicator|Fragment
      - type: "MessageBox.error"
        verbatim: "MessageBox.error(this._getText('ERR_IMPORTO'))"
      - type: "navigation"
        verbatim: "this.getRouter().navTo(\"RouteConferma\""
      - type: "OData.write"
        verbatim: "this.getModel().create(\"/LiquidazioniSet\","

    timing_annotations:                  # v1.3: delay/debounce logic
      - line: 56
        type: "setTimeout"               # enum: setTimeout|setInterval|debounce|throttle
        delay_ms: 500
        verbatim: "setTimeout(function() { this.getModel().create(...); }.bind(this), 500)"

    data_transforms:                   # v1.2+: trasformazioni dati nel metodo
      - line: 67
        # enum: reduce|filter|map|sort|arithmetic|format|parse|date
        operation: "filter"
        verbatim: "aItems.filter(function(o) { return o.stato === 'A'; })"

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
    callbacks:                         # v1.2+: handler success/error della callback OData
      style: "object_config"           # v1.3: enum: object_config|promise|async_await
      success_signature: "function(oData, oResponse)"   # v1.3: verbatim parametri
      success:
        - "this._onSubmitSuccess(oData)"
        - "this.getRouter().navTo(\"RouteConferma\""
      error_signature: "function(oError)"               # v1.3: verbatim parametri
      error:
        - "MessageBox.error(this._getText('ERR_SUBMIT'))"
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
2. **App discovery**: lista tutti i moduli `app*` dal tree root; identifica il modulo `liquidazione` root (CAP)
3. **Identifica tipo modulo**: `app*` → sapui5; modulo root con `srv/` → cap_cds. `wf_*` sono SAP BPM workflow — NON processarli.
4. **Per ogni app — Layer 1 (bash)**:
   - Layer 1-A: deprecated imports + OData v2 calls + EventBus + model lifecycle + fragment loads + dialog lifecycle + external formatters
   - Layer 1-B: method signatures (on*, _*, ES6, lifecycle) + navigation + routing + dataSources + model bindings
   - Layer 1-C: XMLView bindings + Component.js model registration
   - Layer 1-D (solo cap_cds, liquidazione root): CAP handlers + security checks + lib modules + context accesses + CDS annotations + cap_config
   - Layer 1-E: pre-location data_transforms e timing (hints per Layer 2 — non nel fingerprint)
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
- [ ] `branch_true`/`branch_false` sono liste ORDINATE nel fingerprint (schema v1.2+) — diff index-by-index
- [ ] `data_transforms` presente per i metodi con reduce/filter/map/Math/format/parse
- [ ] `external_calls.callbacks.success`/`.error` presenti per le OData calls con callback
- [ ] Layer 1-E grep individua i file con trasformazioni dati e timing logic prima di Layer 2
- [ ] `nesting_depth` integer presente in ogni condizione (v1.3) — cambio depth = CRITICAL
- [ ] `timing_annotations` presenti per metodi con setTimeout/debounce (v1.3)
- [ ] `layer2_completeness` calcolato e validato dopo ogni file (completeness_ratio = 1.0 richiesto)
- [ ] EventBus calls (`eventbus_calls`) tracciate (v1.3)
- [ ] Model lifecycle handlers (`model_lifecycle_handlers`) tracciati (v1.3)
- [ ] Fragment loads, dialog lifecycle, model bindings, external formatters tracciati (v1.3)
- [ ] Layer 1-D CAP si applica SOLO a liquidazione root (`srv/`) — `wf_*` saltati esplicitamente
- [ ] `cap_security_checks` (req.reject) tracciati — rimosso = CRITICAL (v1.3)
- [ ] `cap_config.odata_version` tracciato — cambio = CRITICAL (v1.3)
- [ ] Merge safety criteria: CRITICAL=0 AND LOGIC DIFF ≤ 3 (non solo CRITICAL=0)
- [ ] Tutti i grep Layer 1 con `| sort` prima dei loop while (determinismo su macOS vs Linux)

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
| 10 | CAP CDS come Layer 1-D separato (solo liquidazione root) | Il modulo liquidazione root ha `srv/`; i moduli `wf_*` sono SAP BPM workflow YAML/XML — non CAP services. Errore architetturale corretto in v1.3. |
| 11 | Checkpoint su filesystem dopo ogni app | Sessioni lunghe (70+ app) rischiano crash; il checkpoint permette di riprendere senza ripetere il lavoro già fatto |
| 12 | Skill tipo Rigid | Il protocollo di estrazione non ammette adattamenti: ogni variazione rompe il determinismo. Flexible permetterebbe a Claude di "ottimizzare" con verbatim parafrasati |
| 13 | `branch_true`/`branch_false` come liste ORDINATE (v1.2) | Una singola azione verbatim non cattura branch con più istruzioni; la lista ORDINATA garantisce che reorder `[A,B]→[B,A]` sia rilevato come LOGIC DIFF |
| 14 | `data_transforms` come campo separato (v1.2) | Le trasformazioni dati (reduce/filter/map/format) sono logica di business critica ma non rilevabile come side_effect; un campo dedicato permette un diff granulare |
| 15 | `callbacks` in `external_calls` (v1.2) | La logica post-OData (success/error handler) è spesso dove la business logic si nasconde; ignorarla produce falsi negativi su upgrade che cambiano le signature delle callback |
| 16 | Layer 1-E bash pre-location per data_transforms e timing | Il Layer 2 deve sapere dove concentrarsi; il grep bash riduce i falsi negativi senza aggiungere invocazioni Claude extra |
| 17 | `nesting_depth` integer in condizioni (v1.3) | Stessa condizione a profondità diversa ha semantica diversa (`if` annidato in `else` vs top-level); senza depth il diff è cieco a questo tipo di refactoring |
| 18 | Completeness validation post-Layer 2 (v1.3) | Claude può troncare l'output su file grandi; senza validazione, un file con 8 metodi di cui 3 estratti produce un fingerprint silentemente incompleto che poi passa il diff |
| 19 | Diff ordinato su `branch_true`/`branch_false` (v1.3) | Set-based comparison mancava il reorder delle azioni: `[BusyIndicator.show, create]` e `[create, BusyIndicator.show]` sono semanticamente diversi (race condition) |
| 20 | Merge safety: CRITICAL=0 AND LOGIC DIFF≤3 (v1.3) | Solo CRITICAL=0 era troppo permissivo: un'app con 10 LOGIC DIFF passava come "sicura" anche se richiedeva review approfondita |
| 21 | `grep | sort` obbligatorio in tutti i Layer 1 (v1.3) | Filesystem order diverso su macOS (HFS+) vs Linux (ext4) produce fingerprint non-deterministici; `sort` garantisce output identico su entrambi |
| 22 | EventBus, model lifecycle, fragment, dialog lifecycle (v1.3) | Pattern SAPUI5 avanzati non tracciati in v1.2: EventBus inter-controller, attachMetadataLoaded, Fragment.load() runtime, dialog.close() side-effects — tutti producono falsi negativi |
| 23 | `cap_security_checks` (req.reject) come campo separato (v1.3) | I security check (403 guards) sono la funzionalità più critica da verificare in un upgrade CAP; seppellirli in logic_blocks li rendeva invisibili al diff |
| 24 | `cap_config.odata_version` e feature flags (v1.3) | Il cambio di versione OData e i feature flag CAP sono breaking changes silenti: cambiano il comportamento runtime senza errori di compilazione |

---

## Story Points

**23 SP-Umano / 8 SP-Augmented**

- Tipo dominante: feature nuova cross-domain (skill framework + analisi codice SAP)
- Accelerazione AI: ~3x (logica complessa ma spec definite)
- Evoluzione stime:
  - v1.0 (schema base): 15 SP-U / 5 SP-A
  - v1.2 (+branch_true[], nested, data_transforms, callbacks, Layer 1-E): 18 SP-U / 6 SP-A
  - v1.3 (+nesting_depth, completeness_ratio, timing_annotations, EventBus, model_lifecycle, fragment, dialog, model_bindings, external_formatters, CAP architectural fix, cap_security_checks, diff ordinato, grep sort): +5 SP-U / +2 SP-A
- **Schema v1.3 nota SP:** l'architectural fix CAP (ADR-10 corretto) riduce la complessità di un modulo intero (wf_* saltati) ma aggiunge nuovi campi di tracking (cap_security_checks, cap_lib_modules, cap_context_accesses) — impatto netto +2 SP
