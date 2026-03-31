# Task 02 — Layer 1: Deprecated Imports + OData v2 Calls

**Stato:** [PENDING]
**File:** `skills/siae-btp-upgrade-audit/SKILL.md` (sezione Phase 1, Layer 1 — parte A)
**Dipende da:** Task 01

---

## Obiettivo

Implementare nella skill il protocollo di estrazione Layer 1 per:
- `deprecated_imports`: pattern di import SAP deprecati
- `odata_v2_calls`: chiamate OData v2 (read/create/update/callFunction/remove)

Tutto via `gh api` (accesso remoto al repo — no clone locale).

---

## Step 1 — Leggi il SKILL.md attuale

```bash
cat /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Verifica che contenga `[PLACEHOLDER: PHASE 1 — BASELINE]`.

---

## Step 2 — Sostituisci il placeholder Phase 1 con il contenuto Layer 1 (parte A)

Sostituisci `## [PLACEHOLDER: PHASE 1 — BASELINE]` con la sezione completa seguente.

La sezione da aggiungere è:

```markdown
## Phase 1 — BASELINE: Genera Fingerprint

### Input
- `<branch>`: branch vecchio (es. `main-alt`)
- `[--app=nome]`: opzionale, analizza una sola app

### App Discovery

```bash
# Lista tutti i moduli top-level del repo
gh api repos/itsiae/liquidazione/git/trees/<branch> \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
apps = [x['path'] for x in d.get('tree', [])
        if x['type'] == 'tree'
        and (x['path'].startswith('app') or x['path'].startswith('wf_'))]
print('\n'.join(apps))
"
```

Output atteso: lista di nomi tipo `appavvisi`, `appcausali`, `wf_controlli`, ...

Se `--app=nome` specificato: filtra a solo quel modulo.

---

### Layer 1-A: Deprecated Imports

Per ogni app, ottieni la lista dei file JS del controller:

```bash
# SHA del tree dell'app
APP_TREE_SHA=$(gh api repos/itsiae/liquidazione/git/trees/<branch> \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
for x in d['tree']:
    if x['path'] == '<APP_NAME>':
        print(x['sha'])
        break
")

# Lista file JS nel controller
gh api repos/itsiae/liquidazione/git/trees/${APP_TREE_SHA}?recursive=1 \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
js_files = [x for x in d.get('tree', [])
            if x['path'].endswith('.js') and x['type'] == 'blob']
for f in js_files:
    print(f['path'], f['sha'])
"
```

Per ogni file JS, leggi il contenuto e cerca gli import deprecati:

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

Per ogni file JS, cerca le chiamate OData v2:

```bash
echo "$CONTENT" | grep -n \
  -e "\.read(" \
  -e "\.create(" \
  -e "\.update(" \
  -e "\.remove(" \
  -e "\.callFunction(" \
  | grep -v "//\|console\|test\|spec" \
  | while IFS=: read -r LINE REST; do
      OP=$(echo "$REST" | grep -oE '\.(read|create|update|remove|callFunction)\(' | head -1 | tr -d '.(')
      ENTITY=$(echo "$REST" | grep -oE '"\/[A-Za-z][A-Za-z0-9_]*' | head -1 | tr -d '"')
      VERBATIM=$(echo "$REST" | sed 's/[[:space:]]*//' | cut -c1-80)
      echo "  - file: \"<FILE_PATH>\"\n    line: ${LINE}\n    operation: \"${OP}\"\n    entity: \"${ENTITY}\"\n    verbatim: \"${VERBATIM}\""
    done
```

Output (sezione YAML fingerprint `odata_v2_calls`):
```yaml
odata_v2_calls:
  - file: "webapp/controller/App.controller.js"
    line: 45
    operation: "read"
    entity: "/LiquidazioniSet"
    verbatim: "this.getModel().read(\"/LiquidazioniSet\","
```
```

---

## Step 3 — Verifica che il placeholder sia stato sostituito

```bash
grep -c "PLACEHOLDER: PHASE 1" \
  /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Output atteso: `0`

```bash
grep -c "deprecated_imports" \
  /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Output atteso: `1` o più

---

## Step 4 — Commit

```bash
git add skills/siae-btp-upgrade-audit/SKILL.md
git commit -m "feat(skills): add layer1 deprecated imports and odata v2 extraction to btp-upgrade-audit"
```
