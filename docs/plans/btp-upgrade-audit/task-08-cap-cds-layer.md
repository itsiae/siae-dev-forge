# Task 08 — Layer CAP CDS: srv/ Handlers + CDS Annotations

**Stato:** [PENDING]
**File:** `skills/siae-btp-upgrade-audit/SKILL.md` (sezione Phase 1, Layer 1-D)
**Dipende da:** Task 02, Task 03

**ARCHITECTURAL FIX v1.3:**
I moduli `wf_*` del repo `itsiae/liquidazione` sono moduli **SAP BPM workflow** (YAML/XML),
NON CAP services. NON hanno `srv/` e NON vanno processati da questo layer.
Il vero CAP service è in `liquidazione/srv/` (root del repo).
Questo layer si applica SOLO al modulo `liquidazione` (root) che ha `srv/`.

---

## Obiettivo

Estendere il fingerprint per coprire il CAP CDS service principale:
- `cap_handlers`: event handlers in `srv/*.js` (`before`, `on`, `after`) con ordering
- `cds_annotations`: annotations di sicurezza/accesso sulle entità (`.cds` files)
- `cap_config`: configurazione runtime CAP da `package.json` (sezione `cds`)
- `cap_security_checks`: chiamate `req.reject()` nei handlers (auth guard)
- `cap_lib_modules`: file helper in `srv/lib/*.js` che implementano logica di business
- `cap_context_accesses`: accessi a `req.user` / `req.tenant` / `req.data` nei handlers

**Perché è critico:** gli upgrade `@sap/cds` v6→v7 hanno breaking changes nei handler,
nei nomi delle entità, nelle annotations e nel modello di sicurezza. Un handler rimosso
= transazione business persa. Un `req.reject()` rimosso = escalation di privilegi.

---

## Step 1 — Verifica prerequisito

```bash
grep -c "xmlview_bindings\|odata_v2_calls" \
  /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Output atteso: `2` o più

---

## Step 2 — App Discovery: identifica il modulo CAP corretto

```bash
# Il CAP service è nella ROOT del repo liquidazione — NON nei moduli wf_*
# wf_* sono moduli SAP BPM (YAML/XML), non CAP services con srv/
# Verifica che liquidazione root abbia srv/
gh api "repos/itsiae/liquidazione/git/trees/${ROOT_TREE_SHA}?recursive=0" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
has_srv = any(x['path'] == 'srv' and x['type'] == 'tree' for x in d.get('tree', []))
has_cds = any(x['path'].endswith('.cds') for x in d.get('tree', []))
print(f'CAP root srv/: {has_srv}, .cds files: {has_cds}')
if has_srv:
    print('OK: liquidazione root è il CAP service da processare')
else:
    print('WARN: srv/ non trovato in root — verificare struttura repo')
