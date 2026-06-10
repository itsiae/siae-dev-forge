# Task 03 — pivaUtils + CF enti numerici

**Stato:** [PENDING]

**Goal:** Aggiungere `generaPiva` (Luhn-AdE), `calcolaCFEnte11` (ENTEP), `calcolaCFEnte10`
(ENTE/IST/ONP) — tutti i CF enti numerici. Per SDC/SDP/COOP CF = P.IVA (usa `generaPiva`).

**File coinvolti:**
- `skills/siae-test-data/scripts/generate_profiles.js` — MODIFICA (aggiunge pivaUtils)

---

## Step 1 — Test RED

Aggiungi in `skills/siae-test-data/tests/test_node_fallback.py`:

```python
class TestPivaCfEnti:
    def test_piva_checksum_nota(self):
        """P.IVA nota di test AdE: 00400770939."""
        r = subprocess.run(
            ['node', '-e',
             "const {validaPiva}=require('./generate_profiles.js');"
             "console.log(validaPiva('00400770939'))"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == 'true'

    def test_genera_piva_11_cifre(self):
        r = subprocess.run(
            ['node', '-e',
             "const {generaPiva,validaPiva}=require('./generate_profiles.js');"
             "const p=generaPiva('RM',1234567);"
             "console.log(p.length + ',' + validaPiva(p))"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == '11,true'

    def test_cf_ente11_formato(self):
        r = subprocess.run(
            ['node', '-e',
             "const {calcolaCFEnte11}=require('./generate_profiles.js');"
             "const cf=calcolaCFEnte11(1234567,'RM');"
             "console.log(cf.length + ',' + /^\\d{11}$/.test(cf))"],
            cwd=SCRIPTS_DIR, capture_output=True, text=True, timeout=5
        )
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == '11,true'
```

Run: `cd skills/siae-test-data && python -m pytest tests/test_node_fallback.py::TestPivaCfEnti -v`
Output atteso: `FAILED`

---

## Step 2 — Verifica RED

```
FAILED — TypeError: validaPiva is not a function
```

---

## Step 3 — Implementazione GREEN

Aggiungi in `generate_profiles.js` dopo il blocco cfUtils (prima di `module.exports`):

```js
// ── P.IVA e CF enti numerici ─────────────────────────────────────────────────
const _CODICI_PROV = loadRef('forme_giuridiche.json')['_codici_provincia_istat'] || {};

function checksumPiva(piva10) {
  let s = 0;
  for (let i = 0; i < 10; i++) {
    let d = parseInt(piva10[i], 10);
    if (i % 2 === 1) { d *= 2; if (d > 9) d -= 9; }
    s += d;
  }
  return String((10 - s % 10) % 10);
}
function validaPiva(p) {
  if (!p || !/^\d{11}$/.test(p)) return false;
  return checksumPiva(p.slice(0,10)) === p[10];
}
function generaPiva(siglaProv, progressivo) {
  const cod = (_CODICI_PROV[siglaProv] || '001');
  const prog = String(progressivo).padStart(7,'0');
  const p10  = prog + cod;
  return p10 + checksumPiva(p10);
}
// Per SDC/SDP/COOP: CF = P.IVA (chiama generaPiva)
function generaCFUgualePiva(siglaProv, progressivo) {
  return generaPiva(siglaProv, progressivo);
}
// Per ENTEP: CF 11 cifre numeriche (progressivo 7 cifre + codice prov 3 + checksum)
function calcolaCFEnte11(progressivo, siglaProv) {
  return generaPiva(siglaProv, progressivo);  // stessa formula P.IVA
}
// Per ENTE/IST/ONP: CF 10 cifre numeriche (progressivo 10 cifre)
function calcolaCFEnte10(progressivo) {
  return String(progressivo).padStart(10,'0').slice(0,10);
}
```

Aggiorna `module.exports`:
```js
module.exports = { loadRef, parseArgs, makePRNG,
  normalizza, codiceCognome, codiceNome, checksumCF, calcolaCF,
  validaPiva, generaPiva, generaCFUgualePiva, calcolaCFEnte11, calcolaCFEnte10 };
```

---

## Step 4 — Verifica GREEN

Run: `cd skills/siae-test-data && python -m pytest tests/test_node_fallback.py::TestPivaCfEnti -v`
Output atteso: 3 PASSED

---

## Step 5 — Commit

```
test(siae-test-data): RED pivaUtils CF enti Node.js
feat(siae-test-data): pivaUtils — Luhn-AdE, genera_piva, CF enti 10/11 cifre
```

## Criteri di accettazione

- [ ] `validaPiva('00400770939')` === `true`
- [ ] `generaPiva('RM',1234567)` produce P.IVA 11 cifre valida
- [ ] `calcolaCFEnte11` e `calcolaCFEnte10` producono formato numerico corretto
- [ ] 3 test TestPivaCfEnti PASS
