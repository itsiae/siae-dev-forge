# Glue Definitions YAML — Pattern Dichiarativo

> Basato su pattern reali estratti da `datalake-anagrafica-dipendenti-etl`.

---

## Concetto

I Glue job sono definiti in un file YAML dichiarativo (`glue-definitions.yaml`),
non direttamente in Terraform. Terraform legge il YAML e crea le risorse con `count`.

Questo separa **la configurazione dei job** (competenza data engineering) dalla
**infrastruttura** (competenza IaC), permettendo ai data engineer di aggiungere
job senza toccare Terraform.

---

## Struttura `glue-definitions.yaml`

```yaml
jobs:
  - name: areedipendenti
    src_file: aree_dipendenti
    silver_table: aree_dipendenti
    dev_number_of_workers: 2
    qa_number_of_workers: 2
    prod_number_of_workers: 2
    timeout: 60
    enable_gluejob_sparkui: true

  - name: dipendenti
    src_file: dipendenti
    silver_table: dipendenti
    dev_number_of_workers: 4
    qa_number_of_workers: 4
    prod_number_of_workers: 4
    timeout: 90
    enable_gluejob_sparkui: true

  - name: unitaorganizzative
    src_file: unita_organizzative
    silver_table: unita_organizzative
    dev_number_of_workers: 4
    qa_number_of_workers: 4
    prod_number_of_workers: 4
    timeout: 90
    enable_gluejob_sparkui: true
```

### Campi

| Campo | Tipo | Scopo |
|-------|------|-------|
| `name` | string | Nome del Glue job (senza prefisso ambiente) |
| `src_file` | string | Nome del file Python in `glue-jobs/src/` (senza `.py`) |
| `silver_table` | string | Nome della tabella silver target |
| `dev_number_of_workers` | int | Worker per ambiente dev |
| `qa_number_of_workers` | int | Worker per ambiente qa |
| `prod_number_of_workers` | int | Worker per ambiente prod |
| `timeout` | int | Timeout in minuti |
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
}

# Creazione risorse iterando sulla lista
resource "aws_glue_job" "silver" {
  count = length(local.glue_jobs.jobs)

  name     = "${local.prefix}-${local.glue_jobs.jobs[count.index].name}"
  role_arn = aws_iam_role.silver_batch_jobs.arn

  command {
    name            = "glueetl"
    script_location = "s3://${var.glue_packages_bucket.id}/etl/${var.module}/${local.glue_jobs.jobs[count.index].src_file}.py"
    python_version  = "3"
  }

  glue_version      = "5.0"
  worker_type       = "G.1X"
  execution_class   = "FLEX"
  number_of_workers = local.glue_jobs.jobs[count.index]["${var.env}_number_of_workers"]
  timeout           = local.glue_jobs.jobs[count.index].timeout
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
      try(local.glue_jobs.jobs[count.index].enable_gluejob_sparkui, "false")
    )
  }

  depends_on = [aws_s3_object.glue_script_upload]
}

# Upload script su S3 per ogni job
resource "aws_s3_object" "glue_script_upload" {
  count  = length(local.glue_jobs.jobs)
  bucket = var.glue_packages_bucket.id
  key    = "etl/${var.module}/${local.glue_jobs.jobs[count.index].src_file}.py"
  source = "${path.module}/glue-jobs/src/${local.glue_jobs.jobs[count.index].src_file}.py"
  etag   = filemd5("${path.module}/glue-jobs/src/${local.glue_jobs.jobs[count.index].src_file}.py")
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
3. **Non toccare `glue-jobs.tf`** — il `count` itera automaticamente sulla nuova entry
4. **Aggiorna `silver-etl.json`** — aggiungi la tabella al `silver_mapping` nella Step Function
5. **Verifica con `terraform plan`** — deve mostrare solo la nuova risorsa `aws_glue_job`
