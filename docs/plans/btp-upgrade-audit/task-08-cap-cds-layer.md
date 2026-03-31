# Task 08 — Layer CAP CDS: srv/ Handlers + CDS Annotations

**Stato:** [PENDING]
**File:** `skills/siae-btp-upgrade-audit/SKILL.md` (sezione Phase 1, Layer 1-D)
**Dipende da:** Task 02, Task 03

**Scope:** Moduli `wf_*` del repo `itsiae/liquidazione` che sono CAP services.
Le app `app*` (SAPUI5 puro) non hanno `srv/` — questo layer si applica SOLO ai moduli con directory `srv/`.

---

## Obiettivo

Estendere il fingerprint per coprire i CAP CDS services:
- `cap_handlers`: event handlers nel file `srv/*.js` (`before`, `on`, `after`)
- `cds_annotations`: annotations di sicurezza/accesso sulle entità (`.cds` files)
- `cap_config`: configurazione runtime CAP da `package.json` (sezione `cds`)

**Perché è critico:** gli upgrade `@sap/cds` v6→v7 hanno breaking changes nei handler,
nei nomi delle entità, e nelle annotations. Un handler rimosso = transazione business persa.

---

## Step 1 — Verifica prerequisito

```bash
grep -c "xmlview_bindings\|odata_v2_calls" \
  /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Output atteso: `2` o più

---

## Step 2 — App Discovery: identifica moduli CAP (wf_*)

```bash
# Usa TREE_SHA già risolto dalla fase di App Discovery
gh api "repos/itsiae/liquidazione/git/trees/${TREE_SHA}" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
# CAP modules: hanno directory srv/ al loro interno
# Controlla i moduli wf_* (workflow CAP)
cap_candidates = [x['path'] for x in d.get('tree', [])
                  if x['type'] == 'tree' and x['path'].startswith('wf_')]
