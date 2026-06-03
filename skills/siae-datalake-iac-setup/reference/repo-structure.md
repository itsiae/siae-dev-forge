# Struttura Repository — datalake-{dominio}-iac

> Struttura directory canonica, template file, e pattern IaC per repo IaC datalake SIAE.
> Basato su `datalake-zucchetti-iac` e `datalake-edw-iac`.

---

## Struttura completa

```
datalake-{dominio}-iac/
├── config.yaml                          # Configurazione globale (nomi, tag, region)
├── Makefile                             # Deploy shortcuts via git tag
├── utils/deploy-tag.sh                  # Script alternativo per push tag
├── chart/
│   └── Chart.yaml                       # Helm chart metadata (name, repository)
├── .github/
│   ├── CODEOWNERS
│   ├── CODE_OF_CONDUCT.md
│   ├── CONTRIBUTING.md
│   ├── SECURITY.md
│   ├── copilot-instructions.md
│   └── workflows/
│       ├── cd-terragrunt-plan-collaudo.yaml          # Plan only collaudo
│       ├── cd-terragrunt-plan-deploy-collaudo.yaml   # Plan + apply collaudo
│       ├── cd-terragrunt-plan-certificazione.yaml    # Plan only cert
│       ├── cd-terragrunt-plan-deploy-certificazione.yaml
│       ├── cd-terragrunt-plan-produzione.yaml        # Plan only prod (manual dispatch)
│       ├── cd-terragrunt-plan-deploy-produzione.yaml # Plan + apply prod (manual dispatch)
│       ├── code-scan.yaml                            # Qodana weekly scan
│       └── release-please.yaml                       # Release automation
├── live/
│   ├── terragrunt.hcl                   # Root: backend S3, provider AWS, default_tags
│   ├── _envs/
│   │   ├── dev.tmpl                     # Template variabili dev (placeholder $VAR)
│   │   ├── qa.tmpl                      # Template variabili qa
│   │   └── prod.tmpl                    # Template variabili prod
│   ├── bronze/
│   │   └── terragrunt.hcl              # Modulo bronze
│   └── silver/
│       └── terragrunt.hcl              # Modulo silver
├── modules/
│   ├── bronze/
│   │   ├── _input.tf
│   │   ├── _local.tf
│   │   ├── _output.tf
│   │   └── bronze.tf                   # Glue DB, tabelle, crawler, IAM
│   └── silver/
│       ├── _input.tf
│       ├── _local.tf
│       ├── _output.tf
│       └── silver.tf                   # Glue DB silver, IAM policy
└── tables_definition/
    ├── bronze/
    │   └── {dominio}.yaml              # Definizione tabelle bronze (list of objects)
    ├── silver/
    │   ├── dev-{dominio}-silver-ddl.sql
    │   ├── qa-{dominio}-ddl.sql
    │   └── prod-{dominio}-ddl.sql
    └── source/
        └── {dominio}.sql               # DDL sorgente originale
```

---

## live/terragrunt.hcl (root)

```hcl
locals {
  config = yamldecode(file(find_in_parent_folders("config.yaml")))
  stage  = yamldecode(file("_envs/${get_env("ENV")}.yaml"))

  global_tags = { for t in local.config.tags: t.key => t.value }
  stage_tags  = { for t in local.stage.tags: t.key => t.value }
  default_tags = merge(local.global_tags, local.stage_tags)
}

remote_state {
  backend = "s3"
  config = {
    encrypt        = true
    bucket         = "${local.stage.env}-${local.config.repository_name}-terraform-state"
    key            = "${path_relative_to_include()}/terraform.tfstate"
    region         = local.config.region.primary
    dynamodb_table = "${local.stage.env}-${local.config.repository_name}-terraform-state"
    s3_bucket_tags      = local.default_tags
    dynamodb_table_tags = local.default_tags
  }
}

terraform {
  source = "${path_relative_from_include()}/../modules/${path_relative_to_include()}"
}

inputs = {
  default_tags = local.default_tags
}

generate "provider" {
  path      = "provider.tf"
  if_exists = "overwrite"
  contents  = <<EOF
  variable default_tags {
    type    = map
    default = {}
  }
  provider "aws" {
    region = "${local.config.region.primary}"
    default_tags {
      tags = var.default_tags
    }
  }
  EOF
}

generate "backend" {
  path      = "backend.tf"
  if_exists = "overwrite"
  contents  = <<EOF
  terraform {
    backend "s3" {}
  }
  EOF
}
```

