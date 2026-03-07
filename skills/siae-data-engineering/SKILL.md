---
name: siae-data-engineering
description: >
  Pattern data engineering SIAE: Medallion Architecture, AWS Glue, PySpark.
  Trigger: ETL, data pipeline, Glue job, Step Functions, data lake.
  Basato su pattern reali da 23 repo Python itsiae.
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

---

## Panoramica

Pattern data engineering da 23 repo Python itsiae (dataplatform-datalake-etl, performing-etl, datalake-sport-etl, etc.). Guida pipeline ETL, Glue jobs, Step Functions e data lake.

**Trigger**: ETL, data pipeline, Glue job, Step Functions, data lake, PySpark, EventBridge.

---

## 1. Medallion Architecture

### Due layer obbligatori

| Layer    | Scopo                                          | Naming             |
|----------|------------------------------------------------|--------------------|
| **Bronze** | Raw ingestion dai sistemi sorgente. Dati as-is, nessuna trasformazione business. | `bronze-{domain}` |
| **Silver** | Dati cleansed, enriched, con business logic applicata. Pronti per il consumo. | `silver-{domain}` |

**Flusso**: Sistemi sorgente --> Bronze (raw) --> Silver (cleansed + enriched)

- **Bronze**: no trasformazioni business, solo conversione formato (CSV->Parquet), dedup tecnica, metadata (`ingestion_timestamp`, `source_system`)
- **Silver**: validazione, business rules, join tra domini, calcoli derivati, schema enforcement

---

## 2. AWS Glue

### Struttura PySpark job

```python
import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job

args = getResolvedOptions(sys.argv, [
    "JOB_NAME",
    "source_path",
    "target_path",
    "database_name",
    "table_name"
])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

# --- Business logic ---

df = spark.read.parquet(args["source_path"])
# trasformazioni...
df_output.write.mode("overwrite").partitionBy("year", "month", "day").parquet(args["target_path"])

job.commit()
```

### Glue Catalog e Definizioni

- Ogni tabella registrata nel Glue Data Catalog, database: `bronze_{domain}`, `silver_{domain}`
- Job definitions in `glue-definitions.yaml` (name, script_path, glue_version 4.0, worker_type, arguments)
- Risorse Terraform: `glue-jobs-{domain}.tf`

**🚨 Operazione CRITICA — pre-flight card OBBLIGATORIA prima di deploy Glue job:**

```bash
echo '{
  "level": "CRITICO",
  "skill": "siae-data-engineering",
  "context": [
    {"emoji": "🏗️", "label": "Ambiente", "value": "<ambiente>"},
    {"emoji": "📋", "label": "Job", "value": "<job-name>"},
    {"emoji": "🔄", "label": "Layer", "value": "<bronze|silver|gold>"}
  ],
  "actions": [
    {"emoji": "⚠️", "label": "Deploy Glue job via terraform apply", "path": "<modulo terraform>"}
  ],
  "reason": "Job aggiornato, test locali verdi",
  "ifno": "STOP — job non deployato, versione precedente resta attiva"
}' | python3 design-system/generate-card.py
```

**🔴 Operazione ALTO rischio — pre-flight card prima di modifica schema:**

```bash
echo '{
  "level": "ALTO",
  "skill": "siae-data-engineering",
  "context": [
    {"emoji": "🗄️", "label": "Database", "value": "<glue-database>"},
    {"emoji": "🔧", "label": "Tabella", "value": "<table-name>"},
    {"emoji": "📦", "label": "Downstream", "value": "<query/job dipendenti>"}
  ],
  "actions": [
    {"emoji": "🔧", "label": "Modifica schema Glue Catalog (backward compatibility)", "path": "<file schema/terraform>"}
  ],
  "reason": "Schema da aggiornare per nuovi requisiti dati",
  "ifno": "Schema invariato, downstream non impattati"
}' | python3 design-system/generate-card.py
```

---

## 3. Step Functions

Pattern: `BronzeIngestion` --> `SilverTransform` --> (end) | `NotifyFailure` (on error)

Ogni state Glue usa `arn:aws:states:::glue:startJobRun.sync` con:

```json
"Retry": [{"ErrorEquals": ["States.TaskFailed"], "IntervalSeconds": 60, "MaxAttempts": 2, "BackoffRate": 2.0}],
"Catch": [{"ErrorEquals": ["States.ALL"], "Next": "NotifyFailure"}]
```

### Regole Step Functions

- Sempre `Retry` con backoff esponenziale per task Glue
- Sempre `Catch` con notifica SNS per failure
- `.sync` per attesa completamento Glue job
- State machine definition in file JSON separato

**🔴 Operazione ALTO rischio — pre-flight card prima di esecuzione manuale:**

