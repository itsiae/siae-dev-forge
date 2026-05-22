# Template Modulo Silver — datalake-{dominio}-iac

> Template completo dei file Terraform per il modulo silver.
> Sostituisci `{dominio}` con il nome del dominio (es. `zucchetti`).

---

## modules/silver/_input.tf

```hcl
# * Module Input Variables from other modules and from config
# * ----------------------------------------------------------

variable "account_id" {
  description = "The AWS Account number used for deploying Terraform"
  type        = string
}

variable "region" {
  description = "Primary AWS Region to be used"
  type        = string
}

variable "project" {
  description = "The Project Name"
  type        = string
}

variable "env" {
  description = "The current environment"
  type        = string
}

variable "module" {
  description = "The Descriptive Name for this module"
  type        = string
}

variable "config" {
  description = "configuration map for this module. Defined in _envs yaml files"
  type = object({
    s3_datalake = map(any)

    # states if global resources at level account has already been deployed
    # (used when multiple environment points to the same account)
    global_resources_already_deployed = bool
  })
}
```

---

## modules/silver/_local.tf

```hcl
locals {
  prefix        = "${var.env}-${var.project}-${var.module}"
  global_suffix = "${var.region}-${var.account_id}"
}
```

---

## modules/silver/_output.tf

```hcl
# Nessun output richiesto per il modulo silver base.
# Aggiungere output se altri moduli dipendono da questo (es. ARN policy).
```

---

## modules/silver/silver.tf

```hcl
#
# Database for Silver tables
#
resource "aws_glue_catalog_database" "{dominio}_silver" {
  name = var.env == "prod" ? "{dominio}_silver" : "${var.env}_{dominio}_silver"

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_iam_policy" "{dominio}_silver_access" {
  name = "${local.prefix}-{dominio}-silver-access"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          # catalog read
          "glue:GetDatabase",
          "glue:GetTable",
          "glue:GetTables",
          "glue:GetPartition",
          "glue:GetPartitions",
          "glue:BatchGetPartition",
          # partition write (Glue jobs scrivono le partizioni Iceberg)
          "glue:CreatePartition",
          "glue:BatchCreatePartition",
          "glue:UpdatePartition",
        ],
        Effect = "Allow",
        Resource = [
          "arn:aws:glue:${var.region}:${var.account_id}:catalog",
          "arn:aws:glue:${var.region}:${var.account_id}:database/${aws_glue_catalog_database.{dominio}_silver.name}",
          "arn:aws:glue:${var.region}:${var.account_id}:table/${aws_glue_catalog_database.{dominio}_silver.name}/*",
          "arn:aws:glue:${var.region}:${var.account_id}:partition/${aws_glue_catalog_database.{dominio}_silver.name}/*/*",
        ]
      }
    ]
  })
}
```

---

## Differenza Bronze vs Silver — Azioni IAM

| Azione | Bronze | Silver |
|---|---|---|
| `glue:GetDatabase` | ✅ | ✅ |
| `glue:GetTable` / `GetTables` | ✅ | ✅ |
| `glue:GetPartition` / `GetPartitions` / `BatchGetPartition` | ✅ | ✅ |
| `glue:CreatePartition` / `BatchCreatePartition` / `UpdatePartition` | ✅ | ✅ |
| `glue:StartCrawler` / `StopCrawler` | ✅ | ❌ |
| `glue:GetCrawler` / `GetCrawlerMetrics` | ✅ | ❌ |
| `glue:UpdateDatabase` / `CreateDatabase` | ✅ | ❌ |

Il layer silver **non ha crawler** — le partizioni Iceberg sono gestite direttamente dai Glue jobs.
Le azioni crawler lifecycle sono escluse dalla policy silver per principio di least privilege.

---

## Evoluzione del modulo silver

Il template base crea solo il database Glue e la policy di accesso.
In un repo ETL completo (`datalake-{dominio}-etl`) il modulo silver aggiunge:

- `aws_glue_job` — Glue jobs PySpark per la trasformazione bronze→silver
- `aws_sfn_state_machine` — Step Functions per orchestrazione
- `aws_cloudwatch_event_rule` — EventBridge scheduler
- Tabelle Iceberg (create dai Glue jobs, non da Terraform)

Nel repo IaC puro (`datalake-{dominio}-iac`) il modulo silver è intenzionalmente minimale:
registra il database nel catalogo e predispone le policy IAM per i job ETL del repo separato.
