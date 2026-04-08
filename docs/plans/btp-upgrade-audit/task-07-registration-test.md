# Task 07 — Registrazione Skill + Smoke Test con appavvisi

**Stato:** [PENDING]
**File:** skill catalog index, smoke test manuale
**Dipende da:** Task 01–06 (tutti)

---

## Obiettivo

1. Registrare `siae-btp-upgrade-audit` nel catalogo skill di siae-dev-forge
2. Eseguire smoke test (positive + negative) su `appavvisi` dal repo `itsiae/liquidazione`
3. Verificare che il fingerprint sia YAML valido, senza campi liberi, e che il tool rilevi regressioni

---

## Step 1 — Verifica struttura completa della skill

```bash
wc -l /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Output atteso: > 200 righe (skill completa con tutti i layer)

```bash
# Verifica zero placeholder rimasti
grep -c "PLACEHOLDER" \
  /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Output atteso: `0`

```bash
# Verifica tipo Rigid
grep "Tipo:" /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Output atteso: riga contenente `Rigid`

---

## Step 2 — Registra la skill nel catalogo DevForge

**FIX:** NON modificare manualmente `using-devforge` — il Dynamic Skill Catalog è auto-generato.
Identificare la sorgente corretta per la registrazione:

```bash
# Cerca il file sorgente del catalogo
find /Users/mazzacuv/Git/siae-dev-forge -name "catalog*" \
  -not -path "*/node_modules/*" -not -path "*/.git/*" 2>/dev/null

# Cerca dove le altre skill sono registrate
grep -r "siae-btp\|Flexible.*4\. Impl" \
  /Users/mazzacuv/Git/siae-dev-forge/skills/ \
  --include="*.md" -l 2>/dev/null | head -5
