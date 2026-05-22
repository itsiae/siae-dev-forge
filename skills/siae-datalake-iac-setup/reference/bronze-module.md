# Template Modulo Bronze — datalake-{dominio}-iac

> Template completo dei file Terraform per il modulo bronze.
> Sostituisci `{dominio}` con il nome del dominio (es. `zucchetti`).

---

## modules/bronze/_input.tf

```hcl
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

variable "{dominio}_tables_def" {
  description = "Tables definition for {Dominio} tables"
  type = list(object({
    name    = string
    columns = list(object({ Name = string, Type = string }))
    path    = string
  }))
}

variable "s3_datalake_bronze_name" {
  type = string
}

variable "config" {
  description = "configuration map for this module. Defined in _envs yaml files"
  type = object({
    crawler_scheduling = object({
      status = bool
      cron   = string
    })
  })
}
```

---

## modules/bronze/_local.tf

```hcl
locals {
  prefix        = "${var.env}-${var.project}-${var.module}"
  global_suffix = "${var.region}-${var.account_id}"
}
```

---

## modules/bronze/_output.tf

```hcl
# Nessun output richiesto per il modulo bronze base.
# Aggiungere output se altri moduli dipendono da questo (es. ARN policy).
```

---

## modules/bronze/bronze.tf

```hcl
#
# ------------------------------------------- DATABASE -------------------------------------------
#

resource "aws_glue_catalog_database" "{dominio}_bronze" {
  name = var.env == "prod" ? "{dominio}_bronze" : "${var.env}_{dominio}_bronze"

  lifecycle {
    prevent_destroy = true
  }
}

data "aws_s3_bucket" "datalake_bronze" {
  bucket = var.s3_datalake_bronze_name
}


#
# ------------------------------------------- TABLES -------------------------------------------
#

locals {
  {dominio}_tables_by_name = {
    for t in var.{dominio}_tables_def :
    t.name => t
  }
}

resource "aws_glue_catalog_table" "{dominio}_bronze_tables" {
  for_each = local.{dominio}_tables_by_name

  name          = each.value.name
  database_name = aws_glue_catalog_database.{dominio}_bronze.name

  table_type = "EXTERNAL_TABLE"

  storage_descriptor {
    location      = "s3://${data.aws_s3_bucket.datalake_bronze.bucket}/bronze/{dominio}/${each.value.path}/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "parquet"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    dynamic "columns" {
      for_each = each.value.columns
      content {
        name = columns.value["Name"]
        type = columns.value["Type"]
      }
    }
  }

  partition_keys {
    name = "year"
    type = "string"
  }
  partition_keys {
    name = "month"
    type = "string"
  }
  partition_keys {
    name = "day"
    type = "string"
  }
}


#
# ------------------------------------------- CRAWLERS -------------------------------------------
#

resource "aws_glue_crawler" "{dominio}_tables" {
  database_name = aws_glue_catalog_database.{dominio}_bronze.name
  name          = "${local.prefix}-{dominio}-crawler-parquet"
  schedule      = var.config.crawler_scheduling.status ? var.config.crawler_scheduling.cron : null

  role = aws_iam_role.{dominio}_crawler.arn

  catalog_target {
    database_name = aws_glue_catalog_database.{dominio}_bronze.name
    tables        = [for table in aws_glue_catalog_table.{dominio}_bronze_tables : table.name]
  }

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "LOG"
  }

  configuration = jsonencode(
    {
      "Version" : 1.0,
      "CrawlerOutput" : {
        "Partitions" : { "AddOrUpdateBehavior" : "InheritFromTable" }
      }
    }
  )
}

resource "aws_iam_role" "{dominio}_crawler" {
  name = "${local.prefix}-{dominio}-crawler-parquet"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action    = "sts:AssumeRole",
        Effect    = "Allow",
        Principal = { Service = "glue.amazonaws.com" }
      }
    ]
  })

  inline_policy {
    name = "read-bucket"
    policy = jsonencode({
      Version = "2012-10-17",
      Statement = [
        {
          Action   = ["s3:GetObject", "s3:ListBucket"],
          Effect   = "Allow",
          Resource = [
            "${data.aws_s3_bucket.datalake_bronze.arn}",
            "${data.aws_s3_bucket.datalake_bronze.arn}/*"
          ]
        }
      ]
    })
  }

  inline_policy {
    name = "logs-access"
    policy = jsonencode({
      Version = "2012-10-17",
      Statement = [
        {
          Action = [
            "logs:CreateLogGroup",
            "logs:CreateLogStream",
            "logs:PutLogEvents"
          ],
          Effect   = "Allow",
          Resource = [
            "arn:aws:logs:${var.region}:${var.account_id}:*",
            "arn:aws:logs:${var.region}:${var.account_id}:log-group:*",
          ]
        }
      ]
    })
  }
}

resource "aws_iam_policy" "{dominio}_bronze_db_access" {
  name = "${local.prefix}-{dominio}-bronze-access"

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
          # partition write (crawler popola le partizioni)
          "glue:CreatePartition",
          "glue:BatchCreatePartition",
          "glue:UpdatePartition",
          # crawler lifecycle
          "glue:StartCrawler",
          "glue:StopCrawler",
          "glue:GetCrawler",
          "glue:GetCrawlerMetrics",
          "glue:UpdateDatabase",
          "glue:CreateDatabase",
        ],
        Effect = "Allow",
        Resource = [
          "arn:aws:glue:${var.region}:${var.account_id}:catalog",
          "arn:aws:glue:${var.region}:${var.account_id}:database/${aws_glue_catalog_database.{dominio}_bronze.name}",
          "arn:aws:glue:${var.region}:${var.account_id}:table/${aws_glue_catalog_database.{dominio}_bronze.name}/*",
          "arn:aws:glue:${var.region}:${var.account_id}:partition/${aws_glue_catalog_database.{dominio}_bronze.name}/*/*",
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "{dominio}_crawler_db_access" {
  role       = aws_iam_role.{dominio}_crawler.id
  policy_arn = aws_iam_policy.{dominio}_bronze_db_access.arn
}
```

---

## Note di sostituzione

Quando usi questo template, sostituisci `{dominio}` con il nome esatto del dominio:

| Placeholder | Esempio (dominio = zucchetti) |
|---|---|
| `{dominio}` | `zucchetti` |
| `{Dominio}` | `Zucchetti` (solo per commenti/titoli) |

Il path S3 (`bronze/{dominio}/...`) deve corrispondere alla struttura del bucket bronze della piattaforma.
Verifica con il team di data platform il path esatto prima di fare `terraform apply`.
