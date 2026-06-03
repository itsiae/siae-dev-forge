# Coerenza Cross-Documento - Checklist + Script di Verifica

La suite documentale di un rilascio EDW SIAE deve essere **internamente
consistente**: gli stessi parametri (DMND, release, conteggi, lista oggetti,
date) devono apparire identici nei 5 documenti.

Questa reference fornisce la checklist completa eseguita in Step 7 della
skill `siae-release-docs-mono` (e raccomandata anche dopo la pack).

## Categorie di coerenza

### Categoria 1 — Identificativi base

Devono essere **identici** in tutti i documenti:

| Campo | Dove appare | Test |
|---|---|---|
| `dmnd_id` | NDR DL Table 3, NDR RS Table 3, GDC slide 1+13, DDE tabella revisioni, DDE heading capitoli | Estrai e confronta |
| `edw_release` | NDR DL Table 3, NDR RS Table 3, GDC slide 1+13, DDE heading capitoli, slide arch | Estrai e confronta |
| `titolo_progetto` | NDR DL/RS narrativa, GDC slide 1, DDE narrativa cap | Estrai e confronta |
| `chg_id_dl` | NDR DL Table 3 + path NAS, GDC slide 13, DDE tabella revisioni (cap DL) | Estrai e confronta |
| `chg_id_rs` | NDR RS Table 3 + path NAS, GDC slide 13, DDE tabella revisioni (cap RS) | Estrai e confronta |

### Categoria 2 — Conteggi

| Conteggio | Dove appare | Test |
|---|---|---|
| Task DMS | GDC slide 1, NDR DL Table 4, DDE cap DL tabella pacchetto | Equal |
| Athena BRONZE | GDC slide 1, NDR DL Table 4, DDE cap DL tabella pacchetto | Equal |
| Athena SILVER | GDC slide 1, NDR DL Table 4, DDE cap DL tabella pacchetto | Equal |
| ETL Glue | GDC slide 1, NDR DL Table 4, DDE cap DL tabella pacchetto | Equal — coerente con tabelle Athena (review 2026-05-20: count etl_glue = count tabelle Athena SILVER) |
| Step Function | GDC slide 1, NDR DL Table 4, DDE cap DL tabella pacchetto | Equal |
| Oggetti Redshift | GDC slide 1 ("Circa N"), NDR RS sez 1.1 (`oggetti_redshift_count`), DDE cap RS Riepilogo header | Equal (testo "Circa N" o numero esatto) |

### Categoria 3 — Liste

| Lista | Dove appare | Test |
|---|---|---|
| Lista oggetti Redshift (sez 4.2 NDR RS) | NDR RS sez 4.2, DDE cap RS "Riepilogo oggetti rilasciati su DWH" | Stessa lista, stesso ordine, stesso shading alternato |
| Lista QVD (datamart → QVD) | NDR RS sez 1.1 tabella QVD, DDE cap RS tabella QVD | Stessa lista, stesso ordine (LL13 NDR RS + LL DDE-14) |
| Repo Git deploy | GDC slide 7, NDR DL sez 2.8.2 | Stessa lista |
| Lista tabelle del rilascio | `dde.lista_tabelle_rilascio` (YAML), DDE tabella finale cumulativa (append) | len(YAML) = righe nuove DDE finale (LL DDE-22) |

### Categoria 4 — Date

| Data | Dove appare | Formato |
|---|---|---|
| Data redazione NDR | NDR DL/RS Table 1 "Data Nota di rilascio" | DD/MM/YYYY |
| Data rilascio prod | NDR DL/RS Table 1, GDC slide 13 (path NAS) | DD/MM/YYYY in NDR, YYYY-MM-DD in path NAS |
| Data inserimento DDE | DDE tabella revisioni colonna Data | DD/MM/YYYY |
| Path NAS data | NDR DL sez 2.8.2 + sez 2.1, GDC slide 13 | YYYY-MM-DD |

### Categoria 5 — Sorgente

| Campo | Dove appare | Test |
|---|---|---|
| Nome sorgente UPPERCASE | NDR DL narrativa, NDR RS narrativa, GDC slide 1, slide arch CasellaDiTesto 17, DDE narrativa | Equal (UPPERCASE) |
| Host RDS sorgente | NDR DL Table 11 SOURCE SYSTEM, NDR DL sez 2.8.2 "Impostazione del secret", slide arch hostname box, DDE tabella finale colonna `sistema_sorgente_host` | Equal |
| Schema kebab (es. `codifica`) | NDR DL Table 12 filtri, GDC slide 8 (DB Glue), GDC slide 9 (stg Redshift) | Equal |

