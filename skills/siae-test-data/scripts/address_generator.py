"""Generazione indirizzi coerenti per profili anagrafici SIAE.

Supporta:
- Indirizzi standard italiani (Via, Piazza, Corso, ecc.)
- Edge case: SNC, bis/ter, km progressivi, range doppi, bilingue, lotto industriale
- Indirizzi esteri (UE/extra-UE) con formati paese specifici
"""

from __future__ import annotations

import json
import random
from pathlib import Path

REFS = Path(__file__).resolve().parent.parent / "references"


def _carica_cap_citta() -> dict:
    with open(REFS / "cap_citta.json", encoding="utf-8") as f:
        return json.load(f)


CAP_CITTA = _carica_cap_citta()

TOPONIMI_STANDARD = ["VIA", "PIAZZA", "CORSO", "VIALE", "VICOLO", "LARGO", "PIAZZALE"]
TOPONIMI_RURALI = ["CONTRADA", "LOCALITÀ", "FRAZIONE", "STRADA COMUNALE", "STRADA VICINALE"]
TOPONIMI_INFRA = ["STRADA STATALE", "STRADA PROVINCIALE", "STRADA REGIONALE", "AUTOSTRADA"]

NOMI_VIE_IT = [
    "Roma", "Garibaldi", "Mazzini", "Cavour", "Dante", "Manzoni", "Verdi", "Leopardi",
    "Vittorio Emanuele II", "XX Settembre", "IV Novembre", "della Repubblica", "della Liberta",
    "Marconi", "Galileo Galilei", "Leonardo da Vinci", "San Giovanni", "Sant'Antonio",
    "delle Vigne", "del Mulino", "Aurelia", "Tiburtina", "Appia", "Cassia", "Salaria",
    "degli Orti", "della Vigna Nuova", "Appia Nuova", "Tirrena Inferiore", "Muoio Piccolo",
]

EDGE_PATTERNS = [
    "SNC",
    "ALFANUM_SLASH",
    "BIS",
    "TER",
    "KM_PROGRESSIVO_PLUS",
    "KM_VIRGOLA",
    "RANGE_DOPPIO",
    "BILINGUE_DE",
    "INTERNO",
    "SCALA_PIANO",
    "ZONA_INDUSTRIALE",
    "FRAZIONE",
    "AUTOSTRADA_KM",
    "CONTRADA_SNC",
]


def genera_indirizzo_standard_it(citta: str, rng: random.Random) -> dict:
    """Genera indirizzo italiano standard, con CAP/provincia coerenti."""
    if citta not in CAP_CITTA["Italia"]:
        # Fallback su Roma
        citta = "Roma"
    info = CAP_CITTA["Italia"][citta]
    cap = rng.choice(info["cap_pool"])
    toponimo = rng.choice(TOPONIMI_STANDARD)
    via = rng.choice(NOMI_VIE_IT)
    civico = str(rng.randint(1, 250))
    return {
        "toponimo": toponimo,
        "via": via,
        "civico": civico,
        "cap": cap,
        "citta": citta,
        "provincia": info["provincia"],
        "stato": "Italia",
        "tipo": "RES",
        "edge_case": None,
    }


def genera_indirizzo_edge_it(citta: str, edge_pattern: str, rng: random.Random) -> dict:
    """Genera indirizzo italiano con un edge case specifico."""
    if citta not in CAP_CITTA["Italia"]:
        citta = "Roma"
    info = CAP_CITTA["Italia"][citta]
    cap = rng.choice(info["cap_pool"])
    base = {
        "cap": cap,
        "citta": citta,
        "provincia": info["provincia"],
        "stato": "Italia",
        "tipo": "RES",
        "edge_case": edge_pattern,
    }

    if edge_pattern == "SNC":
        base.update({
            "toponimo": rng.choice(["VIA", "FRAZIONE", "LOCALITÀ"]),
            "via": rng.choice(NOMI_VIE_IT),
            "civico": "SNC",
        })
    elif edge_pattern == "ALFANUM_SLASH":
        base.update({
            "toponimo": "VIA",
            "via": "della Vigna Nuova",
            "civico": f"{rng.randint(1, 99)}/{rng.choice(['A', 'B', 'C', 'D'])}",
        })
    elif edge_pattern == "BIS":
        base.update({
            "toponimo": "CORSO",
            "via": rng.choice(["Francia", "Italia", "Vittorio Emanuele II"]),
            "civico": f"{rng.randint(1, 200)}bis",
        })
    elif edge_pattern == "TER":
        base.update({
            "toponimo": "VIA",
            "via": rng.choice(["Appia Nuova", "Aurelia", "Tiburtina"]),
            "civico": f"{rng.randint(1, 50)}ter",
        })
    elif edge_pattern == "KM_PROGRESSIVO_PLUS":
        base.update({
            "toponimo": "STRADA STATALE",
            "via": f"{rng.randint(1, 700)} Tirrena Inferiore",
            "civico": f"km {rng.randint(1, 99)}+{rng.choice(['100', '200', '500', '750'])}",
        })
    elif edge_pattern == "KM_VIRGOLA":
        base.update({
            "toponimo": "STRADA PROVINCIALE",
            "via": str(rng.randint(1, 300)),
            "civico": f"km {rng.randint(1, 50)},{rng.choice(['100', '200', '500'])}",
        })
    elif edge_pattern == "RANGE_DOPPIO":
        n = rng.randint(2, 200) * 2
        base.update({
            "toponimo": "VIALE",
            "via": rng.choice(["della Repubblica", "della Liberta", "Marconi"]),
            "civico": f"{n}-{n+2}",
        })
    elif edge_pattern == "BILINGUE_DE":
        # Caso bilingue IT/DE tipico Alto Adige
        base.update({
            "toponimo": "VIA / STRASSE",
            "via": "dei Vigneti / Weinbergweg",
            "civico": f"{rng.randint(1, 30)}/{rng.choice(['A', 'B'])}",
            "citta": "Bolzano",
            "provincia": "BZ",
            "cap": "39100",
        })
    elif edge_pattern == "INTERNO":
        base.update({
            "toponimo": "TRAVERSA",
            "via": "San Giovanni",
            "civico": f"{rng.randint(1, 30)} int. {rng.randint(1, 12)}",
        })
    elif edge_pattern == "SCALA_PIANO":
        base.update({
            "toponimo": "VIA",
            "via": "XX Settembre",
            "civico": f"{rng.randint(50, 200)} scala {rng.choice(['A', 'B', 'C'])} piano {rng.randint(1, 6)}",
        })
    elif edge_pattern == "ZONA_INDUSTRIALE":
        base.update({
            "toponimo": "ZONA INDUSTRIALE",
            "via": "ASI Marcianise",
            "civico": f"lotto {rng.randint(1, 50)}",
            "citta": "Marcianise",
            "provincia": "CE",
            "cap": "81025",
        })
    elif edge_pattern == "FRAZIONE":
        base.update({
            "toponimo": "FRAZIONE",
            "via": rng.choice(["Rometta", "San Bartolomeo", "Casalecchio"]),
            "civico": "SNC",
        })
    elif edge_pattern == "AUTOSTRADA_KM":
        base.update({
            "toponimo": "AUTOSTRADA",
            "via": f"A{rng.randint(1, 30)}",
            "civico": f"km {rng.randint(10, 500)}",
        })
    elif edge_pattern == "CONTRADA_SNC":
        base.update({
            "toponimo": "CONTRADA",
            "via": rng.choice(["Muoio Piccolo", "Santa Lucia", "Pian del Lago"]),
            "civico": "SNC",
        })
    else:
        # fallback standard
        return genera_indirizzo_standard_it(citta, rng)

    return base