```

Se esiste un file `catalog-source.yaml` o `_catalog.md`: aggiungi la entry lì.
Se il catalogo è inline in `using-devforge` come unica fonte: aggiungi nell'apposita tabella.

Entry da aggiungere:
```
| siae-btp-upgrade-audit | upgrade SAP BTP, librerie deprecate SAP, gap analysis SAP BTP, no-regression upgrade UI5, /forge-btp-baseline, /forge-btp-audit, migrazione BTP, verifica regressioni UI5 | Rigid | 4. Implementation |
```

---

## Step 3 — Smoke Test Positivo: Fase 1 BASELINE su `appavvisi`

**FIX:** usare risoluzione branch → SHA (branch name non funziona con `/git/trees/`).

```bash
# 1. Risolvi branch main-alt → tree SHA
REF_SHA=$(gh api repos/itsiae/liquidazione/git/ref/heads/main-alt \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['object']['sha'])")
TREE_SHA=$(gh api repos/itsiae/liquidazione/git/commits/${REF_SHA} \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['tree']['sha'])")
echo "main-alt → tree: ${TREE_SHA}"
```

Output atteso: `main-alt → tree: <sha40>`
Se fallisce: il branch `main-alt` non esiste — usare il branch corretto del repo.

```bash
# 2. Ottieni SHA subtree di appavvisi
APPAVVISI_SHA=$(gh api "repos/itsiae/liquidazione/git/trees/${TREE_SHA}" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
for x in d['tree']:
    if x['path'] == 'appavvisi':
        print(x['sha'])
        break
else:
    print('NOT_FOUND', file=sys.stderr)
")
echo "appavvisi SHA: $APPAVVISI_SHA"
```

Output atteso: stringa SHA di 40 caratteri

```bash
# 3. Lista file JS e XML del controller
gh api "repos/itsiae/liquidazione/git/trees/${APPAVVISI_SHA}?recursive=1" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
files = [x for x in d.get('tree',[])
         if x['type'] == 'blob'
         and (x['path'].endswith('.js') or x['path'].endswith('.view.xml')
              or x['path'].endswith('.fragment.xml')
              or x['path'].endswith('Component.js'))]
print(f'Files trovati: {len(files)}')
for f in files: print(f'  {f[\"path\"]}')
"
```

Output atteso: lista che include `controller/App.controller.js`, `webapp/manifest.json`,
almeno un file `.view.xml`, e `webapp/Component.js`

Genera il fingerprint baseline e salvalo:
```bash
# (esegui Layer 1-A, 1-B, 1-C, Layer 2 su ogni file — vedi SKILL.md per protocollo)
# Salva output in:
mkdir -p /tmp/btp-audit/fingerprints/old
# > /tmp/btp-audit/fingerprints/old/appavvisi.yaml
```

---

## Step 4 — Verifica fingerprint YAML generato

```bash
python3 -c "import yaml, sys; yaml.safe_load(sys.stdin); print('YAML VALID')" \
  < /tmp/btp-audit/fingerprints/old/appavvisi.yaml
```

Output atteso: `YAML VALID`

```bash
# Verifica assenza campi liberi (nessuna stringa > 120 char)
python3 -c "
import yaml, sys

def check_verbatim(obj, path=''):
    if isinstance(obj, str) and len(obj) > 120:
        print(f'WARN: campo troppo lungo a {path}: {obj[:50]}...')
    elif isinstance(obj, dict):
        for k, v in obj.items(): check_verbatim(v, path+'.'+k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj): check_verbatim(v, path+f'[{i}]')

data = yaml.safe_load(sys.stdin)
check_verbatim(data)
print('SCAN DONE')
" < /tmp/btp-audit/fingerprints/old/appavvisi.yaml
```

Output atteso: `SCAN DONE` senza righe `WARN`

```bash
# Verifica che i campi chiave siano presenti nel fingerprint
python3 -c "
import yaml, sys
data = yaml.safe_load(sys.stdin)
required = ['deprecated_imports','odata_v2_calls','method_signatures',
            'xmlview_bindings','component_models','data_sources']
missing = [k for k in required if k not in data]
if missing:
    print('FAIL — campi mancanti:', missing)
else:
    print('PASS — tutti i campi presenti')
" < /tmp/btp-audit/fingerprints/old/appavvisi.yaml
```

Output atteso: `PASS — tutti i campi presenti`

---

## Step 4b — Negative Test: verifica che il tool rilevi regressioni

**Questo step è obbligatorio.** Senza un negative test, non possiamo garantire
che il tool rilevi ciò che dichiara di rilevare.

```bash
# 1. Crea una versione "degradata" del fingerprint (simula branch con regressioni)
cp /tmp/btp-audit/fingerprints/old/appavvisi.yaml \
   /tmp/btp-audit/fingerprints/new/appavvisi.yaml

# 2. Modifica artificialmente il fingerprint "new":
#    - Rimuovi il primo error_handler (simula handler rimosso)
#    - Cambia verbatim di una condizione (simula logica alterata)
python3 << 'EOF'
import yaml

with open('/tmp/btp-audit/fingerprints/new/appavvisi.yaml') as f:
    data = yaml.safe_load(f)

# Simula rimozione error handler
if data.get('error_handlers'):
    data['error_handlers'][0]['present'] = False
    data['error_handlers'][0]['verbatim'] = None

# Simula condizione modificata (guard rimosso)
for lb in data.get('logic_blocks', []):
    if lb.get('conditions'):
        lb['conditions'][0]['verbatim'] = 'if (oData.importo < 0)'  # rimosso guard == 0

with open('/tmp/btp-audit/fingerprints/new/appavvisi.yaml', 'w') as f:
    yaml.dump(data, f, allow_unicode=True)

print('Fingerprint "new" degradato creato')
EOF
```

```bash
# 3. Esegui diff engine tra old e new degradato
# (usa il protocollo Diff Engine della SKILL.md)
# Il risultato deve contenere:
#   CRITICAL: error handler rimosso
#   LOGIC DIFF: condizione modificata
```

Output atteso del gap report:
```
## CRITICAL (1)
- [C1] error_handlers — onInit: error handler rimosso (present: true → false)

## LOGIC DIFF (1)
### <metodo> — condizione #1
OLD: if (oData.importo <= 0 || oData.importo > 999999)
NEW: if (oData.importo < 0)
⚠️ DIFFERENZA STRUTTURALE RILEVATA — REVISIONE UMANA RICHIESTA
```

Se il report NON contiene questi item → il tool non rileva le regressioni che dichiara.
In questo caso: fermarsi e investigare il diff engine prima di procedere.

---

## Step 5 — Commit finale

```bash
git add skills/siae-btp-upgrade-audit/SKILL.md
# + eventuali file catalogo modificati
git commit -m "feat(skills): register siae-btp-upgrade-audit in DevForge catalog with smoke test validated"
```

---

## Criterio di successo del Task 07

- [ ] `skills/siae-btp-upgrade-audit/SKILL.md` esiste, ha > 200 righe, tipo `Rigid`
- [ ] Zero placeholder nella skill
- [ ] Skill registrata nel catalogo DevForge (sorgente corretta, non using-devforge editato a mano)
- [ ] Smoke test positivo: fingerprint YAML valido, `PASS — tutti i campi presenti`
- [ ] Nessun campo libero nel fingerprint (`SCAN DONE` senza `WARN`)
- [ ] Negative test: gap report contiene almeno `CRITICAL` e `LOGIC DIFF` attesi
- [ ] Tutti i commit dei task 01–08 sono nella history del branch
