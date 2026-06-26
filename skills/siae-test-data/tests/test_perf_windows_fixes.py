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

    def test_stati_extra_ue_not_empty(self):
        """_STATI_EXTRA_UE deve contenere stati extra-europei (es. Giappone, USA).
        Bug fix: belfiore_esteri.json usa 'EXTRA-UE'; il filtro deve usare 'EXTRA-UE' non 'EXTRA_UE'."""
        import generate_profiles
        assert hasattr(generate_profiles, "_STATI_EXTRA_UE")
        assert isinstance(generate_profiles._STATI_EXTRA_UE, list)
        assert len(generate_profiles._STATI_EXTRA_UE) > 0, (
            "_STATI_EXTRA_UE è vuota: il filtro usa 'EXTRA_UE' ma il JSON ha 'EXTRA-UE'"
        )

    def test_stato_random_extra_ue_non_sempre_germania(self):
        """_stato_random('EXTRA_UE', rng) non deve restituire sempre 'Germania'."""
        import random
        from generate_profiles import _stato_random
        stati = {_stato_random("EXTRA_UE", random.Random(f"seed-{i}")) for i in range(20)}
        assert len(stati) > 1, f"_stato_random EXTRA_UE restituisce sempre lo stesso stato: {stati}"
        assert "Germania" not in stati or len(stati) > 1

    def test_precomputed_lists_match_dict_iteration(self):
        """Pre-computed lists devono coincidere con la computazione inline (determinismo)."""
        import generate_profiles
        from generate_profiles import BELFIORE_COMUNI, BELFIORE_ESTERI, CAP_CITTA
        assert generate_profiles._BELFIORE_COMUNI_KEYS == list(BELFIORE_COMUNI.keys())
        assert generate_profiles._CAP_ITALIA_KEYS == list(CAP_CITTA["Italia"].keys())
        expected_ue = [k for k, v in BELFIORE_ESTERI.items() if v["area"] == "UE"]
        assert generate_profiles._STATI_UE == expected_ue
        expected_extra = [k for k, v in BELFIORE_ESTERI.items() if v["area"] == "EXTRA-UE"]
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


# ─── TASK 01 — id_tag auto-epoch ────────────────────────────────────────────

class TestIdTagAutoEpoch:
    """id_tag auto-generato da epoch quando assente; deterministico se esplicito."""

    def test_id_tag_auto_generato_quando_assente(self):
        from generate_profiles import genera_dataset
        config = {
            "categorie": ["PRIVATO"],
            "area_residenza": "IT",
            "quantita_per_tipo": 1,
            "edge_case": False,
        }
        profili = genera_dataset(config)
        pid = profili[0]["profilo_id"]
        parts = pid.split("-")
        assert len(parts) == 4, f"Attesi 4 segmenti, trovato: {pid}"
        assert parts[1].isdigit() and len(parts[1]) <= 5, f"Secondo segmento non numerico: {pid}"

    def test_id_tag_esplicito_preserva_determinismo(self):
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


# ─── TASK 02 — run_epoch nel meta ───────────────────────────────────────────

class TestRunEpochMeta:
    """meta.generated_at_epoch presente in ogni profilo."""

    def test_meta_generated_at_epoch_presente(self):
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
                f"Campo mancante in meta: {list(p['meta'].keys())}"
            )
            assert isinstance(p["meta"]["generated_at_epoch"], int)
            assert p["meta"]["generated_at_epoch"] > 1_700_000_000

    def test_meta_epoch_uguale_per_stessa_run(self):
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

    def test_meta_epoch_presente_per_soggetto_giuridico(self):
        from generate_profiles import genera_dataset
        config = {
            "categorie": ["BUSINESS"],
            "area_residenza": "IT",
            "forme_giuridiche": ["SDC"],
            "quantita_per_tipo": 1,
            "edge_case": False,
            "id_tag": "TEST1",
        }
        profili = genera_dataset(config)
        assert "generated_at_epoch" in profili[0]["meta"]

    def test_meta_epoch_zero_con_id_tag_esplicito(self):
        """Con id_tag esplicito run_epoch=0: determinismo garantito, no dipendenza dall'orologio."""
        from generate_profiles import genera_dataset
        config = {
            "categorie": ["PRIVATO"],
            "area_residenza": "IT",
            "quantita_per_tipo": 2,
            "edge_case": False,
            "id_tag": "FIXED",
        }
        profili = genera_dataset(config)
        for p in profili:
            assert p["meta"]["generated_at_epoch"] == 0, (
                f"Con id_tag esplicito generated_at_epoch deve essere 0, "
                f"trovato: {p['meta']['generated_at_epoch']}"
            )