> ⚠️ Nel root `terragrunt.hcl` **non** c'è default per `get_env("ENV")` — la variabile
> ENV viene sempre settata dalla CI/CD. Il default "dev" è solo nei `live/bronze/` e
> `live/silver/terragrunt.hcl` per esecuzioni locali.

---

## live/_envs/ — Template ambienti

I file `.tmpl` contengono placeholder `$VARIABILE` sostituiti dalla CI/CD a runtime.
I file `.yaml` generati **non sono committati nel repo**.

```yaml
# dev.tmpl / qa.tmpl / prod.tmpl
env: &env $AWS_ENV

tags:
  - key: Environment
    value: *env

s3_datalake_bronze_name: $S3_DATALAKE_BRONZE_NAME
s3_datalake_silver_name: $S3_DATALAKE_SILVER_NAME

config:
  crawler_scheduling:
    status: $CRON_SCHED_STATUS
    cron: $CRON_SCHED

silver:
  s3_datalake:
    backup: "default"
  global_resources_already_deployed: false
```

| Variabile | Scopo |
|---|---|
| `$AWS_ENV` | Nome ambiente (dev/qa/prod) |
| `$S3_DATALAKE_BRONZE_NAME` | Nome bucket bronze S3 |
| `$S3_DATALAKE_SILVER_NAME` | Nome bucket silver S3 |
| `$CRON_SCHED_STATUS` | `true` / `false` — scheduling crawler attivo |
| `$CRON_SCHED` | Cron expression (es. `cron(0 0 * * ? *)`) |

---

## Makefile — Deploy shortcuts

Tag pattern per CI/CD:

| Target make | Tag pushato | Workflow triggerato |
|---|---|---|
| `make plan_dev` | `rc-PLAN-COLLAUDO` | `cd-terragrunt-plan-collaudo.yaml` |
| `make dev` | `rc-COLLAUDO` | `cd-terragrunt-plan-deploy-collaudo.yaml` |
| `make plan_qa` | `rc-PLAN-CERTIFICAZIONE` | `cd-terragrunt-plan-certificazione.yaml` |
| `make qa` | `rc-CERTIFICAZIONE` | `cd-terragrunt-plan-deploy-certificazione.yaml` |
| `make prod` | — (bloccato) | Link manuale a GitHub Actions UI |

Il Makefile cancella e ricrea il tag a ogni invocazione (tag flottanti).

---

## Naming risorse AWS

| Risorsa | Pattern |
|---|---|
| Prefix generico | `${var.env}-${var.project}-${var.module}` |
| Glue DB bronze (prod) | `{dominio}_bronze` |
| Glue DB bronze (non-prod) | `{env}_{dominio}_bronze` |
| Glue DB silver (prod) | `{dominio}_silver` |
| Glue DB silver (non-prod) | `{env}_{dominio}_silver` |
| Glue Crawler | `{env}-{project}-{module}-{dominio}-crawler-parquet` |
| IAM role crawler | `{env}-{project}-{module}-{dominio}-crawler-parquet` |
| IAM policy bronze | `{env}-{project}-{module}-{dominio}-bronze-access` |
| IAM policy silver | `{env}-{project}-{module}-{dominio}-silver-access` |

---

## Remote state — Isolamento per ambiente

| Componente | Pattern |
|---|---|
| Bucket S3 | `{env}-datalake-{dominio}-iac-terraform-state` |
| Key bronze | `bronze/terraform.tfstate` |
| Key silver | `silver/terraform.tfstate` |
| DynamoDB lock | stesso nome del bucket S3 |
| Encryption | sempre `true` |
