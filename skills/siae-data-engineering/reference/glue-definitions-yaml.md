# Glue Definitions YAML — Pattern Dichiarativo

> Basato su pattern reali estratti da `datalake-anagrafica-dipendenti-etl`.

---

## Concetto

I Glue job sono definiti in un file YAML dichiarativo (`glue-definitions.yaml`),
non direttamente in Terraform. Terraform legge il YAML e crea le risorse con `for_each`.

Questo separa **la configurazione dei job** (competenza data engineering) dalla
**infrastruttura** (competenza IaC), permettendo ai data engineer di aggiungere
job senza toccare Terraform.

---

## Struttura `glue-definitions.yaml`

```yaml
jobs:
  - job_name: areedipendenti
    description: "ETL bronze-to-silver aree dipendenti"
    file_name: aree_dipendenti
    silver_table: aree_dipendenti
    worker_type: G.1X
    glue_version: "5.0"
    execution_class: FLEX
    max_concurrent_runs: 1
    dev_number_of_workers: 2
    qa_number_of_workers: 2
    prod_number_of_workers: 2
    timeout_min: 60
    enable_gluejob_sparkui: true

  - job_name: dipendenti
    description: "ETL bronze-to-silver dipendenti"
    file_name: dipendenti
    silver_table: dipendenti
    worker_type: G.1X
    glue_version: "5.0"
    execution_class: FLEX
    max_concurrent_runs: 1
    dev_number_of_workers: 4
    qa_number_of_workers: 4
    prod_number_of_workers: 4
    timeout_min: 90
    enable_gluejob_sparkui: true
```

### Campi

| Campo | Tipo | Scopo |
|-------|------|-------|
| `job_name` | string | Nome del Glue job (senza prefisso ambiente) |
| `description` | string | Descrizione del job |
| `file_name` | string | Nome del file Python in `glue-jobs/src/` (senza `.py`) |
| `silver_table` | string | Nome della tabella silver target |
| `worker_type` | string | Tipo worker Glue (`G.1X`, `G.2X`) |
| `glue_version` | string | Versione Glue (`"4.0"` o `"5.0"`, preferire `"5.0"` per nuovi job) |
| `execution_class` | string | `FLEX` (spot, costo ridotto) o `STANDARD` |
| `max_concurrent_runs` | int | Esecuzioni concorrenti massime (default: 1) |
| `dev_number_of_workers` | int | Worker per ambiente dev |
| `qa_number_of_workers` | int | Worker per ambiente qa |
| `prod_number_of_workers` | int | Worker per ambiente prod |
| `timeout_min` | int | Timeout in minuti |
| `enable_gluejob_sparkui` | bool | Abilita Spark History Server per il job |

---

## Come Terraform legge il YAML

```hcl
# Lettura file YAML
data "local_file" "glue_jobs_definition" {
  filename = "${path.module}/glue-definitions.yaml"
}

locals {
  glue_jobs = yamldecode(data.local_file.glue_jobs_definition.content)
  # Mappa per for_each (key = job_name)
  glue_jobs_map = { for job in local.glue_jobs.jobs : job.job_name => job }
}

# Creazione risorse iterando sulla mappa
resource "aws_glue_job" "silver" {
  for_each = local.glue_jobs_map

  name     = "${local.prefix}-${each.key}"
  role_arn = aws_iam_role.silver_batch_jobs.arn

  command {
    name            = "glueetl"
    script_location = "s3://${var.glue_packages_bucket.id}/etl/${var.module}/${each.value.file_name}.py"
    python_version  = "3"
  }

  glue_version      = each.value.glue_version
  worker_type       = each.value.worker_type
  execution_class   = each.value.execution_class
  number_of_workers = each.value["${var.env}_number_of_workers"]
  timeout           = each.value.timeout_min
  max_retries       = 0
  max_capacity      = null

  default_arguments = {
    "--job-language"                 = "python"
    "--job-bookmark-option"          = "job-bookmark-disable"
    "--datalake-formats"             = "iceberg"
    "--conf"                         = "spark.sql.catalog..."
    "--iceberg_job_catalog_warehouse" = "s3://${var.silver_datalake_bucket.id}/silver/iceberg"
    "--environment"                  = var.env
    "--last_silver_update_time"      = "-1"
    "--next_silver_update_time"      = "-1"
    "--force_no_window"              = var.config.force_no_window
    "--extra-py-files"               = join(",", local.silver_batch_libraries_s3_path)
    "--extra-files"                  = join(",", local.silver_batch_extra_files_s3_path)
    "--enable-spark-ui"              = (
      var.config.enable_spark_ui == "false" ? "false" :
      try(each.value.enable_gluejob_sparkui, "false")
    )
  }

  depends_on = [aws_s3_object.glue_script_upload]
}

# Upload script su S3 per ogni job
resource "aws_s3_object" "glue_script_upload" {
  for_each = local.glue_jobs_map
  bucket   = var.glue_packages_bucket.id
  key      = "etl/${var.module}/${each.value.file_name}.py"
  source   = "${path.module}/glue-jobs/src/${each.value.file_name}.py"
  etag     = filemd5("${path.module}/glue-jobs/src/${each.value.file_name}.py")
}
```

---

## Upload custom libraries

Le classi base e i file di configurazione sono caricati separatamente:

```hcl
# Classe base Python
resource "aws_s3_object" "glue_custom_classes" {
  bucket = var.glue_packages_bucket.id
  key    = "etl/${var.module}/libs/custom_classes.py"
  source = "${path.module}/glue-jobs/src/libs/custom_classes.py"
  etag   = filemd5("${path.module}/glue-jobs/src/libs/custom_classes.py")
}

# Log4j2 per-ambiente
resource "aws_s3_object" "glue_log4j2_properties_upload" {
  bucket = var.glue_packages_bucket.id
  key    = "etl/${var.module}/configs/log4j2.properties"
  source = "${path.module}/glue-jobs/configs/${var.env}/log4j2.properties"
  etag   = filemd5("${path.module}/glue-jobs/configs/${var.env}/log4j2.properties")
}
```

Passati ai job tramite:
- `--extra-py-files` → classi base nel PYTHONPATH
- `--extra-files` → log4j2 distribuito agli executor

---

## Checklist nuovo job

1. **Aggiungi entry in `glue-definitions.yaml`** con nome, src_file, worker, timeout
2. **Crea il file Python** in `glue-jobs/src/{nome}.py`
3. **Non toccare `glue-jobs.tf`** — il `for_each` itera automaticamente sulla nuova entry
4. **Aggiorna `silver-etl.json`** — aggiungi la tabella al `silver_mapping` nella Step Function
5. **Verifica con `terraform plan`** — deve mostrare solo la nuova risorsa `aws_glue_job`