def genera_indirizzo_estero(stato: str, rng: random.Random) -> dict:
    """Genera indirizzo estero coerente con il paese (formato CAP locale)."""
    if stato not in CAP_CITTA["Estero"]:
        # Fallback su Germania
        stato = "Germania"
    info = CAP_CITTA["Estero"][stato]
    # Mantieni accoppiamento citta<->cap per coerenza
    idx = rng.randint(0, min(len(info["citta_pool"]), len(info["cap_pool"])) - 1)
    citta = info["citta_pool"][idx]
    cap = info["cap_pool"][idx]

    toponimi_estero = {
        "Germania": ("STRASSE", ["Hauptstrasse", "Bahnhofstrasse", "Berliner", "Königsallee"]),
        "Francia": ("RUE", ["de Rivoli", "de la Paix", "Saint-Honoré", "Lafayette"]),
        "Spagna": ("CALLE", ["Mayor", "Gran Via", "Alcalá", "Serrano"]),
        "Regno Unito": ("STREET", ["Oxford", "Baker", "Regent", "Bond"]),
        "Giappone": ("", ["Shibuya", "Ginza", "Roppongi", "Asakusa"]),
        "Stati Uniti": ("STREET", ["Main", "Broadway", "5th Avenue", "Wall"]),
        "Svizzera": ("STRASSE", ["Bahnhofstrasse", "Limmatquai", "Paradeplatz"]),
        "Romania": ("STRADA", ["Victoriei", "Lipscani", "Magheru"]),
        "Polonia": ("ULICA", ["Nowy Świat", "Marszałkowska", "Floriańska"]),
        "Olanda": ("STRAAT", ["Damrak", "Kalverstraat", "Leidsestraat"]),
        "Belgio": ("RUE", ["Royale", "de la Loi", "Neuve"]),
        "Austria": ("STRASSE", ["Mariahilfer", "Kärntner", "Ringstrasse"]),
    }
    top, vie = toponimi_estero.get(stato, ("STREET", ["Main"]))
    via = rng.choice(vie)
    civico = str(rng.randint(1, 250))

    return {
        "toponimo": top,
        "via": via,
        "civico": civico,
        "cap": cap,
        "citta": citta,
        "provincia": "—",
        "stato": stato,
        "tipo": "RES",
        "edge_case": None,
    }


def normalize_telefono(stato: str, prefisso: str, rng: random.Random) -> str:
    """Genera numero telefonico E.164 con prefisso paese."""
    if stato == "Italia" or prefisso == "+39":
        # Cellulare italiano
        return f"+39 3{rng.randint(20, 99)}{rng.randint(1000000, 9999999)}"
    digits = "".join(str(rng.randint(0, 9)) for _ in range(rng.randint(8, 10)))
    return f"{prefisso} {digits}"


if __name__ == "__main__":
    rng = random.Random("test-seed")
    a1 = genera_indirizzo_standard_it("Roma", rng)
    print("Standard Roma:", a1)

    a2 = genera_indirizzo_edge_it("Cosenza", "CONTRADA_SNC", rng)
    print("Edge Cosenza CONTRADA_SNC:", a2)

    a3 = genera_indirizzo_edge_it("Napoli", "KM_PROGRESSIVO_PLUS", rng)
    print("Edge Napoli km+:", a3)

    a4 = genera_indirizzo_estero("Francia", rng)
    print("Estero Francia:", a4)

    a5 = genera_indirizzo_edge_it("Bolzano", "BILINGUE_DE", rng)
    print("Edge bilingue:", a5)

    print("OK - address_generator smoke test")
