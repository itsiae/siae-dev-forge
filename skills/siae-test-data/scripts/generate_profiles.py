"""Generatore interattivo di profili anagrafici SIAE autoconsistenti.

Flusso a 6 step:
  1) Tipo soggetto (PRIVATO/BUSINESS/AUTORE/EDITORE/COMBO)
  2) Residenza/sede (IT/UE/EXTRA_UE/MIX)
  3) Forme giuridiche (se BUSINESS/EDITORE societario)
  4) Edge case indirizzi (S/N)
  5) Quantita per tipo
  6) Formato output (J/C/T/A)

Uso non-interattivo (CLI):
  python3 generate_profiles.py --config config.json --output out.json
  oppure parametri inline:
  python3 generate_profiles.py --categorie PRIVATO,AUTORE --residenza IT --quantita 3 --formato JSON

Uso interattivo:
  python3 generate_profiles.py
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import random
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import data_store
from cf_calculator import (
    calcola_cf_persona_fisica,
    carica_belfiore_comuni,
    carica_belfiore_esteri,
    date_to_excel_serial,
    genera_cf_ente_numerico,
)
from piva_calculator import genera_cf_uguale_piva, genera_piva
from address_generator import (
    CAP_CITTA,
    EDGE_PATTERNS,
    genera_indirizzo_edge_it,
    genera_indirizzo_estero,
    genera_indirizzo_standard_it,
    normalize_telefono,
)
from validators import valida_profilo

REFS = Path(__file__).resolve().parent.parent / "references"


def _carica_json(name: str) -> dict:
    return data_store.get(name)


NOMI_IT = _carica_json("nomi_italiani.json")
NOMI_ESTERI = _carica_json("nomi_esteri.json")
FORME_GIURIDICHE = _carica_json("forme_giuridiche.json")
BELFIORE_COMUNI = carica_belfiore_comuni()
BELFIORE_ESTERI = carica_belfiore_esteri()

# Pre-computed lookup lists — eliminano allocazioni O(N) in-loop (RC4)
_BELFIORE_COMUNI_KEYS = list(BELFIORE_COMUNI.keys())
_CAP_ITALIA_KEYS = list(CAP_CITTA["Italia"].keys())
_STATI_UE = [k for k, v in BELFIORE_ESTERI.items() if v["area"] == "UE"]
_STATI_EXTRA_UE = [k for k, v in BELFIORE_ESTERI.items() if v["area"] == "EXTRA-UE"]


def _seed_rng(profilo_id: str) -> random.Random:
    """RNG deterministico per profilo_id."""
    return random.Random(profilo_id)


def _pick_nome_cognome(
    stato_cittadinanza: str,
    genere: str,
    rng: random.Random,
    run_epoch: int = 0,
    run_counter: int = 0,
) -> tuple[str, str]:
    """Selezione nome+cognome epoch-driven: idx = (epoch*7919 + counter*1013) % (N*M).
    Garantisce unicità su N*M=100.000 combinazioni con run_counter globale."""
    if stato_cittadinanza == "Italia":
        pool_n = NOMI_IT["nomi_maschili"] if genere == "M" else NOMI_IT["nomi_femminili"]
        pool_c = NOMI_IT["cognomi"]
    else:
        pool = NOMI_ESTERI.get(stato_cittadinanza)
        if not pool or isinstance(pool, str):
            pool = NOMI_ESTERI["Germania"]
        pool_n = pool["nomi_maschili"] if genere == "M" else pool["nomi_femminili"]
        pool_c = pool["cognomi"]

    N = len(pool_n)   # atteso 100
    M = len(pool_c)   # atteso 1000
    idx = (run_epoch * 7919 + run_counter * 1013) % (N * M)
    nome_idx = idx % N
    cogn_idx = idx // N
    return pool_n[nome_idx], pool_c[cogn_idx]


def _pick_data_nascita(rng: random.Random, anno_min: int = 1950, anno_max: int = 2005) -> date:
    anno = rng.randint(anno_min, anno_max)
    inizio = date(anno, 1, 1)
    fine = date(anno, 12, 31)
    return inizio + timedelta(days=rng.randint(0, (fine - inizio).days))


def _stato_random(area: str, rng: random.Random) -> str:
    """Sceglie uno stato dato area (UE/EXTRA_UE/IT)."""
    if area == "IT":
        return "Italia"
    candidates = _STATI_UE if area == "UE" else _STATI_EXTRA_UE
    return rng.choice(candidates) if candidates else "Germania"


def _genera_anagrafica_persona_fisica(
    profilo_id: str,
    residenza_kind: str,  # "P-IT", "P-EU-RES", "P-EU-NORES", "P-EXT-RES", "P-EXT-NORES"
    edge_case_flag: bool,
    rng: random.Random,
    edge_pattern_filter: list[str] | None = None,
    edge_probability: float = 0.6,
    run_epoch: int = 0,
    run_counter: int = 0,
) -> dict:
    """Genera struttura anagrafica completa per persona fisica + indirizzo."""

    genere = rng.choice(["M", "F"])

    # Determina stato di nascita / cittadinanza coerente con residenza_kind
    if residenza_kind == "P-IT":
        stato_nascita = "Italia"
        cittadinanza = "Italiana"
    elif residenza_kind in ("P-EU-RES", "P-EU-NORES"):
        stato_nascita = _stato_random("UE", rng)
        cittadinanza = stato_nascita
    else:  # P-EXT-RES / P-EXT-NORES
        stato_nascita = _stato_random("EXTRA_UE", rng)
        cittadinanza = stato_nascita

    nome, cognome = _pick_nome_cognome(stato_nascita, genere, rng, run_epoch=run_epoch, run_counter=run_counter)
    data_nasc = _pick_data_nascita(rng)

    # Comune/provincia di nascita
    if stato_nascita == "Italia":
        comune_nascita = rng.choice(_BELFIORE_COMUNI_KEYS)
        provincia_nascita = BELFIORE_COMUNI[comune_nascita]["provincia"]
        codice_belfiore = BELFIORE_COMUNI[comune_nascita]["codice_belfiore"]
    else:
        comune_nascita = None
        provincia_nascita = "—"
        codice_belfiore = BELFIORE_ESTERI[stato_nascita]["codice_belfiore"]

    # CF
    cf_value: str | None = None
    cf_status = "non_inserito"
    if residenza_kind == "P-IT":
        cf_value = calcola_cf_persona_fisica(nome, cognome, data_nasc, genere, codice_belfiore)
        cf_status = "calcolato"
    elif residenza_kind in ("P-EU-RES", "P-EXT-RES"):
        # Stranieri residenti in Italia: CF obbligatorio con Z-xxx
        cf_value = calcola_cf_persona_fisica(nome, cognome, data_nasc, genere, codice_belfiore)
        cf_status = "calcolato"
    else:
        # Stranieri non residenti: CF facoltativo (50% probabilita)
        if rng.random() < 0.5:
            cf_value = calcola_cf_persona_fisica(nome, cognome, data_nasc, genere, codice_belfiore)
            cf_status = "calcolato_facoltativo"
        else:
            cf_value = None
            cf_status = "non_inserito"

    # Indirizzo + telefono
    is_residente_it = residenza_kind in ("P-IT", "P-EU-RES", "P-EXT-RES")
    if is_residente_it:
        # Indirizzo italiano
        citta = rng.choice(_CAP_ITALIA_KEYS)
        pool_pattern = edge_pattern_filter if edge_pattern_filter else EDGE_PATTERNS
        if edge_case_flag and rng.random() < edge_probability:
            pattern = rng.choice(pool_pattern)
            indir = genera_indirizzo_edge_it(citta, pattern, rng)
        else:
            indir = genera_indirizzo_standard_it(citta, rng)
        telefono = normalize_telefono("Italia", "+39", rng)
    else:
        # Indirizzo nel paese di cittadinanza
        stato_residenza = stato_nascita
        if stato_residenza == "Italia":
            stato_residenza = "Germania"
        indir = genera_indirizzo_estero(stato_residenza, rng)
        prefisso = BELFIORE_ESTERI.get(stato_residenza, {}).get("prefisso_telefonico", "+49")
        telefono = normalize_telefono(stato_residenza, prefisso, rng)

    anagrafica = {
        "nome": nome,
        "cognome": cognome,
        "codice_fiscale": cf_value,
        "data_nascita": data_nasc.isoformat(),
        "data_nascita_serial": date_to_excel_serial(data_nasc),
        "genere": genere,
        "cittadinanza": cittadinanza,
        "stato_nascita": stato_nascita,
        "provincia_nascita": provincia_nascita,
        "comune_nascita": comune_nascita,
    }
    contatti = {"telefono": telefono}
    return {
        "anagrafica": anagrafica,
        "contatti": contatti,
        "indirizzo": indir,
        "_meta_cf_status": cf_status,
    }


def _genera_soggetto_giuridico(
    profilo_id: str,
    forma_giuridica_codice: str,
    residenza_kind: str,
    rng: random.Random,
    run_epoch: int = 0,
    run_counter: int = 0,
    id_tag: str = "",
) -> dict:
    """Genera struttura soggetto_giuridico + rappresentante legale.

    residenza_kind: "ITA" o "ESTERA"
    id_tag: tag epoch passato esplicitamente — non estratto dal profilo_id per
            evitare parsing fragile su id_tag che contengono trattini.
    """
    fg_info = FORME_GIURIDICHE[forma_giuridica_codice]
    nat_giur = rng.choice(fg_info["nature_giuridiche"])
    ragione = rng.choice(fg_info["esempi_ragione_sociale"])
    _progressivo = profilo_id[-3:]
    ragione = f"{ragione} {_progressivo}-{id_tag}" if id_tag else f"{ragione} {_progressivo}"

    # Sede legale
    if residenza_kind == "ITA":
        citta = rng.choice(_CAP_ITALIA_KEYS)
        sigla_prov = CAP_CITTA["Italia"][citta]["provincia"]
        sede = genera_indirizzo_standard_it(citta, rng)
        sede["tipo"] = "SEDE_LEGALE"
        vat_number = None
    else:
        stato = _stato_random("UE", rng)
        sede = genera_indirizzo_estero(stato, rng)
        sede["tipo"] = "SEDE_LEGALE"
        sigla_prov = "RM"  # fallback per codice progressivo
        vat_number = f"{stato[:2].upper()}{rng.randint(100000000, 999999999)}"

    # CF + PIVA per forma giuridica
    cf_ente: str
    piva: str | None
    if forma_giuridica_codice == "DI":
        # Rappresentante legale e' anche titolare; CF=CF personale 16 char
        rl = _genera_anagrafica_persona_fisica(
            profilo_id + "-RL", "P-IT" if residenza_kind == "ITA" else "P-EU-RES", False, rng,
            run_epoch=run_epoch, run_counter=run_counter + 50003,
        )
        cf_ente = rl["anagrafica"]["codice_fiscale"]
        piva = (
            genera_piva(sigla_prov, seed=profilo_id + "-piva")
            if residenza_kind == "ITA"
            else None
        )
    elif forma_giuridica_codice == "ENTEP":
        cf_ente = genera_cf_ente_numerico(11, seed_key=profilo_id + "-cf-ente")
        piva = genera_piva(sigla_prov, seed=profilo_id + "-piva") if residenza_kind == "ITA" else None
        rl = _genera_anagrafica_persona_fisica(
            profilo_id + "-RL", "P-IT" if residenza_kind == "ITA" else "P-EU-RES", False, rng,
            run_epoch=run_epoch, run_counter=run_counter + 50003,
        )
    elif forma_giuridica_codice in ("ENTE", "IST", "ONP"):
        cf_ente = genera_cf_ente_numerico(10, seed_key=profilo_id + "-cf-ente")
        # P.IVA opzionale (50% per ENTE pubblico, 70% IST/ONP)
        prob_piva = 0.5 if forma_giuridica_codice == "ENTE" else 0.7
        piva = (
            genera_piva(sigla_prov, seed=profilo_id + "-piva")
            if (residenza_kind == "ITA" and rng.random() < prob_piva)
            else None
        )
        rl = _genera_anagrafica_persona_fisica(
            profilo_id + "-RL", "P-IT" if residenza_kind == "ITA" else "P-EU-RES", False, rng,
            run_epoch=run_epoch, run_counter=run_counter + 50003,
        )
    elif forma_giuridica_codice in ("COOP", "SDC", "SDP"):
        if residenza_kind == "ITA":
            cf_piva = genera_cf_uguale_piva(sigla_prov, seed=profilo_id + "-cfpiva")
            cf_ente = cf_piva
            piva = cf_piva
        else:
            cf_ente = "—"
            piva = None
        rl = _genera_anagrafica_persona_fisica(
            profilo_id + "-RL", "P-IT" if residenza_kind == "ITA" else "P-EU-RES", False, rng,
            run_epoch=run_epoch, run_counter=run_counter + 50003,
        )
    else:
        raise ValueError(f"Forma giuridica {forma_giuridica_codice} non gestita")

    # Gruppo IVA (10% probabilita per societa di capitali)
    gruppo_iva = forma_giuridica_codice == "SDC" and rng.random() < 0.1
    gruppo_iva_numero = f"GR{rng.randint(10000, 99999)}" if gruppo_iva else None

    soggetto_giuridico = {
        "ragione_sociale": ragione,
        "forma_giuridica_codice": forma_giuridica_codice,
        "natura_giuridica": nat_giur,
        "codice_fiscale_ente": cf_ente,
        "partita_iva": piva,
        "vat_number": vat_number,
        "gruppo_iva": gruppo_iva,
        "gruppo_iva_numero": gruppo_iva_numero,
        "vincolo_cf_piva": fg_info["vincolo_cf_piva"],
    }

    return {
        "soggetto_giuridico": soggetto_giuridico,
        "rappresentante_legale": rl["anagrafica"] | {"contatti": rl["contatti"]},
        "sede_legale": sede,
    }


def _residenza_kind_from_choice(area: str, rng: random.Random) -> str:
    """Mappa scelta utente in residenza_kind per persona fisica."""
    if area == "IT":
        return "P-IT"
    if area == "UE":
        return rng.choice(["P-EU-RES", "P-EU-NORES"])
    if area == "EXTRA_UE":
        return rng.choice(["P-EXT-RES", "P-EXT-NORES"])
    # MIX
    return rng.choice(["P-IT", "P-EU-RES", "P-EU-NORES", "P-EXT-RES", "P-EXT-NORES"])


def genera_profilo(
    profilo_id: str,
    macro_categoria: str,
    ruoli: list[str],
    area_residenza: str,
    forma_giuridica: str | None,
    edge_case_flag: bool,
    edge_pattern_filter: list[str] | None = None,
    edge_probability: float = 0.6,
    run_epoch: int = 0,
    run_counter: int = 0,
    id_tag: str = "",
) -> dict:
    """Genera un singolo profilo deterministico identificato da profilo_id.

    edge_pattern_filter: lista di pattern ammessi (sottoinsieme di EDGE_PATTERNS);
       se None, usa tutti.
    edge_probability: probabilita' di applicare un edge case quando edge_case_flag=True.
    """
    rng = _seed_rng(profilo_id)

    # Determina tipo_persona
    if macro_categoria in ("PRIVATO", "AUTORE") or (
        macro_categoria == "EDITORE" and forma_giuridica is None
    ):
        tipo_persona = "FISICA"
    elif macro_categoria == "BUSINESS":
        tipo_persona = "GIURIDICA"
    elif macro_categoria == "EDITORE":
        tipo_persona = "GIURIDICA" if forma_giuridica else "FISICA"
    else:
        tipo_persona = "FISICA"

    profilo: dict = {
        "profilo_id": profilo_id,
        "macro_categoria": macro_categoria,
        "ruoli": ruoli,
        "tipo_persona": tipo_persona,
    }

    if tipo_persona == "FISICA":
        residenza_kind = _residenza_kind_from_choice(area_residenza, rng)
        pf = _genera_anagrafica_persona_fisica(
            profilo_id, residenza_kind, edge_case_flag, rng,
            edge_pattern_filter=edge_pattern_filter,
            edge_probability=edge_probability,
            run_epoch=run_epoch,
            run_counter=run_counter,
        )
        profilo["tipo_profilo"] = residenza_kind
        profilo["anagrafica"] = pf["anagrafica"]
        profilo["contatti"] = pf["contatti"]
        profilo["indirizzo"] = pf["indirizzo"]
        profilo["meta"] = {
            "residenza_it": residenza_kind in ("P-IT", "P-EU-RES", "P-EXT-RES"),
            "edge_case": pf["indirizzo"].get("edge_case"),
            "calcolo_cf": pf["_meta_cf_status"],
            "note": "",
            "generated_at_epoch": run_epoch,
        }
    else:
        # Giuridica
        residenza_kind = "ITA" if area_residenza == "IT" else (
            "ESTERA" if area_residenza in ("UE", "EXTRA_UE") else
            ("ITA" if rng.random() < 0.7 else "ESTERA")
        )
        fg = forma_giuridica or "SDC"
        sg = _genera_soggetto_giuridico(profilo_id, fg, residenza_kind, rng, run_epoch=run_epoch, run_counter=run_counter, id_tag=id_tag)
        profilo["tipo_profilo"] = f"G-{fg}"
        profilo["soggetto_giuridico"] = sg["soggetto_giuridico"]
        profilo["rappresentante_legale"] = sg["rappresentante_legale"]
        profilo["indirizzo"] = sg["sede_legale"]
        profilo["meta"] = {
            "residenza_it": residenza_kind == "ITA",
            "edge_case": sg["sede_legale"].get("edge_case"),
            "calcolo_cf": "ente_numerico" if fg in ("ENTEP", "ENTE", "IST", "ONP") else (
                "uguale_piva" if fg in ("COOP", "SDC", "SDP") else "personale_titolare"
            ),
            "note": "",
            "generated_at_epoch": run_epoch,
        }

    return profilo


def genera_dataset(config: dict) -> list[dict]:
    """Genera un dataset completo dato la config interattiva.

    config: {
      "categorie": ["PRIVATO", "BUSINESS", "AUTORE", "EDITORE"],
      "area_residenza": "IT" | "UE" | "EXTRA_UE" | "MIX",
      "forme_giuridiche": ["DI", "SDC", "SDP", ...],
      "edge_case": True | False,
      "edge_pattern_filter": ["KM_PROGRESSIVO_PLUS", ...]  (opzionale)
      "edge_probability": 0.6  (default 0.6)
      "quantita_per_tipo": 1,
      "id_tag": "KM"  (opzionale, inserito tra prefisso categoria e area per differenziare seed)
    }
    """
    out: list[dict] = []
    categorie = config["categorie"]
    area = config["area_residenza"]
    fg_list = config.get("forme_giuridiche", ["SDC"])
    edge = config.get("edge_case", False)
    qta = int(config.get("quantita_per_tipo", 1))
    edge_pattern_filter = config.get("edge_pattern_filter")
    edge_probability = float(config.get("edge_probability", 0.6))
    id_tag = config.get("id_tag", "")
    _now = int(time.time())
    if not id_tag:
        id_tag = str(_now % 100_000)
    run_epoch = _now
    tag_suffix = f"-{id_tag}"

    _global_counter = 0

    def _mk_profilo(pid: str, cat: str, ruoli: list[str], fg: str | None, counter: int):
        return genera_profilo(
            pid, cat, ruoli, area, fg, edge,
            edge_pattern_filter=edge_pattern_filter,
            edge_probability=edge_probability,
            run_epoch=run_epoch,
            run_counter=counter,
            id_tag=id_tag,
        )

    # Categorie PRIVATO / AUTORE
    for cat in categorie:
        if cat in ("PRIVATO", "AUTORE"):
            ruoli = ["UTILIZZATORE"] if cat == "PRIVATO" else ["AUTORE"]
            for i in range(1, qta + 1):
                pid = f"{cat[0]}{tag_suffix}-{area}-{i:03d}"
                out.append(_mk_profilo(pid, cat, ruoli, None, _global_counter))
                _global_counter += 1
        elif cat == "BUSINESS":
            ruoli = ["UTILIZZATORE"]
            for fg in fg_list:
                for i in range(1, qta + 1):
                    pid = f"B-{fg}{tag_suffix}-{area}-{i:03d}"
                    out.append(_mk_profilo(pid, "BUSINESS", ruoli, fg, _global_counter))
                    _global_counter += 1
        elif cat == "EDITORE":
            ruoli = ["EDITORE"]
            for fg in fg_list:
                for i in range(1, qta + 1):
                    pid = f"E-{fg}{tag_suffix}-{area}-{i:03d}"
                    out.append(_mk_profilo(pid, "EDITORE", ruoli, fg, _global_counter))
                    _global_counter += 1
        elif cat == "COMBO":
            # Autore + Editore sulla stessa anagrafica
            for i in range(1, qta + 1):
                pid = f"AE{tag_suffix}-{area}-{i:03d}"
                out.append(_mk_profilo(pid, "AUTORE", ["AUTORE", "EDITORE"], None, _global_counter))
                _global_counter += 1

    return out


def valida_e_filtra(
    profili: list[dict],
    strict: bool = True,
    skip_validation: bool = False,
) -> tuple[list[dict], list[dict]]:
    """Valida tutti i profili. Ritorna (validi, invalidi).

    strict=True: alza eccezione su invalidi.
    skip_validation=True: salta il loop di validazione (profili già corretti per costruzione).
    """
    if skip_validation:
        return profili, []
    validi, invalidi = [], []
    for p in profili:
        ok, errs = valida_profilo(p)
        if ok:
            validi.append(p)
        else:
            p["_errori"] = errs
            invalidi.append(p)
    if strict and invalidi:
        raise RuntimeError(
            f"Validazione fallita per {len(invalidi)} profili: {[(p['profilo_id'], p['_errori']) for p in invalidi]}"
        )
    return validi, invalidi


def to_csv(profili: list[dict]) -> str:
    """Serializza profili in CSV piatto (campi principali)."""
    fieldnames = [
        "profilo_id", "macro_categoria", "ruoli", "tipo_persona", "tipo_profilo",
        "nome", "cognome", "codice_fiscale", "data_nascita", "data_nascita_serial",
        "genere", "cittadinanza", "stato_nascita", "comune_nascita", "telefono",
        "ragione_sociale", "forma_giuridica", "cf_ente", "partita_iva", "vat_number",
        "gruppo_iva", "indirizzo_toponimo", "indirizzo_via", "indirizzo_civico",
        "indirizzo_cap", "indirizzo_citta", "indirizzo_provincia", "indirizzo_stato",
        "edge_case",
    ]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames)
    w.writeheader()
    for p in profili:
        anag = p.get("anagrafica") or p.get("rappresentante_legale") or {}
        sg = p.get("soggetto_giuridico") or {}
        ind = p.get("indirizzo", {})
        contatti = p.get("contatti") or (anag.get("contatti") if isinstance(anag.get("contatti"), dict) else {}) or {}
        row = {
            "profilo_id": p["profilo_id"],
            "macro_categoria": p["macro_categoria"],
            "ruoli": "|".join(p["ruoli"]),
            "tipo_persona": p["tipo_persona"],
            "tipo_profilo": p.get("tipo_profilo", ""),
            "nome": anag.get("nome", ""),
            "cognome": anag.get("cognome", ""),
            "codice_fiscale": anag.get("codice_fiscale") or "",
            "data_nascita": anag.get("data_nascita", ""),
            "data_nascita_serial": anag.get("data_nascita_serial", ""),
            "genere": anag.get("genere", ""),
            "cittadinanza": anag.get("cittadinanza", ""),
            "stato_nascita": anag.get("stato_nascita", ""),
            "comune_nascita": anag.get("comune_nascita") or "",
            "telefono": contatti.get("telefono", ""),
            "ragione_sociale": sg.get("ragione_sociale", ""),
            "forma_giuridica": sg.get("forma_giuridica_codice", ""),
            "cf_ente": sg.get("codice_fiscale_ente", ""),
            "partita_iva": sg.get("partita_iva") or "",
            "vat_number": sg.get("vat_number") or "",
            "gruppo_iva": sg.get("gruppo_iva", ""),
            "indirizzo_toponimo": ind.get("toponimo", ""),
            "indirizzo_via": ind.get("via", ""),
            "indirizzo_civico": ind.get("civico", ""),
            "indirizzo_cap": ind.get("cap", ""),
            "indirizzo_citta": ind.get("citta", ""),
            "indirizzo_provincia": ind.get("provincia", ""),
            "indirizzo_stato": ind.get("stato", ""),
            "edge_case": ind.get("edge_case") or "",
        }
        w.writerow(row)
    return buf.getvalue()


def to_markdown_table(profili: list[dict]) -> str:
    """Tabella Markdown leggibile (1 riga per profilo, colonne essenziali)."""
    lines = ["| ID | Categoria | Tipo | Nome / Ragione Sociale | CF / CF Ente | P.IVA | Indirizzo | Edge |",
             "|---|---|---|---|---|---|---|---|"]
    for p in profili:
        anag = p.get("anagrafica") or p.get("rappresentante_legale") or {}
        sg = p.get("soggetto_giuridico") or {}
        ind = p.get("indirizzo", {})
        if p["tipo_persona"] == "FISICA":
            nome_o_rag = f"{anag.get('nome','')} {anag.get('cognome','')}".strip()
            cf = anag.get("codice_fiscale") or "—"
            piva = "—"
        else:
            nome_o_rag = sg.get("ragione_sociale", "")
            cf = sg.get("codice_fiscale_ente", "")
            piva = sg.get("partita_iva") or "—"
        indir_str = f"{ind.get('toponimo','')} {ind.get('via','')} {ind.get('civico','')}, {ind.get('cap','')} {ind.get('citta','')} ({ind.get('provincia','')}) {ind.get('stato','')}"
        edge = ind.get("edge_case") or "—"
        lines.append(
            f"| {p['profilo_id']} | {p['macro_categoria']} | {p['tipo_profilo']} | {nome_o_rag} | {cf} | {piva} | {indir_str} | {edge} |"
        )
    return "\n".join(lines)


# ---------- INTERFACCIA INTERATTIVA ----------

def _ask(prompt: str, valid: set[str] | None = None, default: str | None = None) -> str:
    while True:
        suffix = f" [default: {default}]" if default else ""
        ans = input(f"{prompt}{suffix}\n> ").strip().upper()
        if not ans and default:
            ans = default.upper()
        if not valid or ans in valid:
            return ans
        print(f"  Opzione non valida. Scegli tra: {sorted(valid)}")


def _ask_multi(prompt: str, valid: set[str]) -> list[str]:
    while True:
        ans = input(f"{prompt}\n> ").strip().upper()
        if not ans:
            print("  Inserisci almeno un'opzione.")
            continue
        chosen = {x.strip() for x in ans.replace(",", " ").split() if x.strip()}
        if chosen.issubset(valid):
            return sorted(chosen)
        print(f"  Opzioni non valide. Disponibili: {sorted(valid)}")


def flusso_interattivo() -> dict:
    print("=" * 70)
    print("SIAE TEST DATA - Generatore Profili Anagrafici Autoconsistenti")
    print("=" * 70)

    print("\n[Step 1] Che tipo di soggetti vuoi generare? (multipla, separa con virgola)")
    print("  [A] Utilizzatori Privati (persone fisiche)")
    print("  [B] Utilizzatori Business (enti/societa)")
    print("  [C] Autori (persone fisiche con diritti)")
    print("  [D] Editori")
    print("  [E] Combinazione Autore + Editore sulla stessa anagrafica")
    map_cat = {"A": "PRIVATO", "B": "BUSINESS", "C": "AUTORE", "D": "EDITORE", "E": "COMBO"}
    selez = _ask_multi("Lettere (es. A,B,C):", set(map_cat.keys()))
    categorie = [map_cat[x] for x in selez]

    print("\n[Step 2] Che residenza/sede devono avere?")
    print("  [1] Italiana")
    print("  [2] Europea (UE non IT)")
    print("  [3] Estera extra-UE")
    print("  [4] Mix di tutte")
    map_res = {"1": "IT", "2": "UE", "3": "EXTRA_UE", "4": "MIX"}
    res_choice = _ask("Numero:", set(map_res.keys()), default="1")
    area_residenza = map_res[res_choice]

    forme_giuridiche: list[str] = []
    if any(c in ("BUSINESS", "EDITORE") for c in categorie):
        print("\n[Step 3] Forme giuridiche da includere?")
        print("  [1] Tutte (DI, ENTEP, ENTE, IST, ONP, COOP, SDC, SDP)")
        print("  [2] Solo societa (COOP, SDC, SDP)")
        print("  [3] Solo enti (ENTEP, ENTE, IST, ONP)")
        print("  [4] Solo ditte individuali (DI)")
        print("  [5] Selezione personalizzata")
        ch = _ask("Numero:", {"1", "2", "3", "4", "5"}, default="1")
        if ch == "1":
            forme_giuridiche = ["DI", "ENTEP", "ENTE", "IST", "ONP", "COOP", "SDC", "SDP"]
        elif ch == "2":
            forme_giuridiche = ["COOP", "SDC", "SDP"]
        elif ch == "3":
            forme_giuridiche = ["ENTEP", "ENTE", "IST", "ONP"]
        elif ch == "4":
            forme_giuridiche = ["DI"]
        else:
            forme_giuridiche = _ask_multi(
                "Inserisci codici separati da virgola (DI ENTEP ENTE IST ONP COOP SDC SDP):",
                {"DI", "ENTEP", "ENTE", "IST", "ONP", "COOP", "SDC", "SDP"},
            )

    print("\n[Step 4] Includere edge case di indirizzo (SNC, bis/ter, km+, bilingue, ecc.)?")
    edge_choice = _ask("[S]i / [N]o:", {"S", "N"}, default="S")
    edge_case = edge_choice == "S"

    print("\n[Step 5] Quanti profili per ogni tipo selezionato? (intero, es. 1, 3, 5)")
    raw_qta = input("> ").strip() or "1"
    try:
        qta = max(1, int(raw_qta))
    except ValueError:
        qta = 1

    print("\n[Step 6] In che formato vuoi l'output?")
    print("  [J] JSON")
    print("  [C] CSV")
    print("  [T] Tabella Markdown")
    print("  [A] Tutti e tre")
    out_choice = _ask("Lettera:", {"J", "C", "T", "A"}, default="J")

    return {
        "categorie": categorie,
        "area_residenza": area_residenza,
        "forme_giuridiche": forme_giuridiche or ["SDC"],
        "edge_case": edge_case,
        "quantita_per_tipo": qta,
        "formato_output": out_choice,
    }


def render(profili: list[dict], formato: str) -> str:
    if formato == "J":
        return json.dumps(profili, indent=2, ensure_ascii=False)
    if formato == "C":
        return to_csv(profili)
    if formato == "T":
        return to_markdown_table(profili)
    # All
    return (
        "=== JSON ===\n"
        + json.dumps(profili, indent=2, ensure_ascii=False)
        + "\n\n=== CSV ===\n"
        + to_csv(profili)
        + "\n\n=== TABELLA ===\n"
        + to_markdown_table(profili)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera profili anagrafici SIAE autoconsistenti")
    parser.add_argument("--config", type=Path, help="Path a config JSON (non-interactive)")
    parser.add_argument("--output", type=Path, help="Path output (default: stdout)")
    parser.add_argument("--categorie", help="CSV: PRIVATO,BUSINESS,AUTORE,EDITORE,COMBO")
    parser.add_argument("--residenza", help="IT|UE|EXTRA_UE|MIX")
    parser.add_argument("--forme-giuridiche", help="CSV: DI,ENTEP,ENTE,IST,ONP,COOP,SDC,SDP")
    parser.add_argument("--edge-case", action="store_true", help="Includi edge case indirizzi")
    parser.add_argument("--quantita", type=int, default=1, help="Quantita per tipo")
    parser.add_argument("--formato", choices=["JSON", "CSV", "MARKDOWN", "ALL"], default="JSON")
    parser.add_argument("--strict", action="store_true", help="Fallisci se validazione invalidi")
    parser.add_argument("--skip-validation", action="store_true", dest="skip_validation",
                        help="Salta validazione post-generazione (profili generati deterministicamente)")
    parser.add_argument("--id-tag", dest="id_tag", default=None,
                        help="Tag univoco nel profilo_id (default: auto-generato da epoch 5 cifre)")
    args = parser.parse_args()

    if args.config:
        config = json.loads(args.config.read_text(encoding="utf-8"))
    elif args.categorie:
        config = {
            "categorie": args.categorie.split(","),
            "area_residenza": args.residenza or "IT",
            "forme_giuridiche": (args.forme_giuridiche.split(",") if args.forme_giuridiche else ["SDC"]),
            "edge_case": args.edge_case,
            "quantita_per_tipo": args.quantita,
            "formato_output": {"JSON": "J", "CSV": "C", "MARKDOWN": "T", "ALL": "A"}[args.formato],
            "id_tag": args.id_tag or "",
        }
    else:
        # Interattivo
        config = flusso_interattivo()

    profili = genera_dataset(config)
    validi, invalidi = valida_e_filtra(profili, strict=args.strict, skip_validation=args.skip_validation)

    if invalidi and not args.strict:
        print(f"WARNING: {len(invalidi)} profili invalidi (mostrati con _errori)", file=sys.stderr)
        validi = validi + invalidi

    formato = config.get("formato_output", "J")
    if formato in ("JSON",):
        formato = "J"
    output_text = render(validi, formato)

    if args.output:
        args.output.write_text(output_text, encoding="utf-8")
        print(f"Scritti {len(validi)} profili validi in {args.output}", file=sys.stderr)
    else:
        print(output_text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
