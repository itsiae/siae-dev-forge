---
name: siae-data-engineering
description: >
  Guida la costruzione, migrazione e debug di data pipeline ed ETL job su AWS.
  NON per Terraform (usa siae-iac), REST endpoint o frontend.
  Trigger: Glue job, PySpark, ETL, pipeline di ingestion, trasformazione dati,
  Step Functions, data lake, Medallion architecture, bronze-to-silver,
  silver-to-gold, data quality, crawler, batch notturno, Iceberg, CDC,
  delta window, migrare dati da legacy, costruire pipeline, orchestrazione batch,
  implementa Medallion, ingestion file CSV.
---

# SIAE Data Engineering

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨  DevForge  ·  SIAE Data Engineering              ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Flexible | **Fase SDLC:** 4. Implementation
>
> Pattern data engineering da 23 repo Python itsiae. Basato su pattern reali
> estratti da `datalake-anagrafica-dipendenti-etl`, `datalake-sport-etl`,
> `dataplatform-datalake-etl`, e altri repo di produzione.

---

> 📊 **Dai repo itsiae:** Pipeline senza data quality check hanno 4.1x piu' rerun manuali. Il 62% dei job Glue falliti era per schema drift non validato.
> Fonte: analisi su 816 repository GitHub itsiae (60 Java, 44 HCL, 23 Python, 22 TypeScript).

## Panoramica

Guida pipeline ETL su AWS: Glue jobs PySpark, Apache Iceberg, CDC (Change Data Capture),
Step Functions orchestration, EventBridge scheduling, e data lake S3.

**Trigger**: ETL, data pipeline, Glue job, Step Functions, data lake, PySpark,
EventBridge, Iceberg, CDC, bronze-to-silver, delta window, data quality.

**Reference files** per pattern dettagliati:

| File | Contenuto |
|------|-----------|
| `reference/glue-job-patterns.md` | Template job Iceberg, classi base, struttura ereditaria |
| `reference/ingestion-cdc-patterns.md` | CDC, delta window, dedup, soft delete, full reload |
| `reference/step-functions-patterns.md` | Map parallelo, error handling per-branch, Lambda coordinamento |
| `reference/glue-definitions-yaml.md` | Pattern dichiarativo YAML → Terraform `for_each` |
| `reference/data-quality-checklist.md` | Validazioni obbligatorie, metriche, logging strutturato |
| `reference/testing-pyspark.md` | Test locali PySpark: pytest, fixture, MERGE Iceberg, limiti |
| `reference/repo-structure.md` | Struttura directory repo ETL, IaC integration, ambienti |

---

Copia questa checklist e traccia il progresso:

```
Pipeline Progress:
- [ ] Step 1: Identifica sorgente e schema input
- [ ] Step 2: Definisci trasformazione (mapping campi)
- [ ] Step 3: Implementa Glue job con test locale
- [ ] Step 4: Valida output (data quality checks)
- [ ] Step 5: Configura orchestrazione (Step Functions/EventBridge)
```

## 1. Medallion Architecture

### Due layer obbligatori

| Layer | Scopo | Database Glue Catalog | Storage |
|-------|-------|-----------------------|---------|
| **Bronze** | Raw CDC dai sistemi sorgente. Dati as-is con metadata CDC (`op`, `commit_time`, `transact_id`). Partizionato Hive-style. | `{env_prefix}bronze_{domain}` | S3 Parquet, partizioni `year/month/day` |
| **Silver** | Dati cleansed, deduplicated, con business logic. Formato Iceberg per MERGE upsert. | `{env_prefix}{domain}_silver` | S3 Iceberg (catalogo Glue, warehouse `s3://{bucket}/silver/iceberg`) |

**Flusso**: Sistemi sorgente → CDC → Bronze (Parquet partitioned) → Silver (Iceberg managed)

- **Bronze**: nessuna trasformazione business, dati CDC grezzi con `op` (I/U/D), `commit_time`, `transact_id`. Partizionati per data di ingestion (`year/month/day`)
- **Silver**: deduplicazione CDC, MERGE INTO Iceberg per upsert idempotente, soft delete (`deleted=1`), schema alignment con target, `last_updated_at` timestamp di elaborazione

### Multi-ambiente

Il prefisso ambiente gestisce la separazione dei database:
- `dev_` / `qa_` per ambienti non-prod (es. `dev_anagrafica_dipendenti_silver`)
- Nessun prefisso per prod (es. `anagrafica_dipendenti_silver`)

