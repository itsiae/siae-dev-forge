# Task 08 — test_node_fallback.py completo (7 test accettazione)

**Stato:** [PENDING]

**Goal:** Completare `skills/siae-test-data/tests/test_node_fallback.py` con i
7 test di accettazione finali dal design doc. I test delle classi precedenti
(TestScaffold, TestCfPersonaFisica, ecc.) sono già stati aggiunti nei task 1-7;
questo task verifica che l'intera suite sia coerente e aggiunge eventuali test
mancanti rispetto al design doc.

**File coinvolti:**
- `skills/siae-test-data/tests/test_node_fallback.py` — VERIFICA + eventuale integrazione

---

## Step 1 — Verifica copertura test design doc

Esegui tutta la suite e verifica che i 7 test del design doc siano tutti presenti:

```
design doc test                           → classe::test
────────────────────────────────────────────────────────
test_node_available                       → fixture require_node (autouse)
test_node_1_privato_json                  → TestFormatMain::test_10_privati_json ✓ (superset)
test_node_cf_mario_rossi_diretto          → TestCfPersonaFisica::test_cf_mario_rossi_diretto ✓
test_node_distribuzione_ita_ue            → TestFormatMain::test_distribuzione_ita_ue_70_30 ✓
test_node_business_sdc_ita_rapp_legale    → TestProfileBusiness::test_sdc_rapp_legale_cf_presente ✓
test_node_business_sdc_extra_ue_rapp_leg  → TestProfileBusiness::test_sdc_extra_ue_rapp_legale_belfiore_z ✓
test_node_bench_50_profili                → TestFormatMain::test_bench_50_profili ✓
```

Run: `cd skills/siae-test-data && python -m pytest tests/test_node_fallback.py -v`
Output atteso: tutti i test PASSED (o SKIPPED se node assente)

---

## Step 2 — Aggiunta test mancanti (se necessario)

Se un test del design doc non è presente, aggiungilo alla classe appropriata.
Template test mancante:

```python
# Aggiungere solo se non già coperto dai task precedenti
def test_node_available_esplicito(self):
    """node --version deve exitare 0."""
    r = subprocess.run(['node', '--version'], capture_output=True, text=True)
    # Se non disponibile, il fixture autouse fa già skip
    assert r.returncode == 0
```

---

## Step 3 — Run suite completa

Run: `cd skills/siae-test-data && python -m pytest tests/test_node_fallback.py -v --tb=short`

Output atteso (con Node disponibile):
```
PASSED tests/test_node_fallback.py::TestScaffold::test_file_esiste_e_richiede_senza_errori
PASSED tests/test_node_fallback.py::TestScaffold::test_loadref_carica_nomi_italiani
PASSED tests/test_node_fallback.py::TestCfPersonaFisica::test_cf_mario_rossi_diretto
PASSED tests/test_node_fallback.py::TestCfPersonaFisica::test_cf_checksum_alessandra
PASSED tests/test_node_fallback.py::TestPivaCfEnti::test_piva_checksum_nota
PASSED tests/test_node_fallback.py::TestPivaCfEnti::test_genera_piva_11_cifre
PASSED tests/test_node_fallback.py::TestPivaCfEnti::test_cf_ente11_formato
PASSED tests/test_node_fallback.py::TestAddressNames::test_indirizzo_it_coerente
PASSED tests/test_node_fallback.py::TestAddressNames::test_pick_nome_cognome_italia
PASSED tests/test_node_fallback.py::TestProfilePrivato::test_privato_it_cf_valido
PASSED tests/test_node_fallback.py::TestProfilePrivato::test_privato_light_no_indirizzo
PASSED tests/test_node_fallback.py::TestProfileBusiness::test_sdc_cf_uguale_piva
PASSED tests/test_node_fallback.py::TestProfileBusiness::test_sdc_rapp_legale_cf_presente
PASSED tests/test_node_fallback.py::TestProfileBusiness::test_sdc_extra_ue_rapp_legale_belfiore_z
PASSED tests/test_node_fallback.py::TestFormatMain::test_10_privati_json
PASSED tests/test_node_fallback.py::TestFormatMain::test_distribuzione_ita_ue_70_30
PASSED tests/test_node_fallback.py::TestFormatMain::test_bench_50_profili
```

Verifica anche che pytest Python esistente non regredisca:
Run: `cd skills/siae-test-data && python -m pytest tests/test_perf_windows_fixes.py -v --tb=short`
Output atteso: `23 passed`

---

## Step 4 — Commit

```
test(siae-test-data): suite completa test_node_fallback.py — 17 test Node.js integrazione
```

## Criteri di accettazione

- [ ] Tutti i 7 test del design doc sono presenti e PASS
- [ ] Nessuna regressione su `test_perf_windows_fixes.py` (23 PASS invariati)
- [ ] `pytest.skip` su Node assente (non FAIL)