# ─── TASK 03 — ragione sociale epoch ────────────────────────────────────────

class TestRagioneSocialeEpoch:
    """ragione_sociale include epoch tag per unicità cross-run."""

    def test_ragione_sociale_contiene_epoch_tag(self):
        from generate_profiles import genera_dataset
        config = {
            "categorie": ["BUSINESS"],
            "area_residenza": "IT",
            "forme_giuridiche": ["SDC"],
            "quantita_per_tipo": 1,
            "edge_case": False,
            "id_tag": "99999",
        }
        profili = genera_dataset(config)
        rag = profili[0]["soggetto_giuridico"]["ragione_sociale"]
        assert "99999" in rag, f"Epoch tag '99999' assente in ragione_sociale: '{rag}'"

    def test_ragione_sociale_due_run_diverse(self):
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


# ─── TASK 07 — cross-run uniqueness E2E ─────────────────────────────────────

class TestCrossRunUniqueness:
    """Due run con id_tag diversi producono nomi diversi; stesso id_tag = deterministico."""

    def test_due_run_con_id_tag_diversi_producono_nomi_diversi(self):
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
        assert nomi1 != nomi2, f"Run diverse hanno prodotto gli stessi nomi:\n{nomi1}"

    def test_cf_valido_dopo_epoch_in_pid(self):
        import re
        from generate_profiles import genera_dataset
        CF_PATTERN = re.compile(r'^[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]$')
        profili = genera_dataset({
            "categorie": ["PRIVATO"],
            "area_residenza": "IT",
            "quantita_per_tipo": 5,
            "edge_case": False,
            "id_tag": "83421",
        })
        for p in profili:
            cf = p["anagrafica"]["codice_fiscale"]
            assert CF_PATTERN.match(cf), f"CF non valido per {p['profilo_id']}: '{cf}'"

    def test_stesso_id_tag_preserva_determinismo(self):
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

    def test_autore_id_tag_auto(self):
        from generate_profiles import genera_dataset
        profili = genera_dataset({
            "categorie": ["AUTORE"],
            "area_residenza": "IT",
            "quantita_per_tipo": 1,
            "edge_case": False,
        })
        pid = profili[0]["profilo_id"]
        parts = pid.split("-")
        assert len(parts) == 4, f"AUTORE pid non ha 4 segmenti: {pid}"
        assert parts[0] == "A"

    def test_business_due_run_diverse(self):
        from generate_profiles import genera_dataset
        base = {
            "categorie": ["BUSINESS"],
            "area_residenza": "IT",
            "forme_giuridiche": ["SDC"],
            "quantita_per_tipo": 3,
            "edge_case": False,
        }
        p1 = genera_dataset({**base, "id_tag": "55555"})
        p2 = genera_dataset({**base, "id_tag": "66666"})
        piva1 = [x["soggetto_giuridico"]["partita_iva"] for x in p1]
        piva2 = [x["soggetto_giuridico"]["partita_iva"] for x in p2]
        assert piva1 != piva2, "PIVA identica tra run con id_tag diversi"


# ─── VALIDATORS ─────────────────────────────────────────────────────────────

