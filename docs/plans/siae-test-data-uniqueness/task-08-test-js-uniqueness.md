# Task 08 — Test cross-run uniqueness Node.js (E2E)

**Goal:** Test E2E subprocess che verifica che due invocazioni Node.js con `--id-tag` diversi producono nomi diversi, e che il CF rimane valido.

**File coinvolti:**
- Modifica: `skills/siae-test-data/tests/test_node_fallback.py`

**Dipende da:** Task 05 (generate_profiles.js già aggiornato)

---

## Step 1 — Scrivi i test

Aggiungi nella classe `TestJsEpochUniqueness` (creata in Task 05), o crea classe separata `TestJsCrossRunUniqueness`:

```python
class TestJsCrossRunUniqueness:
    """Test E2E: due run Node.js successive producono nomi diversi."""

    @staticmethod
    def _run_js(id_tag: str, quantita: int = 5) -> list[dict]:
        import subprocess, json, sys
        from pathlib import Path
        script = str(Path(__file__).parent.parent / "scripts" / "generate_profiles.js")
        result = subprocess.run(
            ["node", script,
             "--categorie", "PRIVATO",
             "--nazionalita", "ITA",
             "--quantita", str(quantita),
             "--id-tag", id_tag,
             "--skip-validation"],
            capture_output=True, text=True, timeout=15
        )
        assert result.returncode == 0, f"Script fallito: {result.stderr[:500]}"
        return json.loads(result.stdout)

    def test_due_run_js_producono_nomi_diversi(self):
        """Due run JS con id-tag diversi producono almeno 1 nome diverso su 5."""
        profili1 = self._run_js("11111")
        profili2 = self._run_js("22222")

        nomi1 = [(p["anagrafica"]["nome"], p["anagrafica"]["cognome"]) for p in profili1]
        nomi2 = [(p["anagrafica"]["nome"], p["anagrafica"]["cognome"]) for p in profili2]
        assert nomi1 != nomi2, (
            f"Le due run JS hanno prodotto gli stessi nomi.\n"
            f"Run 1: {nomi1}\nRun 2: {nomi2}"
        )

    def test_js_cf_valido_con_epoch_in_pid(self):
        """Il CF JS rimane valido (16 char) con epoch nel profilo_id."""
        import re
        CF_PATTERN = re.compile(r'^[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]$')
        profili = self._run_js("83421", quantita=5)
        for p in profili:
            cf = p["anagrafica"]["codice_fiscale"]
            assert CF_PATTERN.match(cf), (
                f"CF JS non valido per pid {p['profilo_id']}: '{cf}'"
            )

    def test_js_stesso_id_tag_preserva_determinismo(self):
        """Stesso --id-tag produce gli stessi profili tra due run JS."""
        profili1 = self._run_js("REPLAY", quantita=3)
        profili2 = self._run_js("REPLAY", quantita=3)

        for p1, p2 in zip(profili1, profili2):
            assert p1["anagrafica"]["nome"] == p2["anagrafica"]["nome"], (
                f"Nomi diversi con stesso id-tag: '{p1['anagrafica']['nome']}' vs '{p2['anagrafica']['nome']}'"
            )
            assert p1["anagrafica"]["codice_fiscale"] == p2["anagrafica"]["codice_fiscale"]
```

Run: `cd skills/siae-test-data/scripts && python -m pytest ../tests/test_node_fallback.py::TestJsCrossRunUniqueness -v 2>&1 | tail -20`

Output atteso (con Task 05 completato): `3 passed`

---

## Step 2 — Verifica suite completa Node.js

Run: `cd skills/siae-test-data/scripts && python -m pytest ../tests/test_node_fallback.py -v 2>&1 | tail -25`

Output atteso: tutti i test verdi. Se `test_distribuzione_ita_ue_70_30` o `test_10_privati_json` falliscono per via del nuovo formato pid, verificare se controllano il valore del `profilo_id` — se sì, aggiornarli per accettare 4 segmenti. Usare grep: `grep -n "profilo_id\|P-ITA\|P-IT" skills/siae-test-data/tests/test_node_fallback.py`.

---

## Step 3 — Commit

```
git add skills/siae-test-data/tests/test_node_fallback.py
git commit -m "test(test-data): aggiungi test E2E cross-run uniqueness Node.js"
```

## Criteri di accettazione

- [ ] `test_due_run_js_producono_nomi_diversi` passa
- [ ] `test_js_cf_valido_con_epoch_in_pid` passa
- [ ] `test_js_stesso_id_tag_preserva_determinismo` passa
- [ ] Suite completa `test_node_fallback.py`: 0 failure