Pattern nel codice: `env_prefix = f"{environment}_" if environment != "prod" else ""`

---

## 2. AWS Glue — Pattern Iceberg

### Struttura job con classi base

Ogni repo ETL usa un pattern di ereditarieta' con classi base condivise in `libs/custom_classes.py`:

```python
class NomeJob(IcebergGlueJob, DatePartitionedGlueJob):
    def __init__(self):
        IcebergGlueJob.__init__(self)        # SparkConf Iceberg, env_prefix
        DatePartitionedGlueJob.__init__(self)  # Delta window, partition pushdown, dedup
        # ... init SparkContext, GlueContext, Job, logger
        # ... definizione bronze_db, bronze_table, silver_db, silver_table, silver_table_pk
        self.job.init(self.job_name, self.args)

    def run(self):
        # 1. Read bronze via Glue Catalog con push_down_predicate
        # 2. ApplyMapping (rename + cast) — UNICA PARTE CHE VARIA TRA JOB
        # 3. Dedup CDC via ROW_NUMBER() su PK + commit_time
        # 4. Standardize (sanitize strings, null handling)
        # 5. Add last_updated_at + deleted flag
        # 6. MERGE INTO Iceberg (upsert + soft delete)
```

**Vedi `reference/glue-job-patterns.md`** per il template completo delle classi base e il flusso dettagliato.

### Glue Catalog e Definizioni

- Ogni tabella registrata nel Glue Data Catalog
- Database naming: `{env_prefix}bronze_{domain}`, `{env_prefix}{domain}_silver`
- **Job definitions in `glue-definitions.yaml`** — file YAML dichiarativo che definisce nome, worker, timeout, per-ambiente. Terraform itera con `for_each` per creare le risorse. Vedi `reference/glue-definitions-yaml.md`
- Risorse Terraform: `glue-jobs.tf` (itera su YAML), `glue-jobs-custom-libraries-upload.tf` (carica libs su S3)
- Glue version: **5.0** con `--datalake-formats: iceberg`
- Worker type: `G.1X`, execution class: `FLEX` (spot, costo ridotto)

### Parametri Glue obbligatori

| Parametro | Scopo |
|-----------|-------|
| `--JOB_NAME` | Nome job (standard Glue) |
| `--iceberg_job_catalog_warehouse` | Path S3 warehouse Iceberg (`s3://{bucket}/silver/iceberg`) |
| `--environment` | `dev`, `qa`, `prod` — determina `env_prefix` |
| `--last_silver_update_time` | Epoch Unix inizio finestra delta (da Step Function) |
| `--next_silver_update_time` | Epoch Unix fine finestra delta (da Step Function) |
| `--force_no_window` | `1` = full reload, `0` = modalita' incrementale |

**🚨 Operazione CRITICA — pre-flight card OBBLIGATORIA prima di deploy Glue job:**

| 🚨 CRITICO (irreversibile) — 🔨 DevForge · siae-data-engineering |
|:---|
| ⚠️ AZIONE IRREVERSIBILE — CONFERMA RICHIESTA |
| 🏗️ Ambiente: `<ambiente>` |
| 📋 Job: `<job-name>` |
| 🔄 Layer: `<bronze\|silver>` |
| 1. ⚠️ Azione: Deploy Glue job via terraform apply |
| 📂 `<modulo terraform>` |
| 💡 Perche': Job aggiornato, test locali verdi |
| 🚫 Se NO: STOP — job non deployato, versione precedente resta attiva |

**🔴 Operazione ALTO rischio — pre-flight card prima di modifica schema:**

| 🔴 ALTO (difficile da annullare) — 🔨 DevForge · siae-data-engineering |
|:---|
| ⚠️ OPERAZIONE DIFFICILE DA ANNULLARE |
| 🗄️ Database: `<glue-database>` |
| 🔧 Tabella: `<table-name>` |
| 📦 Downstream: `<query/job dipendenti>` |
| 1. 🔧 Azione: Modifica schema Glue Catalog (backward compatibility) |
| 📂 `<file schema/terraform>` |
| 💡 Perche': Schema da aggiornare per nuovi requisiti dati |
| 🚫 Se NO: Schema invariato, downstream non impattati |

---

## 3. CDC — Change Data Capture

Il pattern CDC e' il cuore del flusso bronze-to-silver. Vedi `reference/ingestion-cdc-patterns.md` per i dettagli.

### Flusso CDC in sintesi

