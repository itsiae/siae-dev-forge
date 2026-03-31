# Task 02 — Layer 1: Deprecated Imports + OData v2 Calls + XMLView Bindings

**Stato:** [PENDING]
**File:** `skills/siae-btp-upgrade-audit/SKILL.md` (sezione Phase 1, Layer 1 — parti A e C)
**Dipende da:** Task 01

---

## Obiettivo

Implementare nella skill il protocollo di estrazione Layer 1 per:
- `deprecated_imports`: pattern di import SAP deprecati
- `odata_v2_calls`: chiamate OData v2 (tutti i metodi del modello, non solo read/create)
- `xmlview_bindings`: formatter, event handler, fragment include nei file `.view.xml` / `.fragment.xml`
- `component_models`: registrazione modelli in `Component.js`

Tutto via `gh api` (accesso remoto al repo — no clone locale).

**FIX CRITICO:** il GitHub API non accetta branch name in `/git/trees/`. Richiede SHA.
Ogni accesso al tree DEVE passare per la risoluzione branch → commit SHA → tree SHA.

---

## Step 1 — Leggi il SKILL.md attuale

```bash
cat /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Verifica che contenga `[PLACEHOLDER: PHASE 1 — BASELINE]`.

---

## Step 2 — Sostituisci il placeholder Phase 1 con il contenuto Layer 1 (parti A e C)

Sostituisci `## [PLACEHOLDER: PHASE 1 — BASELINE]` con la sezione completa seguente.

La sezione da aggiungere è:

```markdown
## Phase 1 — BASELINE: Genera Fingerprint

### Input
- `<branch>`: branch vecchio (es. `main-alt`)
- `[--app=nome]`: opzionale, analizza una sola app

### Risoluzione Branch → SHA (OBBLIGATORIA)

<EXTREMELY-IMPORTANT>
Il GitHub API non accetta branch name in /git/trees/. Richiede SHA.
Eseguire SEMPRE questa sequenza di risoluzione PRIMA di qualsiasi accesso al tree.
Salvare REF_SHA e TREE_SHA come variabili di sessione per riuso.
</EXTREMELY-IMPORTANT>

```bash
# Step A: branch → commit SHA
REF_SHA=$(gh api repos/itsiae/liquidazione/git/ref/heads/<BRANCH> \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['object']['sha'])")

# Step B: commit SHA → tree SHA
TREE_SHA=$(gh api repos/itsiae/liquidazione/git/commits/${REF_SHA} \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['tree']['sha'])")

echo "Branch <BRANCH> → tree: ${TREE_SHA}"
```

Output atteso: `Branch main-alt → tree: <sha40>`

Se il branch non esiste: `gh api` restituisce 404 → interrompi con messaggio:
`ERRORE: branch '<BRANCH>' non trovato in itsiae/liquidazione`

---

### App Discovery

```bash
# Lista tutti i moduli top-level del repo (usa TREE_SHA già risolto)
gh api "repos/itsiae/liquidazione/git/trees/${TREE_SHA}" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
apps = [x['path'] for x in d.get('tree', [])
        if x['type'] == 'tree'
        and (x['path'].startswith('app') or x['path'].startswith('wf_'))]
if not apps:
    print('ERRORE: nessun modulo app* o wf_* trovato nel tree root', file=sys.stderr)
    sys.exit(1)
