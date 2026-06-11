# Task 06 — profileGen BUSINESS/EDITORE + rappresentante legale

**Stato:** [PENDING]

**Goal:** Implementare `generaRappLegale(area, rng)` e `generaProfiloBusiness(profiloId, area, formaGiu, profiloTipo, rng)` con vincoli CF=P.IVA per SDC/SDP/COOP, CF ente numerico, rappresentante legale per ITA/UE/EXTRA-UE.

**File coinvolti:**
- `skills/siae-test-data/scripts/generate_profiles.js` — MODIFICA

---

## Step 1 — Test RED

Aggiungi in `test_node_fallback.py`:

```python
class TestProfileBusiness:
    def test_sdc_cf_uguale_piva(self):
        r = subprocess.run(
            ['node', '-e',
             "const {generaProfiloBusiness,makePRNG}=require('./generate_profiles.js');"
             "const rng=makePRNG('B-SDC-IT-001');"
             "const p=generaProfiloBusiness('B-SDC-IT-001','IT','SDC','LIGHT',rng);"
             "const sg=p.soggetto_giuridico;"
             "console.log(sg.codice_fiscale_ente === sg.partita_iva)"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == 'true'

    def test_sdc_rapp_legale_cf_presente(self):
        r = subprocess.run(
            ['node', '-e',
             "const {generaProfiloBusiness,makePRNG}=require('./generate_profiles.js');"
             "const rng=makePRNG('B-SDC-IT-002');"
             "const p=generaProfiloBusiness('B-SDC-IT-002','IT','SDC','LIGHT',rng);"
             "const rl=p.soggetto_giuridico.rappresentante_legale;"
             "console.log(rl.cf.length + ',' + !!rl.data_nascita)"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == '16,true'

    def test_sdc_extra_ue_rapp_legale_belfiore_z(self):
        r = subprocess.run(
            ['node', '-e',
             "const {generaProfiloBusiness,makePRNG}=require('./generate_profiles.js');"
             "const rng=makePRNG('B-SDC-EXTUE-001');"
             "const p=generaProfiloBusiness('B-SDC-EXTUE-001','EXTRA-UE','SDC','LIGHT',rng);"
             "const cf=p.soggetto_giuridico.rappresentante_legale.cf;"
             "console.log(cf.substring(11,15).startsWith('Z'))"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == 'true'
```

Run: `cd skills/siae-test-data && python -m pytest tests/test_node_fallback.py::TestProfileBusiness -v`
Output atteso: `FAILED`

---

## Step 2 — Verifica RED

```
FAILED — TypeError: generaProfiloBusiness is not a function
```

---

## Step 3 — Implementazione GREEN

Aggiungi in `generate_profiles.js` dopo `generaProfiloPrivato` (prima di `module.exports`):

