"""Calcolo e validazione Partita IVA italiana (11 cifre).

Algoritmo ufficiale Agenzia delle Entrate (DPR 633/72):
- Posizioni 1-7: numero progressivo univoco
- Posizioni 8-10: codice ISTAT ufficio provinciale (es. 001=AG, 058=Roma)
- Posizione 11: cifra di controllo (Luhn-AdE)

Algoritmo cifra di controllo:
1. Cifre in posizione dispari (1,3,5,7,9): sommate cosi' come sono
2. Cifre in posizione pari (2,4,6,8,10): raddoppiate; se >9 sottrai 9
3. Somma totale
4. (10 - somma % 10) % 10 = cifra di controllo
"""

from __future__ import annotations

import random
import re
from pathlib import Path

import data_store

REFS = Path(__file__).resolve().parent.parent / "references"


def _carica_codici_provincia() -> dict:
    """Carica mapping sigla_provincia -> codice ISTAT 3 cifre."""
    raw = data_store.get("forme_giuridiche.json")["_codici_provincia_istat"]
    return {k: v for k, v in raw.items() if not k.startswith("_")}


CODICI_PROVINCIA = _carica_codici_provincia()


def calcola_checksum_piva(piva_10: str) -> str:
    """Calcola la cifra di controllo dato i primi 10 caratteri."""
    if len(piva_10) != 10 or not piva_10.isdigit():
        raise ValueError(f"P.IVA parziale deve essere 10 cifre, ricevuto '{piva_10}'")
    s = 0
    for i, ch in enumerate(piva_10, start=1):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        s += d
    chk = (10 - s % 10) % 10
    return str(chk)


def valida_piva(piva: str) -> bool:
    """Verifica formato e checksum P.IVA."""
    if not piva or not isinstance(piva, str):
        return False
    piva = piva.strip()
    if not re.match(r"^\d{11}$", piva):
        return False
    return calcola_checksum_piva(piva[:10]) == piva[10]


def genera_piva(sigla_provincia: str = "RM", progressivo: int | None = None, seed: str | None = None) -> str:
    """Genera una P.IVA valida (11 cifre).

    - sigla_provincia: codice provincia ISTAT (es. RM -> 001)
    - progressivo: numero da 1 a 9999999; se None genera deterministicamente da seed
    """
    if sigla_provincia not in CODICI_PROVINCIA:
        cod_prov = "001"
    else:
        cod_prov = CODICI_PROVINCIA[sigla_provincia]

    if progressivo is None:
        rng = random.Random(seed) if seed else random.Random()
        progressivo = rng.randint(1000000, 9999999)
    if not (0 <= progressivo <= 9999999):
        raise ValueError("Progressivo deve essere tra 0 e 9999999")

    prog_str = f"{progressivo:07d}"
    piva_10 = prog_str + cod_prov
    chk = calcola_checksum_piva(piva_10)
    return piva_10 + chk


def genera_cf_uguale_piva(sigla_provincia: str = "RM", seed: str | None = None) -> str:
    """Per SDC/SDP/COOP: CF coincide con P.IVA."""
    return genera_piva(sigla_provincia=sigla_provincia, seed=seed)


if __name__ == "__main__":
    p1 = genera_piva("RM", progressivo=1234567)
    print(f"PIVA test RM 1234567: {p1}")
    assert valida_piva(p1), f"PIVA non valida: {p1}"

    p2 = genera_piva("MI", seed="test-seed-1")
    print(f"PIVA test MI seed=test-seed-1: {p2}")
    assert valida_piva(p2)

    p2_bis = genera_piva("MI", seed="test-seed-1")
    assert p2 == p2_bis, "Determinismo seed violato"

    p3 = genera_piva("MI", seed="test-seed-1")
    assert p3 == p2

    # Validazione P.IVA reale (esempio storico AdE)
    assert valida_piva("00400770939")
    assert not valida_piva("12345678901")  # checksum errato
    assert not valida_piva("1234567890")  # solo 10 cifre

    print("OK - piva_calculator passa smoke test")
