# Template: modules/silver/tests/silver_resources.tftest.hcl

Sostituisci solo `{dominio}` con il valore reale.
`account_id` e `region` usano i default SIAE — cambia solo se l'utente specifica valori diversi.

**Default SIAE:**
- `region` = `eu-west-1`
- `account_id` dev/qa = `613577363574`
- `account_id` prod = `043188932291`

```hcl
# ---------------------------------------------------------------------------
# IaC tests for the silver module.
# Verifica naming del Glue database e della IAM policy su dev, qa, prod.
# Esecuzione: cd modules/silver && terraform init -backend=false && terraform test
# ---------------------------------------------------------------------------

mock_provider "aws" {}

variables {
  account_id = "613577363574"   # default SIAE dev/qa
  region     = "eu-west-1"      # default SIAE
  project    = "{dominio}"
  module     = "silver"
  env        = "dev"

  config = {
    s3_datalake = {
      backup = "default"
    }
    global_resources_already_deployed = false
  }
}

# ---------------------------------------------------------------------------
# DEV
# ---------------------------------------------------------------------------
run "dev_database_has_prefixed_name" {
  command = plan

  assert {
    condition     = aws_glue_catalog_database.{dominio}_silver.name == "dev_{dominio}_silver"
    error_message = "In dev il database deve chiamarsi 'dev_{dominio}_silver'."
  }
}

run "dev_iam_policy_name_and_resources" {
  command = plan

  assert {
    condition     = aws_iam_policy.{dominio}_silver_access.name == "dev-{dominio}-silver-{dominio}-silver-access"
    error_message = "La IAM policy in dev deve avere il prefix 'dev-{dominio}-silver-'."
  }

  assert {
    condition = contains(
      flatten([
        for stmt in jsondecode(aws_iam_policy.{dominio}_silver_access.policy).Statement :
        stmt.Resource
      ]),
      "arn:aws:glue:eu-west-1:613577363574:database/dev_{dominio}_silver"
    )
    error_message = "In dev la IAM policy deve riferire il database 'dev_{dominio}_silver'."
  }
}

# ---------------------------------------------------------------------------
# QA
# ---------------------------------------------------------------------------
run "qa_database_has_prefixed_name" {
  command = plan

  variables {
    env = "qa"
  }

  assert {
    condition     = aws_glue_catalog_database.{dominio}_silver.name == "qa_{dominio}_silver"
    error_message = "In qa il database deve chiamarsi 'qa_{dominio}_silver'."
  }

  assert {
    condition     = aws_iam_policy.{dominio}_silver_access.name == "qa-{dominio}-silver-{dominio}-silver-access"
    error_message = "La IAM policy in qa deve avere il prefix 'qa-{dominio}-silver-'."
  }

  assert {
    condition = contains(
      flatten([
        for stmt in jsondecode(aws_iam_policy.{dominio}_silver_access.policy).Statement :
        stmt.Resource
      ]),
      "arn:aws:glue:eu-west-1:613577363574:database/qa_{dominio}_silver"
    )
    error_message = "In qa la IAM policy deve riferire il database 'qa_{dominio}_silver'."
  }
}

# ---------------------------------------------------------------------------
# PROD
# ---------------------------------------------------------------------------
run "prod_database_has_no_prefix" {
  command = plan

  variables {
    env = "prod"
  }

  assert {
    condition     = aws_glue_catalog_database.{dominio}_silver.name == "{dominio}_silver"
    error_message = "In prod il database deve chiamarsi '{dominio}_silver' (senza prefix env)."
  }

  assert {
    condition     = aws_iam_policy.{dominio}_silver_access.name == "prod-{dominio}-silver-{dominio}-silver-access"
    error_message = "La IAM policy in prod deve avere il prefix 'prod-{dominio}-silver-'."
  }

  assert {
    condition = contains(
      flatten([
        for stmt in jsondecode(aws_iam_policy.{dominio}_silver_access.policy).Statement :
        stmt.Resource
      ]),
      "arn:aws:glue:eu-west-1:043188932291:database/{dominio}_silver"   # default SIAE prod
    )
    error_message = "In prod la IAM policy deve riferire il database '{dominio}_silver' senza prefix."
  }
}
```