print('\n'.join(apps))
"
```

Output atteso: lista di nomi tipo `appavvisi`, `appcausali`, `wf_controlli`, ...

Se `--app=nome` specificato: verifica che `nome` sia nella lista, poi filtra a solo quel modulo.
Se non trovato: `ERRORE: app '<nome>' non trovata. App disponibili: <lista>`

---

### Acquisizione SHA Tree per Singola App

```bash
# Ottieni SHA subtree dell'app (usa TREE_SHA già risolto)
APP_TREE_SHA=$(gh api "repos/itsiae/liquidazione/git/trees/${TREE_SHA}" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
for x in d['tree']:
    if x['path'] == '<APP_NAME>':
        print(x['sha'])
        break
else:
    import sys; print('NOT_FOUND', file=sys.stderr); sys.exit(1)
")

# Lista file del controller (JS e XML) con SHA
gh api "repos/itsiae/liquidazione/git/trees/${APP_TREE_SHA}?recursive=1" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
files = [x for x in d.get('tree', [])
         if x['type'] == 'blob'
         and (x['path'].endswith('.js') or x['path'].endswith('.view.xml')
              or x['path'].endswith('.fragment.xml'))
         and ('controller/' in x['path'] or 'view/' in x['path']
              or x['path'].endswith('Component.js'))]
for f in files:
    print(f['path'], f['sha'])
"
```

---

### Layer 1-A: Deprecated Imports

Per ogni file `.js`, leggi il contenuto e cerca gli import deprecati:

```bash
# Leggi contenuto file via blob SHA
CONTENT=$(gh api repos/itsiae/liquidazione/git/blobs/<FILE_SHA> \
  | python3 -c "
import sys, json, base64
d = json.load(sys.stdin)
print(base64.b64decode(d['content']).decode('utf-8', errors='replace'))
")

# Cerca pattern deprecated con numero di riga
echo "$CONTENT" | grep -n \
  -e "sap/ui/model/odata/v2/ODataModel" \
  -e "sap/ui/model/odata/v2/ODataListBinding" \
  -e "jQuery\.sap\." \
  -e "sap\.ui\.getCore()" \
  -e "sap/ui/core/BusyIndicator" \
  -e "@ui5/cli.*[\"']2\." \
  -e "sap/m/MessageToast" \
  -e "sap\.ui\.require\s*\(" \
  | awk -F: '{print "  - file: \"<FILE_PATH>\"\n    line: " $1 "\n    api: \"" $2 "\"\n    verbatim: \"" $0 "\""}'
```

Output (sezione YAML fingerprint `deprecated_imports`):
```yaml
deprecated_imports:
  - file: "webapp/controller/App.controller.js"
    line: 3
    api: "sap/ui/model/odata/v2/ODataModel"
    verbatim: "sap/ui/model/odata/v2/ODataModel"
```

---

### Layer 1-A: OData v2 Calls

Per ogni file `.js`, cerca TUTTE le chiamate al modello OData (non solo read/create):

```bash
echo "$CONTENT" | grep -n \
  -e "\.read(" \
  -e "\.create(" \
  -e "\.update(" \
  -e "\.remove(" \
  -e "\.callFunction(" \
  -e "\.submitChanges(" \
  -e "\.resetChanges(" \
  -e "\.setProperty(" \
  -e "\.getProperty(" \
  -e "\.bindElement(" \
  -e "\.attachBatchRequestCompleted(" \
  -e "\.attachRequestCompleted(" \
  | grep -v "^\s*//" \
  | while IFS=: read -r LINE REST; do
      OP=$(echo "$REST" | grep -oE '\.(read|create|update|remove|callFunction|submitChanges|resetChanges|setProperty|getProperty|bindElement|attachBatchRequestCompleted|attachRequestCompleted)\(' | head -1 | tr -d '.(')
      ENTITY=$(echo "$REST" | grep -oE '"\/[A-Za-z][A-Za-z0-9_]*' | head -1 | tr -d '"')
      VERBATIM=$(echo "$REST" | sed 's/^[[:space:]]*//' | cut -c1-120)
      printf "  - file: \"%s\"\n    line: %s\n    operation: \"%s\"\n    entity: \"%s\"\n    verbatim: \"%s\"\n" \
        "<FILE_PATH>" "${LINE}" "${OP}" "${ENTITY:-null}" "${VERBATIM}"
    done
```

Enum `operation` aggiornato:
`read | create | update | remove | callFunction | submitChanges | resetChanges | setProperty | getProperty | bindElement | attachBatchRequestCompleted | attachRequestCompleted`

Output (sezione YAML fingerprint `odata_v2_calls`):
```yaml
odata_v2_calls:
  - file: "webapp/controller/App.controller.js"
    line: 45
    operation: "read"
    entity: "/LiquidazioniSet"
    verbatim: "this.getModel().read(\"/LiquidazioniSet\","
  - file: "webapp/controller/App.controller.js"
    line: 89
    operation: "submitChanges"
    entity: null
    verbatim: "this.getModel().submitChanges({"
```

---

### Layer 1-C: XMLView Bindings + Component.js Models

Per ogni file `.view.xml` e `.fragment.xml`:

```bash
XML_CONTENT=$(gh api repos/itsiae/liquidazione/git/blobs/<FILE_SHA> \
  | python3 -c "
import sys, json, base64
d = json.load(sys.stdin)
print(base64.b64decode(d['content']).decode('utf-8', errors='replace'))
")

# Cerca formatter, event handler bindings, fragment includes
echo "$XML_CONTENT" | grep -n \
  -e "formatter=" \
  -e " press=" \
  -e " change=" \
  -e " selectionChange=" \
  -e " liveChange=" \
  -e "core:Fragment" \
  | while IFS=: read -r LINE REST; do
      TYPE=$(echo "$REST" | grep -oE 'formatter=|press=|change=|selectionChange=|liveChange=|core:Fragment' | head -1 | tr -d '=')
      VERBATIM=$(echo "$REST" | sed 's/^[[:space:]]*//' | cut -c1-120)
      printf "  - file: \"%s\"\n    line: %s\n    type: \"%s\"\n    verbatim: \"%s\"\n" \
        "<FILE_PATH>" "${LINE}" "${TYPE}" "${VERBATIM}"
    done
```

Enum `type`: `formatter | press | change | selectionChange | liveChange | fragment`

Output (sezione YAML fingerprint `xmlview_bindings`):
```yaml
xmlview_bindings:
  - file: "webapp/view/App.view.xml"
    line: 12
    type: "formatter"
    verbatim: "text=\"{path: '/Status', formatter: '.formatStatusLabel'}\""
  - file: "webapp/view/App.view.xml"
    line: 34
    type: "press"
    verbatim: "press=\".onSubmit\""
```

Per `Component.js`, cerca registrazioni modello:

```bash
COMP_CONTENT=$(gh api repos/itsiae/liquidazione/git/blobs/<COMPONENT_SHA> \
  | python3 -c "
import sys, json, base64
d = json.load(sys.stdin)
print(base64.b64decode(d['content']).decode('utf-8', errors='replace'))
")

echo "$COMP_CONTENT" | grep -n \
  -e "setModel\s*(" \
  -e "new ODataModel\|new JSONModel\|new ResourceModel" \
  | while IFS=: read -r LINE REST; do
      TYPE=$(echo "$REST" | grep -oE 'ODataModel|JSONModel|ResourceModel' | head -1)
      NAME=$(echo "$REST" | grep -oE '"[^"]*"' | tail -1 | tr -d '"')
      VERBATIM=$(echo "$REST" | sed 's/^[[:space:]]*//' | cut -c1-120)
      printf "  - name: \"%s\"\n    type: \"%s\"\n    verbatim: \"%s\"\n    file: \"webapp/Component.js\"\n    line: %s\n" \
        "${NAME:-}" "${TYPE:-unknown}" "${VERBATIM}" "${LINE}"
    done
```

Output (sezione YAML fingerprint `component_models`):
```yaml
component_models:
  - name: ""
    type: "ODataModel"
    verbatim: "this.setModel(new ODataModel(sServiceUrl), \"\");"
    file: "webapp/Component.js"
    line: 34
  - name: "i18n"
    type: "ResourceModel"
    verbatim: "this.setModel(new ResourceModel({ bundleName: ... }), \"i18n\");"
    file: "webapp/Component.js"
    line: 41
```
```

---

## Step 3 — Verifica che il placeholder sia stato sostituito e i nuovi layer siano presenti

```bash
grep -c "PLACEHOLDER: PHASE 1" \
  /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Output atteso: `0`

```bash
grep -c "deprecated_imports\|odata_v2_calls\|xmlview_bindings\|component_models" \
  /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Output atteso: `4` o più

```bash
# Verifica fix gh api: nessuna occorrenza del pattern errato
grep -c "git/trees/main\|git/trees/feature\|git/trees/<branch>" \
  /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Output atteso: `0`

---

## Step 4 — Commit

```bash
git add skills/siae-btp-upgrade-audit/SKILL.md
git commit -m "feat(skills): add layer1-A (deprecated+odata extended) and layer1-C (xmlview+component) to btp-upgrade-audit"
```
