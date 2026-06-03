---
name: siae-datalake-ingestion-setup
description: >
  Guida il setup iniziale di un nuovo repo IaC ingestion DMS `datalake-{dominio}-ingestion`
  seguendo il pattern DMS (AWS Database Migration Service) di SIAE.
  Trigger: nuovo repo datalake ingestion, setup dominio ingestion, scaffolding DMS,
  datalake-{nome}-ingestion, nuovo dominio ingestion, configurazione repo IaC DMS,
  scaffolding ingestion, setup bm-utilizzazioni, setup bm-estero, setup accertatori.
---

# SIAE Datalake Ingestion Setup

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗    ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║    ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║    ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝    ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝     ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝      ║
║       🔨 DevForge · SIAE DATALAKE INGESTION SETUP             ║
║         "Il codice si forgia. Il developer cresce."            ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Flexible | **Fase SDLC:** 2. Setup & Scaffolding

---

> 📊 **Dai repo itsiae:** I repo `datalake-{dominio}-ingestion` seguono tutti la stessa
> struttura DMS: modulo `{dominio}` con replication instance, endpoint source/target S3,
> task definitions YAML e mapping JSON. Il repo canonico è `datalake-accertatori-ingestion`.

---

## Input Richiesti

| Parametro | Descrizione | Esempio |
|-----------|-------------|---------|
| `repo-riferimento` | Repo di riferimento (default: `datalake-accertatori-ingestion`) | `datalake-accertatori-ingestion` |
| `repo-target` | Path locale del repo da configurare | `/path/to/datalake-bm-utilizzazioni-ingestion` |
| `dominio` | Nome dominio in kebab-case | `bm-utilizzazioni` |
| `database-name` | Nome reale del DB PostgreSQL sorgente | `utilizzazioni` |

Se un parametro manca, chiedi prima di procedere. Non assumere valori di default senza conferma.

**Derivazioni automatiche:**
- `{DOMINIO_UNDERSCORE}` = dominio con trattini → underscore (`bm-utilizzazioni` → `bm_utilizzazioni`)
- `modulo` = `{dominio}` (es. `bm-utilizzazioni`)
- `bucket_folder` = `transient/{DOMINIO_UNDERSCORE}/`

---

## Checklist Progress

```
Datalake Ingestion Setup Progress:
- [ ] Step 1: Raccolta e validazione parametri
- [ ] Step 2: Analisi struttura repo di riferimento
- [ ] Step 3: Aggiornamento config.yaml e chart/Chart.yaml
- [ ] Step 4: Aggiornamento live/_envs/ (dev/qa/prod .tmpl)
- [ ] Step 5: Aggiornamento live/terragrunt.hcl
- [ ] Step 6: Creazione live/{dominio}/terragrunt.hcl
- [ ] Step 7: Creazione modules/{dominio}/ (tutti i file tf)
- [ ] Step 8: Creazione dms-task-definitions.yaml e mapping/ placeholder
- [ ] Step 9: Aggiornamento workflow GitHub Actions
- [ ] Step 10: Rimozione scaffolding example
- [ ] Step 11: Aggiornamento README.md
- [ ] Step 12: GitHub Env Sync (siae-github-env-sync)
- [ ] Step 13: Primo commit (siae-git-workflow)
```

---

## Step 1 — Raccolta e Validazione Parametri

🟢 SICURO

Verifica tutti i parametri. Se `repo-riferimento` non è specificato, usa
`datalake-accertatori-ingestion` e comunicalo all'utente.

Mostra riepilogo derivazioni e chiedi conferma prima di procedere:
```
repo-riferimento:  datalake-accertatori-ingestion
repo-target:       datalake-{dominio}-ingestion
dominio:           {dominio}
modulo:            {dominio}
database-name:     {database-name}
bucket_folder:     transient/{DOMINIO_UNDERSCORE}/
```

---

## Step 2 — Analisi Struttura Repo di Riferimento

