"""Test suite per i 7 fix di performance Windows — siae-test-data.

Struttura:
  RC3 — data_store lazy singleton (elimina duplicate json.load)
  RC4 — pre-computed lookup lists (elimina list() O(N) per profilo)
  RC5 — _NORMALIZE_TABLE costante di modulo (elimina str.maketrans per-call)
  RC7 — skip_validation param in valida_e_filtra (elimina O(N) ridondante)

RC1/RC2/RC6 sono modifiche a SKILL.md (documentazione) — nessun unit test applicabile.
"""

import sys
import os

# Aggiungi scripts/ al path per importazioni dirette
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, os.path.abspath(SCRIPTS_DIR))


# ─── RC3 — data_store lazy singleton ────────────────────────────────────────

class TestDataStore:
    def test_module_importable(self):
        """data_store.py deve esistere e importare senza errori."""
        import data_store  # noqa: F401

    def test_get_returns_dict(self):
        """data_store.get() deve restituire un dict per file valido."""
        import data_store
        data_store._CACHE.clear()
        result = data_store.get("nomi_italiani.json")
        assert isinstance(result, dict)

    def test_second_get_returns_same_object(self):
        """Seconda chiamata get() deve restituire lo stesso oggetto in memoria (cache hit)."""
        import data_store
        data_store._CACHE.clear()
        r1 = data_store.get("nomi_italiani.json")
        r2 = data_store.get("nomi_italiani.json")
        assert r1 is r2, "data_store deve restituire lo stesso oggetto (identity), non una copia"

    def test_cache_populated_after_get(self):
        """Dopo get(), il file deve essere nella cache."""
        import data_store
        data_store._CACHE.clear()
        data_store.get("cap_citta.json")
        assert "cap_citta.json" in data_store._CACHE

    def test_all_six_reference_files_loadable(self):
        """Tutti e 6 i file reference devono essere caricabili via data_store."""
        import data_store
        data_store._CACHE.clear()
        expected_files = [
            "nomi_italiani.json",
            "nomi_esteri.json",
            "forme_giuridiche.json",
            "cap_citta.json",
            "belfiore_comuni.json",
            "belfiore_esteri.json",
        ]
        for fname in expected_files:
            result = data_store.get(fname)
            assert isinstance(result, dict), f"{fname} deve essere un dict"
        assert len(data_store._CACHE) == 6, (
            f"Attesi 6 file in cache, trovati {len(data_store._CACHE)}: {list(data_store._CACHE.keys())}"
        )


# ─── RC5 — _NORMALIZE_TABLE costante di modulo ──────────────────────────────

class TestNormalizeTable:
    def test_normalize_table_exists_at_module_level(self):
        """_NORMALIZE_TABLE deve essere una costante di modulo in cf_calculator."""
        import cf_calculator
        assert hasattr(cf_calculator, "_NORMALIZE_TABLE"), (
            "_NORMALIZE_TABLE non trovata come costante di modulo in cf_calculator.py"
        )

    def test_normalize_table_is_translation_table(self):
        """_NORMALIZE_TABLE deve essere un oggetto translation table (dict-like)."""
        import cf_calculator
        # str.maketrans restituisce un dict; verifica che translate funzioni
        result = "test".translate(cf_calculator._NORMALIZE_TABLE)
        assert isinstance(result, str)

    def test_normalize_removes_umlaut(self):
        """_normalize('Müller') deve restituire 'MULLER'."""
        from cf_calculator import _normalize
        assert _normalize("Müller") == "MULLER"

    def test_normalize_removes_accented_vowels(self):
        """_normalize deve sostituire vocali accentate con non-accentate."""
        from cf_calculator import _normalize
        assert _normalize("Àlèssandra") == "ALESSANDRA"

    def test_normalize_handles_sharp_s(self):
        """_normalize deve sostituire ß con S."""
        from cf_calculator import _normalize
        assert _normalize("Straßburg") == "STRASSBURG"

    def test_normalize_removes_spaces_and_non_alpha(self):
        """_normalize deve rimuovere spazi e non-alfabetici."""
        from cf_calculator import _normalize
        assert _normalize("De La Cruz") == "DELACRUZ"

    def test_cf_mario_rossi_unchanged(self):
        """Il CF di Mario Rossi deve restare RSSMRA85A01H501Z dopo la modifica."""
        from cf_calculator import calcola_cf_persona_fisica
        from datetime import date
        cf = calcola_cf_persona_fisica("Mario", "Rossi", date(1985, 1, 1), "M", "H501")
        assert cf == "RSSMRA85A01H501Z", f"Determinismo violato: {cf}"


# ─── RC4 — Pre-computed lookup lists ────────────────────────────────────────

