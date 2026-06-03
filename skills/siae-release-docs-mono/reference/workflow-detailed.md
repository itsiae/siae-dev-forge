# Workflow Dettagliato - Release Docs Mono

Workflow operativo step-by-step. Ogni step descrive **come** la skill mono
esegue inline la logica che nelle 5 skill specializzate vive separata.

Per snippet di codice puntuali, vedi le reference dettagliate:
- [ndr-generator-dl/reference/docx-generation.md](../../ndr-generator-dl/reference/docx-generation.md)
- [ndr-generator/reference/docx-generation.md](../../ndr-generator/reference/docx-generation.md)
- [gdc-generator/reference/pptx-generation.md](../../gdc-generator/reference/pptx-generation.md)
- [architecture-slides-generator/reference/slide-template-rules.md](../../architecture-slides-generator/reference/slide-template-rules.md)
- [dde-generator/reference/docx-append.md](../../dde-generator/reference/docx-append.md)

## Orchestrazione complessiva

```
┌─────────────────────────────────────────────────────────────────┐
│ Step 0: Carica YAML + validazione (V01-V42 + C01-C06)           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: Localizza master files + backup automatico              │
│  - NDR DL ref, NDR RS ref, GDC prev, DDE master, Arch master    │
└─────────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
        ┌────────────┐ ┌────────────┐ ┌────────────┐
        │ Step 2     │ │ Step 3     │ │ Step 4     │
        │ NDR DL     │ │ NDR RS     │ │ GDC        │
        │ (se DL=T)  │ │ (se RS=T)  │ │ (sempre)   │
        └────────────┘ └────────────┘ └────────────┘
                │             │             │
                └─────────────┴─────────────┘
                              │
                              ▼
                ┌─────────────────────────────┐
                │ Step 5: Architettura + PNG  │
                │ (genera input per Step 6)   │
                └─────────────────────────────┘
                              │
                              ▼
                ┌─────────────────────────────┐
                │ Step 6: DDE                 │
                │ (embed PNG, append cap,     │
                │  update tabella finale,     │
                │  update tabella revisioni)  │
                └─────────────────────────────┘
                              │
                              ▼
                ┌─────────────────────────────┐
                │ Step 7: Verifica cross-doc  │
                │ + report finale             │
                └─────────────────────────────┘
```

## Step 0 - Carica YAML + validazione

```python
import yaml
from pathlib import Path

with open(yaml_path, encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

# Esegui validazioni V01-V42 e C01-C06 (vedi yaml-schema-validation.md)
errors = validate_yaml(cfg)
if errors:
    for e in errors:
        print(f"❌ {e}")
    raise SystemExit("Sistemare lo YAML prima di proseguire.")

# Stampa matrice generazione
print(f"Layer DL: {'SI' if cfg['layer_impattati']['data_lake'] else 'NO'}")
print(f"Layer RS: {'SI' if cfg['layer_impattati']['redshift'] else 'NO'}")
print(f"Output dir: {cfg['release']['output_dir']}")
```

## Step 1 - Localizza master + backup

```python
import shutil
from datetime import datetime

BASE = Path(r"C:\Users\frmonaco\Downloads\Claude documentazione")

def pick_latest(directory: Path, pattern: str) -> Path:
    """File piu' recente per data modifica."""
    files = sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None

NDR_DL_REF  = pick_latest(BASE / "NDR DL", "*.docx")
NDR_RS_REF  = pick_latest(BASE / "NDR", "*.docx")
GDC_REF     = BASE / "GDC" / "DMND000XXXXX - GDC - AWS Data Platform - EDW_XX_XX_TEST.pptx"
GDC_PREV    = pick_latest(BASE / "GDC", "DMND0*.pptx")
DDE_MASTER  = pick_latest(BASE / "DDE", "DDE-DataPlatform-Ingestion-*.docx")
ARCH_PPTX   = BASE / "Architettura DDE" / "DdE - Architettura - New.pptx"

# Backup
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_dir = Path(cfg['release']['output_dir']) / "backups"
backup_dir.mkdir(parents=True, exist_ok=True)
shutil.copy2(DDE_MASTER, backup_dir / f"{DDE_MASTER.stem}_backup_{ts}.docx")
shutil.copy2(ARCH_PPTX,  backup_dir / f"{ARCH_PPTX.stem}_backup_{ts}.pptx")
```