```
Bronze (Parquet, partizioni year/month/day)
  │  contiene: op (I/U/D), commit_time, transact_id, payload
  │
  ├─ Push-down predicate → filtra solo partizioni nella finestra delta
  ├─ ApplyMapping → rename + cast colonne
  ├─ ROW_NUMBER() OVER (PARTITION BY PK ORDER BY commit_time DESC, transact_id DESC)
  │  → dedup: mantiene solo l'operazione piu' recente per PK
  ├─ Standardize → sanitize strings, null handling
  ├─ Add metadata → last_updated_at, deleted flag (op='D' → deleted=1)
  │
  └─ MERGE INTO Iceberg
       WHEN MATCHED AND op='D' → soft delete (deleted=1, last_op='D')
       WHEN MATCHED AND op!='D' → UPDATE SET *
       WHEN NOT MATCHED → INSERT *
```

### Delta window

La finestra temporale incrementale (`last_silver_update_time` → `next_silver_update_time`) viene:
1. Gestita dalla Lambda `silver_updates_manager` (mode RETRIEVE/UPDATE)
2. Passata dalla Step Function come parametri ai Glue job
3. Usata dal `push_down_predicate` per filtrare le partizioni bronze

**`force_no_window=1`**: forza full reload (finestra 0 → anno 3000). Usare con cautela in prod.

---

## 4. Step Functions

Pattern reale: orchestrazione parallela con **Map state**, error handling per-branch, e aggregazione finale.

```
RetrieveTablesToUpdate (Lambda)
  → AreThereTablesToUpdate (Choice)
    → No → Succeed
    → Si → LaunchSilverETL (Map, MaxConcurrency=10)
              Per ogni tabella:
                CheckUpdateTime → AdjustUpdateTime (sottrai 1 giorno overlap)
                → SilverGlueJob (.sync)
                  → [errore] → NotifyETLError (EventBridge) → SetFailedStatus
                  → [ok] → UpdateSilverCommitTime (Lambda) → NotifyNewDataInSilver (EventBridge) → SetSuccessStatus
           → GetFailedJobs (filtra FAILED)
           → CheckForFailures
             → ci sono falliti → JobFailed (Fail)
             → nessun fallito → Tables Updated (Succeed)
```

**Vedi `reference/step-functions-patterns.md`** per la definizione ASL completa e i pattern di error handling.

### Regole Step Functions

- **Map state** per parallelismo job (non esecuzione sequenziale)
- `.sync` per attesa completamento Glue job
- **Catch per-branch** (non globale): ogni job puo' fallire senza bloccare gli altri
- Aggregazione finale: conta i falliti e fallisce solo se > 0
- **EventBridge dual bus**: notifiche su `datalake_events` (successo) e `dataplatform_errors` (failure)
- State machine definition in `orchestration/silver-etl.json` (template Terraform con `templatefile`)

**🔴 Operazione ALTO rischio — pre-flight card prima di esecuzione manuale:**

| 🔴 ALTO (difficile da annullare) — 🔨 DevForge · siae-data-engineering |
|:---|
| ⚠️ OPERAZIONE DIFFICILE DA ANNULLARE |
| 📋 Job: `<job-name>` |
| 🏗️ Ambiente: `<ambiente>` |
| 🔧 Parametri: `<parametri input>` |
| 1. 🖥️ Azione: Esecuzione manuale Glue job (consuma risorse, scrive S3) |
| 📂 `aws glue start-job-run --job-name <name>` |
| 💡 Perche': Esecuzione manuale necessaria per `<motivazione>` |
| 🚫 Se NO: Job non eseguito, nessun dato processato |

---

## 5. EventBridge

### Dual bus pattern

| Bus | Scopo | Naming |
|-----|-------|--------|
| **datalake_events** | Notifiche successo (nuovi dati in silver) | DetailType: `silver-notification/{scope}/{table}` |
| **dataplatform_errors** | Notifiche failure (job falliti) | DetailType: `silver-{scope}-glue-failure` |

### Scheduler

- Regola cron sul **default event bus** (non custom) per triggerare la Step Function
- Naming: `{env}-{project}-schedule-orchestr`
- Cron expression e stato (`ENABLED`/`DISABLED`) configurabili per ambiente via file env template
- Il trigger usa un IAM role dedicato (`silver_batch_trigger_orchestration`) separato dal role della Step Function

---

## 6. S3 Data Lake Structure

### Bronze layer (Parquet Hive-style)

