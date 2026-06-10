# Task 07 — formatOutput + distribuzione nazionalità + main()

**Stato:** [PENDING]

**Goal:** Implementare `formatOutput(profili, formato)` per JSON/CSV, la funzione
di distribuzione nazionalità (floor + residuo) e `main()` completo con tutti i
parametri CLI. Lo script deve produrre output utilizzabile da SKILL.md Passo 6-bis.

**File coinvolti:**
- `skills/siae-test-data/scripts/generate_profiles.js` — MODIFICA (completa main)

---

## Step 1 — Test RED

Aggiungi in `test_node_fallback.py`:

```python
class TestFormatMain:
    def test_10_privati_json(self):
        r = _node('--categorie', 'PRIVATO', '--nazionalita', 'ITA',
                  '--quantita', '10', '--formato', 'JSON', '--skip-validation')
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert len(data) == 10
        for p in data:
            assert len(p['anagrafica']['codice_fiscale']) == 16

    def test_distribuzione_ita_ue_70_30(self):
        r = _node('--categorie', 'PRIVATO', '--nazionalita', 'ITA,UE',
                  '--distribuzione', '70,30', '--quantita', '10',
                  '--formato', 'JSON', '--skip-validation')
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert len(data) == 10
        it_count  = sum(1 for p in data if p['anagrafica']['stato_nascita'] == 'Italia')
        ue_count  = sum(1 for p in data if p['anagrafica']['stato_nascita'] != 'Italia')
        assert it_count == 7
        assert ue_count == 3

    def test_bench_50_profili(self):
        start = time.time()
        r = _node('--categorie', 'PRIVATO', '--nazionalita', 'ITA',
                  '--quantita', '50', '--formato', 'JSON', '--skip-validation',
                  timeout=10)
        elapsed = time.time() - start
        assert r.returncode == 0, r.stderr
        assert elapsed < 2.0, f'Benchmark fallito: {elapsed:.1f}s > 2.0s'
        assert len(json.loads(r.stdout)) == 50
```

Run: `cd skills/siae-test-data && python -m pytest tests/test_node_fallback.py::TestFormatMain -v`
Output atteso: `FAILED`

---

## Step 2 — Verifica RED

```
FAILED — Error: main() stub, no output
```

---

## Step 3 — Implementazione GREEN

Sostituisci la funzione `main()` stub con:

```js
// ── Format output ─────────────────────────────────────────────────────────────
function formatOutput(profili, formato) {
  if (formato === 'CSV') {
    const header = 'profilo_id,macro_categoria,nome,cf,piva,stato_nascita';
    const rows = profili.map(p => {
      const a  = p.anagrafica || {};
      const sg = p.soggetto_giuridico || {};
      return [
        p.profilo_id, p.macro_categoria,
        a.nome || sg.nome_ente || '',
        a.codice_fiscale || sg.codice_fiscale_ente || '',
        sg.partita_iva || '',
        a.stato_nascita || '',
      ].join(',');
    });
    return [header, ...rows].join('\n');
  }
  return JSON.stringify(profili, null, 2);
}

// ── Distribuzione nazionalità (floor + residuo) ──────────────────────────────
function calcolaDistribuzione(n, gruppi, pct) {
  // gruppi: ['ITA','UE','EXTRA-UE'], pct: [70,20,10] somma=100
  const counts = [];
  let somma = 0;
  for (let i = 0; i < gruppi.length - 1; i++) {
    const c = Math.floor(n * pct[i] / 100);
    counts.push(c);
    somma += c;
  }
  counts.push(n - somma);  // ultimo gruppo riceve il residuo
  return counts;
}

// ── Main ──────────────────────────────────────────────────────────────────────
function main() {
  const args = parseArgs(process.argv);
  const categorie = (args['categorie'] || 'PRIVATO').split(',');
  const nazList   = (args['nazionalita'] || 'ITA').split(',');
  const pctRaw    = args['distribuzione'] ? args['distribuzione'].split(',').map(Number)
                  : nazList.map(() => Math.floor(100 / nazList.length));
  // Normalizza pct a somma 100
  const pctTot = pctRaw.reduce((a,b) => a+b, 0);
  const pct    = pctRaw.map((p,i) => i < pctRaw.length-1 ? Math.round(p*100/pctTot)
                                                           : 0);
  pct[pct.length-1] = 100 - pct.slice(0,-1).reduce((a,b)=>a+b,0);

  const quantita    = parseInt(args['quantita'] || '10', 10);
  const formato     = (args['formato'] || 'JSON').toUpperCase();
  const profiloTipo = (args['profilo'] || 'FULL').toUpperCase();
  const formaGiu    = (args['forme-giuridiche'] || 'SDC').split(',')[0];
  const skipVal     = !!args['skip-validation'];

  // Mappa nazionalità → area
  const areaMap = { 'ITA': 'IT', 'UE': 'UE', 'EXTRA-UE': 'EXTRA-UE' };
  const gruppi  = nazList.map(n => areaMap[n] || 'IT');
  const counts  = calcolaDistribuzione(quantita, gruppi, pct);

  const profili = [];
  let idx = 0;
  for (let g = 0; g < gruppi.length; g++) {
    const area = gruppi[g];
    const cat  = categorie[0].toUpperCase();
    for (let k = 0; k < counts[g]; k++) {
      idx++;
      const profiloId = `P-${area}-${String(idx).padStart(3,'0')}`;
      const rng = makePRNG(profiloId);
      if (['BUSINESS','EDITORE'].includes(cat)) {
        profili.push(generaProfiloBusiness(profiloId, area, formaGiu, profiloTipo, rng));
      } else {
        profili.push(generaProfiloPrivato(profiloId, area, profiloTipo, rng));
      }
    }
  }

  const out = formatOutput(profili, formato);
  if (args['output']) {
    fs.writeFileSync(args['output'], out, 'utf8');
  } else {
    process.stdout.write(out + '\n');
  }
}
```

---

## Step 4 — Verifica GREEN

Run: `cd skills/siae-test-data && python -m pytest tests/test_node_fallback.py::TestFormatMain -v`
Output atteso: 3 PASSED, `test_bench_50_profili` elapsed < 2.0s

---

## Step 5 — Commit

```
test(siae-test-data): RED formatOutput + main Node.js
feat(siae-test-data): formatOutput JSON/CSV + distribuzione nazionalità + main() completo
```

## Criteri di accettazione

- [ ] N=10 PRIVATO ITA produce array JSON con 10 profili, CF 16 char
- [ ] Distribuzione 70/30 ITA+UE su N=10 → 7 ITA + 3 UE
- [ ] N=50 in < 2.0s (benchmark macOS)
- [ ] 3 test TestFormatMain PASS
