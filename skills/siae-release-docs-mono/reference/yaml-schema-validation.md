# Schema YAML Unificato + Validazioni Semantiche

Schema YAML completo per `siae-release-docs-mono`. Unifica i parametri delle
5 skill specializzate in un singolo manifesto.

Per i dettagli delle singole sezioni, vedi:
- [ndr-generator-dl/reference/input-schema.md](../../ndr-generator-dl/reference/input-schema.md)
- [ndr-generator/reference/input-schema.md](../../ndr-generator/reference/input-schema.md)
- [gdc-generator/reference/input-schema.md](../../gdc-generator/reference/input-schema.md)
- [architecture-slides-generator/reference/yaml-schema.md](../../architecture-slides-generator/reference/yaml-schema.md)
- [dde-generator/reference/input-schema.md](../../dde-generator/reference/input-schema.md)

## Top-level structure

```yaml
release:
  edw_release: "01.28"                 # [tutti]
  dmnd_id: "DMND0006343"               # [tutti]
  titolo_progetto: "Visibilita' dato nuovo modulo codifica..."
  wave: "Wave 2"                        # [tutti] o null se non Wave
  data_redazione_ndr: "18/05/2026"     # [NDR]
  data_inserimento_dde: "18/05/2026"   # [DDE]
  data_rilascio_prod: "27/05/2026"     # [NDR][GDC]
  data_path_nas: "2026-05-27"          # [NDR][GDC]
  redatto_da: "F. Monaco"              # [NDR]
  output_dir: "C:/.../Execution 1/output"  # [tutti] dove scrivere gli output

layer_impattati:
  data_lake: true                       # se true → genera NDR DL, cap DL DDE, slide arch DL
  redshift: true                        # se true → genera NDR RS, cap RS DDE, slide arch RS
  qlik: false                           # [GDC] solo per slide 12 GDC, nessun cap DDE

chg_numbers:
  data_lake: "CHG0067486"               # obbligatorio se layer_impattati.data_lake
  redshift: "CHG0067484"                # obbligatorio se layer_impattati.redshift
  qlik: null

sorgente:
  display_gdc: "Codifica (RDS)"         # [GDC slide 1]
  nome_uppercase: "CODIFICA"            # [NDR][DDE]
  tipo_db: "RDS"                        # [GDC]
  is_nuova_sorgente: true               # [DDE] - rilevante per tabella monitoraggio
  schema_kebab: "codifica"              # [NDR DL TABLE #12 - LL DL-J]
  schemi_glue_nuovi: ["codifica"]       # [GDC slide 8]
  schema_stg_redshift_nuovo: "codifica" # [GDC slide 9]

narrativa:
  pattern: "custom"                     # o "acquisizione_nuove_sorgenti", etc.
  testo_dl: |
    Consiste nell'acquisizione di 6 tabelle da CODIFICA...
  testo_rs: |
    Consiste nell'acquisizione di 6 tabelle da CODIFICA...

pacchetto_software:                     # [NDR DL Table 4] + [NDR RS Table 5/6]
  task_dms:    { numero: 1, azione: "nuovo" }
  athena_bronze: { numero: 6, azione: "nuove" }
  athena_silver: { numero: 6, azione: "nuove" }
  etl_glue:    { numero: 6, azione: "nuove" }   # ⚠️ DEVE coincidere con count tabelle Athena (review 2026-05-20)
  step_function: { numero: 1, azione: "nuova" }

# === NDR RS ===
ndr_rs:
  testo_scopo: |
    Custom narrative per sez 1.1 NDR RS
  ha_dl_parallelo: true                 # cita NDR DL in 2.5.4
  include_post_installation: false      # mostra sez 4.3
  oggetti_redshift_count: "Circa 55"    # [NDR RS sez 1.1]
  oggetti_redshift:                     # [NDR RS sez 4.2 + DDE cap RS "Riepilogo"]
    - {object: "stg.codifica", type: "Schema", status: "Creato"}
    - {object: "stg.codifica.master_usage", type: "Table", status: "Creato"}
    # ... una entry per oggetto SQL del rilascio (55+ entries)
  tipo_riassunto_qvd: "datamart_aggiornati"  # [NDR RS sez 1.1 tabella QVD]
  datamart_qvd_map:                     # SEMPRE presente, anche con tutti N.A. (LL13 NDR RS)
    - { datamart: "dmt.dmt.mus_master_usage_cod_extract", qvd: "N.A." }
    # ... una entry per nuovo datamart Redshift

# === NDR DL ===
ndr_dl:
  testo_scopo: |
    Custom narrative per sez 1.1 NDR DL
  ha_rs_parallelo: true
  dipendenze_2_5_1: { pattern: "non_dipendenze_propedeutiche" }
  installazione_2_8_2:
    repo_git_blocchi:
      - { sorgente: "CODIFICA", repos: ["datalake-codifica-iac", "datalake-codifica-ingestion", "datalake-codifica-etl"] }
    repos_extra: ["dataplatform-datalake-iaac", "dataplatform-dwh-etl"]
    installazione_manuale_blocchi:
      - { sorgente: "CODIFICA", host_db: "prod-codifica-datasource-db.cluster-..." }  # ⚠️ NO null/TBD (LL DL-N)
  censimento_dl:
    source_system_rows:                  # [NDR DL sez 4.1 TABLE #13]
      - { host_remoto: "prod-codifica-datasource-db.cluster-c16q6qm6a9wx.eu-west-1.rds.amazonaws.com",
          database: "codifica", schema: "public", tabella: "master_usage", status: "Creato" }
      # ... una entry per source table
    bronze_dms_rows:                     # [NDR DL sez 4.1 TABLE #14]
      - { source_table: "master_usage", task_def: "codifica/dms-task-definitions.yaml", ... }

# === GDC ===
gdc:
  descrizione_narrativa: |
    Narrativa slide 1
  data_rilascio: "2026-05-27"            # [GDC slide 13]

# === Architettura ===
architecture:
  enabled: true
  source_pptx: "C:/.../DdE - Architettura - New.pptx"
  output_pptx: "DdE - Architettura - New con 01.28 Wave 2.pptx"
  archive_previous: true
  release_code: "01.28"
  wave: "WAVE 2"
  template_slides:
    DL: { slide_number: 3 }
    RS: { slide_number: 8 }
  new_sources:
    - name: "CODIFICA"
      host: "prod-codifica-datasource-db.cluster-c16q6qm6a9wx.eu-west-1.rds.amazonaws.com"  # ⚠️ NON null/TBD (LL ARCH-10)
      type: "aurora_rds"                 # o "external"
      placement: "auto"                  # o { l_cm: X, t_cm: Y }
  screenshots:
    out_dir: "C:/.../output/architettura/"
    DL_filename: "architettura_DL.png"
    RS_filename: "architettura_RS.png"
    width_px: 1920

# === DDE ===
dde:
  versione_dde: "1.7.3"                 # invariata salvo bump esplicito (LL DDE-8)
  azione_dl: "I"                         # I/M/I/M
  azione_rs: "I"
  modalita: "overwrite"
  lista_qvd_dl: []                       # lista QVD per cap DL (lowercase)
  lista_qvd_rs: []                       # lista QVD per cap RS (UPPERCASE)
  lista_tabelle_rilascio:                # OBBLIGATORIA per tabella finale (LL DDE-22)
    - rilascio: "01.28_DL - Wave 2"
      oggetto: "dmt.dmt.mus_master_usage_cod_extract"
      sistema_sorgente_host: "prod-codifica-datasource-db.cluster-..."
      sistema_sorgente_db: "Codifica"
      sistema_sorgente_schema: "public"
      sistema_sorgente_tabella: "master_usage"
      athena_db_bronze: "codifica_bronze"
      athena_db_silver: "codifica_silver"
      redshift_schema_stg: "stg.codifica"
      redshift_tabella_stg: "master_usage"
      redshift_tabella_dwh: "master_usage_cod"
    # ... una entry per ogni nuova tabella
```

