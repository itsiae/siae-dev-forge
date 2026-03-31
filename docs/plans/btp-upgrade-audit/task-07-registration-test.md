# Task 07 — Registrazione Skill + Smoke Test con appavvisi

**Stato:** [PENDING]
**File:** skill catalog index, smoke test manuale
**Dipende da:** Task 01–06 (tutti)

---

## Obiettivo

1. Registrare `siae-btp-upgrade-audit` nel catalogo skill di siae-dev-forge
2. Eseguire uno smoke test reale su `appavvisi` dal repo `itsiae/liquidazione` (branch `main-alt`)
3. Verificare che il fingerprint generato sia valido YAML senza campi liberi

---

## Step 1 — Verifica struttura completa della skill

```bash
wc -l /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Output atteso: > 150 righe (skill completa)

```bash
# Verifica zero placeholder rimasti
grep -c "PLACEHOLDER" \
  /Users/mazzacuv/Git/siae-dev-forge/skills/siae-btp-upgrade-audit/SKILL.md
```

Output atteso: `0`

---

## Step 2 — Aggiungi la skill al catalogo DevForge

Trova il file del catalogo skill (tipicamente `skills/catalog.md` o simile):

```bash
find /Users/mazzacuv/Git/siae-dev-forge/skills -name "catalog*" -o -name "index*" 2>/dev/null | head -5
```

Se il catalogo esiste, aggiungi la entry:

```
| siae-btp-upgrade-audit | upgrade SAP BTP, librerie deprecate SAP, gap analysis SAP BTP, no-regression upgrade UI5, /forge-btp-baseline, /forge-btp-audit | Flexible | 4. Implementation |
```

Se il catalogo non esiste come file separato (il catalogo è embedded nel `using-devforge` skill),
la registrazione avviene aggiornando il Dynamic Skill Catalog nella skill `using-devforge`
con la stessa entry sopra.

---

## Step 3 — Smoke test: Fase 1 BASELINE su `appavvisi`

Esegui manualmente la Fase 1 della skill su `appavvisi` (branch `main-alt`):

```bash
# 1. Verifica accesso al repo
gh api repos/itsiae/liquidazione/git/trees/main-alt \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK — tree has', len(d.get('tree',[])), 'entries')"
```

Output atteso: `OK — tree has N entries`

```bash
# 2. Ottieni SHA tree di appavvisi
APPAVVISI_SHA=$(gh api repos/itsiae/liquidazione/git/trees/main-alt \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
for x in d['tree']:
    if x['path'] == 'appavvisi':
        print(x['sha'])
        break
")
echo "appavvisi SHA: $APPAVVISI_SHA"
```

Output atteso: stringa SHA di 40 caratteri

```bash
# 3. Lista file JS del controller
gh api "repos/itsiae/liquidazione/git/trees/${APPAVVISI_SHA}?recursive=1" \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
js = [x for x in d.get('tree',[]) if x['path'].endswith('.js') and x['type']=='blob']
print(f'JS files found: {len(js)}')
for f in js: print(f'  {f[\"path\"]}')
"
```

Output atteso: lista di file `.js` inclusi `controller/App.controller.js` e `controller/View1.controller.js`

---

## Step 4 — Verifica fingerprint YAML generato

Dopo lo smoke test, verifica che il fingerprint prodotto:
1. Sia YAML valido (parsabile)
2. Non contenga campi liberi (nessun campo di tipo stringa > 120 caratteri)
3. Contenga almeno: `deprecated_imports`, `odata_v2_calls`, `method_signatures`

```bash
# Se hai salvato il fingerprint in un file temporaneo:
python3 -c "import yaml, sys; yaml.safe_load(sys.stdin); print('YAML VALID')" < /tmp/appavvisi-fingerprint.yaml
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
" < /tmp/appavvisi-fingerprint.yaml
```

Output atteso: `SCAN DONE` (con zero `WARN`)

---

## Step 5 — Commit finale con registrazione

```bash
git add skills/siae-btp-upgrade-audit/SKILL.md
# + eventuali file catalogo modificati
git commit -m "feat(skills): register siae-btp-upgrade-audit in DevForge catalog"
```

---

## Criterio di successo del Task 07

- [ ] `skills/siae-btp-upgrade-audit/SKILL.md` esiste e ha > 150 righe
- [ ] Skill registrata nel catalogo DevForge
- [ ] Smoke test su `appavvisi` produce fingerprint YAML valido
- [ ] Nessun campo libero nel fingerprint (`SCAN DONE` senza `WARN`)
- [ ] Tutti i commit dei task 01–07 sono nella history del branch
