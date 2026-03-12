# Repo Structure — Repository ETL Data Lake

> Struttura directory, IaC integration, ambienti, e pattern di deploy.
> Basato su pattern reali estratti da `datalake-anagrafica-dipendenti-etl`.

---

## Struttura completa

```
datalake-{domain}-etl/
├── config.yaml                            # Configurazione globale progetto
├── Makefile                               # Deploy shortcuts via git tag
├── utils/deploy-tag.sh                    # Script alternativo per push tag
├── .github/
│   ├── workflows/
│   │   ├── cd-terragrunt-plan-collaudo.yaml          # Plan only collaudo
│   │   ├── cd-terragrunt-plan-deploy-collaudo.yaml   # Plan + apply collaudo
│   │   ├── cd-terragrunt-plan-certificazione.yaml    # Plan only cert
│   │   ├── cd-terragrunt-plan-deploy-certificazione.yaml
│   │   ├── cd-terragrunt-plan-produzione.yaml        # Plan only prod
│   │   ├── cd-terragrunt-plan-deploy-produzione.yaml # Plan + apply prod
│   │   └── code-scan.yaml                            # Qodana weekly scan
│   └── copilot-instructions.md
├── live/                                  # Terragrunt entry points
│   ├── terragrunt.hcl                     # Root config (backend, provider, tags)
│   ├── _envs/
│   │   ├── dev.tmpl                       # Template variabili dev
│   │   ├── qa.tmpl                        # Template variabili qa
│   │   └── prod.tmpl                      # Template variabili prod
│   ├── shared/
│   │   └── terragrunt.hcl                 # Lookup risorse piattaforma
│   └── silver-{domain}/
│       └── terragrunt.hcl                 # Modulo ETL + dependency shared
└── modules/                               # Moduli Terraform
    ├── shared/                            # Data sources only (nessuna risorsa creata)
    │   ├── _input.tf
    │   ├── _local.tf
    │   ├── _output.tf
    │   ├── s3.tf                          # Lookup 5 bucket (glue, spark, transient, bronze, silver)
    │   ├── kms.tf                         # Lookup KMS key silver
    │   ├── vpc.tf                         # Lookup VPC + 3 subnet server
    │   ├── dynamodb-tables-updated.tf     # Lookup tabella tracking aggiornamenti
    │   └── eventbridge-datalake-bus.tf    # Lookup 2 bus (datalake + errors)
    └── silver-{domain}/
        ├── _input.tf
        ├── _local.tf
        ├── _output.tf
        ├── glue-definitions.yaml          # Definizione dichiarativa job
        ├── glue-jobs.tf                   # Risorse Glue + IAM + CloudWatch
        ├── glue-jobs-custom-libraries-upload.tf  # Upload libs + log4j2 su S3
        ├── stepfunction-orchestration.tf  # Step Function + 2 IAM roles
        ├── eventbridge-etl-scheduler.tf   # Cron trigger
        └── glue-jobs/
            ├── README.md
            ├── src/
            │   ├── {tabella_1}.py
            │   ├── {tabella_2}.py
            │   ├── ...
            │   └── libs/
            │       ├── __init__.py
            │       └── custom_classes.py  # Classi base condivise
            ├── configs/
            │   ├── dev/log4j2.properties
            │   ├── qa/log4j2.properties
            │   └── prod/log4j2.properties
            └── orchestration/
                ├── silver-etl.json        # ASL Step Function (template Terraform)
                └── new_db_silver_mapping.json  # Riferimento mapping sorgente
```

---

## config.yaml

Fonte unica per nomi, tag, e region:

```yaml
repository_name: datalake-{domain}-etl
project_name: datalake-etl-silver-{short-domain}  # < 30 chars per nomi risorse
region:
  primary: eu-west-1
tags:
  Iac: Terraform
  Repository: datalake-{domain}-etl
  Project: datalake-etl-silver-{short-domain}
  CostCenter: {cost-center}
  BusinessUnit: {business-unit}
  Availability: {availability}
  DataClassification: Confidential
  PrivacySensitive: "true"
```

I tag sono iniettati come `default_tags` nel provider AWS — tutte le risorse li ereditano.

---

## Template ambienti (`_envs/*.tmpl`)

I file `.tmpl` contengono placeholder `$VARIABILE` sostituiti dalla CI/CD a runtime.
I file `.yaml` generati **non sono committati nel repo**.

### Variabili principali

| Variabile | Scopo |
|-----------|-------|
| `$AWS_ENV` | Nome ambiente (dev/qa/prod) |
| `$VPC_STAGE` | Stage VPC per lookup subnet |
| `$BRONZE_DATALAKE_BUCKET_ID` | Bucket bronze |
| `$SILVER_DATALAKE_BUCKET_ID` | Bucket silver |
| `$GLUE_PACKAGES_BUCKET_ID` | Bucket script Glue |
| `$EVENTBRIDGE_DATALAKE_BUS_ID` | Bus eventi datalake |
| `$EVENTBRIDGE_DATAPLATFORM_ERRORS_ID` | Bus errori piattaforma |
| `$DYNAMO_BRONZE_TABLE_UPDATE_ID` | Tabella DynamoDB tracking |
| `$SILVER_UPDATES_MANAGER_LAMBDA_ARN` | Lambda coordinamento timestamp |
| `$STEPFUN_CRON_SCHEDULE` | Cron EventBridge (es. `cron(0 2 * * ? *)`) |
| `$STEPFUN_CRON_STATUS` | `ENABLED` o `DISABLED` |