"
```

```bash
# Lista tutti i file srv/ e srv/lib/ per il tree root
CAP_FILES=$(gh api "repos/itsiae/liquidazione/git/trees/${ROOT_TREE_SHA}?recursive=1" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
# Solo srv/*.js e srv/lib/*.js e *.cds
for x in d.get('tree', []):
    p = x['path']
    if x['type'] == 'blob' and (
        (p.startswith('srv/') and p.endswith('.js')) or
        p.endswith('.cds')
    ):
        print(x['path'], x['sha'])
")
```

**REGOLA ARCHITETTURALE:** NON processare i moduli `wf_*`. Sono workflow SAP BPM.
Il layer CAP si applica ESCLUSIVAMENTE al modulo root `liquidazione/`.

---

## Step 3 — Aggiungi Layer 1-D nella skill

Aggiungi dopo la sezione `component_models` la sezione seguente:

```markdown
### Layer 1-D: CAP CDS Handlers + Security (solo liquidazione root srv/)

**IMPORTANTE:** Applicare SOLO al modulo `liquidazione` (root). I moduli `wf_*`
sono SAP BPM workflow (YAML/XML) e NON hanno `srv/`. Saltarli sempre.

#### CAP Service Handlers (srv/*.js)

```bash
# Per ogni file srv/*.js della liquidazione root
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
  | sort \
  | while IFS=: read -r LINE REST; do
      HOOK=$(echo "$REST" | grep -oE '\.(before|on|after)\s*\(' | head -1 | tr -d '. (')
      EVENT=$(echo "$REST" | grep -oE "'[A-Z_a-z][A-Za-z0-9_]*'" | head -1 | tr -d "'")
      ENTITY=$(echo "$REST" | grep -oE "'[A-Za-z][A-Za-z0-9]*'" | sed -n '2p' | tr -d "'")
      VERBATIM=$(echo "$REST" | sed 's/^[[:space:]]*//' | cut -c1-120)
      printf "  - file: \"%s\"\n    hook: \"%s\"\n    event: \"%s\"\n    entity: \"%s\"\n    verbatim: \"%s\"\n    line: %s\n" \
        "<SRV_FILE_PATH>" "${HOOK}" "${EVENT}" "${ENTITY}" "${VERBATIM}" "${LINE}"
    done
```

**REGOLA ORDERING per handler:** i handler `before`/`on`/`after` sullo stesso
`event`+`entity` devono essere confrontati in ordine di registrazione (ordine linea).
Un riordino di handler cambia la semantica di esecuzione → diff ordinato, non set.

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

#### CAP Security Checks (req.reject nei handlers)

```bash
echo "$SRV_CONTENT" | grep -n \
  -e "req\.reject\s*(" \
  -e "req\.error\s*(" \
  | sort \
  | while IFS=: read -r LINE REST; do
      HTTP_CODE=$(echo "$REST" | grep -oE '[0-9]{3}' | head -1)
      VERBATIM=$(echo "$REST" | sed 's/^[[:space:]]*//' | cut -c1-120)
      METHOD=$(awk -v target="$LINE" 'NR<target && /this\.(before|on|after)\s*\(/ {m=$0} END {print m}' <<< "$SRV_CONTENT" \
               | grep -oE "'[A-Z_a-z][A-Za-z0-9_]*'" | head -1 | tr -d "'")
      printf "  - file: \"%s\"\n    line: %s\n    method_context: \"%s\"\n    http_code: %s\n    verbatim: \"%s\"\n" \
        "<SRV_FILE_PATH>" "${LINE}" "${METHOD}" "${HTTP_CODE:-null}" "${VERBATIM}"
    done
```

Output (sezione YAML fingerprint `cap_security_checks`):
```yaml
cap_security_checks:
  - file: "srv/liquidazione-service.js"
    line: 15
    method_context: "CREATE"
    http_code: 403
    verbatim: "req.reject(403, 'Accesso negato: utente non autorizzato');"
```

**Diff rule:** `req.reject()` rimosso → `CRITICAL: security check rimosso — possibile escalation di privilegi`

---

#### CAP Lib Modules (srv/lib/*.js)

```bash
# Lista i file srv/lib/*.js — contengono helper di business logic
LIB_FILES=$(gh api "repos/itsiae/liquidazione/git/trees/${ROOT_TREE_SHA}?recursive=1" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
for x in d.get('tree', []):
    if x['type'] == 'blob' and x['path'].startswith('srv/lib/') and x['path'].endswith('.js'):
        print(x['path'], x['sha'])
")

# Per ogni lib, estrai le funzioni esportate
LIB_CONTENT=$(gh api repos/itsiae/liquidazione/git/blobs/<LIB_SHA> \
  | python3 -c "
import sys, json, base64
d = json.load(sys.stdin)
print(base64.b64decode(d['content']).decode('utf-8', errors='replace'))
")

echo "$LIB_CONTENT" | grep -n \
  -e "module\.exports\s*=" \
  -e "exports\.[a-zA-Z]" \
  -e "^const [a-zA-Z]\+\s*=\s*" \
  | sort \
  | while IFS=: read -r LINE REST; do
      VERBATIM=$(echo "$REST" | sed 's/^[[:space:]]*//' | cut -c1-80)
      printf "  - file: \"%s\"\n    line: %s\n    verbatim: \"%s\"\n" \
        "<LIB_FILE_PATH>" "${LINE}" "${VERBATIM}"
    done
```

Output (sezione YAML fingerprint `cap_lib_modules`):
```yaml
cap_lib_modules:
  - file: "srv/lib/validation.js"
    line: 1
    verbatim: "module.exports = { validateLiquidazione, checkAutore }"
  - file: "srv/lib/utils.js"
    line: 3
    verbatim: "exports.formatImporto = function(val) {"
```

**Diff rule:** lib module rimosso → `HIGH: helper di business logic rimosso — verificare se la logica è stata inline o persa`

---

#### CAP Context Accesses (req.user, req.tenant, req.data)

```bash
echo "$SRV_CONTENT" | grep -n \
  -e "req\.user\b" \
  -e "req\.tenant\b" \
  -e "req\.data\b" \
  -e "req\.params\b" \
  | sort \
  | while IFS=: read -r LINE REST; do
      ACCESS_TYPE=$(echo "$REST" | grep -oE "req\.(user|tenant|data|params)" | head -1 | sed 's/req\.//')
      VERBATIM=$(echo "$REST" | sed 's/^[[:space:]]*//' | cut -c1-120)
      printf "  - file: \"%s\"\n    line: %s\n    access_type: \"%s\"\n    verbatim: \"%s\"\n" \
        "<SRV_FILE_PATH>" "${LINE}" "${ACCESS_TYPE}" "${VERBATIM}"
    done
```

Enum `access_type`: `user | tenant | data | params`

Output (sezione YAML fingerprint `cap_context_accesses`):
```yaml
cap_context_accesses:
  - file: "srv/liquidazione-service.js"
    line: 18
    access_type: "user"
    verbatim: "if (req.user.is('admin')) { req.reject(403); }"
```

---

#### CDS Annotations (*.cds files)

```bash
# Per ogni file .cds, cerca annotations di sicurezza/accesso
echo "$CDS_CONTENT" | grep -n \
  -e "@restrict" \
  -e "@requires" \
  -e "@insertonly" \
  -e "@readonly" \
  -e "@odata\.draft" \
  | sort \
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
echo "$PKG_CONTENT" | python3 -c "
import sys, json
pkg = json.load(sys.stdin)
cds_conf = pkg.get('cds', {})
deps = pkg.get('dependencies', {})

print('cap_config:')
print('  cds_version: \"' + deps.get('@sap/cds', 'unknown') + '\"')

# odata.version (breaking: v6 default OData v4, v7 strict)
odata = cds_conf.get('odata', {})
if odata.get('version'):
    print('  odata_version: \"' + str(odata['version']) + '\"')
else:
    print('  odata_version: null')

# features flags (cambiano behavior v6→v7)
features = cds_conf.get('features', {})
for k, v in features.items():
    print('  feature_' + k + ': ' + json.dumps(v))

# requires (service bindings)
requires = cds_conf.get('requires', {})
print('  requires:')
for svc, conf in requires.items():
    print('    - service: \"' + svc + '\"')
    print('      kind: \"' + conf.get('kind', '') + '\"')

# sql settings (native_hana_associations — breaking in cds v7)
sql = cds_conf.get('sql', {})
if sql:
    print('  sql_native_hana_associations: ' + json.dumps(sql.get('native_hana_associations', None)))
"
```

Output (sezione YAML fingerprint `cap_config`):
```yaml
cap_config:
  cds_version: "^6.8.0"
  odata_version: "v4"
  feature_lean_draft: true
  sql_native_hana_associations: null
  requires:
    - service: "db"
      kind: "hana"
    - service: "messaging"
      kind: "enterprise-messaging"
```
```

---

## Step 4 — Regole Diff Engine per campi CAP

Aggiungere in task-05 (diff engine) le seguenti regole:

```markdown
#### cap_handlers
- Per ogni entry in `old.cap_handlers` (per `hook` + `event` + `entity`, confronto ORDINATO per linea):
  - Trovata con stesso `verbatim` canonicalizzato → `OK`
  - Trovata con `verbatim` diverso → `LOGIC DIFF: handler CAP modificato — logica transazione cambiata`
  - Non trovata → `CRITICAL: handler CAP rimosso — transazione business persa`
- Per ogni entry in `new.cap_handlers` NON in `old`: `INFO: nuovo handler CAP introdotto`
- **ORDERING:** Se due handler sullo stesso `event`+`entity` sono riordinati (`before` e `on` scambiati) → `CRITICAL: ordine handler CAP cambiato — semantica transazione alterata`

#### cap_security_checks
- Per ogni entry in `old.cap_security_checks` (per `method_context`):
  - Trovata con stesso `http_code` e `verbatim` canonicalizzato → `OK`
  - Trovata con `http_code` diverso → `HIGH: http_code security check cambiato — verificare policy`
  - Non trovata → `CRITICAL: security check req.reject() rimosso — possibile escalation di privilegi`

#### cap_lib_modules
- Per ogni entry in `old.cap_lib_modules` (per `file`):
  - Trovata con stesso `verbatim` canonicalizzato → `OK`
  - Trovata con `verbatim` diverso → `HIGH: helper di business logic modificato`
  - Non trovata → `HIGH: helper di business logic rimosso — verificare se logica è inline o persa`

#### cap_context_accesses
- Per ogni entry in `old.cap_context_accesses` (per `access_type`):
  - Trovata con stesso `verbatim` canonicalizzato → `OK`
  - Non trovata → `HIGH: accesso a req.{access_type} rimosso — verificare flusso autenticazione/dati`

#### cds_annotations
- Per ogni entry in `old.cds_annotations` (per `annotation` + file):
  - Trovata con stesso `verbatim` canonicalizzato → `OK`
  - Trovata con `verbatim` diverso → `CRITICAL: annotation sicurezza/accesso modificata`
  - Non trovata → `CRITICAL: annotation rimossa — potenziale escalation di privilegi`

#### cap_config
- `old.cap_config.cds_version` vs `new.cap_config.cds_version`:
  - Identica → `OK`
  - Diversa → `INFO: versione @sap/cds cambiata — verificare breaking changes nel changelog`
- `old.cap_config.odata_version` vs `new.cap_config.odata_version`:
  - Identica → `OK`
  - Diversa → `CRITICAL: versione OData cambiata — breaking change per tutti i client`
- Per ogni feature flag in `old.cap_config`:
  - Stesso valore in `new` → `OK`
  - Valore cambiato → `HIGH: feature flag CAP modificato — comportamento runtime cambiato`
- Per ogni `service` in `old.cap_config.requires`:
  - Trovato con stesso `kind` → `OK`
  - Non trovato → `CRITICAL: binding servizio CAP rimosso — servizio non raggiungibile`
- `old.cap_config.sql_native_hana_associations` vs `new`:
  - Cambiato → `HIGH: sql.native_hana_associations cambiato — breaking per query HANA`
```

---

## Step 5 — Verifica

```bash
grep -c "cap_handlers\|cap_security_checks\|cap_lib_modules\|cap_context_accesses\|cds_annotations\|cap_config" \
  /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Output atteso: `6` o più

---

## Step 6 — Commit

```bash
git add skills/siae-btp-upgrade-audit/SKILL.md
git commit -m "feat(skills): add layer1-D CAP CDS handlers and security checks to btp-upgrade-audit"
```