class TestValidators:
    """Esercita validators.py tramite profili reali generati."""

    def _profilo_privato(self, id_tag="V001"):
        from generate_profiles import genera_dataset
        profili = genera_dataset({
            "categorie": ["PRIVATO"],
            "area_residenza": "IT",
            "quantita_per_tipo": 1,
            "edge_case": False,
            "id_tag": id_tag,
        })
        return profili[0]

    def _profilo_business(self, fg="SDC", id_tag="V002"):
        from generate_profiles import genera_dataset
        profili = genera_dataset({
            "categorie": ["BUSINESS"],
            "area_residenza": "IT",
            "forme_giuridiche": [fg],
            "quantita_per_tipo": 1,
            "edge_case": False,
            "id_tag": id_tag,
        })
        return profili[0]

    def test_valida_profilo_privato_valido(self):
        from validators import valida_profilo
        profilo = self._profilo_privato()
        ok, errori = valida_profilo(profilo)
        assert ok, f"Profilo privato non valido: {errori}"

    def test_valida_profilo_business_sdc_valido(self):
        from validators import valida_profilo
        profilo = self._profilo_business("SDC")
        ok, errori = valida_profilo(profilo)
        assert ok, f"Profilo SDC non valido: {errori}"

    def test_valida_telefono_e164_valido(self):
        from validators import valida_telefono_e164
        ok, msg = valida_telefono_e164("+39 02 1234567")
        assert ok, f"Telefono IT non valido: {msg}"

    def test_valida_telefono_e164_non_valido(self):
        from validators import valida_telefono_e164
        ok, msg = valida_telefono_e164("non-un-telefono")
        assert not ok

    def test_valida_cap_citta_coerente_valido(self):
        from validators import valida_cap_citta_coerente
        # 00184 è nel cap_pool di Roma (da lookup)
        ok, msg = valida_cap_citta_coerente("00184", "Roma", "RM")
        assert ok, f"Roma/RM non valido: {msg}"

    def test_valida_cap_citta_coerente_stato_estero(self):
        from validators import valida_cap_citta_coerente
        # Stato estero → sempre ok (validazione non implementata per CAP esteri)
        ok, _ = valida_cap_citta_coerente("75001", "Paris", "FR", stato="Francia")
        assert ok

    def test_valida_vincolo_cf_piva_sdc_valido(self):
        from validators import valida_vincolo_cf_piva
        from piva_calculator import genera_piva
        # SDC: CF deve essere uguale a PIVA (stesso valore, entrambi validi)
        piva = genera_piva("RM", seed="test-sdc-valid")
        ok, msg = valida_vincolo_cf_piva("SDC", piva, piva)
        assert ok, f"SDC CF=PIVA non valido: {msg}"

    def test_valida_vincolo_cf_piva_di_valido(self):
        from validators import valida_vincolo_cf_piva
        from piva_calculator import genera_piva
        # DI: CF=16 char alfanumerico, PIVA=11 cifre, devono essere DIVERSI
        cf = "RSSMRA85A01H501Z"
        piva = genera_piva("RM", seed="test-di-valid")
        ok, msg = valida_vincolo_cf_piva("DI", cf, piva)
        assert ok, f"DI CF+PIVA non valido: {msg}"

    def test_valida_vincolo_cf_piva_sede_estera_vat_ok(self):
        from validators import valida_vincolo_cf_piva
        ok, _ = valida_vincolo_cf_piva("SDC", "12345678901", None,
                                        sede_italiana=False, vat_number="DE123456789")
        assert ok

    def test_valida_vincolo_cf_piva_sede_estera_no_vat(self):
        from validators import valida_vincolo_cf_piva
        ok, msg = valida_vincolo_cf_piva("SDC", "12345678901", None,
                                          sede_italiana=False, vat_number=None)
        assert not ok

    def test_valida_data_serial_bidir(self):
        from validators import valida_data_serial_bidir
        ok, msg = valida_data_serial_bidir("1985-01-01", 31048)
        assert ok, f"Data serial non valido: {msg}"

    def test_valida_belfiore_coerente_comune(self):
        from validators import valida_belfiore_coerente
        cf = "RSSMRA85A01H501Z"  # H501 = Roma
        ok, msg = valida_belfiore_coerente(cf, "Italia", "Roma")
        assert ok, f"Belfiore Roma non valido: {msg}"

    def test_valida_profilo_business_di_valido(self):
        from validators import valida_profilo
        profilo = self._profilo_business("DI", id_tag="V003")
        ok, errori = valida_profilo(profilo)
        assert ok, f"Profilo DI non valido: {errori}"

    def test_valida_vincolo_cf_piva_entep_valido(self):
        from validators import valida_vincolo_cf_piva
        from piva_calculator import genera_piva
        piva = genera_piva("RM", seed="entep-valid")
        cf_entep = piva  # per ENTEP CF e PIVA sono indipendenti (11 cifre)
        ok, msg = valida_vincolo_cf_piva("ENTEP", cf_entep, piva)
        assert ok, f"ENTEP non valido: {msg}"

    def test_valida_vincolo_cf_piva_ente_valido(self):
        from validators import valida_vincolo_cf_piva
        cf_ente = "1234567890"  # 10 cifre numeriche
        ok, msg = valida_vincolo_cf_piva("ENTE", cf_ente, None)
        assert ok, f"ENTE senza PIVA non valido: {msg}"

    def test_valida_vincolo_cf_piva_onp_valido(self):
        from validators import valida_vincolo_cf_piva
        ok, _ = valida_vincolo_cf_piva("ONP", "1234567890", None)
        assert ok

    def test_valida_vincolo_cf_piva_forma_sconosciuta(self):
        from validators import valida_vincolo_cf_piva
        ok, msg = valida_vincolo_cf_piva("XYZ", "abc", None)
        assert not ok
        assert "sconosciuta" in msg.lower() or "XYZ" in msg

    def test_valida_vincolo_cf_piva_sdc_no_piva(self):
        from validators import valida_vincolo_cf_piva
        ok, msg = valida_vincolo_cf_piva("SDC", "12345678901", None)
        assert not ok

    def test_valida_cap_citta_non_esistente(self):
        from validators import valida_cap_citta_coerente
        ok, msg = valida_cap_citta_coerente("00000", "CittàInesistente", "XX")
        assert not ok

    def test_valida_cap_provincia_sbagliata(self):
        from validators import valida_cap_citta_coerente
        # Roma ha provincia RM, non MI
        ok, msg = valida_cap_citta_coerente("00184", "Roma", "MI")
        assert not ok

    def test_valida_telefono_vuoto(self):
        from validators import valida_telefono_e164
        ok, _ = valida_telefono_e164("")
        assert not ok

    def test_valida_data_serial_errato(self):
        from validators import valida_data_serial_bidir
        ok, msg = valida_data_serial_bidir("1985-01-01", 99999)
        assert not ok

    def test_valida_belfiore_sconosciuto(self):
        from validators import valida_belfiore_coerente
        cf = "RSSMRA85A01Z999Z"  # Z999 = codice inesistente
        ok, _ = valida_belfiore_coerente(cf, "Italia", "Roma")
        assert not ok  # belfiore inesistente → invalido

    def test_valida_profilo_ue(self):
        from generate_profiles import genera_dataset
        from validators import valida_profilo
        profili = genera_dataset({
            "categorie": ["PRIVATO"],
            "area_residenza": "UE",
            "quantita_per_tipo": 1,
            "edge_case": False,
            "id_tag": "V004",
        })
        ok, errori = valida_profilo(profili[0])
        assert ok, f"Profilo UE non valido: {errori}"