🟢 SICURO

Leggi in parallelo i file chiave via `gh api`:

```bash
# Struttura root
gh api repos/itsiae/{repo-riferimento}/contents/ | python3 -c "..."

# live/ e modules/
gh api repos/itsiae/{repo-riferimento}/contents/live | python3 -c "..."
gh api repos/itsiae/{repo-riferimento}/contents/modules | python3 -c "..."

# File chiave
gh api repos/itsiae/{repo-riferimento}/contents/live/_envs/dev.tmpl | python3 -c "import sys,json,base64; d=json.load(sys.stdin); print(base64.b64decode(d['content']).decode())"
gh api repos/itsiae/{repo-riferimento}/contents/live/{dominio-ref}/terragrunt.hcl | python3 -c "..."
gh api repos/itsiae/{repo-riferimento}/contents/modules/{dominio-ref}/_input.tf | python3 -c "..."
```

Identifica il nome del modulo di riferimento dalla struttura `modules/` prima di procedere.

---

## Step 3 — config.yaml e chart/Chart.yaml

🟢 SICURO

**config.yaml** — aggiorna `repository_name`, `project_name`, `BusinessUnit`:
```yaml
repository_name: &repo_name datalake-{dominio}-ingestion
project_name: &proj_name datalake
# BusinessUnit: Music (per domini BM), TBD per altri
```

**chart/Chart.yaml** — aggiorna `name` e `template.repository` usando underscore:
```yaml
name: datalake_{DOMINIO_UNDERSCORE}_ingestion
template:
  repository: datalake_{DOMINIO_UNDERSCORE}_ingestion
```

---

## Step 4 — live/_envs/ (dev/qa/prod .tmpl)

🟢 SICURO

Crea/sovrascrivi `dev.tmpl`, `qa.tmpl`, `prod.tmpl` seguendo il **pattern canonico accertatori**:

```yaml
env: &env $AWS_ENV
vpc_stage: $VPC_STAGE
tags:
- key: Environment
  value: *env
log_level: $LOG_LEVEL
log_retention_days: $LOG_RETENTION_DAYS

generic_s3_endpoint_settings: &generic_settings
  add_column_name: true
  ssl_mode: "none"
  add_trailing_padding_character: false
  cdc_inserts_and_updates: false
  cdc_min_file_size: 122880
  data_format: "parquet"
  timestamp_column_name: "commit_time"
  glue_catalog_generation: false
  include_op_for_full_load: true
  rfc4180: true

vpc_default_sg_id: $VPC_DEFAULT_SG_ID
transient_bucket_name: $TRANSIENT_BUCKET_NAME

{dominio}:
  s3_endpoint_settings: *generic_settings
  dms_instance_config:
    instance_type: $DMS_INSTANCE_TYPE
    engine_version: $DMS_VERSION
    preferred_maintenance_window: "sun:00:15-sun:04:15"
    multi_az: $DMS_MULTI_AZ
    allocated_storage: $DMS_STORAGE
```

**Variabili placeholder canoniche** (verificate su `accertatori` e `pmo`):
`$DMS_VERSION`, `$DMS_MULTI_AZ`, `$DMS_STORAGE`, `$VPC_DEFAULT_SG_ID`

**Non usare:** `$DMS_ENGINE_VERSION`, `$DMS_ALLOCATED_STORAGE`, `$DEFAULT_SECURITY_GROUP` — sono naming alternativi presenti in repo più vecchi come `bm-estero`.

---

## Step 5 — live/terragrunt.hcl

🟢 SICURO

Aggiorna con il contenuto del riferimento. Assicurati che includa `required_providers`:
```hcl
generate "backend" {
  contents = <<EOF
  terraform {
    backend "s3" {}
    required_providers {
      aws = {
        source  = "hashicorp/aws"
        version = ">= 0.12, < 6.1.0"
      }
    }
  }
  EOF
}
```

---

