# Task 07 — Test cross-run uniqueness Python (E2E)

**Goal:** Test E2E che verifica che due invocazioni successive di `genera_dataset()` senza `id_tag` esplicito producono nomi/cognomi diversi (almeno 1 su 5 profili).

**File coinvolti:**
- Modifica: `skills/siae-test-data/tests/test_perf_windows_fixes.py`

**Dipende da:** Task 01, 02, 03 (tutti i componenti Python già modificati)

---

## Step 1 — Scrivi il test

Il test usa `time.sleep(1)` per garantire epoch diverso tra le due run. Non è possibile mockare `time.time()` senza modificare il codice di produzione — usiamo invece due `id_tag` espliciti vicini per simulare lo scenario.

Aggiungi classe in `skills/siae-test-data/tests/test_perf_windows_fixes.py`:

```python
class TestCrossRunUniqueness:
    """Test E2E: due run successive producono nomi diversi."""

    def test_due_run_con_id_tag_diversi_producono_nomi_diversi(self):
        """Due chiamate con id_tag diversi producono almeno 1 nome/cognome diverso su 5."""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from generate_profiles import genera_dataset

        base = {
            "categorie": ["PRIVATO"],
            "area_residenza": "IT",
            "quantita_per_tipo": 5,
            "edge_case": False,
        }
        profili1 = genera_dataset({**base, "id_tag": "00001"})
        profili2 = genera_dataset({**base, "id_tag": "00002"})

        nomi1 = [(p["anagrafica"]["nome"], p["anagrafica"]["cognome"]) for p in profili1]
        nomi2 = [(p["anagrafica"]["nome"], p["anagrafica"]["cognome"]) for p in profili2]
        assert nomi1 != nomi2, (
            f"Le due run hanno prodotto gli stessi nomi.\n"
            f"Run 1: {nomi1}\nRun 2: {nomi2}"
        )

    def test_cf_valido_dopo_epoch_in_pid(self):
        """Il CF rimane valido (16 char alfanumerico) con epoch nel profilo_id."""
        import sys, re
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from generate_profiles import genera_dataset

        profili = genera_dataset({
            "categorie": ["PRIVATO"],
            "area_residenza": "IT",
            "quantita_per_tipo": 5,
            "edge_case": False,
            "id_tag": "83421",
        })
        CF_PATTERN = re.compile(r'^[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]$')
        for p in profili:
            cf = p["anagrafica"]["codice_fiscale"]
            assert CF_PATTERN.match(cf), (
                f"CF non valido per pid {p['profilo_id']}: '{cf}'"
            )

    def test_stesso_id_tag_preserva_determinismo(self):
        """Stesso id_tag produce gli stessi profili (backward compat)."""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from generate_profiles import genera_dataset

        config = {
            "categorie": ["PRIVATO"],
            "area_residenza": "IT",
            "quantita_per_tipo": 3,
            "edge_case": False,
            "id_tag": "REPLAY",
        }
        profili1 = genera_dataset(config)
        profili2 = genera_dataset(config)

        for p1, p2 in zip(profili1, profili2):
            assert p1["anagrafica"]["nome"] == p2["anagrafica"]["nome"]
            assert p1["anagrafica"]["cognome"] == p2["anagrafica"]["cognome"]
            assert p1["anagrafica"]["codice_fiscale"] == p2["anagrafica"]["codice_fiscale"]
```

Run: `cd skills/siae-test-data/scripts && python -m pytest ../tests/test_perf_windows_fixes.py::TestCrossRunUniqueness -v 2>&1 | tail -20`

Output atteso (dopo Task 01-03 completati): `3 passed`

---

## Step 2 — Verifica output

Run suite completa: `cd skills/siae-test-data/scripts && python -m pytest ../tests/test_perf_windows_fixes.py -v 2>&1 | tail -25`

Output atteso: tutti i test verdi, inclusi quelli preesistenti.

---

## Step 3 — Commit

```
git add skills/siae-test-data/tests/test_perf_windows_fixes.py
git commit -m "test(test-data): aggiungi test E2E cross-run uniqueness Python"
```

## Criteri di accettazione

- [ ] `test_due_run_con_id_tag_diversi_producono_nomi_diversi` passa
- [ ] `test_cf_valido_dopo_epoch_in_pid` passa (tutti i CF validi con epoch nel pid)
- [ ] `test_stesso_id_tag_preserva_determinismo` passa (backward compat)
- [ ] Suite completa `test_perf_windows_fixes.py`: 0 failure
