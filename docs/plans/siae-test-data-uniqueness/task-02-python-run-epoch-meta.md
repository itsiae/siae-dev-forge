# Task 02 — Propagare run_epoch in genera_profilo() e meta block (Python)

**Goal:** Aggiungere `meta.generated_at_epoch` (epoch Unix intero) in ogni profilo generato, propagando `run_epoch` da `genera_dataset()` fino a `genera_profilo()`.

**File coinvolti:**
- Modifica: `skills/siae-test-data/scripts/generate_profiles.py`

**Dipende da:** Task 01 (run_epoch viene calcolato insieme a id_tag)

---

## Step 1 — Scrivi il test fallente

File: `skills/siae-test-data/tests/test_perf_windows_fixes.py`

Aggiungi nella classe `TestIdTagAutoEpoch` (creata in Task 01):

```python
    def test_meta_generated_at_epoch_presente(self):
        """genera_dataset produce meta.generated_at_epoch in ogni profilo."""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from generate_profiles import genera_dataset

        config = {
            "categorie": ["PRIVATO"],
            "area_residenza": "IT",
            "quantita_per_tipo": 2,
            "edge_case": False,
        }
        profili = genera_dataset(config)
        for p in profili:
            assert "generated_at_epoch" in p["meta"], (
                f"Campo mancante in meta: {p['meta'].keys()}"
            )
            assert isinstance(p["meta"]["generated_at_epoch"], int), (
                f"generated_at_epoch deve essere int, trovato: {type(p['meta']['generated_at_epoch'])}"
            )
            assert p["meta"]["generated_at_epoch"] > 1_700_000_000, (
                f"Epoch non plausibile: {p['meta']['generated_at_epoch']}"
            )

    def test_meta_epoch_uguale_per_stessa_run(self):
        """Tutti i profili della stessa run hanno lo stesso generated_at_epoch."""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from generate_profiles import genera_dataset

        config = {
            "categorie": ["PRIVATO"],
            "area_residenza": "IT",
            "quantita_per_tipo": 3,
            "edge_case": False,
        }
        profili = genera_dataset(config)
        epochs = {p["meta"]["generated_at_epoch"] for p in profili}
        assert len(epochs) == 1, f"Epoch diversi nella stessa run: {epochs}"
```

Run: `cd skills/siae-test-data/scripts && python -m pytest ../tests/test_perf_windows_fixes.py::TestIdTagAutoEpoch::test_meta_generated_at_epoch_presente -v 2>&1 | tail -10`

Output atteso: `FAILED KeyError: 'generated_at_epoch'`

---

## Step 2 — Verifica che il test fallisce

Run: `cd skills/siae-test-data/scripts && python -m pytest "../tests/test_perf_windows_fixes.py::TestIdTagAutoEpoch::test_meta_generated_at_epoch_presente" -v 2>&1 | tail -10`

Output atteso: `FAILED`

---

## Step 3 — Implementa la modifica

**3a. In `genera_dataset()` — calcola run_epoch insieme a id_tag (dopo le righe modificate nel Task 01):**

```python
    id_tag = config.get("id_tag", "")
    if not id_tag:
        id_tag = str(int(time.time()) % 100_000)
    run_epoch = int(time.time())    # ← AGGIUNGERE questa riga
    tag_suffix = f"-{id_tag}"
```

**3b. Aggiorna `_mk_profilo` in `genera_dataset()` per passare `run_epoch`:**

PRIMA:
```python
    def _mk_profilo(pid: str, cat: str, ruoli: list[str], fg: str | None):
        return genera_profilo(
            pid, cat, ruoli, area, fg, edge,
            edge_pattern_filter=edge_pattern_filter,
            edge_probability=edge_probability,
        )
```

DOPO:
```python
    def _mk_profilo(pid: str, cat: str, ruoli: list[str], fg: str | None):
        return genera_profilo(
            pid, cat, ruoli, area, fg, edge,
            edge_pattern_filter=edge_pattern_filter,
            edge_probability=edge_probability,
            run_epoch=run_epoch,
        )
```

**3c. Modifica firma `genera_profilo()` — aggiungi parametro `run_epoch: int = 0`:**

Riga ~309, aggiungi parametro in coda:
```python
def genera_profilo(
    profilo_id: str,
    macro_categoria: str,
    ruoli: list[str],
    area_residenza: str,
    forma_giuridica: str | None,
    edge_case_flag: bool,
    edge_pattern_filter: list[str] | None = None,
    edge_probability: float = 0.6,
    run_epoch: int = 0,    # ← AGGIUNGERE
) -> dict:
```

**3d. Aggiorna entrambi i blocchi `profilo["meta"]`:**

Blocco persona fisica (riga ~357):
```python
        profilo["meta"] = {
            "residenza_it": residenza_kind in ("P-IT", "P-EU-RES", "P-EXT-RES"),
            "edge_case": pf["indirizzo"].get("edge_case"),
            "calcolo_cf": pf["_meta_cf_status"],
            "note": "",
            "generated_at_epoch": run_epoch,    # ← AGGIUNGERE
        }
```

Blocco giuridica (riga ~375):
```python
        profilo["meta"] = {
            "residenza_it": residenza_kind == "ITA",
            "edge_case": sg["sede_legale"].get("edge_case"),
            "calcolo_cf": "ente_numerico" if fg in ("ENTEP", "ENTE", "IST", "ONP") else (
                "uguale_piva" if fg in ("COOP", "SDC", "SDP") else "personale_titolare"
            ),
            "note": "",
            "generated_at_epoch": run_epoch,    # ← AGGIUNGERE
        }
```

---

## Step 4 — Verifica che i test passano

Run: `cd skills/siae-test-data/scripts && python -m pytest ../tests/test_perf_windows_fixes.py::TestIdTagAutoEpoch -v 2>&1 | tail -15`

Output atteso: tutti e 4 i test della classe verdi.

---

## Step 5 — Commit

```
git add skills/siae-test-data/scripts/generate_profiles.py skills/siae-test-data/tests/test_perf_windows_fixes.py
git commit -m "feat(test-data): aggiungi meta.generated_at_epoch propagato da genera_dataset"
```

## Criteri di accettazione

- [ ] `run_epoch = int(time.time())` calcolato in `genera_dataset()`
- [ ] `genera_profilo()` accetta parametro `run_epoch: int = 0`
- [ ] Entrambi i blocchi `profilo["meta"]` contengono `"generated_at_epoch": run_epoch`
- [ ] `test_meta_generated_at_epoch_presente` passa
- [ ] `test_meta_epoch_uguale_per_stessa_run` passa
- [ ] Nessun test preesistente si rompe (il parametro ha default 0 = backward compat)
