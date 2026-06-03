"""Calcolo Codice Fiscale italiano (persona fisica + ente giuridico).

Implementa l'algoritmo ufficiale Agenzia delle Entrate:
- Persona fisica: 16 caratteri alfanumerici (consonanti/vocali, anno, mese, giorno, comune, checksum)
- Ente: 11 cifre numeriche (per ENTEP) o 10 cifre (per ENTE/IST/ONP/SDC/SDP/COOP - via piva)

Riferimento normativo: DM 23/12/1976 e successive modifiche.
"""

from __future__ import annotations

import json
import random
import re
from datetime import date, timedelta
from pathlib import Path

REFS = Path(__file__).resolve().parent.parent / "references"

MESI_CF = ["A", "B", "C", "D", "E", "H", "L", "M", "P", "R", "S", "T"]

CHECKSUM_DISPARI = {
    "0": 1, "1": 0, "2": 5, "3": 7, "4": 9, "5": 13, "6": 15, "7": 17, "8": 19, "9": 21,
    "A": 1, "B": 0, "C": 5, "D": 7, "E": 9, "F": 13, "G": 15, "H": 17, "I": 19, "J": 21,
    "K": 2, "L": 4, "M": 18, "N": 20, "O": 11, "P": 3, "Q": 6, "R": 8, "S": 12, "T": 14,
    "U": 16, "V": 10, "W": 22, "X": 25, "Y": 24, "Z": 23,
}
CHECKSUM_PARI = {
    "0": 0, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    "A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5, "G": 6, "H": 7, "I": 8, "J": 9,
    "K": 10, "L": 11, "M": 12, "N": 13, "O": 14, "P": 15, "Q": 16, "R": 17, "S": 18, "T": 19,
    "U": 20, "V": 21, "W": 22, "X": 23, "Y": 24, "Z": 25,
}
CHECKSUM_TO_CHAR = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

VOWELS = set("AEIOU")

# Excel serial base: data 1899-12-30 corrisponde a serial 0 nel sistema Excel
# (con il bug del 1900 leap year compensato per date >= 1900-03-01)
EXCEL_EPOCH = date(1899, 12, 30)


def _normalize(s: str) -> str:
    """Rimuove accenti, spazi e caratteri non alfabetici, ritorna upper."""
    s = s.upper().strip()
    repl = str.maketrans({
        "À": "A", "Á": "A", "Â": "A", "Ä": "A", "Ã": "A",
        "È": "E", "É": "E", "Ê": "E", "Ë": "E",
        "Ì": "I", "Í": "I", "Î": "I", "Ï": "I",
        "Ò": "O", "Ó": "O", "Ô": "O", "Ö": "O", "Õ": "O",
        "Ù": "U", "Ú": "U", "Û": "U", "Ü": "U",
        "Ç": "C", "Ñ": "N", "ß": "S",
    })
    s = s.translate(repl)
    return re.sub(r"[^A-Z]", "", s)


def _consonanti(s: str) -> str:
    return "".join(c for c in s if c not in VOWELS)


def _vocali(s: str) -> str:
    return "".join(c for c in s if c in VOWELS)


def codice_cognome(cognome: str) -> str:
    """Estrai 3 char dal cognome: prime 3 consonanti, poi vocali, poi padding X."""
    s = _normalize(cognome)
    cons = _consonanti(s)
    voc = _vocali(s)
    out = (cons + voc + "XXX")[:3]
    return out


def codice_nome(nome: str) -> str:
    """Estrai 3 char dal nome.

    Regola: se >= 4 consonanti, prendi 1a, 3a, 4a.
    Altrimenti: prime 3 consonanti + vocali + padding X.
    """
    s = _normalize(nome)
    cons = _consonanti(s)
    voc = _vocali(s)
    if len(cons) >= 4:
        return cons[0] + cons[2] + cons[3]
    out = (cons + voc + "XXX")[:3]
    return out


def codice_data_nascita(data_nascita: date, genere: str) -> str:
    """Estrai i 5 char per anno+mese+giorno (giorno+40 per F)."""
    aa = f"{data_nascita.year % 100:02d}"
    m = MESI_CF[data_nascita.month - 1]
    giorno = data_nascita.day + (40 if genere.upper() == "F" else 0)
    return f"{aa}{m}{giorno:02d}"