## Validazioni semantiche (eseguite in Step 0)

### Validazioni globali

| ID | Campo | Regola | Errore se | LL |
|---|---|---|---|---|
| V01 | `release.dmnd_id` | regex `DMND\d{7}` | non matcha | - |
| V02 | `release.edw_release` | regex `\d{2}\.\d{2}` | non matcha | - |
| V03 | `release.wave` | regex `Wave \d+` o null | formato invalido | - |
| V04 | `release.data_*` | formato `DD/MM/YYYY` (o `YYYY-MM-DD` per nas) parsabile | non parsa | - |
| V05 | `layer_impattati` | almeno uno tra `data_lake`/`redshift` true | tutti false | - |
| V06 | `chg_numbers.<layer>` | popolato se `layer_impattati.<layer>=true` | mancante | - |
| V07 | `sorgente.nome_uppercase` | tutto MAIUSCOLO | mixed case | - |

### Validazioni per layer DL

| ID | Campo | Regola | Errore se | LL |
|---|---|---|---|---|
| V10 | `narrativa.testo_dl` | non vuoto | vuoto | - |
| V11 | `ndr_dl.installazione_2_8_2.installazione_manuale_blocchi[*].host_db` | NON null, NON `TBD` | null/TBD/vuoto | LL DL-N |
| V12 | `ndr_dl.censimento_dl.source_system_rows` | non vuota; ogni `host_remoto` valido o `N.A.` esplicito | vuota o TBD residui | LL DL-N |
| V13 | `pacchetto_software.etl_glue.numero` | coerente con `len(athena_silver tables)` | divergenti | - |