## Step 6 — live/{dominio}/terragrunt.hcl

🟢 SICURO

```hcl
include {
  path = find_in_parent_folders()
}

locals {
  module = "{dominio}"
  config = yamldecode(file(find_in_parent_folders("config.yaml")))
  stage  = yamldecode(file("../_envs/${get_env("ENV")}.yaml"))
}

inputs = {
  account_id            = get_aws_account_id()
  region                = local.config.region.primary
  project               = local.config.project_name
  module                = local.module
  env                   = local.stage.env
  vpc_stage             = local.stage.vpc_stage
  log_level             = local.stage.log_level
  vpc_default_sg_id     = local.stage.vpc_default_sg_id
  s3_endpoint_settings  = local.stage.{dominio}.s3_endpoint_settings
  dms_instance_config   = local.stage.{dominio}.dms_instance_config
  transient_bucket_name = local.stage.transient_bucket_name
}
```

---

## Step 7 — modules/{dominio}/

🟢 SICURO

Crea `modules/{dominio}/` con i file copiati dal riferimento sostituendo:

| Riferimento | Target |
|---|---|
| `{dominio-ref}` (es. `accertatori`) | `{dominio}` |
| `{DOMINIO_REF_UNDERSCORE}` (es. `accertatori`) | `{DOMINIO_UNDERSCORE}` |
| `database_name = "..."` in `dms-endpoints.tf` | `database_name = "{database-name}"` |
| `bucket_folder = "transient/{dominio-ref}/"` | `bucket_folder = "transient/{DOMINIO_UNDERSCORE}/"` |
| Secret name con dominio-ref | Secret name con dominio target |

**File da creare:** `_input.tf`, `_local.tf`, `_output.tf`, `_data.tf`, `dms-endpoints.tf`,
`dms-instance.tf`, `dms-replication-task.tf`, `iam.tf`, `s3.tf`,
`secrets-manager.tf`, `security-group.tf`, `vpc.tf`

Vedi [reference/tf-files-detail.md](reference/tf-files-detail.md) per il contenuto completo di ogni file.

---

## Step 8 — dms-task-definitions.yaml e mapping/

🟢 SICURO

**`dms-task-definitions.yaml`:**
```yaml
tasks:
  - name: "{dominio}-1"
    path: "mapping/{dominio}-1.json"
    migration_type: "full-load-and-cdc"
```

**`mapping/{dominio}-1.json`** — placeholder con regole base da personalizzare:
```json
{
  "rules": [
    {
      "rule-type": "transformation",
      "rule-id": "1",
      "rule-name": "add-transact-id-num",
      "rule-target": "column",
      "object-locator": { "schema-name": "%public", "table-name": "%" },
      "rule-action": "add-column",
      "value": "transact_id",
      "expression": "$AR_H_CHANGE_SEQ",
      "data-type": { "type": "string", "length": 50 }
    },
    {
      "rule-type": "transformation",
      "rule-id": "2",
      "rule-name": "change-data-type-to-string",
      "rule-target": "column",
      "object-locator": { "schema-name": "%", "table-name": "%", "column-name": "%" },
      "rule-action": "change-data-type",
      "data-type": { "type": "string", "length": "999999", "scale": "" }
    },
    {
      "rule-type": "selection",
      "rule-id": "100",
      "rule-name": "include-all-public-tables",
      "object-locator": { "schema-name": "%public", "table-name": "%" },
      "rule-action": "include"
    }
  ]
}
```

> ⚠️ **Segnala sempre all'utente** che `mapping/{dominio}-1.json` è un placeholder
> e va personalizzato con le tabelle reali del dominio prima del deploy.

---

## Step 9 — Workflow GitHub Actions

🟢 SICURO

Allinea tutte le versioni `siae-gh-actions` nei workflow:

```bash
# Verifica versioni attualmente presenti
grep -rh "siae-gh-actions" .github/workflows/ | grep -o "@v[0-9.]*" | sort -u

# Allinea alla versione del riferimento
LATEST_VERSION=$(gh api repos/itsiae/{repo-riferimento}/contents/.github/workflows/cd-terragrunt-plan-collaudo.yaml \
  | python3 -c "import sys,json,base64; print(base64.b64decode(json.load(sys.stdin)['content']).decode())" \
  | grep -o "@v[0-9.]*" | head -1)

sed -i "s/@v[0-9]\+\.[0-9]\+\.[0-9]\+/${LATEST_VERSION}/g" .github/workflows/*.yaml
```

**Eccezione:** `code-scan.yaml` usa un workflow diverso (`qodana-scan-generic`) con versioning separato — allinealo alla versione presente nel repo di riferimento.

---

## Step 10 — Rimozione Scaffolding Example

🟡 MEDIO — Verifica prima di rimuovere

```bash
ls modules/example/ live/example/ 2>/dev/null
```

Se presenti, rimuovi:
```bash
rm -rf modules/example/ live/example/
```

---

## Step 11 — README.md

🟢 SICURO

Aggiorna il titolo principale:
```bash
sed -i 's/# 🚀 \[INSERIRE NOME PROGETTO QUI\]/# 🚀 datalake-{dominio}-ingestion/' README.md
```

---

## Step 12 — GitHub Env Sync

🔴 ALTO — Pre-flight obbligatoria

```
REQUIRED SUB-SKILL: siae-github-env-sync
```

**⚠️ PREREQUISITO CRITICO:** Gli ambienti GitHub (`collaudo`, `certificazione`, `produzione`)
devono essere creati **manualmente** prima del sync via API. La GitHub API `PUT /environments`
può restituire 404 anche su piano Enterprise se il token non ha `administration:write`.

**Procedura:**
1. Crea gli ambienti manualmente su GitHub:
   `https://github.com/itsiae/{repo-target}/settings/environments`
2. Crea: `collaudo`, `certificazione`, `produzione`
3. Poi esegui `siae-github-env-sync` con `repo-riferimento=datalake-accertatori-ingestion`

**Variabili GitHub canoniche** (pattern `accertatori`):

| Variabile | collaudo | certificazione | produzione |
|-----------|----------|----------------|------------|
| `AWS_ENV` | `dev` | `qa` | `prod` |
| `AWS_ORG_ACCOUNT` | `104589273752` | `104589273752` | `104589273752` |
| `AWS_REGION` | `eu-west-1` | `eu-west-1` | `eu-west-1` |
| `AWS_ROLE` | `github-pipeline-rw` | `github-pipeline-rw` | `github-pipeline-rw` |
| `AWS_TARGET_ACCOUNT_ID` | `613577363574` | `613577363574` | `043188932291` |
| `DMS_INSTANCE_TYPE` | da definire | da definire | da definire |
| `DMS_MULTI_AZ` | `false` | `false` | `false` |
| `DMS_STORAGE` | da definire | da definire | da definire |
| `DMS_VERSION` | `3.5.4` | `3.5.4` | `3.5.4` |
| `LOG_LEVEL` | `ERROR` | `ERROR` | `ERROR` |
| `LOG_RETENTION_DAYS` | `7` | `7` | `365` |
| `TRANSIENT_BUCKET_NAME` | `dev-datalake-bronze-tier-eu-west-1-613577363574` | `qa-datalake-bronze-tier-eu-west-1-613577363574` | `prod-datalake-bronze-tier-eu-west-1-043188932291` |
| `VPC_DEFAULT_SG_ID` | `sg-0d6cf31ea95751d96` | `sg-007036a2f3788298b` | `sg-082a1beb09c0ce7f6` |
| `VPC_STAGE` | `devtest` | `quality` | `prod` |

---

## Step 13 — Primo Commit

🔴 ALTO — Pre-flight obbligatoria

```
REQUIRED SUB-SKILL: siae-git-workflow
```