```js
// ── Rappresentante legale ────────────────────────────────────────────────────
function generaRappLegale(areaRapp, rng) {
  const genere = rng.choice(['M','F']);
  const stato  = _statoRandom(areaRapp, rng);
  const [nome, cognome] = _pickNomeCognome(stato, genere, rng);
  const dataNascita     = _randomDate(rng, 1960, 1985);

  let belfioreCode, statoNascita = stato, comuneNascita = null;
  if (stato === 'Italia') {
    comuneNascita = rng.choice(_COMUNI_KEYS);
    belfioreCode  = BELFIORE_COMUNI[comuneNascita].codice_belfiore;
  } else {
    belfioreCode = (BELFIORE_ESTERI[stato] || {}).codice_belfiore || 'Z000';
  }
  const cf = calcolaCF(nome, cognome, dataNascita, genere, belfioreCode);
  return {
    nome, cognome, genere, cf,
    data_nascita: dataNascita,
    stato_nascita: statoNascita,
    ...(comuneNascita ? { comune_nascita: comuneNascita } : {}),
  };
}

// ── Generatore profilo business ──────────────────────────────────────────────
function generaProfiloBusiness(profiloId, area, formaGiu, profiloTipo, rng) {
  const fg = formaGiu.toUpperCase();
  const siglaProv = rng.choice(['RM','MI','TO','NA','FI','BO','VE','GE']);
  const progressivo = rng.randint(1000000, 9999999);

  // CF e P.IVA per forma giuridica
  let cfEnte, piva, vatNumber = null;
  const sedeIT = area === 'IT';
  if (!sedeIT) {
    // Sede estera: VAT Number, no P.IVA italiana
    cfEnte = calcolaCFEnte11(progressivo, siglaProv);  // CF numerico interno
    piva   = null;
    vatNumber = `EU${String(progressivo).padStart(9,'0')}`;
  } else if (['SDC','SDP','COOP'].includes(fg)) {
    piva   = generaCFUgualePiva(siglaProv, progressivo);
    cfEnte = piva;  // CF = P.IVA
  } else if (fg === 'ENTEP') {
    cfEnte = calcolaCFEnte11(progressivo, siglaProv);
    piva   = generaPiva(siglaProv, progressivo + 1);
  } else if (fg === 'DI') {
    // DI: CF del titolare (persona fisica)
    const titGenere = rng.choice(['M','F']);
    const titStato  = 'Italia';
    const [titNome, titCog] = _pickNomeCognome(titStato, titGenere, rng);
    const titData   = _randomDate(rng, 1960, 1985);
    const titComune = rng.choice(_COMUNI_KEYS);
    cfEnte = calcolaCF(titNome, titCog, titData, titGenere,
                       BELFIORE_COMUNI[titComune].codice_belfiore);
    piva   = generaPiva(siglaProv, progressivo);
  } else {
    // ENTE, IST, ONP: CF 10 cifre
    cfEnte = calcolaCFEnte10(progressivo);
    piva   = rng.choice([null, generaPiva(siglaProv, progressivo + 1)]);
  }

  const nomeEnte = `${fg} Test ${profiloId}`;
  const rappLeg  = generaRappLegale(area, rng);

  const soggetto_giuridico = {
    nome_ente: nomeEnte,
    forma_giuridica_codice: fg,
    codice_fiscale_ente: cfEnte,
    ...(piva     ? { partita_iva: piva }     : {}),
    ...(vatNumber ? { vat_number: vatNumber } : {}),
    rappresentante_legale: rappLeg,
  };

  const profilo = {
    profilo_id: profiloId,
    macro_categoria: 'BUSINESS',
    soggetto_giuridico,
  };

  if (profiloTipo === 'FULL') {
    const citta = rng.choice(_CAP_IT_KEYS);
    profilo.indirizzo = sedeIT
      ? generaIndirizzoIT(citta, rng)
      : generaIndirizzoEstero(_statoRandom(area, rng), rng);
    profilo.contatti = {
      telefono: '+39 06 ' + String(rng.randint(1000000, 9999999)),
    };
  } else {
    profilo.nazione_residenza = area === 'IT' ? 'Italia' : _statoRandom(area, rng);
  }

  return profilo;
}
```

Aggiorna `module.exports` aggiungendo `generaRappLegale`, `generaProfiloBusiness`.

---

## Step 4 — Verifica GREEN

Run: `cd skills/siae-test-data && python -m pytest tests/test_node_fallback.py::TestProfileBusiness -v`
Output atteso: 3 PASSED

---

## Step 5 — Commit

```
test(siae-test-data): RED profileGen business + rapp legale Node.js
feat(siae-test-data): generaProfiloBusiness + generaRappLegale ITA/UE/EXTRA-UE
```

## Criteri di accettazione

- [ ] SDC IT: `codice_fiscale_ente === partita_iva`
- [ ] Rappresentante legale CF ha lunghezza 16 e data_nascita presente
- [ ] Rappresentante legale EXTRA-UE: caratteri 12-15 del CF iniziano con `Z`
- [ ] 3 test TestProfileBusiness PASS