# ─── ADDRESS GENERATOR ───────────────────────────────────────────────────────

class TestAddressGenerator:
    """Esercita address_generator.py direttamente."""

    def test_genera_indirizzo_standard_it(self):
        import random
        from address_generator import genera_indirizzo_standard_it
        rng = random.Random("test-addr")
        addr = genera_indirizzo_standard_it("Roma", rng)
        assert "via" in addr or "indirizzo" in addr or "tipo" in addr or addr
        assert isinstance(addr, dict)
        assert addr.get("comune") == "Roma" or addr.get("citta") == "Roma" or "Roma" in str(addr)

    def test_genera_indirizzo_estero(self):
        import random
        from address_generator import genera_indirizzo_estero
        rng = random.Random("test-estero")
        addr = genera_indirizzo_estero("Germania", rng)
        assert isinstance(addr, dict)
        assert len(addr) > 0

    def test_normalize_telefono_italia(self):
        import random
        from address_generator import normalize_telefono
        rng = random.Random("test-tel")
        tel = normalize_telefono("Italia", "+39", rng)
        assert tel.startswith("+39") or len(tel) > 5

    def test_normalize_telefono_estero(self):
        import random
        from address_generator import normalize_telefono
        rng = random.Random("test-tel2")
        tel = normalize_telefono("Germania", "+49", rng)
        assert len(tel) > 3


# ─── OUTPUT FORMATTERS ───────────────────────────────────────────────────────

