# Task 04 — addressUtils + _pickNomeCognome

**Stato:** [PENDING]

**Goal:** Aggiungere lookup dati anagrafici di riferimento (BELFIORE_COMUNI,
BELFIORE_ESTERI, CAP_CITTA, NOMI_IT, NOMI_ESTERI), liste pre-computate per
stato UE/EXTRA-UE, `_pickNomeCognome`, `generaIndirizzoIT`, `generaIndirizzoEstero`.

**File coinvolti:**
- `skills/siae-test-data/scripts/generate_profiles.js` — MODIFICA

---

## Step 1 — Test RED

Aggiungi in `test_node_fallback.py`:

```python
class TestAddressNames:
    def test_indirizzo_it_coerente(self):
        r = subprocess.run(
            ['node', '-e',
             "const {generaIndirizzoIT,makePRNG}=require('./generate_profiles.js');"
             "const rng=makePRNG('t1');"
             "const a=generaIndirizzoIT('Roma',rng);"
             "console.log(a.stato + ',' + (a.cap.length===5) + ',' + !!a.via)"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == 'Italia,true,true'

    def test_pick_nome_cognome_italia(self):
        r = subprocess.run(
            ['node', '-e',
             "const {_pickNomeCognome,makePRNG}=require('./generate_profiles.js');"
             "const rng=makePRNG('t2');"
             "const [n,c]=_pickNomeCognome('Italia','M',rng);"
             "console.log(typeof n + ',' + typeof c)"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == 'string,string'
```

Run: `cd skills/siae-test-data && python -m pytest tests/test_node_fallback.py::TestAddressNames -v`
Output atteso: `FAILED`

---

## Step 2 — Verifica RED

```
FAILED — TypeError: generaIndirizzoIT is not a function
```

---

## Step 3 — Implementazione GREEN

Aggiungi in `generate_profiles.js` dopo pivaUtils (prima di `module.exports`):

```js
// ── Dati di riferimento ──────────────────────────────────────────────────────
const BELFIORE_COMUNI = loadRef('belfiore_comuni.json');
const BELFIORE_ESTERI = loadRef('belfiore_esteri.json');
const CAP_CITTA       = loadRef('cap_citta.json');
const NOMI_IT         = loadRef('nomi_italiani.json');
const NOMI_ESTERI     = loadRef('nomi_esteri.json');
const FORME_GIU       = loadRef('forme_giuridiche.json');

const _COMUNI_KEYS    = Object.keys(BELFIORE_COMUNI);
const _CAP_IT_KEYS    = Object.keys(CAP_CITTA['Italia']);
const _STATI_UE       = Object.entries(BELFIORE_ESTERI)
                          .filter(([,v]) => v.area === 'UE').map(([k]) => k);
const _STATI_EXTRA_UE = Object.entries(BELFIORE_ESTERI)
                          .filter(([,v]) => v.area === 'EXTRA-UE').map(([k]) => k);

const TOPONIMI = ['VIA','PIAZZA','CORSO','VIALE','VICOLO','LARGO'];
const NOMI_VIE = ['Roma','Garibaldi','Mazzini','Cavour','Dante','Verdi',
                  'XX Settembre','della Repubblica','Marconi','Galileo Galilei'];

// ── Nomi/cognomi ─────────────────────────────────────────────────────────────
function _pickNomeCognome(stato, genere, rng) {
  if (stato === 'Italia') {
    const pool = genere === 'M' ? NOMI_IT.nomi_maschili : NOMI_IT.nomi_femminili;
    return [rng.choice(pool), rng.choice(NOMI_IT.cognomi)];
  }
  const pool = NOMI_ESTERI[stato];
  if (pool && Array.isArray(pool.nomi_maschili)) {
    const np = genere === 'M' ? pool.nomi_maschili : (pool.nomi_femminili || pool.nomi_maschili);
    return [rng.choice(np), rng.choice(pool.cognomi || NOMI_IT.cognomi)];
  }
  return [rng.choice(NOMI_IT.nomi_maschili), rng.choice(NOMI_IT.cognomi)];
}

// ── Stato random per area ────────────────────────────────────────────────────
function _statoRandom(area, rng) {
  if (area === 'IT') return 'Italia';
  const cands = area === 'UE' ? _STATI_UE : _STATI_EXTRA_UE;
  return cands.length ? rng.choice(cands) : 'Germania';
}

// ── Indirizzi ────────────────────────────────────────────────────────────────
function generaIndirizzoIT(citta, rng) {
  if (!CAP_CITTA['Italia'][citta]) citta = 'Roma';
  const info = CAP_CITTA['Italia'][citta];
  const cap  = rng.choice(info.cap_pool);
  const top  = rng.choice(TOPONIMI);
  const via  = rng.choice(NOMI_VIE);
  const civ  = String(rng.randint(1, 200));
  return { via: `${top} ${via}`, civico: civ, cap, citta,
           provincia: info.provincia, stato: 'Italia' };
}
function generaIndirizzoEstero(stato, rng) {
  const info = BELFIORE_ESTERI[stato] || {};
  return { via: 'N/A', civico: '1', cap: '00000',
           citta: stato, provincia: '', stato,
           nazione_code: info.codice_belfiore || 'Z000' };
}
```

Aggiorna `module.exports`:
```js
module.exports = { loadRef, parseArgs, makePRNG,
  normalizza, codiceCognome, codiceNome, checksumCF, calcolaCF,
  validaPiva, generaPiva, generaCFUgualePiva, calcolaCFEnte11, calcolaCFEnte10,
  _pickNomeCognome, _statoRandom, generaIndirizzoIT, generaIndirizzoEstero,
  BELFIORE_COMUNI, BELFIORE_ESTERI, CAP_CITTA };
```

---

## Step 4 — Verifica GREEN

Run: `cd skills/siae-test-data && python -m pytest tests/test_node_fallback.py::TestAddressNames -v`
Output atteso: 2 PASSED

---

## Step 5 — Commit

```
test(siae-test-data): RED addressUtils Node.js
feat(siae-test-data): addressUtils + _pickNomeCognome + lookup lists
```

## Criteri di accettazione

- [ ] `generaIndirizzoIT('Roma', rng)` produce oggetto con `stato='Italia'`, CAP 5 cifre, `via` non vuota
- [ ] `_statoRandom('EXTRA-UE', rng)` non ritorna sempre `'Germania'`
- [ ] `_STATI_EXTRA_UE.length > 0` (filtro 'EXTRA-UE' corretto)
- [ ] 2 test TestAddressNames PASS