```
s3://{bronze-bucket}/bronze/{domain}/{table}/year=YYYY/month=MM/day=DD/
```

Esempio: `s3://siae-datalake-prod/bronze/anagrafica-dipendenti/dipendenti/year=YYYY/month=MM/day=DD/`

- Partizione obbligatoria: `year`, `month`, `day`
- Formato: Parquet
- Contiene eventi CDC raw

### Silver layer (Iceberg managed)

```
s3://{silver-bucket}/silver/iceberg/{database}/{table}/
```

Esempio: `s3://siae-silver-prod/silver/iceberg/anagrafica_dipendenti_silver/dipendenti/`

- Formato: Apache Iceberg (gestito da Glue Catalog)
- Nessuna partizione Hive esplicita — Iceberg gestisce internamente
- Upsert via MERGE INTO

### Landing zone

```
s3://{transient-bucket}/landing/{domain}/
```

Per dati raw prima dell'ingestion nel bronze.

**🚨 Operazione CRITICA — pre-flight card OBBLIGATORIA prima di cancellazione S3:**

| 🚨 CRITICO (irreversibile) — 🔨 DevForge · siae-data-engineering |
|:---|
| ⚠️ AZIONE IRREVERSIBILE — CONFERMA RICHIESTA |
| 🗄️ Bucket: `<bucket-name>` |
| 📁 Prefix: `<s3-prefix>` |
| 📊 File coinvolti: `<N> file, <size>` |
| 1. 🗑️ Azione: Cancellazione dati S3 (irreversibile senza backup) |
| 📂 `s3://<bucket>/<prefix>` |
| 💡 Perche': Dati obsoleti/corrotti da rimuovere |
| 🚫 Se NO: STOP — dati preservati, nessuna cancellazione |

---

## 7. Struttura Repository ETL

Ogni repo ETL segue questa struttura. Vedi `reference/repo-structure.md` per i dettagli IaC.

```
datalake-{domain}-etl/
├── config.yaml                          # Tag globali, project name, region
├── Makefile                             # Deploy via tag (make dev/qa)
├── live/
│   ├── terragrunt.hcl                   # Root: backend S3, provider, default_tags
│   ├── _envs/{dev,qa,prod}.tmpl         # Template ambiente (CI genera .yaml a runtime)
│   ├── shared/terragrunt.hcl            # Lookup risorse piattaforma (data sources only)
│   └── silver-{domain}/terragrunt.hcl   # Modulo ETL con dependency shared
└── modules/
    ├── shared/                          # Data sources: S3, VPC, KMS, DynamoDB, EventBridge
    └── silver-{domain}/
        ├── _input.tf / _local.tf / _output.tf
        ├── glue-definitions.yaml        # Definizione dichiarativa job
        ├── glue-jobs.tf                 # for_each su YAML → risorse Glue + IAM
        ├── glue-jobs-custom-libraries-upload.tf  # Upload libs + log4j2 su S3
        ├── stepfunction-orchestration.tf         # Step Function + IAM roles
        ├── eventbridge-etl-scheduler.tf          # Cron trigger
        └── glue-jobs/
            ├── src/{table}.py           # 1 job PySpark per tabella
            ├── src/libs/custom_classes.py  # Classi base (IcebergGlueJob, DatePartitionedGlueJob)
            ├── configs/{env}/log4j2.properties  # Logging per-ambiente
            └── orchestration/silver-etl.json    # ASL Step Function (template Terraform)
```

### Pattern IaC chiave

- **Shared module = data source registry**: solo lookup di risorse create altrove (piattaforma). Nessuna risorsa creata.
- **glue-definitions.yaml → Terraform**: file YAML dichiarativo, Terraform itera con `for_each` per creare i job
- **Custom libraries upload**: `--extra-py-files` per classi base, `--extra-files` per log4j2. Change detection via `etag = filemd5()`
- **Template .tmpl**: i file ambiente non sono committati. La CI/CD li genera a runtime sostituendo variabili (`$AWS_ENV`, `$BRONZE_DATALAKE_BUCKET_ID`, etc.)
- **Deploy tag-based**: `make dev` → tag `COLLAUDO`, `make qa` → tag `CERTIFICAZIONE`. Produzione solo via GitHub Actions UI

---

## 8. Vincoli Inviolabili

Queste regole sono **OBBLIGATORIE**. Violarne una significa bloccare la review.