### Validazioni per layer RS

| ID | Campo | Regola | Errore se | LL |
|---|---|---|---|---|
| V20 | `ndr_rs.oggetti_redshift` | lista non vuota | vuota | - |
| V21 | `ndr_rs.datamart_qvd_map` | non vuota se RS impattato (SEMPRE presente anche se tutti N.A.) | vuota / mancante | LL13 NDR RS |

### Validazioni per architettura

| ID | Campo | Regola | Errore se | LL |
|---|---|---|---|---|
| V30 | `architecture.new_sources[*].host` | NON null, NON `TBD` (esplicito `N.A.` ok per on-prem) | null/TBD/vuoto | LL ARCH-10 |
| V31 | `architecture.template_slides.<layer>.slide_number` | indice 1-based valido | fuori range | - |
| V32 | `architecture.screenshots.out_dir` | path valido (creabile) | non scrivibile | - |

### Validazioni per DDE

| ID | Campo | Regola | Errore se | LL |
|---|---|---|---|---|
| V40 | `dde.lista_tabelle_rilascio` | non vuota; conteggio coerente con tabelle del rilascio | vuota / count divergente | LL DDE-22 |
| V41 | `dde.versione_dde` | regex `\d+\.\d+\.\d+`; di default uguale alla corrente del DDE master | bump non autorizzato | LL DDE-8 |
| V42 | `dde.lista_tabelle_rilascio[*].sistema_sorgente_host` | hostname valido o `N.A.` esplicito | TBD residui | LL ARCH-10 + LL DL-N |

### Validazioni di coerenza cross-sezione

| ID | Regola | Errore se |
|---|---|---|
| C01 | `release.dmnd_id` invariato in tutte le sezioni che lo citano | divergenti |
| C02 | `release.edw_release` invariato | divergenti |
| C03 | `chg_numbers.data_lake` = host_db di tutti i blocchi `installazione_manuale_blocchi` (NDR DL) | divergenti |
| C04 | `sorgente.nome_uppercase` = nome in `new_sources[0].name` (architettura) | divergenti |
| C05 | `len(ndr_rs.datamart_qvd_map)` = `len(dde.lista_tabelle_rilascio)` se RS impattato | divergenti |
| C06 | `ndr_rs.oggetti_redshift_count` coerente con `len(ndr_rs.oggetti_redshift)` | discrepanza forte |

## Implementazione validazione

```python
def validate_yaml(yaml_dict) -> list[str]:
    errors = []

    # V01
    if not re.match(r'DMND\d{7}', yaml_dict['release']['dmnd_id']):
        errors.append(f"V01: dmnd_id formato invalido: {yaml_dict['release']['dmnd_id']!r}")

    # V11 - LL DL-N
    forbidden_host = (None, "", "TBD", "tbd", "<TODO>", "todo")
    for blocco in yaml_dict.get('ndr_dl', {}).get('installazione_2_8_2', {}).get('installazione_manuale_blocchi', []):
        if blocco.get('host_db') in forbidden_host:
            errors.append(f"V11/LL DL-N: host_db non valorizzato per sorgente '{blocco.get('sorgente')}'. "
                         f"Compila lo YAML con valore reale o 'N.A.' esplicito.")

    # V30 - LL ARCH-10
    for src in yaml_dict.get('architecture', {}).get('new_sources', []):
        if src.get('host') in forbidden_host:
            errors.append(f"V30/LL ARCH-10: host architettura null/TBD per '{src.get('name')}'.")

    # V40 - LL DDE-22
    lista_tab = yaml_dict.get('dde', {}).get('lista_tabelle_rilascio', [])
    if not lista_tab:
        errors.append("V40/LL DDE-22: dde.lista_tabelle_rilascio vuota o mancante. "
                     "Compila lo YAML con 1 entry per ogni nuova tabella del rilascio.")

    return errors

# Uso in Step 0
errs = validate_yaml(yaml_dict)
if errs:
    for e in errs:
        print(f"❌ {e}")
    raise SystemExit("Validazione YAML fallita. Sistemare lo YAML prima di proseguire.")
```

Se la lista errori e' non vuota, **fermare la skill** e mostrare al partner
tutte le validazioni fallite in un colpo solo (no fail-fast: meglio
fix multipli in 1 round che 10 round 1 fix ciascuno).