### Flag critici per-ambiente

| Flag | dev | qa | prod |
|------|-----|-----|------|
| `stepfunction_force_no_window` | 1 (full reload) | 0 | 0 |
| `force_no_window` | 1 | 0 | 0 |

---

## Shared module — Data source registry

Il modulo `shared` **non crea risorse**. Fa solo lookup (`data` source) di risorse
create dalla piattaforma in repo separati:

| Data source | Risorsa lookuppata |
|-------------|-------------------|
| `aws_s3_bucket` × 5 | glue_packages, spark_ui, transient, bronze, silver |
| `aws_kms_key` × 1 | `alias/datalake/s3/silver` |
| `aws_vpc` × 1 | `platform-data-{vpc_stage}-vpc` |
| `aws_subnet` × 3 | server-a, server-b, server-c (multi-AZ) |
| `aws_dynamodb_table` × 1 | Tracking aggiornamenti bronze |
| `aws_cloudwatch_event_bus` × 2 | datalake_events, dataplatform_errors |

Gli output di `shared` sono consumati dal modulo `silver-{domain}` tramite
Terragrunt `dependency`.

---

## Terragrunt dependency

```hcl
# live/silver-{domain}/terragrunt.hcl
dependency "shared" {
  config_path = find_in_parent_folders("shared")
  mock_outputs_allowed_terraform_commands = ["init", "validate", "plan"]
  mock_outputs_merge_with_state = contains(["init", "validate", "plan"], ...) ? true : false
}
```

- `mock_outputs` permettono `terraform plan` senza che `shared` sia deployato
- In `apply` servono gli output reali dello state di `shared`
- Ordine deploy obbligatorio: `shared` prima, `silver-{domain}` dopo

---

## CI/CD — Deploy tag-based

### Trigger

| Tag | Workflow | Azione |
|-----|----------|--------|
| `PLAN-COLLAUDO` | `cd-terragrunt-plan-collaudo.yaml` | Solo plan |
| `COLLAUDO` | `cd-terragrunt-plan-deploy-collaudo.yaml` | Plan + apply |
| `PLAN-CERTIFICAZIONE` | `cd-terragrunt-plan-certificazione.yaml` | Solo plan |
| `CERTIFICAZIONE` | `cd-terragrunt-plan-deploy-certificazione.yaml` | Plan + apply |
| *(nessun tag)* | `cd-terragrunt-plan-produzione.yaml` | Solo plan (manual dispatch) |
| *(nessun tag)* | `cd-terragrunt-plan-deploy-produzione.yaml` | Plan + apply (manual dispatch) |

### Makefile shortcuts

```bash
make dev       # Push tag COLLAUDO → deploy collaudo
make qa        # Push tag CERTIFICAZIONE → deploy certificazione
make plan_dev  # Push tag PLAN-COLLAUDO → solo plan collaudo
make plan_qa   # Push tag PLAN-CERTIFICAZIONE → solo plan certificazione
make prod      # BLOCCATO — messaggio con link a GitHub Actions UI
```

Il Makefile cancella e ricrea il tag ad ogni invocazione (tag flottanti).
Produzione richiede trigger manuale da GitHub Actions UI.

### Workflow reusable

Tutti i workflow delegano a `itsiae/siae-gh-actions@v2.1.0`:
- `terragrunt-plan.yaml` — solo plan
- `cd-terragrunt-plan-deploy.yaml` — plan + apply
- `tagging-and-releasing-mgmt.yaml` — gestione tag post-deploy

`working_dir: live` e' costante in tutti i workflow.

---

## Remote state

```hcl
remote_state {
  backend = "s3"
  config = {
    bucket         = "${get_env("ENV")}-{repo}-terraform-state"
    key            = "${path_relative_to_include()}/terraform.tfstate"
    region         = local.config.region.primary
    encrypt        = true
    dynamodb_table = "${get_env("ENV")}-{repo}-terraform-state"
  }
}
```

- Bucket S3 con prefisso `{env}-` → stato isolato per ambiente
- DynamoDB lock con stesso nome del bucket
- Key basata su `path_relative_to_include()` → `shared/terraform.tfstate`, `silver-{domain}/terraform.tfstate`
- Encryption sempre abilitata

---

## Naming risorse

| Risorsa | Pattern |
|---------|---------|
| Glue job | `{env}-{project}-{job_name}` |
| Step Function | `{env}-{project}-silver-orchestration` |
| EventBridge rule | `{env}-{project}-schedule-orchestr` |
| IAM role Glue | `{env}-{project}-glue-job-role` |
| IAM role SFN | `{env}-{project}-silver-orchestration` |
| IAM role trigger | `{env}-{project}-silver-orchestr-trig` |
| CloudWatch log group | `/{env}/datalake/silver/{module}/glue-etl` |
| S3 script path | `s3://{bucket}/etl/{module}/{file}.py` |