## Step 2 - Genera NDR DL (se DL=true)

Skip se `layer_impattati.data_lake=false`.

```python
if not cfg['layer_impattati']['data_lake']:
    print("Layer DL non impattato, skip Step 2 (NDR DL)")
else:
    # Output filename (WAVE maiuscolo per DL)
    fname = (f"{cfg['release']['dmnd_id']} - NDR - EDW Data Lake - "
             f"EDW_{cfg['release']['edw_release']}_DL")
    if cfg['release'].get('wave'):
        wave_n = cfg['release']['wave'].split()[-1]
        fname += f" - WAVE {wave_n}"
    output_ndr_dl = Path(cfg['release']['output_dir']) / f"{fname}.docx"

    # Copia NDR DL ref come base
    shutil.copy2(NDR_DL_REF, output_ndr_dl)

    # Applica modifiche inline (riusa pattern documentati in ndr-generator-dl/reference)
    from docx import Document
    doc = Document(str(output_ndr_dl))

    # Front-matter (Table 1, Table 3)
    update_ambito_table(doc, cfg)            # Table 1
    update_demand_table(doc, cfg)            # Table 3 (LL12)
    update_pacchetto_table(doc, cfg)         # Table 4 (LL5, LL DL-H)

    # Sez 2.5.x varianti
    apply_section_25_variants(doc, cfg)

    # Sez 2.8.2 (LL DL-L + LL DL-A: clona blocco template, preserva indentazioni)
    update_section_282(doc, cfg)

    # Sez 3.1 TABLE #12 (LL DL-F + LL DL-J)
    update_section_31_filters(doc, cfg)

    # Sez 4.1 TABLE #13 + #14
    update_section_41_census(doc, cfg)

    # Table 10 monitoraggio (LL DL-M: clona da NDR DL precedente)
    update_table_10_monitoring(doc, NDR_DL_REF, cfg)

    # Page break standard (LL2)
    ensure_page_breaks_ndr_dl(doc)

    # Cleanup
    remove_residual_yellow_highlight(doc)
    strip_trailing_empty_paragraphs(doc)

    doc.save(output_ndr_dl)
    print(f"✅ NDR DL generato: {output_ndr_dl.name}")
```

## Step 3 - Genera NDR RS (se RS=true)

```python
if not cfg['layer_impattati']['redshift']:
    print("Layer RS non impattato, skip Step 3 (NDR RS)")
else:
    fname = (f"{cfg['release']['dmnd_id']} - NDR - EDW Redshift - "
             f"EDW_{cfg['release']['edw_release']}_RS")
    if cfg['release'].get('wave'):
        wave_n = cfg['release']['wave'].split()[-1]
        fname += f" - Wave {wave_n}"  # mixed-case per RS
    output_ndr_rs = Path(cfg['release']['output_dir']) / f"{fname}.docx"

    shutil.copy2(NDR_RS_REF, output_ndr_rs)
    doc = Document(str(output_ndr_rs))

    # Front-matter
    update_ambito_table_rs(doc, cfg)
    update_demand_table_rs(doc, cfg)
    update_pacchetto_table_rs(doc, cfg)

    # Sez 1.1 tabella QVD (LL13: SEMPRE presente)
    update_qvd_table(doc, cfg)  # Anche se tutti N.A.

    # Sez 4.2 tabella oggetti con shading alternato (LL7)
    update_section_42_objects(doc, cfg)

    apply_section_25_variants_rs(doc, cfg)
    ensure_page_breaks_ndr_rs(doc)
    remove_residual_yellow_highlight(doc)

    doc.save(output_ndr_rs)
    print(f"✅ NDR RS generato: {output_ndr_rs.name}")
```

## Step 4 - Genera GDC

