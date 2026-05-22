# Template: modules/bronze/tests/bronze_resources.tftest.hcl

Sostituisci il placeholder `{dominio}` e `{tabella}` con i valori reali.
`account_id` e `region` usano i default SIAE — cambia solo se l'utente specifica valori diversi.

**Default SIAE:**
- `region` = `eu-west-1`
- `account_id` dev/qa = `613577363574`
- `account_id` prod = `043188932291`

```hcl
# ---------------------------------------------------------------------------
# IaC tests for the bronze module.
# Verifica che il piano Terraform produca le risorse attese per dev, qa, prod.
# Esecuzione: cd modules/bronze && terraform init -backend=false && terraform test
# ---------------------------------------------------------------------------

mock_provider "aws" {}

variables {
  account_id              = "613577363574"   # default SIAE dev/qa
  region                  = "eu-west-1"      # default SIAE
  project                 = "{dominio}"
  module                  = "bronze"
  env                     = "dev"
  s3_datalake_bronze_name = "dev-datalake-bronze"

  config = {
    crawler_scheduling = {
      status = true
      cron   = "cron(0 0 * * ? *)"
    }
  }

  {dominio}_tables_def = [
    {
      name = "{tabella}"
      path = "{tabella}"
      columns = [
        { Name = "op", Type = "string" },
        { Name = "cf", Type = "string" },
      ]
    }
  ]
}

# ---------------------------------------------------------------------------
# DEV
# ---------------------------------------------------------------------------
run "dev_database_has_prefixed_name" {
  command = plan

  assert {
    condition     = aws_glue_catalog_database.{dominio}_bronze.name == "dev_{dominio}_bronze"
    error_message = "In dev il database deve chiamarsi 'dev_{dominio}_bronze'."
  }
}

run "dev_tables_are_planned" {
  command = plan

  assert {
    condition     = length(aws_glue_catalog_table.{dominio}_bronze_tables) == 1
    error_message = "In dev deve essere pianificata esattamente 1 tabella ({tabella})."
  }

  assert {
    condition = alltrue([
      for t in aws_glue_catalog_table.{dominio}_bronze_tables :
      startswith(t.storage_descriptor[0].location, "s3://dev-datalake-bronze/bronze/{dominio}/")
    ])
    error_message = "La location delle tabelle deve puntare al bucket bronze di dev."
  }
}

run "dev_crawler_is_named_with_env_prefix" {
  command = plan

  assert {
    condition     = aws_glue_crawler.{dominio}_tables.name == "dev-{dominio}-bronze-{dominio}-crawler-parquet"
    error_message = "Il nome del crawler in dev deve includere il prefix 'dev-{dominio}-bronze-'."
  }

  assert {
    condition     = aws_glue_crawler.{dominio}_tables.schedule == "cron(0 0 * * ? *)"
    error_message = "Il crawler in dev deve avere la schedule configurata quando status=true."
  }
}

run "dev_iam_role_trusts_glue_service" {
  command = plan

  assert {
    condition = contains(
      [
        for stmt in jsondecode(aws_iam_role.{dominio}_crawler.assume_role_policy).Statement :
        try(stmt.Principal.Service, "")
      ],
      "glue.amazonaws.com"
    )
    error_message = "Il IAM role deve consentire a glue.amazonaws.com di assumere il ruolo."
  }
}

run "dev_iam_policy_name_has_env_prefix" {
  command = plan

  assert {
    condition     = aws_iam_policy.{dominio}_bronze_db_access.name == "dev-{dominio}-bronze-{dominio}-bronze-access"
    error_message = "La IAM policy in dev deve avere il prefix 'dev-{dominio}-bronze-'."
  }
}

# ---------------------------------------------------------------------------
# QA
# ---------------------------------------------------------------------------
run "qa_database_has_prefixed_name" {
  command = plan

  variables {
    env                     = "qa"
    s3_datalake_bronze_name = "qa-datalake-bronze"
  }

  assert {
    condition     = aws_glue_catalog_database.{dominio}_bronze.name == "qa_{dominio}_bronze"
    error_message = "In qa il database deve chiamarsi 'qa_{dominio}_bronze'."
  }

  assert {
    condition     = aws_glue_crawler.{dominio}_tables.name == "qa-{dominio}-bronze-{dominio}-crawler-parquet"
    error_message = "Il crawler in qa deve avere il prefix 'qa-{dominio}-bronze-'."
  }

  assert {
    condition = alltrue([
      for t in aws_glue_catalog_table.{dominio}_bronze_tables :
      startswith(t.storage_descriptor[0].location, "s3://qa-datalake-bronze/bronze/{dominio}/")
    ])
    error_message = "La location delle tabelle deve puntare al bucket bronze di qa."
  }
}

run "qa_crawler_schedule_disabled_when_status_false" {
  command = plan

  variables {
    env                     = "qa"
    s3_datalake_bronze_name = "qa-datalake-bronze"
    config = {
      crawler_scheduling = {
        status = false
        cron   = "cron(0 0 * * ? *)"
      }
    }
  }

  assert {
    condition     = aws_glue_crawler.{dominio}_tables.schedule == null
    error_message = "Il crawler NON deve avere schedule quando status=false."
  }
}

# ---------------------------------------------------------------------------
# PROD
# ---------------------------------------------------------------------------
run "prod_database_has_no_prefix" {
  command = plan

  variables {
    env                     = "prod"
    s3_datalake_bronze_name = "prod-datalake-bronze"
  }

  assert {
    condition     = aws_glue_catalog_database.{dominio}_bronze.name == "{dominio}_bronze"
    error_message = "In prod il database deve chiamarsi '{dominio}_bronze' (senza prefix env)."
  }

  assert {
    condition     = aws_glue_crawler.{dominio}_tables.name == "prod-{dominio}-bronze-{dominio}-crawler-parquet"
    error_message = "Il crawler in prod deve avere il prefix 'prod-{dominio}-bronze-'."
  }

  assert {
    condition = alltrue([
      for t in aws_glue_catalog_table.{dominio}_bronze_tables :
      startswith(t.storage_descriptor[0].location, "s3://prod-datalake-bronze/bronze/{dominio}/")
    ])
    error_message = "La location delle tabelle deve puntare al bucket bronze di prod."
  }

  assert {
    condition     = aws_iam_policy.{dominio}_bronze_db_access.name == "prod-{dominio}-bronze-{dominio}-bronze-access"
    error_message = "La IAM policy in prod deve avere il prefix 'prod-{dominio}-bronze-'."
  }
}

run "prod_iam_policy_targets_prod_database_arn" {
  command = plan

  variables {
    env                     = "prod"
    s3_datalake_bronze_name = "prod-datalake-bronze"
  }

  assert {
    condition = contains(
      flatten([
        for stmt in jsondecode(aws_iam_policy.{dominio}_bronze_db_access.policy).Statement :
        stmt.Resource
      ]),
      "arn:aws:glue:eu-west-1:043188932291:database/{dominio}_bronze"   # default SIAE prod
    )
    error_message = "In prod la IAM policy deve riferire il database '{dominio}_bronze' senza prefix."
  }
}
```
