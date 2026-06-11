# Task 05 — profileGen PRIVATO/AUTORE (persona fisica)

**Stato:** [PENDING]

**Goal:** Implementare `generaProfiloPrivato(profiloId, area, profilo, rng)` che
produce un oggetto JSON conforme a `output_schema.md` per macro-categorie PRIVATO
e AUTORE — persona fisica, senza soggetto_giuridico.

**File coinvolti:**
- `skills/siae-test-data/scripts/generate_profiles.js` — MODIFICA

---

## Step 1 — Test RED

Aggiungi in `test_node_fallback.py`:

```python
class TestProfilePrivato:
    def test_privato_it_cf_valido(self):
        r = subprocess.run(
            ['node', '-e',
             "const {generaProfiloPrivato,makePRNG,validaCF}=require('./generate_profiles.js');"
             "const rng=makePRNG('P-IT-001');"
             "const p=generaProfiloPrivato('P-IT-001','IT','FULL',rng);"
             "const cf=p.anagrafica.codice_fiscale;"
             "console.log(cf.length + ',' + validaCF(cf))"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == '16,true'

    def test_privato_light_no_indirizzo(self):
        r = subprocess.run(
            ['node', '-e',
             "const {generaProfiloPrivato,makePRNG}=require('./generate_profiles.js');"
             "const rng=makePRNG('P-IT-002');"
             "const p=generaProfiloPrivato('P-IT-002','IT','LIGHT',rng);"
             "console.log(!p.indirizzo + ',' + !p.contatti)"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == 'true,true'
```

Run: `cd skills/siae-test-data && python -m pytest tests/test_node_fallback.py::TestProfilePrivato -v`
Output atteso: `FAILED`

---

## Step 2 — Verifica RED

```
FAILED — TypeError: generaProfiloPrivato is not a function
```

---

## Step 3 — Implementazione GREEN

Aggiungi in `generate_profiles.js` dopo addressUtils (prima di `module.exports`):

```js
// ── Validazione CF ───────────────────────────────────────────────────────────
function validaCF(cf) {
  if (!cf || cf.length !== 16) return false;
  return checksumCF(cf.slice(0,15)) === cf[15];
}

// ── Date helpers ─────────────────────────────────────────────────────────────
const EXCEL_EPOCH_MS = new Date(1899, 11, 30).getTime();
function dateToExcelSerial(dateISO) {
  const d = new Date(dateISO + 'T00:00:00');
  return Math.round((d.getTime() - EXCEL_EPOCH_MS) / 86400000);
}
function _randomDate(rng, from=1950, to=2005) {
  const y = rng.randint(from, to + 1);
  const m = rng.randint(1, 13);
  const d = rng.randint(1, 29);  // conservativo, evita giorni > 28 su feb
  return `${y}-${String(m).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
}

// ── Generatore profilo persona fisica ────────────────────────────────────────
function generaProfiloPrivato(profiloId, area, profiloTipo, rng) {
  const genere = rng.choice(['M','F']);
  const stato  = _statoRandom(area, rng);
  const [nome, cognome] = _pickNomeCognome(stato, genere, rng);
  const dataNascita     = _randomDate(rng);

  // Comune/stato di nascita e codice Belfiore
  let comuneNascita = null, statoNascita = stato, belfioreCode;
  if (stato === 'Italia') {
    comuneNascita = rng.choice(_COMUNI_KEYS);
    belfioreCode  = BELFIORE_COMUNI[comuneNascita].codice_belfiore;
  } else {
    belfioreCode = (BELFIORE_ESTERI[stato] || {}).codice_belfiore || 'Z000';
  }

  const cf = calcolaCF(nome, cognome, dataNascita, genere, belfioreCode);
  const serial = dateToExcelSerial(dataNascita);

  const anagrafica = {
    nome, cognome, genere,
    codice_fiscale: cf,
    data_nascita: dataNascita,
    data_nascita_serial: serial,
    stato_nascita: statoNascita,
    ...(comuneNascita ? { comune_nascita: comuneNascita } : {}),
  };

  const profilo = { profilo_id: profiloId, macro_categoria: 'PRIVATO', anagrafica };

  if (profiloTipo === 'FULL') {
    const citta = stato === 'Italia' ? rng.choice(_CAP_IT_KEYS) : stato;
    profilo.indirizzo = stato === 'Italia'
      ? generaIndirizzoIT(citta, rng)
      : generaIndirizzoEstero(stato, rng);
    const prefix = stato === 'Italia' ? '+39 3' : '+44 7';
    profilo.contatti = {
      telefono: prefix + String(rng.randint(100000000, 999999999)),
    };
  } else {
    profilo.nazione_residenza = statoNascita;
    profilo.nazione_residenza_code = stato === 'Italia' ? 'IT'
      : (BELFIORE_ESTERI[stato] || {}).codice_belfiore || 'Z000';
  }

  return profilo;
}
```

Aggiorna `module.exports` aggiungendo `validaCF`, `dateToExcelSerial`, `generaProfiloPrivato`.

---

## Step 4 — Verifica GREEN

Run: `cd skills/siae-test-data && python -m pytest tests/test_node_fallback.py::TestProfilePrivato -v`
Output atteso: 2 PASSED

---

## Step 5 — Commit

```
test(siae-test-data): RED profileGen privato Node.js
feat(siae-test-data): generaProfiloPrivato — persona fisica FULL/LIGHT
```

## Criteri di accettazione

- [ ] CF profilo PRIVATO IT ha lunghezza 16 e checksum valido
- [ ] Profilo LIGHT non ha chiavi `indirizzo` né `contatti`
- [ ] 2 test TestProfilePrivato PASS