```python
fname = (f"{cfg['release']['dmnd_id']} - GDC - AWS Data Platform - "
         f"EDW_{cfg['release']['edw_release']}")
if cfg['release'].get('wave'):
    wave_n = cfg['release']['wave'].split()[-1]
    fname += f" - Wave {wave_n}"
output_gdc = Path(cfg['release']['output_dir']) / f"{fname}.pptx"

# Base = GDC precedente (per lista cumulativa DB Glue/schemi)
shutil.copy2(GDC_PREV, output_gdc)

from pptx import Presentation
prs = Presentation(str(output_gdc))

# Slide 1 - tabella conteggi (LL2 per indice di riga) + narrativa (LL25)
update_slide_1(prs, cfg)

# Slide 2 - architettura (manuale, flag) (LL11, LL18)
flag_slide_2_for_manual(prs)

# Slide 3 - CDC: testo + "(RIC):" con due punti (LL9 + LL34)
update_slide_3(prs, cfg)

# Slide 4 - profilazioni (boilerplate)
# Slide 5 - Rilasci propedeutici (LL33: ordine slide 5 prima di 6)
update_slide_5_rilasci_propedeutici(prs, cfg)
# Slide 6 - Gruppi firewall (LL33: dopo slide 5)
update_slide_6_firewall(prs, cfg)

# Slide 7 - Deploy repo Git (LL28, LL29)
update_slide_7(prs, cfg)

# Slide 8-11 - tabelle cumulative DB Glue/stg/etc. (LL14, LL20)
update_slide_8(prs, cfg)
update_slide_9(prs, cfg)
update_slide_10(prs, cfg)
update_slide_11(prs, cfg)

# Slide 12 - Qlik (rimuovi tabelle se QK non impattato - LL24)
update_slide_12(prs, cfg)

# Slide 13 - path NAS (LL4 highlight + LL32 -Qlik compatto)
update_slide_13(prs, cfg)

prs.save(output_gdc)
print(f"✅ GDC generata: {output_gdc.name}")
```

## Step 5 - Genera slide architettura + PNG

```python
# Step 5.0 - validazione host (LL ARCH-10)
for src in cfg['architecture']['new_sources']:
    if src.get('host') in (None, "", "TBD", "tbd"):
        raise ValueError(
            f"LL ARCH-10: host null/TBD per sorgente {src['name']!r}. "
            f"Compila lo YAML o conferma 'N.A.' esplicito."
        )

arch_output = Path(cfg['architecture']['source_pptx']).parent / cfg['architecture']['output_pptx']
shutil.copy2(cfg['architecture']['source_pptx'], arch_output)

prs = Presentation(str(arch_output))

# Step 5.1 - clona slide template DL (se DL impattato)
if cfg['layer_impattati']['data_lake']:
    tpl_idx = cfg['architecture']['template_slides']['DL']['slide_number'] - 1
    new_slide_dl = clone_slide(prs, tpl_idx)
    update_release_code(new_slide_dl, cfg, layer='DL')      # CasellaDiTesto 1
    update_acquisizione(new_slide_dl, cfg)                  # CasellaDiTesto 17
    add_new_source_group(new_slide_dl, cfg)                 # CODIFICA group
    move_oval_to_new_source(new_slide_dl, cfg, layer='DL')  # Oval su CODIFICA
    # LL ARCH-9: sposta slide in fondo al blocco DL
    move_slide_to_end_of_layer(prs, new_slide_dl, layer='DL')

# Step 5.2 - clona slide template RS (se RS impattato)
if cfg['layer_impattati']['redshift']:
    tpl_idx = cfg['architecture']['template_slides']['RS']['slide_number'] - 1
    new_slide_rs = clone_slide(prs, tpl_idx)
    update_release_code(new_slide_rs, cfg, layer='RS')
    update_acquisizione(new_slide_rs, cfg)
    add_new_source_group(new_slide_rs, cfg)
    keep_oval_on_redshift(new_slide_rs)                     # LL ARCH RS pattern fisso
    move_slide_to_end_of_layer(prs, new_slide_rs, layer='RS')

prs.save(arch_output)

# Step 5.3 - Esporta PNG via PowerPoint COM
import win32com.client
png_dl = Path(cfg['architecture']['screenshots']['out_dir']) / cfg['architecture']['screenshots']['DL_filename']
png_rs = Path(cfg['architecture']['screenshots']['out_dir']) / cfg['architecture']['screenshots']['RS_filename']
png_dl.parent.mkdir(parents=True, exist_ok=True)

ppt_app = win32com.client.Dispatch("PowerPoint.Application")
pptx_com = ppt_app.Presentations.Open(str(arch_output.resolve()), WithWindow=False)
slide_w = pptx_com.PageSetup.SlideWidth
slide_h = pptx_com.PageSetup.SlideHeight
height_px = int(cfg['architecture']['screenshots']['width_px'] * slide_h / slide_w)

if cfg['layer_impattati']['data_lake']:
    new_dl_idx = find_slide_index_by_release(prs, layer='DL', release=cfg['release']['edw_release'], wave=cfg['release'].get('wave'))
    pptx_com.Slides(new_dl_idx + 1).Export(str(png_dl.resolve()), "PNG", cfg['architecture']['screenshots']['width_px'], height_px)

if cfg['layer_impattati']['redshift']:
    new_rs_idx = find_slide_index_by_release(prs, layer='RS', release=cfg['release']['edw_release'], wave=cfg['release'].get('wave'))
    pptx_com.Slides(new_rs_idx + 1).Export(str(png_rs.resolve()), "PNG", cfg['architecture']['screenshots']['width_px'], height_px)

pptx_com.Close()
ppt_app.Quit()

print(f"✅ Architettura pptx: {arch_output.name}")
print(f"✅ PNG DL: {png_dl.name} ({png_dl.stat().st_size // 1024} KB)")
print(f"✅ PNG RS: {png_rs.name} ({png_rs.stat().st_size // 1024} KB)")
```