```bash
echo '{
  "level": "ALTO",
  "skill": "siae-data-engineering",
  "context": [
    {"emoji": "📋", "label": "Job", "value": "<job-name>"},
    {"emoji": "🏗️", "label": "Ambiente", "value": "<ambiente>"},
    {"emoji": "🔧", "label": "Parametri", "value": "<parametri input>"}
  ],
  "actions": [
    {"emoji": "🖥️", "label": "Esecuzione manuale Glue job (consuma risorse, scrive S3)", "path": "aws glue start-job-run --job-name <name>"}
  ],
  "reason": "Esecuzione manuale necessaria per <motivazione>",
  "ifno": "Job non eseguito, nessun dato processato"
}' | python3 design-system/generate-card.py
```

---

## 4. EventBridge

Trigger event-driven per pipeline ETL. Naming: rule `{project}-{env}-pipeline-{domain}`, target `{project}-{env}-sfn-{domain}`. Schedule con cron expression UTC (es. `cron(0 6 * * ? *)`).

---

## 5. S3 Data Lake Structure

Path: `s3://{bucket}/{layer}/{domain}/{table}/year=YYYY/month=MM/day=DD/`

Esempio: `s3://siae-datalake-prod/bronze/performing/events/year=2025/month=06/day=15/`

- Partizione obbligatoria: `year`, `month`, `day`. Formato: Parquet (Snappy)
- Landing zone raw: `s3://{bucket}/landing/{domain}/`

**🚨 Operazione CRITICA — pre-flight card OBBLIGATORIA prima di cancellazione S3:**

```bash
echo '{
  "level": "CRITICO",
  "skill": "siae-data-engineering",
  "context": [
    {"emoji": "🗄️", "label": "Bucket", "value": "<bucket-name>"},
    {"emoji": "📁", "label": "Prefix", "value": "<s3-prefix>"},
    {"emoji": "📊", "label": "File coinvolti", "value": "<N> file, <size>"}
  ],
  "actions": [
    {"emoji": "🗑️", "label": "Cancellazione dati S3 (irreversibile senza backup)", "path": "s3://<bucket>/<prefix>"}
  ],
  "reason": "Dati obsoleti/corrotti da rimuovere",
  "ifno": "STOP — dati preservati, nessuna cancellazione"
}' | python3 design-system/generate-card.py
```

---

## 6. Vincoli Inviolabili

Queste regole sono **OBBLIGATORIE**. Violarne una significa bloccare la review.

| #  | Vincolo                                    | Motivazione                              |
|----|--------------------------------------------|------------------------------------------|
| V1 | No pandas nei Glue job                     | Usa PySpark. pandas non scala su cluster |
| V2 | Partition key obbligatoria                 | Senza partizioni, query full-scan costose|
| V3 | Job idempotenti (rerunnable senza duplicati)| Overwrite partizione, non append cieco   |
| V4 | Python 3.10+                               | Standard SIAE, Glue 4.0 compatibile     |
| V5 | requirements.txt per job                   | Dipendenze esplicite e pinned            |
| V6 | No hardcoded S3 path nei job               | Usa argomenti Glue (`getResolvedOptions`)|
| V7 | Glue Catalog per schema                    | No schema hardcoded, single source truth |
| V8 | Retry obbligatorio in Step Functions       | Glue job puo' fallire per risorse temp   |

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "Il job funziona, non serve il Medallion" | Senza struttura Bronze/Silver/Gold il data lake diventa data swamp. |
| "I test sui Glue job sono lenti" | Un job non testato che va in produzione costa giorni di recovery. |
| "Lo schema lo valido a runtime" | La validazione a runtime arriva tardi. Valida all'ingresso. |
| "La pipeline e' semplice, non serve Step Functions" | Le pipeline 'semplici' crescono. L'orchestrazione si aggiunge male in corsa. |
| "Il checkpoint lo aggiungo se serve" | Senza checkpoint, un job da 6 ore riparte dall'inizio al primo errore. |
| "I log sono nel CloudWatch, non nel job" | I log strutturati nel job permettono alert e dashboard. CloudWatch non basta. |
| "La partizione non serve per questo volume" | Il volume cresce. La ripartizione a posteriori e' costosa. |

## Classificazione Rischio Operazioni

| Operazione                        | Rischio    | Card            |
|-----------------------------------|------------|-----------------|
| Lettura/analisi codice ETL        | 🟢 Sicuro  | No              |
| Creazione/modifica script PySpark | 🟡 Medio   | No              |
| Modifica glue-definitions.yaml    | 🟡 Medio   | No              |
| Modifica Step Function definition | 🟡 Medio   | No              |
| Deploy Glue job (`terraform apply`) | 🚨 Critico | Si            |
| Cancellazione dati S3             | 🚨 Critico | Si              |
| Modifica schema Glue Catalog      | 🔴 Alto    | Si              |
| `aws glue start-job-run` manuale  | 🔴 Alto    | Si              |
| Modifica EventBridge schedule     | 🔴 Alto    | No              |
