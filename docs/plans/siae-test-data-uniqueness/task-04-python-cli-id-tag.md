# Task 04 — Aggiungere --id-tag al CLI main() (Python)

**Goal:** Il CLI `generate_profiles.py` espone `--id-tag` come argomento opzionale. Se non passato, `genera_dataset()` auto-genera l'epoch (comportamento già implementato nei task precedenti). Se passato, forza il valore — utile per replay deterministico.

**File coinvolti:**
- Modifica: `skills/siae-test-data/scripts/generate_profiles.py`

**Dipende da:** nessuno (wiring CLI puro, logica è già in genera_dataset)

---

## Step 1 — Scrivi il test fallente

File: `skills/siae-test-data/tests/test_perf_windows_fixes.py`

Aggiungi nella classe `TestIdTagAutoEpoch`:

```python
    def test_cli_id_tag_argomento_presente(self):
        """Il parser CLI accetta --id-tag senza errori."""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        import importlib, generate_profiles
        importlib.reload(generate_profiles)
        import argparse

        # Simula sys.argv con --id-tag
        parser = argparse.ArgumentParser()
        parser.add_argument("--id-tag", dest="id_tag", default=None)
        # Verifica che il parse non sollevi eccezione
        args = parser.parse_args(["--id-tag", "REPLAY"])
        assert args.id_tag == "REPLAY"
```

Nota: questo test verifica il parser in isolamento. Il test subprocess è nel Task 07.

Run: `cd skills/siae-test-data/scripts && python -m pytest "../tests/test_perf_windows_fixes.py::TestIdTagAutoEpoch::test_cli_id_tag_argomento_presente" -v 2>&1 | tail -10`

Output atteso: `PASSED` (il test è sulla logica argparse, non sulla presenza del flag nel main reale — per cui verificheremo anche con subprocess nel Task 07).

Aggiungi un secondo test che verifica l'assenza del flag nel parser reale:

```python
    def test_cli_senza_id_tag_produce_pid_con_5_cifre(self):
        """CLI senza --id-tag produce profilo_id con 5 cifre epoch via subprocess."""
        import subprocess, json, sys
        from pathlib import Path
        script = str(Path(__file__).parent.parent / "scripts" / "generate_profiles.py")
        result = subprocess.run(
            [sys.executable, script, "--categorie", "PRIVATO",
             "--residenza", "IT", "--quantita", "1",
             "--skip-validation"],
            capture_output=True, text=True, timeout=15
        )
        assert result.returncode == 0, f"Script fallito: {result.stderr}"
        profili = json.loads(result.stdout)
        pid = profili[0]["profilo_id"]
        parts = pid.split("-")
        assert len(parts) == 4, f"Attesi 4 segmenti, trovato: {pid}"
        assert parts[1].isdigit(), f"Secondo segmento non numerico: {pid}"
```

Run: `cd skills/siae-test-data/scripts && python -m pytest "../tests/test_perf_windows_fixes.py::TestIdTagAutoEpoch::test_cli_senza_id_tag_produce_pid_con_5_cifre" -v 2>&1 | tail -15`

Output atteso: `FAILED` perché `main()` non espone ancora `--id-tag` nella config.

---

## Step 2 — Verifica che il test subprocess fallisce

Il primo test (parser in isolamento) passerà. Il secondo (subprocess) fallirà con `len(parts) == 3` perché `main()` non passa ancora `id_tag` alla config.

---

## Step 3 — Implementa la modifica

In `generate_profiles.py`, funzione `main()` (riga ~671):

**3a. Aggiungi argomento al parser (dopo `--skip-validation` riga ~682):**

```python
    parser.add_argument(
        "--id-tag", dest="id_tag", default=None,
        help="Tag univoco nel profilo_id (default: auto-generato da epoch 5 cifre)"
    )
```

**3b. Aggiorna la build della config nel branch `elif args.categorie` (riga ~688):**

PRIMA:
```python
        config = {
            "categorie": args.categorie.split(","),
            "area_residenza": args.residenza or "IT",
            "forme_giuridiche": (args.forme_giuridiche.split(",") if args.forme_giuridiche else ["SDC"]),
            "edge_case": args.edge_case,
            "quantita_per_tipo": args.quantita,
            "formato_output": {"JSON": "J", "CSV": "C", "MARKDOWN": "T", "ALL": "A"}[args.formato],
        }
```

DOPO:
```python
        config = {
            "categorie": args.categorie.split(","),
            "area_residenza": args.residenza or "IT",
            "forme_giuridiche": (args.forme_giuridiche.split(",") if args.forme_giuridiche else ["SDC"]),
            "edge_case": args.edge_case,
            "quantita_per_tipo": args.quantita,
            "formato_output": {"JSON": "J", "CSV": "C", "MARKDOWN": "T", "ALL": "A"}[args.formato],
            "id_tag": args.id_tag or "",    # ← AGGIUNGERE (None → stringa vuota → auto-epoch)
        }
```

---

## Step 4 — Verifica che i test passano

Run: `cd skills/siae-test-data/scripts && python -m pytest ../tests/test_perf_windows_fixes.py::TestIdTagAutoEpoch -v 2>&1 | tail -20`

Output atteso: tutti e 5 i test della classe verdi (3 da Task 01/02 + 2 da questo task).

Verifica help CLI: `cd skills/siae-test-data/scripts && python generate_profiles.py --help 2>&1 | grep id-tag`

Output atteso: `--id-tag ID_TAG  Tag univoco nel profilo_id (default: auto-generato da epoch 5 cifre)`

---

## Step 5 — Commit

```
git add skills/siae-test-data/scripts/generate_profiles.py skills/siae-test-data/tests/test_perf_windows_fixes.py
git commit -m "feat(test-data): aggiungi --id-tag al CLI per replay deterministico opzionale"
```

## Criteri di accettazione

- [ ] `--id-tag` presente nel parser CLI con `dest="id_tag"` e `default=None`
- [ ] Config build nel branch `elif args.categorie` include `"id_tag": args.id_tag or ""`
- [ ] `test_cli_senza_id_tag_produce_pid_con_5_cifre` passa (subprocess)
- [ ] `python generate_profiles.py --help` mostra `--id-tag`
- [ ] Nessun test preesistente si rompe