## Step 6 - Genera capitoli DDE

```python
from docx import Document

# Step 6.0 - LL DDE-24: verifica gap capitoli vs documenti su disco
gaps = verify_chapter_alignment(DDE_MASTER, base_dir=BASE)
if gaps:
    print("⚠️  LL DDE-24: rilasci documentati ma non in DDE master:")
    for g in gaps:
        print(f"   - {g}")
    # Pre-flight card al partner: recupera o salta?

doc = Document(str(DDE_MASTER))

# Step 6.1 - Determina prossimo numero capitolo (LL DDE-6: dalla tabella revisioni)
next_n = get_max_chapter_n_from_revisions(doc) + 1

# Step 6.2 - Genera cap DL (se DL impattato)
if cfg['layer_impattati']['data_lake']:
    # Clona blocco cap DL template (LL DDE-2: usa cap DL recente)
    dl_template_name = find_template_chapter(doc, layer='DL')
    cloned_dl = clone_chapter_block(doc, dl_template_name)

    # Sostituisci stringhe
    rebuild_heading_in_block(cloned_dl, f"{cfg['release']['dmnd_id']} – EDW_{cfg['release']['edw_release']}_DL – WAVE {wave_n}")
    replace_narrative_in_block(cloned_dl, cfg)
    update_pacchetto_table_in_block(cloned_dl, cfg)
    update_qvd_table_in_block(cloned_dl, cfg)

    # LL DDE-21: tabella monitoraggio cumulativa - clona da cap DL precedente
    prev_dl_chap_h1 = get_last_dl_chapter(doc, exclude=cloned_dl)
    monitoring_tbl = clone_monitoring_filter_table_from_prev_dl_chapter(doc, prev_dl_chap_h1)
    append_filter_rows_for_new_source(monitoring_tbl, cfg)
    replace_monitoring_table_in_block(cloned_dl, monitoring_tbl)

    # LL DDE-23: embed PNG architettura
    replace_placeholder_with_image(cloned_dl, "[placeholder architettura]", png_dl, width_cm=16)

    # Inserisci blocco prima di APPENDICE
    insert_block_before_appendice(doc, cloned_dl)

    # Aggiungi riga tabella revisioni
    insert_revision_row(doc, cap_n=next_n, layer='DL', cfg=cfg)
    next_n += 1

# Step 6.3 - Genera cap RS (se RS impattato)
if cfg['layer_impattati']['redshift']:
    rs_template_name = find_template_chapter(doc, layer='RS')
    cloned_rs = clone_chapter_block(doc, rs_template_name)

    rebuild_heading_in_block(cloned_rs, f"{cfg['release']['dmnd_id']} – EDW_{cfg['release']['edw_release']}_RS – WAVE {wave_n}")
    replace_narrative_in_block(cloned_rs, cfg)
    update_pacchetto_table_in_block_rs(cloned_rs, cfg)
    update_qvd_table_in_block_rs(cloned_rs, cfg)

    # Tabella oggetti rilasciati (clona dalla NDR RS sez 4.2 - LL DDE-18)
    objects_tbl = clone_objects_table_from_ndr_rs(output_ndr_rs)
    replace_objects_table_in_block(cloned_rs, objects_tbl)

    # LL DDE-23: embed PNG architettura RS
    replace_placeholder_with_image(cloned_rs, "[placeholder immagine]", png_rs, width_cm=16)

    insert_block_before_appendice(doc, cloned_rs)
    insert_revision_row(doc, cap_n=next_n, layer='RS', cfg=cfg)

# Step 6.4 - LL DDE-22: append righe alla tabella finale cumulativa
lista_tab_finale = find_lista_tabelle_finale(doc)
for entry in cfg['dde']['lista_tabelle_rilascio']:
    append_row_lista_tabelle(lista_tab_finale, entry)

# Salva
doc.save(DDE_MASTER)
print(f"✅ DDE aggiornato: {DDE_MASTER.name}")
```

