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

---

## 4. EventBridge

Trigger event-driven per pipeline ETL. Naming: rule `{project}-{env}-pipeline-{domain}`, target `{project}-{env}-sfn-{domain}`. Schedule con cron expression UTC (es. `cron(0 6 * * ? *)`).

---

## 5. S3 Data Lake Structure

Path: `s3://{bucket}/{layer}/{domain}/{table}/year=YYYY/month=MM/day=DD/`

Esempio: `s3://siae-datalake-prod/bronze/performing/events/year=2025/month=06/day=15/`

- Partizione obbligatoria: `year`, `month`, `day`. Formato: Parquet (Snappy)
- Landing zone raw: `s3://{bucket}/landing/{domain}/`

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

## Classificazione Rischio Operazioni

| Operazione                        | Rischio    |
|-----------------------------------|------------|
| Lettura/analisi codice ETL        | 🟢 Sicuro  |
| Creazione/modifica script PySpark | 🟡 Medio   |
| Modifica glue-definitions.yaml    | 🟡 Medio   |
| Modifica Step Function definition | 🟡 Medio   |
| Deploy Glue job (terraform apply) | 🚨 Critico |
| Esecuzione manuale Glue job       | 🔴 Alto    |
| Modifica EventBridge schedule     | 🔴 Alto    |
| Cancellazione dati S3             | 🚨 Critico |