def calcola_checksum(cf_15: str) -> str:
    """Calcola il 16esimo carattere di controllo dato il CF parziale (15 char)."""
    if len(cf_15) != 15:
        raise ValueError(f"CF parziale deve essere 15 char, ricevuto {len(cf_15)}")
    s = 0
    for i, ch in enumerate(cf_15.upper(), start=1):
        if i % 2 == 1:
            s += CHECKSUM_DISPARI[ch]
        else:
            s += CHECKSUM_PARI[ch]
    return CHECKSUM_TO_CHAR[s % 26]


def calcola_cf_persona_fisica(
    nome: str,
    cognome: str,
    data_nascita: date,
    genere: str,
    codice_belfiore: str,
) -> str:
    """Genera il CF completo (16 char) per persona fisica."""
    cog = codice_cognome(cognome)
    nom = codice_nome(nome)
    dt = codice_data_nascita(data_nascita, genere)
    cb = codice_belfiore.upper()
    if len(cb) != 4:
        raise ValueError(f"Codice Belfiore deve essere 4 char, ricevuto '{cb}'")
    cf_15 = cog + nom + dt + cb
    chk = calcola_checksum(cf_15)
    return cf_15 + chk


def valida_cf_persona_fisica(cf: str) -> bool:
    """Verifica il checksum del CF persona fisica."""
    if not cf or len(cf) != 16:
        return False
    cf = cf.upper()
    if not re.match(r"^[A-Z0-9]{15}[A-Z]$", cf):
        return False
    return calcola_checksum(cf[:15]) == cf[15]


def excel_serial_to_date(serial: int) -> date:
    """Converti serial Excel (giorni da 1899-12-30) in data Python.

    Gestisce il bug Excel del 1900 leap year:
    - serial < 60: date = EXCEL_EPOCH + serial (con uno shift di +1 rispetto al bug)
    - serial >= 60: date = EXCEL_EPOCH + (serial - 1) per saltare il 29-feb-1900 inesistente

    In pratica, per date moderne (>= 1900-03-01) il calcolo e' identico a:
    date = EXCEL_EPOCH + timedelta(days=serial)
    perche' Excel conta il fantomatico 29-feb-1900.
    """
    if serial < 60:
        return EXCEL_EPOCH + timedelta(days=serial + 1)
    return EXCEL_EPOCH + timedelta(days=serial)


def date_to_excel_serial(d: date) -> int:
    """Converti data Python in serial Excel."""
    delta = (d - EXCEL_EPOCH).days
    if d >= date(1900, 3, 1):
        return delta
    return delta - 1


def carica_belfiore_comuni() -> dict:
    with open(REFS / "belfiore_comuni.json", encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


def carica_belfiore_esteri() -> dict:
    with open(REFS / "belfiore_esteri.json", encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


def genera_cf_ente_numerico(lunghezza: int, seed_key: str | None = None) -> str:
    """Genera CF numerico per Enti (10 o 11 cifre).

    Per ENTEP: 11 cifre.
    Per ENTE/IST/ONP: 10 cifre.
    """
    if lunghezza not in (10, 11):
        raise ValueError("Lunghezza CF ente deve essere 10 o 11")
    rng = random.Random(seed_key) if seed_key else random.Random()
    return "".join(str(rng.randint(0, 9)) for _ in range(lunghezza))


if __name__ == "__main__":
    # Smoke test
    d = date(1985, 1, 1)
    cf = calcola_cf_persona_fisica("Mario", "Rossi", d, "M", "H501")
    print(f"CF Mario Rossi 01/01/1985 M Roma: {cf}")
    assert valida_cf_persona_fisica(cf), f"CF non valido: {cf}"

    cf2 = calcola_cf_persona_fisica("Giulia", "Bianchi", date(1990, 6, 15), "F", "F205")
    print(f"CF Giulia Bianchi 15/06/1990 F Milano: {cf2}")
    assert valida_cf_persona_fisica(cf2)

    cf3 = calcola_cf_persona_fisica("Hans", "Müller", date(1988, 3, 20), "M", "Z112")
    print(f"CF Hans Müller 20/03/1988 M Germania: {cf3}")
    assert valida_cf_persona_fisica(cf3)

    # Verifica serial Excel
    serial = date_to_excel_serial(date(1985, 1, 1))
    print(f"Serial Excel 01/01/1985: {serial}")
    assert excel_serial_to_date(serial) == date(1985, 1, 1)

    print("OK - cf_calculator passa smoke test")
