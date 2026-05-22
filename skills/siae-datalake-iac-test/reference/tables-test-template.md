# Template: tables_definition/tests/

Tre file da creare. Sostituisci solo `{dominio}`, `{tabella}` con i valori reali.
`{tabella}` è il nome della tabella principale (es. `trasferte`).

**Default SIAE già incorporati nel template** (cambia solo su indicazione esplicita dell'utente):
- Region: `eu-west-1`
- Account ID dev/qa: `613577363574`
- Account ID prod: `043188932291`

---

## tables_definition/tests/main.tf

```hcl
terraform {
  required_version = ">= 1.6.0"
}

locals {
  bronze_yaml               = yamldecode(file("${path.module}/../bronze/{dominio}.yaml"))
  bronze_tables             = local.bronze_yaml.tables
  bronze_table_names        = [for t in local.bronze_tables : t.name]
  bronze_{tabella}          = one([for t in local.bronze_tables : t if t.name == "{tabella}"])
  bronze_{tabella}_columns  = local.bronze_{tabella} != null ? [for c in local.bronze_{tabella}.columns : c.Name] : []
  bronze_{tabella}_types    = local.bronze_{tabella} != null ? distinct([for c in local.bronze_{tabella}.columns : c.Type]) : []

  ddl_dev  = file("${path.module}/../silver/dev-{dominio}-silver-ddl.sql")
  ddl_qa   = file("${path.module}/../silver/qa-{dominio}-ddl.sql")
  ddl_prod = file("${path.module}/../silver/prod-{dominio}-ddl.sql")

  # Colonne business: popola con le colonne del YAML bronze
  # escluse quelle CDC grezze (op, commit_time, transact_id)
  silver_business_columns = [
    # es: "cf", "cognome", "nome", ...
    # LEGGI il YAML bronze e popola questo elenco
  ]

  silver_cdc_columns = [
    "last_op",
    "last_commit_time",
    "last_transact_id",
    "deleted",
    "last_updated_at",
  ]
}

output "bronze_tables"                { value = local.bronze_tables }
output "bronze_table_names"           { value = local.bronze_table_names }
output "bronze_{tabella}_columns"     { value = local.bronze_{tabella}_columns }
output "bronze_{tabella}_types"       { value = local.bronze_{tabella}_types }
output "ddl_dev"                      { value = local.ddl_dev }
output "ddl_qa"                       { value = local.ddl_qa }
output "ddl_prod"                     { value = local.ddl_prod }
output "silver_business_columns"      { value = local.silver_business_columns }
output "silver_cdc_columns"           { value = local.silver_cdc_columns }
```

---

## tables_definition/tests/bronze_yaml.tftest.hcl

```hcl
# ---------------------------------------------------------------------------
# Test sulla table definition bronze: tables_definition/bronze/{dominio}.yaml
# Esecuzione: cd tables_definition/tests && terraform init -backend=false && terraform test
# ---------------------------------------------------------------------------

run "bronze_yaml_has_{tabella}_table" {
  command = plan

  assert {
    condition     = contains(output.bronze_table_names, "{tabella}")
    error_message = "Il YAML bronze deve definire la tabella '{tabella}'."
  }

  assert {
    condition     = length(output.bronze_table_names) == length(distinct(output.bronze_table_names))
    error_message = "Il YAML bronze non deve contenere tabelle duplicate."
  }
}

run "bronze_{tabella}_columns_are_all_string" {
  command = plan

  assert {
    condition     = length(output.bronze_{tabella}_types) == 1 && output.bronze_{tabella}_types[0] == "string"
    error_message = "In bronze tutte le colonne di '{tabella}' devono essere di tipo string."
  }
}

run "bronze_{tabella}_has_cdc_columns" {
  command = plan

  assert {
    condition     = contains(output.bronze_{tabella}_columns, "op")
    error_message = "Manca la colonna CDC 'op' nel YAML bronze."
  }

  assert {
    condition     = contains(output.bronze_{tabella}_columns, "commit_time")
    error_message = "Manca la colonna CDC 'commit_time' nel YAML bronze."
  }

  assert {
    condition     = contains(output.bronze_{tabella}_columns, "transact_id")
    error_message = "Manca la colonna CDC 'transact_id' nel YAML bronze."
  }
}

run "bronze_{tabella}_has_business_columns" {
  command = plan

  # ADATTA: inserisci qui le colonne business specifiche del dominio
  assert {
    condition = alltrue([
      for c in ["{col1}", "{col2}", "{col3}"] :
      contains(output.bronze_{tabella}_columns, c)
    ])
    error_message = "Mancano una o piu' colonne business nel YAML bronze."
  }
}

run "bronze_{tabella}_columns_are_unique" {
  command = plan

  assert {
    condition     = length(output.bronze_{tabella}_columns) == length(distinct(output.bronze_{tabella}_columns))
    error_message = "Le colonne di '{tabella}' nel YAML bronze devono essere uniche."
  }
}

run "bronze_{tabella}_path_matches_name" {
  command = plan

  assert {
    condition     = output.bronze_tables[0].path == output.bronze_tables[0].name
    error_message = "Il campo 'path' della tabella deve coincidere con il 'name'."
  }
}
```

---

## tables_definition/tests/silver_ddl.tftest.hcl

```hcl
# ---------------------------------------------------------------------------
# Test sulle table definition silver (dev, qa, prod).
# Esecuzione: cd tables_definition/tests && terraform init -backend=false && terraform test
# ---------------------------------------------------------------------------

# ===========================================================================
# DEV
# ===========================================================================
run "dev_ddl_targets_dev_{dominio}_silver_database" {
  command = plan

  assert {
    condition     = strcontains(output.ddl_dev, "CREATE TABLE IF NOT EXISTS dev_{dominio}_silver.{tabella}")
    error_message = "Il DDL dev deve creare la tabella in 'dev_{dominio}_silver'."
  }
}

run "dev_ddl_uses_dev_silver_bucket" {
  command = plan

  assert {
    condition     = strcontains(output.ddl_dev, "s3://dev-datalake-silver-tier-eu-west-1-613577363574/{dominio}/{tabella}")
    error_message = "Il DDL dev deve puntare al bucket silver dev."
  }
}

run "dev_ddl_is_iceberg_partitioned_by_last_updated_at" {
  command = plan

  assert {
    condition     = strcontains(output.ddl_dev, "PARTITIONED BY (`last_updated_at`)")
    error_message = "Il DDL dev deve essere partizionato per last_updated_at."
  }

  assert {
    condition     = strcontains(output.ddl_dev, "'table_type'='iceberg'") && strcontains(output.ddl_dev, "'format'='parquet'")
    error_message = "Il DDL dev deve avere TBLPROPERTIES Iceberg + parquet."
  }
}

run "dev_ddl_has_all_business_columns" {
  command = plan

  assert {
    condition = alltrue([
      for c in output.silver_business_columns :
      strcontains(output.ddl_dev, c)
    ])
    error_message = "Il DDL dev deve contenere tutte le colonne business attese."
  }
}

run "dev_ddl_has_cdc_columns" {
  command = plan

  assert {
    condition = alltrue([
      for c in output.silver_cdc_columns :
      strcontains(output.ddl_dev, c)
    ])
    error_message = "Il DDL dev deve contenere tutte le colonne CDC standard."
  }
}

# ADATTA: aggiungi un run per ogni colonna con cast esplicito di tipo
# run "dev_ddl_casts_{colonna_numerica}_to_decimal" { ... }
# run "dev_ddl_{colonna_ts}_is_timestamp" { ... }

# ===========================================================================
# QA
# ===========================================================================
run "qa_ddl_targets_qa_{dominio}_silver_database" {
  command = plan

  assert {
    condition     = strcontains(output.ddl_qa, "CREATE TABLE IF NOT EXISTS qa_{dominio}_silver.{tabella}")
    error_message = "Il DDL qa deve creare la tabella in 'qa_{dominio}_silver'."
  }
}

run "qa_ddl_uses_qa_silver_bucket" {
  command = plan

  assert {
    condition     = strcontains(output.ddl_qa, "s3://qa-datalake-silver-tier-eu-west-1-613577363574/{dominio}/{tabella}")
    error_message = "Il DDL qa deve puntare al bucket silver qa."
  }
}

run "qa_ddl_is_iceberg_partitioned_by_last_updated_at" {
  command = plan

  assert {
    condition     = strcontains(output.ddl_qa, "PARTITIONED BY (`last_updated_at`)")
    error_message = "Il DDL qa deve essere partizionato per last_updated_at."
  }

  assert {
    condition     = strcontains(output.ddl_qa, "'table_type'='iceberg'") && strcontains(output.ddl_qa, "'format'='parquet'")
    error_message = "Il DDL qa deve avere TBLPROPERTIES Iceberg + parquet."
  }
}

run "qa_ddl_has_all_business_columns" {
  command = plan

  assert {
    condition = alltrue([
      for c in output.silver_business_columns :
      strcontains(output.ddl_qa, c)
    ])
    error_message = "Il DDL qa deve contenere tutte le colonne business attese."
  }
}

run "qa_ddl_has_cdc_columns" {
  command = plan

  assert {
    condition = alltrue([
      for c in output.silver_cdc_columns :
      strcontains(output.ddl_qa, c)
    ])
    error_message = "Il DDL qa deve contenere tutte le colonne CDC standard."
  }
}

# ===========================================================================
# PROD
# ===========================================================================
run "prod_ddl_targets_{dominio}_silver_database_without_prefix" {
  command = plan

  assert {
    condition     = strcontains(output.ddl_prod, "CREATE TABLE IF NOT EXISTS {dominio}_silver.{tabella}")
    error_message = "Il DDL prod deve creare la tabella in '{dominio}_silver' (senza prefix env)."
  }

  assert {
    condition     = !strcontains(output.ddl_prod, "prod_{dominio}_silver.{tabella}")
    error_message = "Il DDL prod NON deve usare il prefix 'prod_' nel database name."
  }
}

run "prod_ddl_uses_prod_silver_bucket" {
  command = plan

  assert {
    condition     = strcontains(output.ddl_prod, "s3://prod-datalake-silver-tier-eu-west-1-043188932291/{dominio}/{tabella}")
    error_message = "Il DDL prod deve puntare al bucket silver prod."
  }
}

run "prod_ddl_does_not_reference_dev_or_qa_buckets" {
  command = plan

  assert {
    condition     = !strcontains(output.ddl_prod, "dev-datalake-silver") && !strcontains(output.ddl_prod, "qa-datalake-silver")
    error_message = "Il DDL prod non deve contenere riferimenti a bucket dev o qa."
  }
}

run "prod_ddl_is_iceberg_partitioned_by_last_updated_at" {
  command = plan

  assert {
    condition     = strcontains(output.ddl_prod, "PARTITIONED BY (`last_updated_at`)")
    error_message = "Il DDL prod deve essere partizionato per last_updated_at."
  }

  assert {
    condition     = strcontains(output.ddl_prod, "'table_type'='iceberg'") && strcontains(output.ddl_prod, "'format'='parquet'")
    error_message = "Il DDL prod deve avere TBLPROPERTIES Iceberg + parquet."
  }
}

run "prod_ddl_has_all_business_columns" {
  command = plan

  assert {
    condition = alltrue([
      for c in output.silver_business_columns :
      strcontains(output.ddl_prod, c)
    ])
    error_message = "Il DDL prod deve contenere tutte le colonne business attese."
  }
}

run "prod_ddl_has_cdc_columns" {
  command = plan

  assert {
    condition = alltrue([
      for c in output.silver_cdc_columns :
      strcontains(output.ddl_prod, c)
    ])
    error_message = "Il DDL prod deve contenere tutte le colonne CDC standard."
  }
}

# ===========================================================================
# Cross-environment consistency
# ===========================================================================
run "all_ddls_share_same_business_schema" {
  command = plan

  assert {
    condition = alltrue([
      for c in concat(output.silver_business_columns, output.silver_cdc_columns) :
      strcontains(output.ddl_dev, c) && strcontains(output.ddl_qa, c) && strcontains(output.ddl_prod, c)
    ])
    error_message = "Lo schema business + CDC deve essere identico tra dev, qa, prod."
  }
}

run "bronze_business_columns_are_present_in_silver_dev" {
  command = plan

  assert {
    condition = alltrue([
      for c in output.bronze_{tabella}_columns :
      contains(["op", "commit_time", "transact_id"], c) ? true : strcontains(output.ddl_dev, c)
    ])
    error_message = "Ogni colonna business del YAML bronze deve esistere nel DDL silver dev."
  }
}
```