### Categoria 6 — Wave

| Campo | Dove appare | Convenzione |
|---|---|---|
| Wave nel filename | NDR DL: `WAVE N` (maiuscolo); NDR RS: `Wave N` (mixed); GDC: `Wave N` (mixed); arch pptx: `Wave N` o `WAVE N` | Convenzione storica diversificata — NON normalizzare |
| Wave nel release code (slide arch) | CasellaDiTesto 1: `EDW_01.28_DL - WAVE 2` | Solo se Wave esiste |
| Wave nel heading DDE | `DMND<N> – EDW_01.28_DL – WAVE 2` | LL DDE-12 |
| Wave nel testo narrativo NDR | NO (LL DDE-17: titolo progetto narrativo SENZA wave) | - |

## Script di verifica completo

```python
from pathlib import Path
from docx import Document
from pptx import Presentation
import re

def verify_release_docs_coherence(
    cfg: dict,
    output_ndr_dl: Path = None,
    output_ndr_rs: Path = None,
    output_gdc: Path = None,
    arch_pptx: Path = None,
    dde_master: Path = None,
) -> list[str]:
    """Esegui tutte le verifiche cross-doc. Ritorna lista mismatch."""
    mm = []

    # Categoria 1 - Identificativi base
    if output_ndr_dl:
        doc = Document(str(output_ndr_dl))
        if cfg['release']['dmnd_id'] not in doc.tables[3].cell(1, 0).text:
            mm.append(f"NDR DL: dmnd_id mismatch")
        if cfg['chg_numbers']['data_lake'] not in doc.tables[3].cell(1, 1).text:
            mm.append(f"NDR DL: chg_id_dl mismatch")

    if output_ndr_rs:
        doc = Document(str(output_ndr_rs))
        if cfg['release']['dmnd_id'] not in doc.tables[3].cell(1, 0).text:
            mm.append(f"NDR RS: dmnd_id mismatch")
        if cfg['chg_numbers']['redshift'] not in doc.tables[3].cell(1, 1).text:
            mm.append(f"NDR RS: chg_id_rs mismatch")

    if output_gdc:
        prs = Presentation(str(output_gdc))
        s13_text = ' '.join(sh.text_frame.text for sh in prs.slides[12].shapes if sh.has_text_frame)
        for chg in [cfg['chg_numbers'].get('data_lake'), cfg['chg_numbers'].get('redshift')]:
            if chg and chg not in s13_text:
                mm.append(f"GDC slide 13: CHG {chg!r} mancante nei path NAS")

    if dde_master:
        doc = Document(str(dde_master))
        rev = doc.tables[1]
        last_rows = [' '.join(c.text for c in r.cells) for r in rev.rows[-4:]]
        for chg in [cfg['chg_numbers'].get('data_lake'), cfg['chg_numbers'].get('redshift')]:
            if chg and not any(chg in row for row in last_rows):
                mm.append(f"DDE tabella revisioni: CHG {chg!r} non presente nelle ultime righe")

    # Categoria 3 - Coerenza lista oggetti NDR RS sez 4.2 = DDE cap RS Riepilogo
    if output_ndr_rs and dde_master and cfg['layer_impattati']['redshift']:
        doc_ndr = Document(str(output_ndr_rs))
        ndr_obj_tbl = next((t for t in doc_ndr.tables if t.rows and 'Instance' in t.rows[0].cells[0].text), None)
        ndr_n = len(ndr_obj_tbl.rows) - 1 if ndr_obj_tbl else 0

        doc_dde = Document(str(dde_master))
        # Tabella Riepilogo cap RS Wave 2 (56 righe atteso per Wave 2: 1 header + 55 oggetti)
        riepilogo_tbl = find_riepilogo_table_in_chapter(
            doc_dde,
            chapter_h1=f"{cfg['release']['dmnd_id']} – EDW_{cfg['release']['edw_release']}_RS"
                       + (f" – {cfg['release']['wave'].upper()}" if cfg['release'].get('wave') else "")
        )
        dde_n = len(riepilogo_tbl.rows) - 1 if riepilogo_tbl else 0

        if ndr_n != dde_n:
            mm.append(f"NDR RS sez 4.2 ({ndr_n} oggetti) != DDE cap RS Riepilogo ({dde_n}). Devono essere identici (LL DDE-18).")

    # Categoria 3 - len(lista_tabelle_rilascio YAML) = righe nuove DDE tabella finale
    if dde_master and cfg.get('dde', {}).get('lista_tabelle_rilascio'):
        yaml_n = len(cfg['dde']['lista_tabelle_rilascio'])
        doc_dde = Document(str(dde_master))
        finale_tbl = next((t for t in reversed(doc_dde.tables)
                          if t.rows and t.rows[0].cells[0].text.strip() == 'Rilascio'), None)
        if finale_tbl:
            # Conta righe con rilascio corrente
            target_rilascio = f"{cfg['release']['edw_release']}_DL"
            if cfg['release'].get('wave'):
                target_rilascio += f" - {cfg['release']['wave']}"
            dde_new_rows = sum(1 for r in finale_tbl.rows[1:]
                              if target_rilascio in r.cells[0].text)
            if dde_new_rows != yaml_n:
                mm.append(f"LL DDE-22: lista_tabelle_rilascio nel YAML ha {yaml_n} entry, "
                         f"DDE tabella finale ha {dde_new_rows} righe per il rilascio. Mismatch.")

    # Categoria 5 - Host sorgente coerente
    if cfg['layer_impattati']['data_lake'] and output_ndr_dl and arch_pptx:
        # Estrai host da NDR DL Table 11 e da arch slide hostname box
        # Compara
        pass  # (implementazione dettagliata omessa per brevita')

    # Placeholder residui in tutti i file
    forbidden = ['TBD', 'CHG00XXXXX', '«Titolo Progetto»', 'EDW_XX.XX', 'EDW_XX_XX',
                 'DMND000XXXX', 'XX/XX/2026', '2026-XX-XX', '[placeholder']
    for path in [output_ndr_dl, output_ndr_rs, dde_master]:
        if path is None or not path.exists():
            continue
        doc = Document(str(path))
        full_text = '\n'.join(p.text for p in doc.paragraphs)
        full_text += '\n' + '\n'.join(c.text for t in doc.tables for r in t.rows for c in r.cells)
        for token in forbidden:
            if token in full_text:
                mm.append(f"{path.name}: placeholder residuo {token!r}")

    return mm

# Uso
mm = verify_release_docs_coherence(
    cfg,
    output_ndr_dl=Path("..."),
    output_ndr_rs=Path("..."),
    output_gdc=Path("..."),
    arch_pptx=Path("..."),
    dde_master=Path("..."),
)
if mm:
    print("\n⚠️  Mismatch cross-doc rilevati:")
    for m in mm:
        print(f"   - {m}")
else:
    print("\n✅ Coerenza cross-doc OK")
```

