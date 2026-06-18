#!/usr/bin/env python3
"""
check_fidelity.py — Confronta un MTP generato con il template canonico.
Uso: python3 check_fidelity.py <output.docx> <template.docx>

Verifica: heading presenti, colore Titolo2, tabella Piattaforme 3 colonne,
          TOC presente, updateFields, media.

NOTA: lo SmartArt del template viene intenzionalmente SOSTITUITO da una tabella
3 colonne scalabile nell'output. Il check NON verifica nodi SmartArt invariati.

Exit 0 = OK, Exit 1 = scostamenti trovati.
"""

import sys
import zipfile
import xml.etree.ElementTree as ET
NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

EXPECTED_HEADINGS = [
    "Obiettivi del Progetto",
    "Test Design",
    "Perimetro",
    "Obiettivi e livelli del test",
    "Performance test",
    "NRT",
    "Test Automatici",
    "GANTT",
    "Out of Scope",
    "Rischi",
]
EXPECTED_HEADING_COLOR = "2F5496"
# Intestazioni attese nella tabella 3 colonne che sostituisce lo SmartArt
EXPECTED_TABLE_HEADERS = {"Piattaforme", "Piattaforme Modificate", "Sistemi Impattati"}


def extract_xml(docx_path, member):
    try:
        with zipfile.ZipFile(str(docx_path), "r") as z:
            return z.read(member).decode("utf-8", errors="replace")
    except (KeyError, Exception):
        return None


def get_heading_texts(doc_xml):
    root = ET.fromstring(doc_xml)
    results = []
    for para in root.iter(f"{{{NS_W}}}p"):
        pPr = para.find(f"{{{NS_W}}}pPr")
        if pPr is None:
            continue
        pStyle = pPr.find(f"{{{NS_W}}}pStyle")
        if pStyle is None:
            continue
        style_val = pStyle.get(f"{{{NS_W}}}val", "")
        if "Titolo" in style_val or "Heading" in style_val:
            text = "".join(t.text or "" for t in para.iter(f"{{{NS_W}}}t"))
            if text.strip():
                results.append((style_val, text.strip()))
    return results


def get_titolo2_colors(doc_xml):
    root = ET.fromstring(doc_xml)
    colors = set()
    for para in root.iter(f"{{{NS_W}}}p"):
        pPr = para.find(f"{{{NS_W}}}pPr")
        if pPr is None:
            continue
        pStyle = pPr.find(f"{{{NS_W}}}pStyle")
        if pStyle is None:
            continue
        if "Titolo2" in pStyle.get(f"{{{NS_W}}}val", ""):
            for color in para.iter(f"{{{NS_W}}}color"):
                val = color.get(f"{{{NS_W}}}val", "")
                if val and val.upper() not in ("AUTO", "000000"):
                    colors.add(val.upper())
    return colors