## Step 7 - Verifica cross-doc + report finale

```python
# Riapri tutti i file e verifica coerenza
mismatches = []

# C01-C02: dmnd_id, edw_release identici in 5 doc
expected = {'dmnd_id': cfg['release']['dmnd_id'], 'edw_release': cfg['release']['edw_release']}

for path in [output_ndr_dl, output_ndr_rs, output_gdc, arch_output, DDE_MASTER]:
    actual = extract_metadata(path)
    for k, v in expected.items():
        if actual.get(k) != v:
            mismatches.append(f"{path.name}: {k}={actual.get(k)!r} (atteso {v!r})")

# C05: len(oggetti_redshift NDR) == righe DDE Riepilogo cap RS
if cfg['layer_impattati']['redshift']:
    n_ndr = count_objects_in_ndr_rs_42(output_ndr_rs)
    n_dde = count_objects_in_dde_riepilogo(DDE_MASTER, layer='RS', release=cfg['release']['edw_release'])
    if n_ndr != n_dde:
        mismatches.append(f"NDR RS sez 4.2 = {n_ndr} oggetti, DDE cap RS Riepilogo = {n_dde}. Devono essere identici.")

# Placeholder residui in tutti i file
for path in [output_ndr_dl, output_ndr_rs, output_gdc, DDE_MASTER]:
    residui = scan_placeholders(path)
    for r in residui:
        mismatches.append(f"{path.name}: placeholder residuo {r!r}")

# Report finale
print("\n" + "=" * 70)
print("REPORT GENERAZIONE COMPLETA")
print("=" * 70)
print(f"NDR DL:    {output_ndr_dl.name if cfg['layer_impattati']['data_lake'] else '(skipped)'}")
print(f"NDR RS:    {output_ndr_rs.name if cfg['layer_impattati']['redshift'] else '(skipped)'}")
print(f"GDC:       {output_gdc.name}")
print(f"Arch pptx: {arch_output.name}")
print(f"DDE:       {DDE_MASTER.name}")
if cfg['layer_impattati']['data_lake']:
    print(f"PNG DL:    {png_dl.name}")
if cfg['layer_impattati']['redshift']:
    print(f"PNG RS:    {png_rs.name}")

if mismatches:
    print("\n⚠️  COERENZA CROSS-DOC: PROBLEMI RILEVATI")
    for m in mismatches:
        print(f"   - {m}")
else:
    print("\n✅ Coerenza cross-doc: OK")

print("\nOPERAZIONI MANUALI:")
print("  1. GDC: rivedi slide 2 architettura (sempre manuale)")
print("  2. Arch pptx: disegna connettori DMS -> nuova sorgente (LL ARCH-1)")
print("  3. DDE: aggiorna TOC (click destro INDICE -> Aggiorna campo)")
print("  4. DDE: compila colonna 'Pagina' tabella revisioni (post-render PDF)")
print("  5. NDR DL/RS: verifica nessun highlight giallo residuo")
```

## Note di implementazione

- **Helper functions** menzionate (es. `update_ambito_table`, `clone_chapter_block`,
  `replace_placeholder_with_image`) sono documentate nelle reference delle 5 skill
  esistenti. La mono **non re-implementa**, ma **incolla inline** quei pattern.
- Se durante l'esecuzione una funzione manca o un pattern non e' documentato,
  consulta la skill specifica corrispondente. Le LL sono il "library di funzioni"
  della mono.
- **Fail-fast policy**: se uno step fallisce, **interrompi** l'esecuzione e
  segnala al partner. Output parziali sono peggio di nessun output.