class TestPrecomputedLists:
    def test_belfiore_comuni_keys_exists(self):
        """_BELFIORE_COMUNI_KEYS deve esistere come costante di modulo."""
        import generate_profiles
        assert hasattr(generate_profiles, "_BELFIORE_COMUNI_KEYS")
        assert isinstance(generate_profiles._BELFIORE_COMUNI_KEYS, list)
        assert len(generate_profiles._BELFIORE_COMUNI_KEYS) > 0

    def test_cap_italia_keys_exists(self):
        """_CAP_ITALIA_KEYS deve esistere come costante di modulo."""
        import generate_profiles
        assert hasattr(generate_profiles, "_CAP_ITALIA_KEYS")
        assert isinstance(generate_profiles._CAP_ITALIA_KEYS, list)
        assert len(generate_profiles._CAP_ITALIA_KEYS) > 0

    def test_stati_ue_exists(self):
        """_STATI_UE deve esistere e contenere stati europei."""
        import generate_profiles
        assert hasattr(generate_profiles, "_STATI_UE")
        assert isinstance(generate_profiles._STATI_UE, list)
        assert "Germania" in generate_profiles._STATI_UE

    def test_stati_extra_ue_exists(self):
        """_STATI_EXTRA_UE deve esistere come lista (può essere vuota — bug preesistente:
        belfiore_esteri.json usa 'EXTRA-UE' ma il codice filtra 'EXTRA_UE'; il comportamento
        attuale (fallback a 'Germania') è preservato intenzionalmente in questo PR)."""
        import generate_profiles
        assert hasattr(generate_profiles, "_STATI_EXTRA_UE")
        assert isinstance(generate_profiles._STATI_EXTRA_UE, list)

    def test_precomputed_lists_match_dict_iteration(self):
        """Pre-computed lists devono coincidere con la computazione inline (determinismo)."""
        import generate_profiles
        from generate_profiles import BELFIORE_COMUNI, BELFIORE_ESTERI, CAP_CITTA
        assert generate_profiles._BELFIORE_COMUNI_KEYS == list(BELFIORE_COMUNI.keys())
        assert generate_profiles._CAP_ITALIA_KEYS == list(CAP_CITTA["Italia"].keys())
        expected_ue = [k for k, v in BELFIORE_ESTERI.items() if v["area"] == "UE"]
        assert generate_profiles._STATI_UE == expected_ue
        expected_extra = [k for k, v in BELFIORE_ESTERI.items() if v["area"] == "EXTRA_UE"]
        assert generate_profiles._STATI_EXTRA_UE == expected_extra


# ─── RC7 — skip_validation in valida_e_filtra ───────────────────────────────

class TestSkipValidation:
    def test_skip_validation_param_exists(self):
        """valida_e_filtra deve accettare skip_validation=False."""
        import inspect
        from generate_profiles import valida_e_filtra
        sig = inspect.signature(valida_e_filtra)
        assert "skip_validation" in sig.parameters, (
            "valida_e_filtra() deve avere parametro skip_validation"
        )
        assert sig.parameters["skip_validation"].default is False

    def test_skip_validation_true_returns_all_profiles(self):
        """Con skip_validation=True, tutti i profili vengono restituiti come validi senza check."""
        from generate_profiles import valida_e_filtra
        profili = [
            {"profilo_id": "X-001", "anagrafica": {}},
            {"profilo_id": "X-002", "anagrafica": {}},
        ]
        validi, invalidi = valida_e_filtra(profili, skip_validation=True)
        assert validi == profili
        assert invalidi == []

    def test_skip_validation_false_validates_normally(self):
        """Con skip_validation=False (default), la validazione viene eseguita normalmente."""
        from generate_profiles import valida_e_filtra
        # CF di 16 char ma checksum sbagliato
        profili = [{"profilo_id": "X-001", "anagrafica": {"codice_fiscale": "AAAAAAAAAAAAAAAA"}}]
        validi, invalidi = valida_e_filtra(profili, skip_validation=False, strict=False)
        # Il CF AAAAAAAAAAAAAAAA è invalido → deve finire in invalidi
        assert len(invalidi) > 0

    def test_default_behavior_unchanged(self):
        """Il comportamento default (skip_validation=False) deve essere identico a prima."""
        from generate_profiles import valida_e_filtra
        import inspect
        sig = inspect.signature(valida_e_filtra)
        # default False = stessa semantica della versione precedente (validazione attiva)
        assert sig.parameters["skip_validation"].default is False


# ─── Regressione determinismo — generazione profilo invariata ────────────────

class TestDeterminismo:
    def test_profilo_it_privato_determinismo(self):
        """P-IT-001 deve produrre lo stesso CF prima e dopo i fix."""
        from generate_profiles import genera_profilo
        p = genera_profilo(
            profilo_id="P-IT-001",
            macro_categoria="PRIVATO",
            ruoli=["UTILIZZATORE"],
            area_residenza="IT",
            forma_giuridica=None,
            edge_case_flag=False,
        )
        assert p["profilo_id"] == "P-IT-001"
        cf = p["anagrafica"]["codice_fiscale"]
        assert cf is not None and len(cf) == 16, f"CF non valido: {cf}"
        # Verifica determinismo: stesso profilo_id → stesso CF
        p2 = genera_profilo(
            profilo_id="P-IT-001",
            macro_categoria="PRIVATO",
            ruoli=["UTILIZZATORE"],
            area_residenza="IT",
            forma_giuridica=None,
            edge_case_flag=False,
        )
        assert p["anagrafica"]["codice_fiscale"] == p2["anagrafica"]["codice_fiscale"]
