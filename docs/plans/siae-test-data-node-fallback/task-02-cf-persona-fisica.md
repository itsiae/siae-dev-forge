# Task 02 — cfUtils: tabelle checksum + codice CF persona fisica

**Stato:** [PENDING]

**Goal:** Aggiungere in `generate_profiles.js` le tabelle CHECKSUM_DISPARI/PARI e le
funzioni `normalizza`, `codiceCognome`, `codiceNome`, `codiceData`, `checksumCF`,
`calcolaCF` — algoritmo DM 23/12/1976.

**File coinvolti:**
- `skills/siae-test-data/scripts/generate_profiles.js` — MODIFICA (aggiunge cfUtils)

---

## Step 1 — Test RED

Aggiungi in `skills/siae-test-data/tests/test_node_fallback.py`:

```python
class TestCfPersonaFisica:
    def test_cf_mario_rossi_diretto(self):
        """Algoritmo CF: input diretto nome/cognome/data/genere/belfiore."""
        r = subprocess.run(
            ['node', '-e',
             "const {calcolaCF}=require('./generate_profiles.js');"
             "console.log(calcolaCF('Mario','Rossi','1985-01-01','M','H501'))"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == 'RSSMRA85A01H501Z'

    def test_cf_checksum_alessandra(self):
        r = subprocess.run(
            ['node', '-e',
             "const {calcolaCF}=require('./generate_profiles.js');"
             "console.log(calcolaCF('Alessandra','Bianchi','1990-06-15','F','F205'))"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5
        )
        assert r.returncode == 0, r.stderr
        cf = r.stdout.strip()
        assert len(cf) == 16
        assert cf[:3] == 'BNC'  # cognome Bianchi → BNC
```

Run: `cd skills/siae-test-data && python -m pytest tests/test_node_fallback.py::TestCfPersonaFisica -v`
Output atteso: `FAILED` (calcolaCF non esportata)

---

## Step 2 — Verifica RED

```
FAILED — TypeError: calcolaCF is not a function
```

---

## Step 3 — Implementazione GREEN

Aggiungi dopo `module.exports = { loadRef, parseArgs, makePRNG }` (rimpiazza quella riga con il blocco completo alla fine del file):

```js
// ── Tabelle CF ───────────────────────────────────────────────────────────────
const MESI_CF = ['A','B','C','D','E','H','L','M','P','R','S','T'];
const DISP = {
  '0':1,'1':0,'2':5,'3':7,'4':9,'5':13,'6':15,'7':17,'8':19,'9':21,
  'A':1,'B':0,'C':5,'D':7,'E':9,'F':13,'G':15,'H':17,'I':19,'J':21,
  'K':2,'L':4,'M':18,'N':20,'O':11,'P':3,'Q':6,'R':8,'S':12,'T':14,
  'U':16,'V':10,'W':22,'X':25,'Y':24,'Z':23,
};
const PARI = {
  '0':0,'1':1,'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,
  'A':0,'B':1,'C':2,'D':3,'E':4,'F':5,'G':6,'H':7,'I':8,'J':9,
  'K':10,'L':11,'M':12,'N':13,'O':14,'P':15,'Q':16,'R':17,'S':18,'T':19,
  'U':20,'V':21,'W':22,'X':23,'Y':24,'Z':25,
};
const TO_CHAR = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
const VOWELS  = new Set('AEIOU');
const NORM_MAP = {
  'À':'A','Á':'A','Â':'A','Ä':'A','Ã':'A',
  'È':'E','É':'E','Ê':'E','Ë':'E',
  'Ì':'I','Í':'I','Î':'I','Ï':'I',
  'Ò':'O','Ó':'O','Ô':'O','Ö':'O','Õ':'O',
  'Ù':'U','Ú':'U','Û':'U','Ü':'U',
  'Ç':'C','Ñ':'N','ß':'S',
};

function normalizza(s) {
  s = s.toUpperCase().trim()
    .replace(/[ÀÁÂÄÃ]/g,'A').replace(/[ÈÉÊË]/g,'E')
    .replace(/[ÌÍÎÏ]/g,'I').replace(/[ÒÓÔÖÕ]/g,'O')
    .replace(/[ÙÚÛÜ]/g,'U').replace(/Ç/g,'C')
    .replace(/Ñ/g,'N').replace(/ß/g,'S');
  return s.replace(/[^A-Z]/g,'');
}
function _cons(s) { return [...s].filter(c => !VOWELS.has(c)).join(''); }
function _voc(s)  { return [...s].filter(c =>  VOWELS.has(c)).join(''); }

function codiceCognome(cog) {
  const s = normalizza(cog);
  return (_cons(s) + _voc(s) + 'XXX').slice(0,3);
}
function codiceNome(nom) {
  const s = normalizza(nom);
  const c = _cons(s);
  if (c.length >= 4) return c[0]+c[2]+c[3];
  return (_cons(s) + _voc(s) + 'XXX').slice(0,3);
}
function codiceData(dataISO, genere) {
  const [y,m,d] = dataISO.split('-').map(Number);
  const aa  = String(y % 100).padStart(2,'0');
  const mes = MESI_CF[m - 1];
  const gg  = String(d + (genere.toUpperCase() === 'F' ? 40 : 0)).padStart(2,'0');
  return aa + mes + gg;
}
function checksumCF(cf15) {
  let tot = 0;
  for (let i = 0; i < 15; i++) {
    tot += (i % 2 === 0 ? DISP : PARI)[cf15[i]];
  }
  return TO_CHAR[tot % 26];
}
function calcolaCF(nome, cognome, dataISO, genere, belfiore) {
  const p = codiceCognome(cognome) + codiceNome(nome) +
            codiceData(dataISO, genere) + belfiore.toUpperCase();
  return p + checksumCF(p);
}
```

Aggiorna `module.exports` in fondo al file:
```js
module.exports = { loadRef, parseArgs, makePRNG,
  normalizza, codiceCognome, codiceNome, checksumCF, calcolaCF };
```

---

## Step 4 — Verifica GREEN

Run: `cd skills/siae-test-data && python -m pytest tests/test_node_fallback.py::TestCfPersonaFisica -v`
Output atteso:
```
PASSED tests/test_node_fallback.py::TestCfPersonaFisica::test_cf_mario_rossi_diretto
PASSED tests/test_node_fallback.py::TestCfPersonaFisica::test_cf_checksum_alessandra
```

---

## Step 5 — Commit

```
test(siae-test-data): RED cfUtils CF persona fisica Node.js
feat(siae-test-data): cfUtils — tabelle + calcolaCF persona fisica in generate_profiles.js
```

## Criteri di accettazione

- [ ] `calcolaCF('Mario','Rossi','1985-01-01','M','H501')` === `'RSSMRA85A01H501Z'`
- [ ] CF Alessandra Bianchi inizia con `BNC` (cognome corretto)
- [ ] 2 test TestCfPersonaFisica PASS
