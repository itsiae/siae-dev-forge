# Naming Substitutions — datalake-etl-setup

Mappa completa delle sostituzioni da applicare quando si adatta un repo ETL
di riferimento al dominio target. Basata sul pattern `datalake-sport-etl`.

## Variabili Derivate dai Parametri

| Variabile | Formula | Esempio (zucchetti) |
|---|---|---|
| `{dominio}` | da nome repo: `datalake-{dominio}-etl` | `zucchetti` |
| `{DOMINIO_UPPER}` | `{dominio}` in uppercase | `ZUCCHETTI` |
| `{MODULO}` | `silver-{dominio}` | `silver-zucchetti` |
| `{SILVER_CONFIG_KEY}` | `silver_{dominio}` | `silver_zucchetti` |
| `{UPDATE_ATTR}` | `last_silver_{dominio}_update_time` | `last_silver_zucchetti_update_time` |

**Nota:** Non esiste `{CRAWLER_VAR}` nel pattern sport — nessun crawler Bronze dedicato.

## Pattern sport-etl vs pattern con crawler

| Aspetto | Pattern sport (default) | Pattern con crawler (pmo/performing) |
|---|---|---|
| Variabili orchestrazione | `STEPFUN_CRON_SCHEDULE`, `STEPFUN_CRON_STATUS` | `CRON_SCHED`, `CRON_SCHED_STATUS` |
| Variabile crawler | assente | `BRONZE_{DOMINIO}_CRAWLER_NAME` |
| SFN StartAt | `RetrieveTablesToUpdate` | `StartBronzeCrawler` |
| IAM Glue | `"Action": "glue:*"` | azioni esplicite |
| File mapping | `new_db_silver_mapping.json` | `silver-mapping.json` |
| Arg Glue `--last_iac_upload_job_timestamp` | assente | presente |

## Sostituzioni File per File (pattern sport)

### live/_envs/*.tmpl

| Da (sport) | A ({dominio}) |
|---|---|
| `silver_sport:` | `silver_{dominio}:` |
| `# Silver Sport vars module` | `# Silver {dominio} vars module` |

**Invariati:** tutti i placeholder `$STEPFUN_CRON_SCHEDULE`, `$STEPFUN_CRON_STATUS`, ecc.

### live/silver-{dominio}/terragrunt.hcl

| Da (sport) | A ({dominio}) |
|---|---|
| `module = "silver-sport"` | `module = "silver-{dominio}"` |
| `local.stage.silver_sport` | `local.stage.silver_{dominio}` |
| `config_path = find_in_parent_folders("shared")` | invariato |

**Non aggiungere** `bronze_{dominio}_crawler_name` — non presente nel pattern sport.

### modules/silver-{dominio}/_input.tf

Nessuna sostituzione specifica del dominio nei nomi variabili — il pattern sport non ha
`bronze_{dominio}_crawler_name`. Il blocco `variable "config"` rimane:

```hcl
variable "config" {
  type = object({
    enable_glue_metrics               = string
    enable_glue_observability_metrics = string
    enable_spark_ui                   = string
    force_no_window                   = number
    orchestration                     = map(any)
  })
}
```

### modules/silver-{dominio}/glue-jobs.tf

| Da (sport) | A ({dominio}) |
|---|---|
| `silver_anagrafiche_glue_etl` | `silver_{dominio}_glue_etl` |
| `aws_cloudwatch_log_group.silver_anagrafiche_glue_etl.name` | `aws_cloudwatch_log_group.silver_{dominio}_glue_etl.name` |

Il resto usa `var.module`, `var.env`, `var.project` → invariato.
**Non includere** `--last_iac_upload_job_timestamp`.

### modules/silver-{dominio}/stepfunction-orchestration.tf

| Da (sport) | A ({dominio}) |
|---|---|
| `scope = "sport"` | `scope = "{dominio}"` |

IAM `glue-jobs-permissions`: mantieni `"Action": "glue:*"` (corretto nel pattern sport).
**Non aggiungere** policy `crawler-permissions`.
**Non aggiungere** `crawler_name` nel blocco `templatefile`.

### orchestration/silver-etl.json

| Da (sport) | A ({dominio}) |
|---|---|
| `"last_silver_sport_update_time"` | `"last_silver_{dominio}_update_time"` |
| `silver_mapping` con job sport | `silver_mapping` con job del nuovo dominio |

`scope` nei `DetailType` è già gestito dalla variabile Terraform `${scope}` → invariato.

### orchestration/new_db_silver_mapping.json

File di mapping con i job del dominio target:
```json
{
  "{nome-job}": ["{nome_tabella_silver}"]
}
```

**Nota:** si chiama `new_db_silver_mapping.json` (non `silver-mapping.json`).

### chart/Chart.yaml

| Da (sport) | A ({dominio}) |
|---|---|
| `name: datalake-sport-etl` | `name: datalake-{dominio}-etl` |
| `repository: datalake-sport-etl` | `repository: datalake-{dominio}-etl` |

## File da Copiare Identici (nessuna sostituzione)

- `live/terragrunt.hcl` — generico
- `live/shared/terragrunt.hcl` — generico
- `modules/shared/` — tutti i file (identico tra sport e altri repo)
- `modules/silver-{dominio}/_local.tf` — usa solo `var.env`, `var.module`
- `modules/silver-{dominio}/_output.tf` — solitamente commentato
- `modules/silver-{dominio}/glue-jobs-custom-libraries-upload.tf` — generico
- `modules/silver-{dominio}/eventbridge-etl-scheduler.tf` — generico
- `glue-jobs/src/libs/custom_classes.py` — libreria generica
- `glue-jobs/src/libs/__init__.py` — vuoto
- `glue-jobs/configs/{dev,qa,prod}/app_conf.json` — configurazione Spark generica
- `glue-jobs/configs/{dev,qa,prod}/log4j2.properties` — configurazione logging generica
