---
name: siae-datalake-iac-test
description: >
  Crea i test IaC (Terraform Test Framework) per un repo datalake-{dominio}-iac SIAE.
  Genera tre suite di test: modulo bronze (risorse AWS pianificate), modulo silver
  (naming database e IAM policy), tables_definition (coerenza YAML bronze e DDL silver).
  Nessun deploy reale, nessuna AWS call — solo `terraform plan` con mock provider.
  Trigger: aggiungere test IaC datalake, test bronze module, test silver module,
  test tables_definition, verificare infrastruttura datalake, test terraform datalake,
  test offline deploy, siae-datalake-iac-test.
---

# SIAE Datalake IaC Test

> **Tipo:** Flexible | **Fase SDLC:** 3. Testing & Verification

Genera tre suite di test Terraform per un repo `datalake-{dominio}-iac`.
Nessun provider AWS reale — tutto gira con `mock_provider "aws" {}` o senza provider.

```
Checklist:
- [ ] Step 1: Raccolta informazioni dominio
- [ ] Step 2: Test modulo bronze  →  modules/bronze/tests/
- [ ] Step 3: Test modulo silver  →  modules/silver/tests/
- [ ] Step 4: Test tables_definition  →  tables_definition/tests/
- [ ] Step 5: Verifica esecuzione locale
```

---

## Default SIAE (usa sempre questi salvo diversa indicazione esplicita dell'utente)

| Parametro | Default |
|---|---|
| Region (tutti gli ambienti) | `eu-west-1` |
| Account ID dev | `613577363574` |
| Account ID qa | `613577363574` |
| Account ID prod | `043188932291` |

> Sovrascrivere solo se l'utente specifica esplicitamente valori diversi.

---

## 1. Informazioni da Raccogliere

| Informazione | Esempio | Dove si trova |
|---|---|---|
| Nome dominio | `zucchetti` | `config.yaml → project_name` |
| Region primaria | `eu-west-1` (**default**) | `config.yaml → region.primary` |
| Account ID dev/qa | `613577363574` (**default**) | DDL silver dev o env vars GitHub |
| Account ID prod | `043188932291` (**default**) | DDL silver prod o env vars GitHub |
| Nome bucket bronze (per env) | `dev-datalake-bronze` | `live/_envs/dev.yaml` o `.tmpl` |
| Nome bucket silver (per env) | `dev-datalake-silver-tier-eu-west-1-613577363574` | DDL silver |
| Tabelle bronze definite | `[trasferte]` | `tables_definition/bronze/{dominio}.yaml` |
| Colonne CDC grezze bronze | `op, commit_time, transact_id` | YAML bronze |
| Colonne CDC silver | `last_op, last_commit_time, last_transact_id, deleted, last_updated_at` | DDL silver |

Leggi i file sorgente prima di scrivere i test:
```bash
cat config.yaml
cat tables_definition/bronze/{dominio}.yaml
cat tables_definition/silver/dev-{dominio}-silver-ddl.sql
cat tables_definition/silver/qa-{dominio}-ddl.sql
cat tables_definition/silver/prod-{dominio}-ddl.sql
cat modules/bronze/_input.tf
cat modules/silver/_input.tf
cat modules/bronze/bronze.tf
cat modules/silver/silver.tf
```

---

## 2. Test Modulo Bronze — `modules/bronze/tests/`

Crea/aggiorna `modules/bronze/tests/bronze_resources.tftest.hcl`.

### Struttura obbligatoria

```hcl
mock_provider "aws" {}

variables {
  account_id              = "123456789012"
  region                  = "{region}"         # es. "eu-west-1"
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
        # ... prime 2 colonne rappresentative dal YAML bronze
      ]
    }
  ]
}
```

### Run obbligatori per ogni suite bronze

Implementa questi run per `dev`, `qa`, `prod` seguendo il pattern della variante `env`:

| Run | Cosa verifica | Env |
|---|---|---|
| `dev_database_has_prefixed_name` | `aws_glue_catalog_database.{dominio}_bronze.name == "dev_{dominio}_bronze"` | dev |
| `dev_tables_are_planned` | `length(aws_glue_catalog_table.{dominio}_bronze_tables) == 1`, location su bucket dev | dev |
| `dev_crawler_is_named_with_env_prefix` | nome crawler `"dev-{dominio}-bronze-{dominio}-crawler-parquet"`, schedule presente | dev |
| `dev_iam_role_trusts_glue_service` | `assume_role_policy` contiene `"glue.amazonaws.com"` | dev |
| `dev_iam_policy_name_has_env_prefix` | `aws_iam_policy.{dominio}_bronze_db_access.name == "dev-{dominio}-bronze-{dominio}-bronze-access"` | dev |
| `qa_database_has_prefixed_name` | db `"qa_{dominio}_bronze"`, crawler `"qa-*"`, bucket qa | qa |
| `qa_crawler_schedule_disabled_when_status_false` | `aws_glue_crawler.{dominio}_tables.schedule == null` quando `status=false` | qa |
| `prod_database_has_no_prefix` | `"{dominio}_bronze"` senza prefisso env | prod |
| `prod_iam_policy_targets_prod_database_arn` | ARN database `"arn:aws:glue:{region}:123456789012:database/{dominio}_bronze"` | prod |