class TestOutputFormatters:
    """Esercita to_csv, to_markdown_table, render."""

    def _profili(self, n=2, id_tag="FMT01"):
        from generate_profiles import genera_dataset
        return genera_dataset({
            "categorie": ["PRIVATO"],
            "area_residenza": "IT",
            "quantita_per_tipo": n,
            "edge_case": False,
            "id_tag": id_tag,
        })

    def test_to_csv_produce_righe(self):
        from generate_profiles import to_csv
        profili = self._profili(2)
        out = to_csv(profili)
        lines = [line for line in out.strip().splitlines() if line]
        assert len(lines) >= 3  # header + 2 profili

    def test_to_csv_ha_header(self):
        from generate_profiles import to_csv
        out = to_csv(self._profili(1))
        assert out.splitlines()[0].startswith("profilo_id")

    def test_to_markdown_table_produce_tabella(self):
        from generate_profiles import to_markdown_table
        out = to_markdown_table(self._profili(1))
        assert "|" in out

    def test_render_json(self):
        import json
        from generate_profiles import render
        profili = self._profili(1)
        out = render(profili, "J")
        parsed = json.loads(out)
        assert len(parsed) == 1

    def test_render_csv(self):
        from generate_profiles import render
        out = render(self._profili(1), "C")
        assert "profilo_id" in out

    def test_render_markdown(self):
        from generate_profiles import render
        out = render(self._profili(1), "T")
        assert "|" in out

    def test_render_all(self):
        from generate_profiles import render
        out = render(self._profili(1), "A")
        assert "JSON" in out and "CSV" in out


# ─── UE / EXTRA_UE PROFILES ─────────────────────────────────────────────────

class TestProfiloUeExtraUe:
    """Profili UE e EXTRA_UE coprono i path alternativi di genera_profilo."""

    def test_profilo_ue_valido(self):
        from generate_profiles import genera_dataset
        profili = genera_dataset({
            "categorie": ["PRIVATO"],
            "area_residenza": "UE",
            "quantita_per_tipo": 2,
            "edge_case": False,
            "id_tag": "UE01",
        })
        assert len(profili) == 2
        for p in profili:
            assert "anagrafica" in p

    def test_profilo_extra_ue(self):
        from generate_profiles import genera_dataset
        profili = genera_dataset({
            "categorie": ["PRIVATO"],
            "area_residenza": "EXTRA_UE",
            "quantita_per_tipo": 1,
            "edge_case": False,
            "id_tag": "EXT1",
        })
        assert len(profili) == 1

    def test_profilo_business_estera(self):
        from generate_profiles import genera_dataset
        profili = genera_dataset({
            "categorie": ["BUSINESS"],
            "area_residenza": "UE",
            "forme_giuridiche": ["SDC"],
            "quantita_per_tipo": 1,
            "edge_case": False,
            "id_tag": "UEB1",
        })
        assert len(profili) == 1

    def test_profilo_editore(self):
        from generate_profiles import genera_dataset
        profili = genera_dataset({
            "categorie": ["EDITORE"],
            "area_residenza": "IT",
            "forme_giuridiche": ["SDC"],
            "quantita_per_tipo": 1,
            "edge_case": False,
            "id_tag": "ED01",
        })
        assert len(profili) == 1
        assert profili[0]["profilo_id"].startswith("E-")

    def test_profilo_combo(self):
        from generate_profiles import genera_dataset
        profili = genera_dataset({
            "categorie": ["COMBO"],
            "area_residenza": "IT",
            "quantita_per_tipo": 1,
            "edge_case": False,
            "id_tag": "CO01",
        })
        assert len(profili) == 1
        assert "AE-" in profili[0]["profilo_id"]

    def test_valida_e_filtra_con_profili_reali(self):
        from generate_profiles import genera_dataset, valida_e_filtra
        profili = genera_dataset({
            "categorie": ["PRIVATO"],
            "area_residenza": "IT",
            "quantita_per_tipo": 3,
            "edge_case": False,
            "id_tag": "VAL1",
        })
        validi, invalidi = valida_e_filtra(profili, strict=False, skip_validation=False)
        assert len(validi) == 3
        assert invalidi == []

    def test_profilo_mix_residenza(self):
        from generate_profiles import genera_dataset
        profili = genera_dataset({
            "categorie": ["PRIVATO"],
            "area_residenza": "MIX",
            "quantita_per_tipo": 5,
            "edge_case": False,
            "id_tag": "MIX1",
        })
        assert len(profili) == 5