print('Moduli CAP candidati:', cap_candidates)
"
```

```bash
# Verifica che il modulo abbia effettivamente una directory srv/
CAP_MOD_SHA=$(gh api "repos/itsiae/liquidazione/git/trees/${TREE_SHA}" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
for x in d['tree']:
    if x['path'] == '<WF_MODULE_NAME>':
        print(x['sha'])
        break
")

gh api "repos/itsiae/liquidazione/git/trees/${CAP_MOD_SHA}?recursive=1" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
has_srv = any(x['path'].startswith('srv/') for x in d.get('tree', []))
has_cds = any(x['path'].endswith('.cds') for x in d.get('tree', []))
print(f'has srv/: {has_srv}, has .cds: {has_cds}')
if not has_srv:
    print('SKIP: modulo senza srv/ — non è un CAP service')
"
```

Output atteso: `has srv/: True, has .cds: True`

---

## Step 3 — Aggiungi Layer 1-D nella skill

Aggiungi dopo la sezione `component_models` la sezione seguente:

```markdown
### Layer 1-D: CAP CDS Handlers + Annotations (solo moduli wf_*)

Applicare SOLO se il modulo ha directory `srv/`. Saltare per app SAPUI5 pure.

#### CAP Service Handlers (srv/*.js)

```bash
# Lista file srv/
SRV_FILES=$(gh api "repos/itsiae/liquidazione/git/trees/${APP_TREE_SHA}?recursive=1" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
srv = [x for x in d.get('tree', [])
       if x['path'].startswith('srv/') and x['path'].endswith('.js')
       and x['type'] == 'blob']
for f in srv:
    print(f['path'], f['sha'])
")

# Per ogni file srv/*.js, cerca handlers
SRV_CONTENT=$(gh api repos/itsiae/liquidazione/git/blobs/<SRV_FILE_SHA> \
  | python3 -c "
import sys, json, base64
d = json.load(sys.stdin)
print(base64.b64decode(d['content']).decode('utf-8', errors='replace'))
")

echo "$SRV_CONTENT" | grep -n \
  -e "this\.before\s*(" \
  -e "this\.on\s*(" \
  -e "this\.after\s*(" \
  | while IFS=: read -r LINE REST; do
      HOOK=$(echo "$REST" | grep -oE '\.(before|on|after)\s*\(' | tr -d '. (')
      EVENT=$(echo "$REST" | grep -oE "'[A-Z_]+'" | head -1 | tr -d "'")
      ENTITY=$(echo "$REST" | grep -oE "'[A-Za-z][A-Za-z0-9]*'" | sed -n '2p' | tr -d "'")
      VERBATIM=$(echo "$REST" | sed 's/^[[:space:]]*//' | cut -c1-120)
      printf "  - file: \"%s\"\n    hook: \"%s\"\n    event: \"%s\"\n    entity: \"%s\"\n    verbatim: \"%s\"\n    line: %s\n" \
        "<SRV_FILE_PATH>" "${HOOK}" "${EVENT}" "${ENTITY}" "${VERBATIM}" "${LINE}"
    done
```

Enum `hook`: `before | on | after`
Enum `event`: `CREATE | READ | UPDATE | DELETE | <action_name>`

Output (sezione YAML fingerprint `cap_handlers`):
```yaml
cap_handlers:
  - file: "srv/liquidazione-service.js"
    hook: "before"
    event: "CREATE"
    entity: "Liquidazioni"
    verbatim: "this.before('CREATE', 'Liquidazioni', async (req) => {"
    line: 12
  - file: "srv/liquidazione-service.js"
    hook: "on"
    event: "submitToApproval"
    entity: "Liquidazioni"
    verbatim: "this.on('submitToApproval', 'Liquidazioni', async (req) => {"
    line: 34
```

---

#### CDS Annotations (*.cds files)

```bash
# Lista file .cds
CDS_FILES=$(gh api "repos/itsiae/liquidazione/git/trees/${APP_TREE_SHA}?recursive=1" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
cds = [x for x in d.get('tree', [])
       if x['path'].endswith('.cds') and x['type'] == 'blob']
for f in cds:
    print(f['path'], f['sha'])
")

# Per ogni file .cds, cerca annotations di sicurezza
CDS_CONTENT=$(gh api repos/itsiae/liquidazione/git/blobs/<CDS_FILE_SHA> \
  | python3 -c "
import sys, json, base64
d = json.load(sys.stdin)
print(base64.b64decode(d['content']).decode('utf-8', errors='replace'))
")

echo "$CDS_CONTENT" | grep -n \
  -e "@restrict" \
  -e "@requires" \
  -e "@insertonly" \
  -e "@readonly" \
  -e "@odata\.draft" \
  | while IFS=: read -r LINE REST; do
      ANN=$(echo "$REST" | grep -oE '@[a-zA-Z.]+' | head -1)
      VERBATIM=$(echo "$REST" | sed 's/^[[:space:]]*//' | cut -c1-120)
      printf "  - file: \"%s\"\n    annotation: \"%s\"\n    verbatim: \"%s\"\n    line: %s\n" \
        "<CDS_FILE_PATH>" "${ANN}" "${VERBATIM}" "${LINE}"
    done
```

Output (sezione YAML fingerprint `cds_annotations`):
```yaml
cds_annotations:
  - file: "srv/liquidazione-service.cds"
    annotation: "@restrict"
    verbatim: "@restrict: [{ grant: 'READ', to: 'authenticated-user' }]"
    line: 8
  - file: "srv/liquidazione-service.cds"
    annotation: "@readonly"
    verbatim: "@readonly entity LiquidazioniView as select from Liquidazioni;"
    line: 24
```

---

#### CAP Config (package.json sezione cds)

```bash
PKG_SHA=$(gh api "repos/itsiae/liquidazione/git/trees/${APP_TREE_SHA}?recursive=1" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
for x in d['tree']:
    if x['path'] == 'package.json':
        print(x['sha'])
        break
")

PKG_CONTENT=$(gh api repos/itsiae/liquidazione/git/blobs/${PKG_SHA} \
  | python3 -c "
import sys, json, base64
d = json.load(sys.stdin)
print(base64.b64decode(d['content']).decode('utf-8', errors='replace'))
")

echo "$PKG_CONTENT" | python3 -c "
import sys, json
pkg = json.load(sys.stdin)
cds_conf = pkg.get('cds', {})
print('cap_config:')
print('  cds_version: \"' + pkg.get('dependencies', {}).get('@sap/cds', 'unknown') + '\"')
requires = cds_conf.get('requires', {})
for svc, conf in requires.items():
    print('  - service: \"' + svc + '\"')
    print('    kind: \"' + conf.get('kind', '') + '\"')
"
```

Output (sezione YAML fingerprint `cap_config`):
```yaml
cap_config:
  cds_version: "^6.8.0"
  - service: "db"
    kind: "hana"
  - service: "messaging"
    kind: "enterprise-messaging"
```
```

---

## Step 4 — Aggiorna regole Diff Engine per cap_handlers

Aggiungere in task-05 (diff engine) le regole per i nuovi campi CAP:

```markdown
#### cap_handlers
- Per ogni entry in `old.cap_handlers` (per `hook` + `event` + `entity`):
  - Trovata con stesso `verbatim` canonicalizzato → `OK`
  - Trovata con `verbatim` diverso → `LOGIC DIFF: handler CAP modificato`
  - Non trovata → `CRITICAL: handler CAP rimosso — transazione business persa`
- Per ogni entry in `new.cap_handlers` NON in `old`: `INFO: nuovo handler CAP introdotto`

#### cds_annotations
- Per ogni entry in `old.cds_annotations` (per `annotation` + file):
  - Trovata con stesso `verbatim` canonicalizzato → `OK`
  - Trovata con `verbatim` diverso → `CRITICAL: annotation sicurezza/accesso modificata`
  - Non trovata → `CRITICAL: annotation rimossa — potenziale escalation di privilegi`

#### cap_config
- `old.cap_config.cds_version` vs `new.cap_config.cds_version`:
  - Identica → `OK`
  - Diversa → `INFO: versione @sap/cds cambiata — verificare breaking changes`
- Per ogni `service` in `old.cap_config`:
  - Trovato con stesso `kind` → `OK`
  - Non trovato → `CRITICAL: binding servizio CAP rimosso`
```

---

## Step 5 — Verifica

```bash
grep -c "cap_handlers\|cds_annotations\|cap_config" \
  /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Output atteso: `3` o più

---

## Step 6 — Commit

```bash
git add skills/siae-btp-upgrade-audit/SKILL.md
git commit -m "feat(skills): add layer1-D CAP CDS handlers and annotations to btp-upgrade-audit"
```