### Regole di naming bronze

```
database name:
  prod  → {dominio}_bronze
  altri → {env}_{dominio}_bronze

crawler name:
  {env}-{dominio}-bronze-{dominio}-crawler-parquet

IAM policy name:
  {env}-{dominio}-bronze-{dominio}-bronze-access

location tabella:
  s3://{s3_datalake_bronze_name}/bronze/{dominio}/{path}/
```

Crea anche `modules/bronze/tests/README.md` con elenco run e istruzioni esecuzione.

---

## 3. Test Modulo Silver — `modules/silver/tests/`

Crea/aggiorna `modules/silver/tests/silver_resources.tftest.hcl`.

### Struttura obbligatoria

```hcl
mock_provider "aws" {}

variables {
  account_id = "123456789012"
  region     = "{region}"
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
```

### Run obbligatori per ogni suite silver

| Run | Cosa verifica | Env |
|---|---|---|
| `dev_database_has_prefixed_name` | `aws_glue_catalog_database.{dominio}_silver.name == "dev_{dominio}_silver"` | dev |
| `dev_iam_policy_name_and_resources` | policy `"dev-{dominio}-silver-{dominio}-silver-access"`, ARN `"dev_{dominio}_silver"` | dev |
| `qa_database_has_prefixed_name` | `"qa_{dominio}_silver"`, policy `"qa-{dominio}-silver-*"`, ARN `"qa_{dominio}_silver"` | qa |
| `prod_database_has_no_prefix` | `"{dominio}_silver"` senza prefisso env, policy `"prod-{dominio}-silver-*"` | prod |

### Regole di naming silver

```
database name:
  prod  → {dominio}_silver
  altri → {env}_{dominio}_silver

IAM policy name:
  {env}-{dominio}-silver-{dominio}-silver-access
```

Crea anche `modules/silver/tests/README.md` con elenco run, istruzioni esecuzione e workaround Zscaler (vedi [reference/zscaler-workaround.md](reference/zscaler-workaround.md)).

---

## 4. Test Tables Definition — `tables_definition/tests/`

Questa suite non usa provider AWS — valida i file dati del dominio con `yamldecode`/`file()`.

### 4A — `tables_definition/tests/main.tf`

```hcl
terraform {
  required_version = ">= 1.6.0"
}

locals {
  bronze_yaml             = yamldecode(file("${path.module}/../bronze/{dominio}.yaml"))
  bronze_tables           = local.bronze_yaml.tables
  bronze_table_names      = [for t in local.bronze_tables : t.name]
  bronze_{tabella}        = one([for t in local.bronze_tables : t if t.name == "{tabella}"])
  bronze_{tabella}_columns = local.bronze_{tabella} != null ? [for c in local.bronze_{tabella}.columns : c.Name] : []
  bronze_{tabella}_types  = local.bronze_{tabella} != null ? distinct([for c in local.bronze_{tabella}.columns : c.Type]) : []

  ddl_dev  = file("${path.module}/../silver/dev-{dominio}-silver-ddl.sql")
  ddl_qa   = file("${path.module}/../silver/qa-{dominio}-ddl.sql")
  ddl_prod = file("${path.module}/../silver/prod-{dominio}-ddl.sql")

  # Colonne business: tutte le colonne del YAML bronze
  # escluse quelle CDC grezze (op, commit_time, transact_id) che in silver
  # diventano last_op, last_commit_time, last_transact_id.
  silver_business_columns = [
    # popola con le colonne business reali del dominio, lette dal YAML bronze
  ]

  silver_cdc_columns = [
    "last_op", "last_commit_time", "last_transact_id", "deleted", "last_updated_at",
  ]
}

output "bronze_tables"              { value = local.bronze_tables }
output "bronze_table_names"         { value = local.bronze_table_names }
output "bronze_{tabella}_columns"   { value = local.bronze_{tabella}_columns }
output "bronze_{tabella}_types"     { value = local.bronze_{tabella}_types }
output "ddl_dev"                    { value = local.ddl_dev }
output "ddl_qa"                     { value = local.ddl_qa }
output "ddl_prod"                   { value = local.ddl_prod }
output "silver_business_columns"    { value = local.silver_business_columns }
output "silver_cdc_columns"         { value = local.silver_cdc_columns }
```

### 4B — `tables_definition/tests/bronze_yaml.tftest.hcl`

Run obbligatori:

| Run | Assert |
|---|---|
| `bronze_yaml_has_{tabella}_table` | `contains(output.bronze_table_names, "{tabella}")`, no duplicati tabelle |
| `bronze_{tabella}_columns_are_all_string` | `length(types) == 1 && types[0] == "string"` |
| `bronze_{tabella}_has_required_columns` | colonne CDC grezze: `op`, `commit_time`, `transact_id` |
| `bronze_{tabella}_has_business_columns` | gruppi di colonne specifici del dominio (anagrafiche, temporali, ecc.) |
| `bronze_{tabella}_columns_are_unique` | `length(cols) == length(distinct(cols))` |
| `bronze_{tabella}_path_matches_name` | `output.bronze_tables[0].path == output.bronze_tables[0].name` |

