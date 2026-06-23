# Task 05 — Aggiungere epoch tag ai pid in generate_profiles.js

**Goal:** Il path Node.js genera `profilo_id` con epoch tag a 5 cifre, producendo nomi diversi tra run successive — stessa logica del path Python.

**File coinvolti:**
- Modifica: `skills/siae-test-data/scripts/generate_profiles.js`

**Dipende da:** nessuno (file JS indipendente)

---

## Contesto

In `generate_profiles.js`, funzione `main()` righe 488–507:

```javascript
// pid PRIVATO/AUTORE/EDITORE (riga 503):
const pid = `${pre}-${nazRaw[ni]}-${String(i).padStart(3,'0')}`;

// pid BUSINESS (riga 496):
const pid = `B-${fg}-${nazRaw[ni]}-${String(i).padStart(3,'0')}`;
```

Il CLI già accetta `--id-tag` tramite `parseArgs()` (verificare). Se non presente, aggiungere anche il parsing.

---

## Step 1 — Verifica stato attuale di parseArgs

Run: `grep -n "id.tag\|idTag\|id_tag" /Users/mazzacuv/Git/siae-dev-forge/skills/siae-test-data/scripts/generate_profiles.js`

Output atteso: nessun match (conferma che il flag non esiste ancora).

---

## Step 2 — Scrivi il test fallente

File: `skills/siae-test-data/tests/test_node_fallback.py`

Aggiungi classe:

```python
class TestJsEpochUniqueness:
    """Verifica che il path Node.js produca pid con epoch tag."""

    def test_js_pid_contiene_epoch_tag(self):
        """Node.js genera profilo_id con 4 segmenti (include epoch)."""
        import subprocess, json, sys
        from pathlib import Path
        script = str(Path(__file__).parent.parent / "scripts" / "generate_profiles.js")
        result = subprocess.run(
            ["node", script,
             "--categorie", "PRIVATO",
             "--nazionalita", "ITA",
             "--quantita", "1",
             "--id-tag", "77777",
             "--skip-validation"],
            capture_output=True, text=True, timeout=15
        )
        assert result.returncode == 0, f"Script fallito: {result.stderr[:500]}"
        profili = json.loads(result.stdout)
        pid = profili[0]["profilo_id"]
        parts = pid.split("-")
        assert len(parts) == 4, f"Attesi 4 segmenti, trovato: {pid}"
        assert "77777" in pid, f"Epoch tag '77777' assente nel pid: {pid}"

    def test_js_due_run_diverse_producono_nomi_diversi(self):
        """Due run JS con id-tag diversi producono almeno 1 nome diverso."""
        import subprocess, json, sys
        from pathlib import Path
        script = str(Path(__file__).parent.parent / "scripts" / "generate_profiles.js")

        def _run(tag):
            r = subprocess.run(
                ["node", script,
                 "--categorie", "PRIVATO",
                 "--nazionalita", "ITA",
                 "--quantita", "5",
                 "--id-tag", tag,
                 "--skip-validation"],
                capture_output=True, text=True, timeout=15
            )
            assert r.returncode == 0
            return {p["anagrafica"]["nome"] + p["anagrafica"]["cognome"]
                    for p in json.loads(r.stdout)}

        nomi1 = _run("11111")
        nomi2 = _run("22222")
        assert nomi1 != nomi2, f"Nomi identici tra run diverse: {nomi1}"
```

Run: `cd skills/siae-test-data/scripts && python -m pytest ../tests/test_node_fallback.py::TestJsEpochUniqueness -v 2>&1 | tail -15`

Output atteso: `FAILED` — il flag `--id-tag` non è ancora supportato da JS, oppure il pid ha ancora 3 segmenti.

---

## Step 3 — Implementa la modifica

In `generate_profiles.js`:

**3a. In `parseArgs()` — verifica se `id-tag` è già letto o aggiungilo.**

Trova la funzione `parseArgs` e aggiungi `'id-tag'` all'elenco dei flag stringa se non presente. Se `parseArgs` usa un pattern generico (tutti i `--xxx` diventano `args['xxx']`), non serve modifica.

Run: `grep -n "parseArgs\|function parseArgs" /Users/mazzacuv/Git/siae-dev-forge/skills/siae-test-data/scripts/generate_profiles.js | head -10`

Se `parseArgs` è generico (raccoglie tutto), passare al punto 3b direttamente.

**3b. In `main()` — calcola `idTag` prima del loop (dopo riga ~484):**

```javascript
const idTag = args['id-tag'] || String(Math.floor(Date.now() / 1000) % 100000).padStart(5, '0');
```

**3c. Aggiorna pid PRIVATO/AUTORE/EDITORE (riga ~503):**

PRIMA:
```javascript
const pid = `${pre}-${nazRaw[ni]}-${String(i).padStart(3,'0')}`;
```

DOPO:
```javascript
const pid = `${pre}-${idTag}-${nazRaw[ni]}-${String(i).padStart(3,'0')}`;
```

**3d. Aggiorna pid BUSINESS (riga ~496):**

PRIMA:
```javascript
const pid = `B-${fg}-${nazRaw[ni]}-${String(i).padStart(3,'0')}`;
```

DOPO:
```javascript
const pid = `B-${fg}-${idTag}-${nazRaw[ni]}-${String(i).padStart(3,'0')}`;
```

---

## Step 4 — Verifica che i test passano

Run: `cd skills/siae-test-data/scripts && python -m pytest ../tests/test_node_fallback.py::TestJsEpochUniqueness -v 2>&1 | tail -15`

Output atteso: `2 passed`

Verifica che i test preesistenti non siano rotti:

Run: `cd skills/siae-test-data/scripts && python -m pytest ../tests/test_node_fallback.py -v 2>&1 | tail -20`

Output atteso: tutti i test preesistenti ancora verdi. Nota: i test che verificano il `profilo_id` hardcoded (`P-ITA-001`) potrebbero richiedere adattamento — se `test_privato_it_cf_valido` chiama `generaProfiloPrivato('P-IT-001', ...)` direttamente (non via `main()`), non è toccato. Verificare con grep: `grep -n "P-ITA-001\|P-IT-001" skills/siae-test-data/tests/test_node_fallback.py`.

---

## Step 5 — Commit

```
git add skills/siae-test-data/scripts/generate_profiles.js skills/siae-test-data/tests/test_node_fallback.py
git commit -m "feat(test-data): aggiungi epoch tag ai pid in generate_profiles.js"
```

## Criteri di accettazione

- [ ] `idTag` calcolato in `main()` da `args['id-tag']` o epoch 5 cifre
- [ ] pid PRIVATO: formato `${pre}-${idTag}-${naz}-${seq}`
- [ ] pid BUSINESS: formato `B-${fg}-${idTag}-${naz}-${seq}`
- [ ] `test_js_pid_contiene_epoch_tag` passa
- [ ] `test_js_due_run_diverse_producono_nomi_diversi` passa
- [ ] Nessun test preesistente si rompe