```
chore(setup): initial repo setup for {dominio}-ingestion domain
```

---

## Fallback Obbligatori

### database-name non noto
Chiedi esplicitamente. Non assumere dal nome del dominio — `bm-utilizzazioni` → `utilizzazioni` è una semplificazione che potrebbe non essere corretta.

### Ambienti GitHub non creabili via API (404)
Il token `siaeGitHubNttData` potrebbe non avere `administration:write`. In questo caso:
1. Mostra la URL diretta per la creazione manuale
2. Fornisci la tabella delle variabili da inserire per ogni ambiente
3. Procedi con il commit IaC senza attendere il sync

### Variabili `DMS_INSTANCE_TYPE` e `DMS_STORAGE` specifiche del dominio
Non copiare ciecamente dal riferimento — `accertatori` usa `dms.t3.micro` e storage 300GB,
altri domini potrebbero richiedere istanze più grandi. Mostra i valori del riferimento
e chiedi conferma all'utente prima di impostare queste variabili.

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realtà |
|----------|--------|
| "Copio le variabili da `bm-estero`, è più vicino al dominio" | `bm-estero` usa naming legacy (`DEFAULT_SECURITY_GROUP`, `DMS_ENGINE_VERSION`) — usa sempre `accertatori` come riferimento |
| "`DMS_ENGINE_VERSION` e `DMS_VERSION` sono equivalenti" | Sono variabili GitHub diverse — il `.tmpl` referenzia `$DMS_VERSION`, non `$DMS_ENGINE_VERSION` |
| "Creo gli ambienti GitHub via API PUT /environments" | Spesso restituisce 404 anche su piano Enterprise — crea gli ambienti manualmente su GitHub prima del sync |
| "Il `database_name` lo derivo dal nome del dominio" | Il nome del DB sorgente va chiesto esplicitamente all'utente — non si può derivare automaticamente |
| "`DMS_STORAGE` e `DMS_ALLOCATED_STORAGE` sono variabili diverse" | Sono equivalenti — entrambe mappano `allocated_storage` nel `dms_instance_config`; il nome GitHub cambia tra repo ma il `.tmpl` usa `$DMS_STORAGE` |
| "Il mapping DMS placeholder va bene per il deploy" | Il mapping va personalizzato con le tabelle reali — segnalarlo sempre all'utente |
| "Copio `DMS_INSTANCE_TYPE` e `DMS_STORAGE` da `accertatori`" | Questi valori sono specifici del carico del dominio — chiedi conferma |

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Lettura repo di riferimento via gh api | 🟢 Sicuro | No |
| Scrittura file Terraform/Terragrunt | 🟢 Sicuro | No |
| Aggiornamento workflow versioni | 🟢 Sicuro | No |
| Rimozione scaffolding example | 🟡 Medio | Sì |
| GitHub Env Sync | 🔴 Alto | Sì (siae-github-env-sync) |
| git commit + push | 🔴 Alto | Sì (siae-git-workflow) |

---

## Vincoli

1. **SEMPRE** usare `datalake-accertatori-ingestion` come riferimento default — non `bm-estero`
2. **MAI** usare `$DEFAULT_SECURITY_GROUP`, `$DMS_ENGINE_VERSION`, `$DMS_ALLOCATED_STORAGE` nei `.tmpl`
3. **SEMPRE** usare `$VPC_DEFAULT_SG_ID`, `$DMS_VERSION`, `$DMS_MULTI_AZ`, `$DMS_STORAGE`
4. **MAI** assumere il `database_name` — chiedere sempre all'utente
5. **SEMPRE** segnalare che `mapping/{dominio}-1.json` è un placeholder da personalizzare
6. **PRE-FLIGHT OBBLIGATORIA** per rimozione file, env sync e git push

---

## Risorse Aggiuntive

- [reference/tf-files-detail.md](reference/tf-files-detail.md) — Contenuto completo dei file Terraform del modulo