# ─── PIVA CALCULATOR ────────────────────────────────────────────────────────

class TestPivaCalculator:
    """Esercita piva_calculator.py direttamente."""

    def test_genera_piva_provincia_rm(self):
        from piva_calculator import genera_piva, valida_piva
        piva = genera_piva("RM", seed="test-rm")
        assert len(piva) == 11
        assert valida_piva(piva)

    def test_genera_piva_provincia_sconosciuta_fallback(self):
        from piva_calculator import genera_piva, valida_piva
        # Provincia sconosciuta usa cod 001 come fallback
        piva = genera_piva("ZZ", seed="test-zz")
        assert valida_piva(piva)

    def test_valida_piva_valida(self):
        from piva_calculator import valida_piva
        assert valida_piva("00400770939")

    def test_valida_piva_checksum_errato(self):
        from piva_calculator import valida_piva
        assert not valida_piva("12345678901")

    def test_valida_piva_troppo_corta(self):
        from piva_calculator import valida_piva
        assert not valida_piva("1234567890")

    def test_valida_piva_none(self):
        from piva_calculator import valida_piva
        assert not valida_piva(None)

    def test_valida_piva_stringa_vuota(self):
        from piva_calculator import valida_piva
        assert not valida_piva("")

    def test_genera_piva_con_progressivo(self):
        from piva_calculator import genera_piva, valida_piva
        piva = genera_piva("MI", progressivo=1234567)
        assert valida_piva(piva)

    def test_genera_cf_uguale_piva(self):
        from piva_calculator import genera_cf_uguale_piva, valida_piva
        cf = genera_cf_uguale_piva("RM", seed="test-uguale")
        assert valida_piva(cf)

    def test_genera_piva_determinismo(self):
        from piva_calculator import genera_piva
        p1 = genera_piva("RM", seed="det-test")
        p2 = genera_piva("RM", seed="det-test")
        assert p1 == p2


# ─── CLI SUBPROCESS ──────────────────────────────────────────────────────────

class TestCliSubprocess:
    """Esercita il CLI main() di generate_profiles.py via subprocess."""

    def test_cli_privato_json(self):
        import subprocess
        import json
        import sys
        from pathlib import Path
        script = str(Path(__file__).parent.parent / "scripts" / "generate_profiles.py")
        r = subprocess.run(
            [sys.executable, script, "--categorie", "PRIVATO",
             "--residenza", "IT", "--quantita", "2",
             "--id-tag", "CLI1", "--skip-validation"],
            capture_output=True, text=True, timeout=15
        )
        assert r.returncode == 0, f"CLI fallito: {r.stderr}"
        data = json.loads(r.stdout)
        assert len(data) == 2
        assert data[0]["profilo_id"] == "P-CLI1-IT-001"

    def test_cli_id_tag_nel_pid(self):
        import subprocess
        import json
        import sys
        from pathlib import Path
        script = str(Path(__file__).parent.parent / "scripts" / "generate_profiles.py")
        r = subprocess.run(
            [sys.executable, script, "--categorie", "PRIVATO",
             "--residenza", "IT", "--quantita", "1",
             "--id-tag", "MYTEST", "--skip-validation"],
            capture_output=True, text=True, timeout=15
        )
        data = json.loads(r.stdout)
        assert "MYTEST" in data[0]["profilo_id"]

    def test_cli_senza_id_tag_epoch_auto(self):
        import subprocess
        import json
        import sys
        from pathlib import Path
        script = str(Path(__file__).parent.parent / "scripts" / "generate_profiles.py")
        r = subprocess.run(
            [sys.executable, script, "--categorie", "PRIVATO",
             "--residenza", "IT", "--quantita", "1", "--skip-validation"],
            capture_output=True, text=True, timeout=15
        )
        assert r.returncode == 0
        data = json.loads(r.stdout)
        parts = data[0]["profilo_id"].split("-")
        assert len(parts) == 4 and parts[1].isdigit()