### 4C — `tables_definition/tests/silver_ddl.tftest.hcl`

Run obbligatori per DEV, QA, PROD + cross-env:

**Per ciascun ambiente:**

| Run | Assert |
|---|---|
| `{env}_ddl_targets_{env}_{dominio}_silver_database` | `strcontains(output.ddl_{env}, "CREATE TABLE IF NOT EXISTS {db_name}.{tabella}")` |
| `{env}_ddl_uses_{env}_silver_bucket` | `strcontains(output.ddl_{env}, "s3://{bucket}/{dominio}/{tabella}")` |
| `{env}_ddl_is_iceberg_partitioned_by_last_updated_at` | `PARTITIONED BY`, `'table_type'='iceberg'`, `'format'='parquet'` |
| `{env}_ddl_has_all_business_columns` | `alltrue([for c in output.silver_business_columns : strcontains(ddl, c)])` |
| `{env}_ddl_has_cdc_columns` | tutte le colonne CDC silver |

**Solo DEV (tipi castati):**

| Run | Assert |
|---|---|
| `dev_ddl_casts_{colonna_numerica}_to_decimal` | colonne con cast `decimal(38,10)` |
| `dev_ddl_{colonna_timestamp}_is_timestamp` | `last_commit_time` come `timestamp` |

**Solo PROD:**

| Run | Assert |
|---|---|
| `prod_ddl_targets_{dominio}_silver_database_without_prefix` | `NOT contains "prod_{dominio}_silver"` |
| `prod_ddl_does_not_reference_dev_or_qa_buckets` | `NOT strcontains dev-datalake-silver`, `NOT strcontains qa-datalake-silver` |

**Cross-env:**

| Run | Assert |
|---|---|
| `all_ddls_share_same_business_schema` | ogni colonna in `silver_business_columns + silver_cdc_columns` presente in tutti e 3 i DDL |
| `bronze_business_columns_are_present_in_silver_dev` | ogni colonna bronze non-CDC presente in DDL dev |

Crea anche `tables_definition/tests/README.md` con elenco run e istruzioni.

---

## 5. Verifica Esecuzione

Esegui i test in quest'ordine e mostra l'output:

```bash
# Bronze
cd modules/bronze
terraform init -backend=false
terraform test

# Silver
cd ../../modules/silver
terraform init -backend=false
terraform test

# Tables definition
cd ../../tables_definition/tests
terraform init -backend=false
terraform test
```

Output atteso per ogni suite:
```
Success! N passed, 0 failed.
```

Se un test fallisce: mostra l'assert fallito, identifica la causa (naming errato, colonna mancante, DDL non aggiornato) e correggi il file sorgente o il test.

---

## Vincoli Inviolabili

| # | Vincolo |
|---|---------|
| V1 | `mock_provider "aws" {}` obbligatorio in bronze e silver — nessuna chiamata AWS reale |
| V2 | `tables_definition/tests/main.tf` non deve dichiarare nessun `provider` |
| V3 | `terraform init -backend=false` sempre — nessun remote state |
| V4 | Le colonne del `zucchetti_tables_def` nel test bronze sono un **campione** (2-3 colonne), non la lista completa |
| V5 | Il test `bronze_{tabella}_columns_are_all_string` deve passare: in bronze i tipi sono tutti `string` |
| V6 | Il DDL prod deve usare database name **senza** prefisso env: `{dominio}_silver`, non `prod_{dominio}_silver` |
| V7 | `prod_ddl_does_not_reference_dev_or_qa_buckets` è obbligatorio — isolamento prod |
| V8 | I README dei test devono includere il workaround Zscaler (`-plugin-dir`) |

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realtà |
|---|---|
| "Metto la lista completa delle colonne nel `variables {}` del test bronze" | Solo un campione: il test verifica il piano Terraform, non la completezza dello schema |
| "Salto i test cross-env perché sono ridondanti" | `all_ddls_share_same_business_schema` è il guardrail più importante: blocca derive tra ambienti |
| "Il cast `decimal(38,10)` lo verifico solo in dev" | Corretto — i DDL di qa e prod sono identici per schema, il tipo è già verificato cross-env |
| "Uso `command = apply` per essere sicuro" | Mai: con `mock_provider` non ci sono risorse reali. Solo `command = plan` |
| "Creo un unico file `.tftest.hcl` per tutto" | Separa bronze/silver (hanno provider) da tables_definition (nessun provider): `init` diversi |

---

## Risorse

- [reference/bronze-test-template.md](reference/bronze-test-template.md) — template completo `bronze_resources.tftest.hcl`
- [reference/silver-test-template.md](reference/silver-test-template.md) — template completo `silver_resources.tftest.hcl`
- [reference/tables-test-template.md](reference/tables-test-template.md) — template completo `main.tf` + `bronze_yaml.tftest.hcl` + `silver_ddl.tftest.hcl`
- [reference/zscaler-workaround.md](reference/zscaler-workaround.md) — workaround Zscaler per `terraform init`