| #  | Vincolo | Motivazione |
|----|---------|-------------|
| V1 | No pandas nei Glue job | Usa PySpark. pandas non scala su cluster |
| V2 | Partition key obbligatoria nel bronze | Senza partizioni, query full-scan costose |
| V3 | Job idempotenti (MERGE INTO, non append) | Rerunnable senza duplicati. MERGE Iceberg garantisce idempotenza |
| V4 | Python 3.10+ | Standard SIAE, Glue 5.0 compatibile |
| V5 | No hardcoded S3 path nei job | Usa argomenti Glue (`getResolvedOptions`) |
| V6 | Glue Catalog per schema | No schema hardcoded, single source of truth |
| V7 | Catch per-branch in Step Functions | Un job fallito non deve bloccare gli altri job paralleli |
| V8 | Metodi condivisi nella classe base | Mai duplicare metodi utility nei singoli job. Usa `libs/custom_classes.py` |
| V9 | Soft delete, mai cancellazione fisica | `op='D'` → `deleted=1`. Preserva audit trail |
| V10 | `force_no_window` mai `1` in prod senza approvazione | Causa riscrittura completa del datalake. Costi e rischi elevati |
| V11 | Cast dei tipi consistente tra tabelle dello stesso dominio | Se `attivo` e' `integer` in una tabella, deve esserlo in tutte |
| V12 | Log almeno WARN attivo in tutti gli ambienti | Log INFO disabilitati in prod = failure silenti invisibili |

---

## 9. Data Quality

**Ogni job DEVE includere** (vedi `reference/data-quality-checklist.md`):

1. **Validazione PK non null** — prima del MERGE, verifica che la primary key non contenga null
2. **Conteggio record** — logga count pre-dedup e post-dedup per monitorare il rapporto
3. **Conteggio MERGE** — logga record inseriti, aggiornati, soft-deleted
4. **Import puliti** — importa solo cio' che usi. No import inutilizzati
5. **No codice morto** — rimuovi metodi commentati. Se non serve, non c'e'

---

## Limiti Operativi

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Tentativi fix per errore | 2 | Fermati. Diagnosi diversa necessaria. |
| File modificati per singolo step | 5 | Se devi toccare piu' file, decomponi in sub-task. |
| Output max per raccomandazione | 200 righe | Prioritizza. Top 5 issue, non lista esaustiva. |

---

## REQUIRED SUB-SKILL: siae-verification

Invoca `siae-verification` prima di dichiarare la pipeline completata.

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "Il job funziona, non serve il Medallion" | Senza struttura Bronze/Silver il data lake diventa data swamp. |
| "I test sui Glue job sono lenti" | Un job non testato che va in produzione costa giorni di recovery. |
| "Lo schema lo valido a runtime" | La validazione a runtime arriva tardi. Valida all'ingresso. |
| "La pipeline e' semplice, non serve Step Functions" | Le pipeline 'semplici' crescono. L'orchestrazione si aggiunge male in corsa. |
| "Il checkpoint lo aggiungo se serve" | Senza checkpoint, un job da 6 ore riparte dall'inizio al primo errore. |
| "I log sono nel CloudWatch, non nel job" | I log strutturati nel job permettono alert e dashboard. CloudWatch non basta. |
| "La partizione non serve per questo volume" | Il volume cresce. La ripartizione a posteriori e' costosa. |
| "Duplico il metodo, tanto e' piccolo" | 7 job × 6 metodi = 42 posti da aggiornare per un singolo fix. Classe base. |
| "force_no_window=1 solo per questa volta" | Una "sola volta" in prod riscrive l'intero datalake. Costi cloud imprevedibili. |
| "Il soft delete spreca spazio" | Lo spazio costa meno di un audit mancante. I dati cancellati fisicamente sono irrecuperabili. |

## Classificazione Rischio Operazioni

| Operazione | Rischio | Card |
|------------|---------|------|
| Lettura/analisi codice ETL | 🟢 Sicuro | No |
| Creazione/modifica script PySpark | 🟡 Medio | No |
| Modifica glue-definitions.yaml | 🟡 Medio | No |
| Modifica Step Function definition | 🟡 Medio | No |
| Modifica `force_no_window` in prod | 🚨 Critico | Si |
| Deploy Glue job (`terraform apply`) | 🚨 Critico | Si |
| Cancellazione dati S3 | 🚨 Critico | Si |
| Modifica schema Glue Catalog | 🔴 Alto | Si |
| `aws glue start-job-run` manuale | 🔴 Alto | Si |
| Modifica EventBridge schedule | 🔴 Alto | No |
