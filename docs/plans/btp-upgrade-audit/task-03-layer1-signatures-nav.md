# Task 03 — Layer 1: Method Signatures + Navigation + Routing Config

**Stato:** [PENDING]
**File:** `skills/siae-btp-upgrade-audit/SKILL.md` (sezione Phase 1, Layer 1 — parte B)
**Dipende da:** Task 01
**Parallelo con:** Task 02

---

## Obiettivo

Aggiungere alla skill il protocollo Layer 1 per:
- `method_signatures`: nomi metodi del controller (on*, _*)
- `navigation_targets`: chiamate `navTo()` con target
- `routing_config`: routes da `manifest.json`

---

## Step 1 — Verifica prerequisito Task 01

```bash
ls /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md \
  && echo "OK" || echo "FAIL — esegui Task 01 prima"
```

Output atteso: `OK`

---

## Step 2 — Aggiungi sezione Layer 1-B nella skill dopo Layer 1-A

Aggiungi il seguente blocco nella sezione Phase 1, dopo `odata_v2_calls`:

```markdown
### Layer 1-B: Method Signatures

Per ogni file JS del controller:

```bash
echo "$CONTENT" | grep -n \
  -e "^\s*on[A-Z][a-zA-Z]*\s*:" \
  -e "^\s*_[a-zA-Z][a-zA-Z]*\s*:" \
  -e "^\s*[a-z][a-zA-Z]*\s*:\s*function" \
  | while IFS=: read -r LINE REST; do
      METHOD=$(echo "$REST" | grep -oE '(on|_)[A-Za-z]+' | head -1)
      echo "  - name: \"${METHOD}\"\n    file: \"<FILE_PATH>\"\n    line: ${LINE}"
    done
```

Output (sezione YAML `method_signatures`):
```yaml
method_signatures:
  - name: "onInit"
    file: "webapp/controller/App.controller.js"
    line: 12
  - name: "_validateForm"
    file: "webapp/controller/App.controller.js"
    line: 67
```

---

### Layer 1-B: Navigation Targets

```bash
echo "$CONTENT" | grep -n "navTo\|getRouter" \
  | while IFS=: read -r LINE REST; do
      TARGET=$(echo "$REST" | grep -oE '"[A-Za-z][A-Za-z0-9_]+"' | head -1 | tr -d '"')
      VERBATIM=$(echo "$REST" | sed 's/[[:space:]]*//' | cut -c1-80)
      echo "  - target: \"${TARGET}\"\n    file: \"<FILE_PATH>\"\n    line: ${LINE}\n    verbatim: \"${VERBATIM}\""
    done
```

Output (sezione YAML `navigation_targets`):
```yaml
navigation_targets:
  - target: "RouteView1"
    file: "webapp/controller/App.controller.js"
    line: 89
    verbatim: "this.getRouter().navTo(\"RouteView1\","
```

---

### Layer 1-B: Routing Config (manifest.json)

```bash
# Leggi manifest.json dell'app
MANIFEST_SHA=$(gh api repos/itsiae/liquidazione/git/trees/${APP_TREE_SHA}?recursive=1 \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
for x in d['tree']:
    if x['path'] == 'webapp/manifest.json':
        print(x['sha'])
        break
")

MANIFEST=$(gh api repos/itsiae/liquidazione/git/blobs/${MANIFEST_SHA} \
  | python3 -c "
import sys, json, base64
d = json.load(sys.stdin)
print(base64.b64decode(d['content']).decode('utf-8', errors='replace'))
")

# Estrai routes
echo "$MANIFEST" | python3 -c "
import sys, json
m = json.load(sys.stdin)
routes = m.get('sap.ui5', {}).get('routing', {}).get('routes', [])
print('routing_config:')
print('  routes: ' + str([r.get('name','') for r in routes]))
"
```

Output (sezione YAML `routing_config`):
```yaml
routing_config:
  routes:
    - "RouteMain"
    - "RouteDetail"
    - "RouteConferma"
```
```

---

## Step 3 — Verifica che i pattern siano presenti nella skill

```bash
grep -c "method_signatures\|navigation_targets\|routing_config" \
  /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Output atteso: `3` o più

---

## Step 4 — Commit

```bash
git add skills/siae-btp-upgrade-audit/SKILL.md
git commit -m "feat(skills): add layer1 method signatures, navigation and routing extraction to btp-upgrade-audit"
```