class TestIdTagConTrattino:
    """Regressione: id_tag con trattino non deve troncare la ragione sociale."""

    def test_id_tag_con_trattino_non_tronca_ragione_sociale(self):
        """MAJOR fix: id_tag='MY-TAG' deve comparire intero nella ragione sociale."""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        from generate_profiles import genera_dataset

        config = {
            "categorie": ["BUSINESS"],
            "area_residenza": "IT",
            "forme_giuridiche": ["SDC"],
            "quantita_per_tipo": 1,
            "id_tag": "MY-TAG",
        }
        profili = genera_dataset(config)
        assert len(profili) == 1
        rs = profili[0].get("soggetto_giuridico", {}).get("ragione_sociale", "")
        assert "MY-TAG" in rs, (
            f"id_tag 'MY-TAG' dovrebbe apparire intero nella ragione sociale, "
            f"ma la ragione e': {rs!r}"
        )


class TestCoverageGap:
    """Test mirati per raggiungere 70% coverage su generate_profiles.py.

    Coprono path di forma giuridica (ENTEP, ENTE), edge case indirizzi e
    output markdown con soggetti giuridici — rami non esercitati dai test esistenti.
    """

    @staticmethod
    def _sys_path():
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

    def test_forma_giuridica_entep(self):
        """ENTEP genera CF ente a 11 cifre + P.IVA."""
        self._sys_path()
        from generate_profiles import genera_dataset
        config = {
            "categorie": ["BUSINESS"],
            "area_residenza": "IT",
            "forme_giuridiche": ["ENTEP"],
            "quantita_per_tipo": 1,
            "edge_case": False,
            "id_tag": "ENTEP1",
        }
        profili = genera_dataset(config)
        assert len(profili) == 1
        sg = profili[0]["soggetto_giuridico"]
        assert sg["codice_fiscale_ente"], "ENTEP deve avere CF ente"
        assert len(sg["codice_fiscale_ente"]) == 11, (
            f"CF ENTEP deve essere 11 cifre, got: {sg['codice_fiscale_ente']}"
        )

    def test_forma_giuridica_ente(self):
        """ENTE genera CF ente a 10 cifre."""
        self._sys_path()
        from generate_profiles import genera_dataset
        config = {
            "categorie": ["BUSINESS"],
            "area_residenza": "IT",
            "forme_giuridiche": ["ENTE"],
            "quantita_per_tipo": 2,
            "edge_case": False,
            "id_tag": "ENTE01",
        }
        profili = genera_dataset(config)
        assert len(profili) == 2
        for p in profili:
            sg = p["soggetto_giuridico"]
            assert sg["codice_fiscale_ente"], "ENTE deve avere CF ente"
            assert len(sg["codice_fiscale_ente"]) == 10, (
                f"CF ENTE deve essere 10 cifre, got: {sg['codice_fiscale_ente']}"
            )

    def test_edge_case_indirizzo_it(self):
        """Con edge_case=True almeno 1 profilo IT ha un edge case nell'indirizzo."""
        self._sys_path()
        from generate_profiles import genera_dataset
        config = {
            "categorie": ["PRIVATO"],
            "area_residenza": "IT",
            "quantita_per_tipo": 10,
            "edge_case": True,
            "id_tag": "EDGE01",
        }
        profili = genera_dataset(config)
        assert len(profili) == 10
        indirizzi = [p["indirizzo"] for p in profili]
        has_edge = any(ind.get("edge_case") for ind in indirizzi)
        assert has_edge, "Con edge_case=True almeno 1 profilo su 10 deve avere edge_case nell'indirizzo"

    def test_to_markdown_con_soggetto_giuridico(self):
        """to_markdown_table copre il ramo soggetto giuridico (tipo_persona=GIURIDICA)."""
        self._sys_path()
        from generate_profiles import genera_dataset, to_markdown_table
        config = {
            "categorie": ["BUSINESS"],
            "area_residenza": "IT",
            "forme_giuridiche": ["SDC"],
            "quantita_per_tipo": 1,
            "edge_case": False,
            "id_tag": "MKDN1",
        }
        profili = genera_dataset(config)
        md = to_markdown_table(profili)
        assert "MKDN1" in md, "Il markdown deve contenere il profilo_id"
        assert "|" in md, "Il markdown deve contenere separatori di tabella"