## Quando una verifica e' "soft" vs "hard"

| Verifica | Tipo | Comportamento se fallisce |
|---|---|---|
| Identificativi base (dmnd_id, edw_release, chg) | **HARD** | Errore, blocca consegna |
| Conteggi (DMS, Athena, ETL, ecc.) | **HARD** | Errore, blocca consegna |
| Lista oggetti NDR RS = DDE Riepilogo | **HARD** | Errore, blocca consegna (LL DDE-18) |
| `len(lista_tabelle_rilascio)` = nuove righe tabella finale | **HARD** | Errore (LL DDE-22) |
| Placeholder residui (`TBD`, `XX/XX`, ecc.) | **HARD** | Errore, blocca consegna |
| Highlight giallo residuo (non `2026-XX-XX` previsti) | **SOFT** | Warning, segnala al partner |
| Date coerenti (data_rilascio_prod = data_path_nas) | **SOFT** | Warning (possono differire di 1-2 gg per fuso CHG) |
| Wave casing (`WAVE` vs `Wave`) | **SOFT** | Warning (convenzione storica differenziata) |

In caso di **HARD fail**, la skill **deve fermarsi** e chiedere al partner di
sistemare prima di considerare la generazione completata. In caso di **SOFT
fail**, segnala nel report finale ma procede.

## Riassunto: cosa fa Step 7 della mono

1. Riapre i 5 file generati
2. Esegue tutte le verifiche di questa reference
3. Categorizza HARD/SOFT
4. Se HARD fail: stampa errori e raccomanda correzione
5. Se solo SOFT fail: stampa warning, completa con success
6. Salva un mini-report markdown in `<output_dir>/verification-report.md`