def run_check(output_docx, template_docx):
    print(f"\n{'='*50}")
    print("VERIFICA FEDELTÀ")
    print(f"Output:   {output_docx}")
    print(f"Template: {template_docx}")
    print(f"{'='*50}")

    issues  = []
    ok_list = []

    # --- 1. document.xml esistente ---
    doc_xml = extract_xml(output_docx, "word/document.xml")
    if not doc_xml:
        print("ERRORE CRITICO: word/document.xml non trovato nell'output.")
        sys.exit(1)

    # --- 2. Heading attesi ---
    headings_out = get_heading_texts(doc_xml)
    texts_out    = [h[1] for h in headings_out]
    for expected in EXPECTED_HEADINGS:
        if any(expected.lower() in t.lower() for t in texts_out):
            ok_list.append(f"Heading '{expected}' presente")
        else:
            issues.append(f"Heading '{expected}' MANCANTE")

    # --- 3. Colore Titolo2 ---
    colors_out = get_titolo2_colors(doc_xml)
    if EXPECTED_HEADING_COLOR in colors_out:
        ok_list.append(f"Colore Titolo2 {EXPECTED_HEADING_COLOR} presente")
    else:
        tmpl_xml   = extract_xml(template_docx, "word/document.xml")
        colors_tmpl = get_titolo2_colors(tmpl_xml) if tmpl_xml else set()
        if colors_out and not colors_tmpl.isdisjoint(colors_out):
            ok_list.append(f"Colore Titolo2 coerente con template ({colors_out})")
        else:
            issues.append(f"Colore Titolo2: atteso {EXPECTED_HEADING_COLOR}, trovato {colors_out or 'nessuno'}")

    # --- 4. Tabella Piattaforme 3 colonne (sostituisce SmartArt) ---
    # Il documento generato deve avere almeno una tabella con le tre intestazioni
    # Piattaforme | Piattaforme Modificate | Sistemi Impattati nell'header row.
    table_headers_found = set()
    if doc_xml:
        root = ET.fromstring(doc_xml)
        for tbl in root.iter(f"{{{NS_W}}}tbl"):
            # Prima riga = header
            rows = list(tbl.iter(f"{{{NS_W}}}tr"))
            if not rows:
                continue
            first_row_texts = set()
            for cell in rows[0].iter(f"{{{NS_W}}}t"):
                if cell.text and cell.text.strip():
                    first_row_texts.add(cell.text.strip())
            if EXPECTED_TABLE_HEADERS.issubset(first_row_texts):
                table_headers_found = EXPECTED_TABLE_HEADERS
                break
            # Partial match: collect for debug
            table_headers_found |= first_row_texts & EXPECTED_TABLE_HEADERS

    if table_headers_found == EXPECTED_TABLE_HEADERS:
        ok_list.append("Tabella Piattaforme 3 colonne presente con intestazioni corrette")
    elif table_headers_found:
        issues.append(
            f"Tabella Piattaforme: trovate solo {table_headers_found}, "
            f"mancano {EXPECTED_TABLE_HEADERS - table_headers_found}"
        )
    else:
        issues.append(
            "Tabella Piattaforme 3 colonne NON trovata nel documento "
            "(SmartArt non sostituito correttamente)"
        )

    # --- 6. TOC presente ---
    if "TOC" in doc_xml or "Sommario" in doc_xml:
        ok_list.append("Campo TOC/Sommario presente")
    else:
        issues.append("Campo TOC MANCANTE nel documento")

    # --- 7. updateFields ---
    settings_out = extract_xml(output_docx, "word/settings.xml")
    if settings_out and "updateFields" in settings_out:
        ok_list.append("updateFields presente in settings.xml")
    else:
        issues.append("updateFields MANCANTE in settings.xml (il TOC non si aggiornerà)")

    # --- 8. Media (logo) ---
    try:
        with zipfile.ZipFile(str(output_docx), "r") as z:
            media = [n for n in z.namelist() if n.startswith("word/media/")]
        if media:
            ok_list.append(f"Media presenti: {len(media)} file (logo incluso)")
        else:
            issues.append("Nessun file media — logo SIAE potrebbe mancare")
    except Exception as ex:
        issues.append(f"Errore lettura media: {ex}")

    # --- Report ---
    print(f"\nCheck superati ({len(ok_list)}):")
    for item in ok_list:
        print(f"  ✓ {item}")

    if issues:
        print(f"\nScostamenti rilevati ({len(issues)}):")
        for item in issues:
            print(f"  ✗ {item}")
        print(
            "\n→ SCOSTAMENTI TROVATI. "
            "Mostrare l'elenco all'utente e chiedere se accettare o rigenerare."
        )
        return False
    else:
        print("\n✓ FEDELTÀ OK — nessuno scostamento non atteso rilevato.")
        return True


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Uso: {sys.argv[0]} <output.docx> <template.docx>")
        sys.exit(1)

    ok = run_check(sys.argv[1], sys.argv[2])
    sys.exit(0 if ok else 1)
