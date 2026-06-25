# Task 03 — Aggiornare ragione sociale con suffisso epoch (Python)

**Goal:** La ragione sociale dei soggetti giuridici include il suffisso epoch estratto dal `profilo_id`, garantendo unicità cross-run anche per BUSINESS/EDITORE.

**File coinvolti:**
- Modifica: `skills/siae-test-data/scripts/generate_profiles.py`

**Dipende da:** Task 01 (il `profilo_id` include già l'epoch nel secondo segmento)

---

## Contesto

Riga 212 di `generate_profiles.py`:
```python
ragione = f"{ragione} {profilo_id[-4:]}"
```

Questo usa i **4 ultimi caratteri** del `profilo_id`. Con il Task 01, il `profilo_id`
di un BUSINESS diventa `B-SDC-83421-IT-001`. `profilo_id[-4:]` = `"0-01"` — non più
solo il progressivo. La logica va aggiornata per usare il progressivo correttamente
e aggiungere il tag epoch dal secondo segmento.

---

## Step 1 — Scrivi il test fallente

File: `skills/siae-test-data/tests/test_perf_windows_fixes.py`

Aggiungi classe separata:

```python
class TestRagioneSocialeEpoch:
    """Verifica che ragione_sociale includa l'epoch tag per unicità cross-run."""

    def test_ragione_sociale_contiene_epoch_tag(self):
        """ragione_sociale di un BUSINESS include il tag epoch dal profilo_id."""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from generate_profiles import genera_dataset

        config = {
            "categorie": ["BUSINESS"],
            "area_residenza": "IT",
            "forme_giuridiche": ["SDC"],
            "quantita_per_tipo": 1,
            "edge_case": False,
            "id_tag": "99999",  # id_tag fisso per test predicibile
        }
        profili = genera_dataset(config)
        rag = profili[0]["soggetto_giuridico"]["ragione_sociale"]
        assert "99999" in rag, f"Epoch tag '99999' assente in ragione_sociale: '{rag}'"

    def test_ragione_sociale_due_run_diverse(self):
        """Due run con id_tag diversi producono ragioni sociali diverse."""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from generate_profiles import genera_dataset

        base = {
            "categorie": ["BUSINESS"],
            "area_residenza": "IT",
            "forme_giuridiche": ["SDC"],
            "quantita_per_tipo": 1,
            "edge_case": False,
        }
        rag1 = genera_dataset({**base, "id_tag": "11111"})[0]["soggetto_giuridico"]["ragione_sociale"]
        rag2 = genera_dataset({**base, "id_tag": "22222"})[0]["soggetto_giuridico"]["ragione_sociale"]
        assert rag1 != rag2, f"Ragioni sociali identiche tra run diverse: '{rag1}'"
```

Run: `cd skills/siae-test-data/scripts && python -m pytest ../tests/test_perf_windows_fixes.py::TestRagioneSocialeEpoch -v 2>&1 | tail -15`

Output atteso: `FAILED AssertionError: Epoch tag '99999' assente`

---

## Step 2 — Verifica che il test fallisce

Run confermato: `FAILED`

---

## Step 3 — Implementa la modifica

In `skills/siae-test-data/scripts/generate_profiles.py`, funzione `_genera_soggetto_giuridico()` riga 210–212:

PRIMA:
```python
    ragione = rng.choice(fg_info["esempi_ragione_sociale"])
    # Aggiungi seed differenziale per evitare collisioni
    ragione = f"{ragione} {profilo_id[-4:]}"
```

DOPO:
```python
    ragione = rng.choice(fg_info["esempi_ragione_sociale"])
    # Estrai progressivo (ultime 3 cifre) e id_tag (secondo segmento) dal profilo_id
    # Formato atteso: B-SDC-83421-IT-001 → parts[2]="83421", parts[-1]="001"
    _parts = profilo_id.split("-")
    _epoch_tag = _parts[2] if len(_parts) >= 4 else ""
    _progressivo = profilo_id[-3:]
    ragione = f"{ragione} {_progressivo}-{_epoch_tag}" if _epoch_tag else f"{ragione} {_progressivo}"
```

---

## Step 4 — Verifica che i test passano

Run: `cd skills/siae-test-data/scripts && python -m pytest ../tests/test_perf_windows_fixes.py::TestRagioneSocialeEpoch -v 2>&1 | tail -15`

Output atteso:
```
PASSED tests/test_perf_windows_fixes.py::TestRagioneSocialeEpoch::test_ragione_sociale_contiene_epoch_tag
PASSED tests/test_perf_windows_fixes.py::TestRagioneSocialeEpoch::test_ragione_sociale_due_run_diverse
2 passed
```

Verifica suite completa: `cd skills/siae-test-data/scripts && python -m pytest ../tests/test_perf_windows_fixes.py -v 2>&1 | tail -20`

Output atteso: tutti i test verdi.

---

## Step 5 — Commit

```
git add skills/siae-test-data/scripts/generate_profiles.py skills/siae-test-data/tests/test_perf_windows_fixes.py
git commit -m "feat(test-data): aggiorna ragione_sociale con suffisso epoch per unicità cross-run"
```

## Criteri di accettazione

- [ ] `_genera_soggetto_giuridico()`: ragione sociale include il tag dal secondo segmento del `profilo_id`
- [ ] `test_ragione_sociale_contiene_epoch_tag` passa
- [ ] `test_ragione_sociale_due_run_diverse` passa
- [ ] Nessun test preesistente si rompe
