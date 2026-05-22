"""Auto-validazione profili generati per la skill siae-test-data.

Ogni profilo deve passare TUTTI i check applicabili prima di essere restituito.
In caso di failure, il generatore deve rigenerare il campo invece di restituire dati invalidi.

Check implementati:
- valida_cf_persona_fisica (delegato a cf_calculator)
- valida_piva (delegato a piva_calculator)
- valida_vincolo_cf_piva (CF=PIVA per SDC/SDP/COOP)
- valida_cap_citta_coerente (lookup CAP/citta/provincia)
- valida_telefono_e164
- valida_data_serial_bidir (date_to_excel_serial <-> excel_serial_to_date)
- valida_belfiore_coerente (codice in CF coincide con stato/comune anagrafico)
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from cf_calculator import (
    carica_belfiore_comuni,
    carica_belfiore_esteri,
    date_to_excel_serial,
    excel_serial_to_date,
    valida_cf_persona_fisica,
)
from piva_calculator import valida_piva

REFS = Path(__file__).resolve().parent.parent / "references"


def _carica_cap_citta() -> dict:
    with open(REFS / "cap_citta.json", encoding="utf-8") as f:
        return json.load(f)


CAP_CITTA = _carica_cap_citta()
BELFIORE_COMUNI = carica_belfiore_comuni()
BELFIORE_ESTERI = carica_belfiore_esteri()


def valida_vincolo_cf_piva(
    forma_giuridica: str,
    cf: str,
    piva: str | None,
    sede_italiana: bool = True,
    vat_number: str | None = None,
) -> tuple[bool, str]:
    """Verifica i vincoli CF<->PIVA per forma giuridica.

    sede_italiana=False: sede estera, P.IVA italiana NON applicabile,
    deve essere presente VAT Number invece.
    """
    fg = forma_giuridica.upper()
    if not sede_italiana:
        # Sede estera: la P.IVA italiana e' sostituita dal VAT Number
        if not vat_number:
            return False, f"{fg} sede estera: VAT Number obbligatorio"
        if piva:
            return False, f"{fg} sede estera: P.IVA italiana NON applicabile"
        # Per societa estera: vincolo CF=P.IVA non si applica (non c'e' P.IVA italiana)
        if fg == "DI":
            if not valida_cf_persona_fisica(cf):
                return False, "DI estera: CF personale titolare non valido (16 char)"
        return True, ""

    # Sede italiana
    if fg in ("SDC", "SDP", "COOP"):
        if not piva:
            return False, f"{fg}: P.IVA obbligatoria"
        if cf != piva:
            return False, f"{fg}: vincolo CF=P.IVA violato (cf={cf} piva={piva})"
        if not valida_piva(piva):
            return False, f"{fg}: P.IVA non valida (checksum)"
        return True, ""
    if fg == "DI":
        if not piva or not valida_piva(piva):
            return False, "DI: P.IVA obbligatoria e valida"
        if not valida_cf_persona_fisica(cf):
            return False, "DI: CF personale titolare non valido (16 char)"
        if cf == piva:
            return False, "DI: CF e P.IVA devono essere DIVERSI"
        return True, ""
    if fg == "ENTEP":
        if not cf or len(cf) != 11 or not cf.isdigit():
            return False, "ENTEP: CF deve essere 11 cifre numeriche"
        if not piva or not valida_piva(piva):
            return False, "ENTEP: P.IVA obbligatoria e valida"
        return True, ""
    if fg in ("ENTE", "IST", "ONP"):
        if not cf or len(cf) != 10 or not cf.isdigit():
            return False, f"{fg}: CF deve essere 10 cifre numeriche"
        if piva and not valida_piva(piva):
            return False, f"{fg}: P.IVA presente ma non valida"
        return True, ""
    return False, f"Forma giuridica sconosciuta: {fg}"


def valida_cap_citta_coerente(cap: str, citta: str, provincia: str, stato: str = "Italia") -> tuple[bool, str]:
    """Verifica coerenza CAP <-> Citta <-> Provincia per indirizzi italiani."""
    if stato != "Italia":
        return True, ""  # validazione CAP estero non implementata
    if citta not in CAP_CITTA["Italia"]:
        return False, f"Citta '{citta}' non in lookup CAP_CITTA"
    info = CAP_CITTA["Italia"][citta]
    if cap not in info["cap_pool"]:
        return False, f"CAP {cap} non coerente con {citta} (atteso uno tra {info['cap_pool']})"
    if provincia.upper() != info["provincia"]:
        return False, f"Provincia {provincia} non coerente con {citta} (atteso {info['provincia']})"
    return True, ""


def valida_telefono_e164(telefono: str) -> tuple[bool, str]:
    """Verifica formato E.164 (+<prefisso> <cifre>)."""
    if not telefono:
        return False, "Telefono vuoto"
    # Tollera spazi interni; rimuovi e verifica
    cleaned = telefono.replace(" ", "")
    if not re.match(r"^\+\d{8,16}$", cleaned):
        return False, f"Telefono '{telefono}' non in formato E.164"
    return True, ""


def valida_data_serial_bidir(data_iso: str, serial: int) -> tuple[bool, str]:
    """Verifica conversione bidirezionale ISO <-> serial Excel."""
    try:
        d = date.fromisoformat(data_iso)
    except ValueError as e:
        return False, f"data_iso non parseable: {e}"
    expected_serial = date_to_excel_serial(d)
    if expected_serial != serial:
        return False, f"Serial Excel: atteso {expected_serial} per {data_iso}, ricevuto {serial}"
    reconstructed = excel_serial_to_date(serial)
    if reconstructed != d:
        return False, f"Round-trip serial->date fallito: {serial} -> {reconstructed} != {d}"
    return True, ""


def valida_belfiore_coerente(cf: str, stato_nascita: str, comune_nascita: str | None) -> tuple[bool, str]:
    """Verifica che il codice catastale (pos 12-15) del CF coincida con stato/comune."""
    if not cf or len(cf) != 16:
        return True, ""  # CF non persona fisica, skip
    codice_nel_cf = cf[11:15].upper()
    if stato_nascita == "Italia":
        if not comune_nascita:
            return False, "Stato Italia ma comune_nascita assente"
        if comune_nascita not in BELFIORE_COMUNI:
            return False, f"Comune {comune_nascita} non in lookup Belfiore"
        atteso = BELFIORE_COMUNI[comune_nascita]["codice_belfiore"]
        if codice_nel_cf != atteso:
            return False, f"Codice Belfiore nel CF ({codice_nel_cf}) != atteso per {comune_nascita} ({atteso})"
        return True, ""
    # Stato estero
    if stato_nascita not in BELFIORE_ESTERI:
        return False, f"Stato {stato_nascita} non in lookup Belfiore esteri"
    atteso = BELFIORE_ESTERI[stato_nascita]["codice_belfiore"]
    if codice_nel_cf != atteso:
        return False, f"Codice Belfiore nel CF ({codice_nel_cf}) != atteso per {stato_nascita} ({atteso})"
    return True, ""


def valida_profilo(profilo: dict) -> tuple[bool, list[str]]:
    """Valida un profilo completo. Ritorna (ok, lista_errori)."""
    errori: list[str] = []

    anag = profilo.get("anagrafica", {})
    contatti = profilo.get("contatti", {})
    indir = profilo.get("indirizzo", {})
    sg = profilo.get("soggetto_giuridico")

    # CF persona fisica (se presente e non null e non opzionale-assente)
    cf = anag.get("codice_fiscale")
    if cf and isinstance(cf, str) and len(cf) == 16:
        if not valida_cf_persona_fisica(cf):
            errori.append(f"CF persona fisica non valido: {cf}")
        ok, msg = valida_belfiore_coerente(
            cf,
            anag.get("stato_nascita", ""),
            anag.get("comune_nascita"),
        )
        if not ok:
            errori.append(msg)

    # Data nascita serial
    if "data_nascita" in anag and "data_nascita_serial" in anag:
        ok, msg = valida_data_serial_bidir(
            anag["data_nascita"], anag["data_nascita_serial"]
        )
        if not ok:
            errori.append(msg)

    # Telefono
    if contatti.get("telefono"):
        ok, msg = valida_telefono_e164(contatti["telefono"])
        if not ok:
            errori.append(msg)

    # Indirizzo Italia
    if indir.get("stato") == "Italia":
        ok, msg = valida_cap_citta_coerente(
            indir.get("cap", ""),
            indir.get("citta", ""),
            indir.get("provincia", ""),
            "Italia",
        )
        if not ok:
            errori.append(f"Indirizzo residenza: {msg}")

    # Soggetto giuridico
    if sg:
        fg = sg.get("forma_giuridica_codice", "")
        sede_ita = (indir.get("stato") == "Italia") if indir else True
        ok, msg = valida_vincolo_cf_piva(
            fg,
            sg.get("codice_fiscale_ente", ""),
            sg.get("partita_iva"),
            sede_italiana=sede_ita,
            vat_number=sg.get("vat_number"),
        )
        if not ok:
            errori.append(f"Soggetto giuridico: {msg}")

    return (len(errori) == 0, errori)


if __name__ == "__main__":
    # Smoke test con un profilo valido
    profilo_test = {
        "anagrafica": {
            "nome": "Mario", "cognome": "Rossi",
            "codice_fiscale": "RSSMRA85A01H501Z",
            "data_nascita": "1985-01-01",
            "data_nascita_serial": date_to_excel_serial(date(1985, 1, 1)),
            "stato_nascita": "Italia", "comune_nascita": "Roma",
        },
        "contatti": {"telefono": "+39 3331112233"},
        "indirizzo": {
            "cap": "00184", "citta": "Roma", "provincia": "RM", "stato": "Italia",
        },
    }
    ok, errs = valida_profilo(profilo_test)
    print(f"Profilo Mario Rossi: ok={ok}, errori={errs}")
    assert ok, errs

    # Test failure: CAP errato
    profilo_test["indirizzo"]["cap"] = "20121"  # CAP Milano
    ok, errs = valida_profilo(profilo_test)
    print(f"Profilo con CAP errato: ok={ok}, errori={errs}")
    assert not ok

    print("OK - validators passa smoke test")
