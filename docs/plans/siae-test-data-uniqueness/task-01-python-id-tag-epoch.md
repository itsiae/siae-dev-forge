# Task 01 — Auto-generate id_tag da epoch in genera_dataset() (Python)

**Goal:** Quando `config["id_tag"]` è assente o stringa vuota, `genera_dataset()` calcola autonomamente un id_tag da 5 cifre (`int(time.time()) % 100_000`), garantendo seed RNG diverso tra run successive.

**File coinvolti:**
- Modifica: `skills/siae-test-data/scripts/generate_profiles.py`

---

## Step 1 — Scrivi il test fallente

File: `skills/siae-test-data/tests/test_perf_windows_fixes.py`

Aggiungi al fondo del file, prima dell'ultima riga `if __name__ == "__main__"`:

```python
class TestIdTagAutoEpoch:
    """Verifica che genera_dataset auto-generi id_tag quando assente."""

    def test_id_tag_auto_generato_quando_assente(self):
        """genera_dataset senza id_tag produce profilo_id con suffisso numerico."""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from generate_profiles import genera_dataset

        config = {
            "categorie": ["PRIVATO"],
            "area_residenza": "IT",
            "quantita_per_tipo": 1,
            "edge_case": False,
        }
        profili = genera_dataset(config)
        pid = profili[0]["profilo_id"]
        # profilo_id deve avere forma P-NNNNN-IT-001 (5 cifre epoch)
        parts = pid.split("-")
        assert len(parts) == 4, f"Attesi 4 segmenti, trovato: {pid}"
        assert parts[1].isdigit() and len(parts[1]) <= 5, f"Secondo segmento non numerico: {pid}"

    def test_id_tag_esplicito_preserva_determinismo(self):
        """genera_dataset con id_tag esplicito produce sempre lo stesso profilo_id."""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from generate_profiles import genera_dataset

        config = {
            "categorie": ["PRIVATO"],
            "area_residenza": "IT",
            "quantita_per_tipo": 1,
            "edge_case": False,
            "id_tag": "FIXED",
        }
        pid1 = genera_dataset(config)[0]["profilo_id"]
        pid2 = genera_dataset(config)[0]["profilo_id"]
        assert pid1 == pid2 == "P-FIXED-IT-001"
```

Run: `cd skills/siae-test-data/scripts && python -m pytest ../tests/test_perf_windows_fixes.py::TestIdTagAutoEpoch -v 2>&1 | tail -20`

Output atteso: `FAILED` — `AssertionError` su `len(parts) == 4` perché oggi il pid è `P-IT-001` (3 segmenti).

---

## Step 2 — Verifica che il test fallisce

Run: `cd skills/siae-test-data/scripts && python -m pytest ../tests/test_perf_windows_fixes.py::TestIdTagAutoEpoch -v 2>&1 | tail -20`

Output atteso (conferma fallimento):
```
FAILED tests/test_perf_windows_fixes.py::TestIdTagAutoEpoch::test_id_tag_auto_generato_quando_assente
```

---

## Step 3 — Implementa la modifica

In `skills/siae-test-data/scripts/generate_profiles.py`:

**3a. Aggiungi `import time` tra gli import a riga ~28** (dopo `import sys`):
```python
import time
```

**3b. Modifica `genera_dataset()` righe 409–410:**

PRIMA:
```python
    id_tag = config.get("id_tag", "")
    tag_suffix = f"-{id_tag}" if id_tag else ""
```

DOPO:
```python
    id_tag = config.get("id_tag", "")
    if not id_tag:
        id_tag = str(int(time.time()) % 100_000)
    tag_suffix = f"-{id_tag}"
```

---

## Step 4 — Verifica che i test passano

Run: `cd skills/siae-test-data/scripts && python -m pytest ../tests/test_perf_windows_fixes.py::TestIdTagAutoEpoch -v 2>&1 | tail -20`

Output atteso:
```
PASSED tests/test_perf_windows_fixes.py::TestIdTagAutoEpoch::test_id_tag_auto_generato_quando_assente
PASSED tests/test_perf_windows_fixes.py::TestIdTagAutoEpoch::test_id_tag_esplicito_preserva_determinismo
2 passed
```

Verifica anche che i test esistenti non siano rotti:
Run: `cd skills/siae-test-data/scripts && python -m pytest ../tests/test_perf_windows_fixes.py -v 2>&1 | tail -20`

Output atteso: tutti i test precedenti ancora verdi.

---

## Step 5 — Commit

```
git add skills/siae-test-data/scripts/generate_profiles.py skills/siae-test-data/tests/test_perf_windows_fixes.py
git commit -m "feat(test-data): auto-genera id_tag da epoch in genera_dataset quando assente"
```

## Criteri di accettazione

- [ ] `import time` presente in `generate_profiles.py`
- [ ] `genera_dataset()` con config senza `id_tag`: `profilo_id` ha forma `P-NNNNN-IT-001` (4 segmenti)
- [ ] `genera_dataset()` con `id_tag="FIXED"`: `profilo_id` è `P-FIXED-IT-001`
- [ ] I 2 nuovi test passano
- [ ] Nessun test preesistente si rompe
