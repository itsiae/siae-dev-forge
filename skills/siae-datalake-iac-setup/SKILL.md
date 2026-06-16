---
name: siae-datalake-iac-setup
description: >
  Guida il setup iniziale di un nuovo repo IaC datalake `datalake-{dominio}-iac`
  seguendo la struttura Medallion (bronze/silver) di SIAE.
  Trigger: nuovo repo datalake iac, setup dominio datalake, scaffolding bronze silver,
  datalake-{nome}-iac, nuovo dominio data lake, configurazione repo IaC medallion.
---

# SIAE Datalake IaC Setup

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║        🔨  DevForge  ·  SIAE Datalake IaC Setup                  ║
║         "Il codice si forgia. Il developer cresce."              ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Flexible | **Fase SDLC:** 2. Setup & Scaffolding

---

> 📊 **Dai repo itsiae:** I repo datalake-*-iac seguono tutti la stessa struttura Medallion.
> Standardizzare il setup iniziale riduce il tempo di bootstrap da ore a minuti.
> Fonte: pattern estratto da `datalake-zucchetti-iac` e `datalake-edw-iac`.

## Panoramica

Questa skill guida il setup completo di un nuovo repo IaC per un dominio data lake SIAE.
Il pattern è `datalake-{dominio}-iac` con architettura Medallion: layer **bronze** (Parquet
CDC raw + Glue Catalog) e layer **silver** (Apache Iceberg managed).

**Trigger**: setup nuovo dominio datalake, scaffolding repo datalake-*-iac, creazione moduli
bronze/silver, configurazione Terragrunt per nuovo dominio data lake.

---

Copia questa checklist e traccia il progresso:

```
Datalake IaC Setup Progress:
- [ ] Step 1: Raccolta informazioni dominio
- [ ] Step 2: Configurazione config.yaml e chart/Chart.yaml
- [ ] Step 3: Configurazione live/ (root terragrunt + _envs)
- [ ] Step 4: Creazione moduli bronze e silver
- [ ] Step 5: Creazione tables_definition/ con placeholder
- [ ] Step 6: Rimozione scaffolding (example module)
- [ ] Step 7: Verifica sicurezza IAM e prevent_destroy
- [ ] Step 8: Git — branch setup e primo commit
```

---

## 1. Informazioni da Raccogliere Prima di Iniziare

Prima di scrivere codice, raccogli queste informazioni dal developer:

| Informazione | Esempio | Note |
|---|---|---|
| Nome dominio | `zucchetti` | Usato nei nomi risorse AWS |
| Repository name | `datalake-zucchetti-iac` | Pattern: `datalake-{dominio}-iac` |
| Project name | `datalake` | **Fisso** per tutti i repo `datalake-{dominio}-iac` — non personalizzare |
| Business Unit | `Human Resources` | Tag AWS |
| Cost Center | `TBD` o codice specifico | Tag AWS |
| Region primaria | `eu-west-1` | Default SIAE |
| Privacy Sensitive | `true` / `false` | Tag AWS |

**Se il template-repo ha già file di scaffolding (es. `live/example/`, `modules/example/`)**:
vanno rimossi e sostituiti con i moduli `bronze` e `silver` del dominio.

---

## 2. File da Configurare

### Step 2A — config.yaml

🟢 SICURO

Il file `config.yaml` alla root è la fonte unica per nomi, tag e region.
Sostituisci **tutti** i placeholder con i valori del dominio:

```yaml
repository_name: &repo_name datalake-{dominio}-iac

project_name: &proj_name datalake   # FISSO per tutti i repo datalake-{dominio}-iac

region:
  primary: eu-west-1

tags:
  - key: Iac
    value: terraform
  - key: Repository
    value: *repo_name
  - key: Project
    value: *proj_name
  - key: CostCenter
    value: {cost-center}
  - key: BusinessUnit
    value: {business-unit}
  - key: Availability
    value: ordinary
  - key: PrivacySensitive
    value: "true"
```

### Step 2B — chart/Chart.yaml

🟢 SICURO

Aggiorna `name` e `repository` con i valori del dominio:

```yaml
apiVersion: v2
name: datalake-{dominio}-iac
...
repository: https://github.com/itsiae/datalake-{dominio}-iac
```

---

## 3. Configurazione live/

### Step 3A — live/terragrunt.hcl (root)

🟢 SICURO

Il file root **non richiede modifiche di dominio** — è generico.
Gestisce: remote state S3+DynamoDB, provider AWS con default_tags, backend S3.

Pattern chiave da verificare:
- Remote state bucket: `${local.stage.env}-${local.config.repository_name}-terraform-state`
- Key: `${path_relative_to_include()}/terraform.tfstate`
- Encryption: `true`
- La variabile ENV **non** ha default nel root — viene sempre settata dalla CI/CD

Vedi [reference/repo-structure.md](reference/repo-structure.md) per il template completo.

### Step 3B — live/_envs/ (template ambienti)

🟢 SICURO

Crea/aggiorna i file template per i 3 ambienti: `dev.tmpl`, `qa.tmpl`, `prod.tmpl`.

Struttura obbligatoria:

```yaml
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

> ⚠️ I file `.yaml` generati a runtime dalla CI/CD **non devono essere committati**.
> I `.tmpl` contengono placeholder `$VARIABILE` sostituiti dalla pipeline.

### Step 3C — live/bronze/terragrunt.hcl

🟢 SICURO

```hcl
include {
  path = find_in_parent_folders()
}

locals {
  module = "bronze"
  config = yamldecode(file(find_in_parent_folders("config.yaml")))
  # default "dev" per esecuzioni locali; in CI/CD ENV è sempre settata esplicitamente
  stage  = yamldecode(file("../_envs/${get_env("ENV", "dev")}.yaml"))
  {dominio}_tables_def = yamldecode(file(find_in_parent_folders("tables_definition/bronze/{dominio}.yaml"))).tables
}

inputs = {
  account_id              = get_aws_account_id()
  region                  = local.config.region.primary
  project                 = local.config.project_name
  module                  = local.module
  env                     = local.stage.env
  s3_datalake_bronze_name = local.stage.s3_datalake_bronze_name
  config                  = local.stage.config
  {dominio}_tables_def    = local.{dominio}_tables_def
}
```

### Step 3D — live/silver/terragrunt.hcl

🟢 SICURO

```hcl
include {
  path = find_in_parent_folders()
}

locals {
  module = "silver"
  config = yamldecode(file(find_in_parent_folders("config.yaml")))
  # default "dev" per esecuzioni locali; in CI/CD ENV è sempre settata esplicitamente
  stage  = yamldecode(file("../_envs/${get_env("ENV", "dev")}.yaml"))
}

inputs = {
  account_id = get_aws_account_id()
  region     = local.config.region.primary
  project    = local.config.project_name
  module     = local.module
  env        = local.stage.env
  config     = local.stage.silver
}
```

---

## 4. Moduli Terraform

### Step 4A — Struttura file modulo

🟢 SICURO

Ogni modulo ha **tre meta-file con prefisso underscore** + uno o più resource file:

| File | Contenuto |
|---|---|
| `_input.tf` | Tutte le `variable` del modulo |
| `_local.tf` | Blocchi `locals` (prefix, suffissi) |
| `_output.tf` | Tutti gli `output` (spesso vuoto in bronze/silver base) |
| `bronze.tf` / `silver.tf` | Risorse AWS specifiche del layer |

**Locals obbligatori in `_local.tf`:**
```hcl
locals {
  prefix        = "${var.env}-${var.project}-${var.module}"
  global_suffix = "${var.region}-${var.account_id}"
  db_name       = var.env == "prod" ? "{dominio_underscore}_bronze" : "${var.env}_{dominio_underscore}_bronze"
}
```

> ℹ️ `{dominio_underscore}` è il nome dominio con trattini sostituiti da underscore (es. `bm-utilizzazioni` → `bm_utilizzazioni`).

**Variabili standard obbligatorie in `_input.tf`:**
```hcl
variable "account_id" { type = string }
variable "region"     { type = string }
variable "project"    { type = string }
variable "env"        { type = string }
variable "module"     { type = string }
```

### Step 4B — modules/bronze/bronze.tf

🟢 SICURO

Risorse chiave del layer bronze. Il naming delle risorse segue il pattern `{dominio_kebab}` (con trattini) per i nomi AWS e `{dominio_underscore}` (con underscore) per gli identificatori Terraform.

**Struttura obbligatoria:**

1. **`aws_glue_catalog_database`** — resource label: `{dominio_underscore}_bronze`, naming da `local.db_name`
   - `lifecycle { prevent_destroy = true }` — **OBBLIGATORIO**
2. **`data.aws_s3_bucket`** — resource label: `datalake_bronze`, lookup da `var.s3_datalake_bronze_name`
3. **`locals`** — block interno con map `{dominio_underscore}_tables_by_name` per il `for_each`
4. **`aws_glue_catalog_table`** — resource label: `{dominio_underscore}_bronze_tables`, `for_each` su local map, path S3: `bronze/{dominio_underscore}/{each.value.path}/`, formato Parquet MapredParquet, partizioni `year/month/day`
5. **`aws_glue_crawler`** — resource label: `{dominio_underscore}_tables`
   - `name = "${local.prefix}-{dominio_kebab}-crawler-parquet"` — **include sempre il dominio nel nome**
   - `catalog_target` con lista dinamica delle tabelle
   - `schema_change_policy`: `delete_behavior = "LOG"`, `update_behavior = "LOG"`
   - `configuration` con `CrawlerOutput.Partitions.AddOrUpdateBehavior = "InheritFromTable"`
6. **`aws_iam_role`** — resource label: `{dominio_underscore}_crawler`
   - `name = "${local.prefix}-{dominio_kebab}-crawler-parquet"` — **include sempre il dominio nel nome**
   - `inline_policy "read-bucket"`: `s3:GetObject`, `s3:ListBucket` sul bucket bronze
   - `inline_policy "logs-access"`: `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`
7. **`aws_iam_policy`** — resource label: `{dominio_underscore}_bronze_db_access`
   - `name = "${local.prefix}-{dominio_kebab}-bronze-db-full-access-parquet"` — **include sempre il dominio**
   - Resource ARN specifici: catalog, database, table, partition — **mai `Resource: "*"`**
8. **`aws_iam_role_policy_attachment`** — resource label: `{dominio_underscore}_crawler_db_access`

**Esempio naming per dominio `bm-utilizzazioni`:**
```hcl
resource "aws_iam_role" "bm_utilizzazioni_crawler" {
  name = "${local.prefix}-bm-utilizzazioni-crawler-parquet"
  ...
}

resource "aws_iam_policy" "bm_utilizzazioni_bronze_db_access" {
  name = "${local.prefix}-bm-utilizzazioni-bronze-db-full-access-parquet"
  ...
}

resource "aws_glue_crawler" "bm_utilizzazioni_tables" {
  name = "${local.prefix}-bm-utilizzazioni-crawler-parquet"
  ...
}
```

**Policy Glue Catalog (ARN specifici obbligatori):**
```hcl
Resource = [
  "arn:aws:glue:${var.region}:${var.account_id}:catalog",
  "arn:aws:glue:${var.region}:${var.account_id}:database/${aws_glue_catalog_database.{dominio_underscore}_bronze.name}",
  "arn:aws:glue:${var.region}:${var.account_id}:table/${aws_glue_catalog_database.{dominio_underscore}_bronze.name}/*",
  "arn:aws:glue:${var.region}:${var.account_id}:partition/${aws_glue_catalog_database.{dominio_underscore}_bronze.name}/*/*",
]
```

> ⚠️ Le inline policy S3/logs vanno nell'`aws_iam_role` direttamente (non come `aws_iam_policy` separata).
> La policy Glue Catalog va come `aws_iam_policy` separata con `aws_iam_role_policy_attachment`.

> ⚠️ **`crawler_scheduling.status`** è un booleano (`true`/`false`) nei repo IaC — usare operatore ternario diretto:
> `schedule = var.config.crawler_scheduling.status ? var.config.crawler_scheduling.cron : null`

### Step 4C — modules/silver/silver.tf

🟢 SICURO

Risorse chiave del layer silver:

1. **`aws_glue_catalog_database`** — naming: `{dominio}_silver` (prod) o `{env}_{dominio}_silver`
   - `lifecycle { prevent_destroy = true }` — **OBBLIGATORIO**
2. **`aws_iam_policy`** — policy Glue Catalog per accesso silver (read + partition write, no crawler lifecycle)

**Azioni IAM per la policy silver** (sottoinsieme del bronze, senza crawler lifecycle):
```
glue:GetDatabase, glue:GetTable, glue:GetTables
glue:GetPartition, glue:GetPartitions, glue:BatchGetPartition
glue:CreatePartition, glue:BatchCreatePartition, glue:UpdatePartition
```

---

## 5. Tables Definition

### Step 5 — tables_definition/

🟢 SICURO

Struttura directory:

```
tables_definition/
├── bronze/
│   └── {dominio}.yaml           # Definizione tabelle bronze (inizialmente vuoto)
├── silver/
│   ├── dev-{dominio}-silver-ddl.sql
│   ├── qa-{dominio}-ddl.sql
│   └── prod-{dominio}-ddl.sql
└── source/
    └── {dominio}.sql            # DDL sorgente originale (Oracle/altro)
```

**Template `tables_definition/bronze/{dominio}.yaml`:**
```yaml
# {Dominio} bronze tables definition
#
# Popolare l'elenco `tables` con le tabelle sorgente da ingestionare
# nel layer bronze del data lake.
#
# Esempio:
#   - name: {dominio}_d_tabella
#     path: {DOMINIO}_D_TABELLA
#     columns:
#       - Name: op
#         Type: string
#       - Name: commit_time
#         Type: string

tables: []
```

I file DDL silver sono placeholder da completare con lo schema reale delle tabelle Iceberg.

---

## 6. Sicurezza — Checklist Pre-Commit

### Step 6 — Verifica IAM e Safety

🟡 MEDIO — esegui questa checklist prima di ogni commit di moduli Terraform

| Check | Cosa verificare |
|---|---|
| ✅ No wildcard IAM | Nessun `glue:Get*`, `s3:*`, o simili nelle policy |
| ✅ `prevent_destroy = true` | Su `aws_glue_catalog_database` bronze e silver |
| ✅ `get_env("ENV", "dev")` | Default "dev" nei `terragrunt.hcl` dei moduli (mai "sviluppo") |
| ✅ Azioni crawler complete | Policy bronze include tutte le azioni crawler lifecycle |
| ✅ Nessun secret hardcoded | Nessun ARN di account hardcoded nei `.tf` — usa `var.account_id` |
| ✅ Naming consistente | Prefix `${var.env}-${var.project}-${var.module}` + dominio nel nome risorse IAM/Glue (es. `${local.prefix}-{dominio}-crawler-parquet`) |
| ✅ Partizioni bronze | Tre partition_keys: `year`, `month`, `day` (tipo string) |

🔴 CRITICO — Mostra pre-flight card prima di eseguire

| 🔴 CRITICO (modifica policy IAM) — 🔨 DevForge · siae-datalake-iac-setup |
|:---|
| **⚠️ OPERAZIONE REMOTA — WRITE/UPDATE/DELETE SU AWS IAM** |
| 📋 Risorsa: `<policy/role name>` · 🌍 Ambiente: `<target>` |
| **▼ Azioni** |
| 1. Scrittura/modifica policy IAM nel modulo bronze/silver → `<file .tf>` |
| 2. La policy verrà applicata all'esecuzione del terraform apply successivo |
| 💡 Perché: Le policy IAM controllano gli accessi a Glue Catalog, S3 e Crawler — una policy errata può bloccare tutti i job o aprire accessi non autorizzati |
| 🚫 Se NO: Policy invariata, accessi non modificati, il modulo non sarà deployabile |

⏸️ **ATTENDI CONFERMA ESPLICITA** — mostra la card e NON eseguire finché l'utente
risponde esplicitamente ("sì, procedi" / "no, annulla"). Silenzio ≠ consenso.

**Solo dopo "sì, procedi"**, esegui:

---

## 7. GitHub Workflows

### Step 7 — Verifica e Aggiornamento Workflows

🟢 SICURO

I workflow CI/CD riutilizzano `itsiae/siae-gh-actions`. Verifica che tutti i workflow
presenti corrispondano al pattern del repo di riferimento:

| Workflow | Trigger | Azione |
|---|---|---|
| `cd-terragrunt-plan-collaudo.yaml` | tag `rc-PLAN-COLLAUDO` | Solo plan |
| `cd-terragrunt-plan-deploy-collaudo.yaml` | tag `rc-COLLAUDO` | Plan + apply |
| `cd-terragrunt-plan-certificazione.yaml` | tag `rc-PLAN-CERTIFICAZIONE` | Solo plan |
| `cd-terragrunt-plan-deploy-certificazione.yaml` | tag `rc-CERTIFICAZIONE` | Plan + apply |
| `cd-terragrunt-plan-produzione.yaml` | workflow_dispatch | Solo plan |
| `cd-terragrunt-plan-deploy-produzione.yaml` | workflow_dispatch | Plan + apply |
| `code-scan.yaml` | schedule weekly | Qodana scan |
| `release-please.yaml` | push main | Release automation |

> ⚠️ Il job `tag-management` deve essere presente in **tutti** i workflow plan+deploy.
> Non rimuoverlo durante il porting da un repo template.

**Aggiornamento versione `siae-gh-actions` — OBBLIGATORIO**

Dopo la verifica, indipendentemente dalla repo di riferimento, imposta **sempre** la versione
`v3.0.0` su tutti i workflow.

Prima di eseguire il `sed`, rileva la situazione attuale:

```bash
# 1. Versione attuale rilevata nei workflow
grep -roh "@v[0-9]\+\.[0-9]\+\.[0-9]\+" .github/workflows/*.yaml | sort -u

# 2. Numero di file .yaml che verranno modificati
grep -rl "siae-gh-actions" .github/workflows/*.yaml | wc -l

# 3. Numero totale di occorrenze
grep -rn "uses:.*siae-gh-actions" .github/workflows/ | wc -l
```

🔴 CRITICO — Mostra pre-flight card prima di eseguire

| 🔴 CRITICO (aggiornamento versione CI/CD) — 🔨 DevForge · siae-datalake-iac-setup |
|:---|
| **⚠️ OPERAZIONE REMOTA — UPDATE SU TUTTI I WORKFLOW CI/CD** |
| 📋 Risorsa: `.github/workflows/*.yaml` · 🌍 Ambiente: tutti (collaudo, certificazione, produzione) |
| **▼ Azioni** |
| 1. `sed -i` sostituisce `siae-gh-actions@{versione attuale rilevata}` → `siae-gh-actions@v3.0.0` |
| 2. N file `.yaml` verranno modificati (valore rilevato dallo step precedente) |
| 3. Tutte le pipeline CI/CD (plan, apply, scan, release) cambieranno versione d'azione simultaneamente |
| 💡 Perché: Il bump di versione modifica il comportamento di TUTTI i pipeline CI/CD — plan, apply, scan, release — su tutti gli ambienti. Una versione errata può rompere i deploy su collaudo, certificazione e produzione |
| 🚫 Se NO: I workflow rimangono alla versione corrente, nessuna modifica ai file `.yaml` |

⏸️ **ATTENDI CONFERMA ESPLICITA** — mostra la card e NON eseguire finché l'utente
risponde esplicitamente ("sì, procedi" / "no, annulla"). Silenzio ≠ consenso.

**Solo dopo "sì, procedi"**, esegui:

```bash
sed -i 's/@v[0-9]\+\.[0-9]\+\.[0-9]\+/@v3.0.0/g' .github/workflows/*.yaml
grep -rn "uses:.*siae-gh-actions" .github/workflows/
```

Verifica che tutte le occorrenze di `siae-gh-actions` riportino `@v3.0.0`.

---

## 8. Git — Branch Setup e Primo Commit

### Step 8 — Setup Branch

Questo step richiede `siae-git-workflow`. Invoca la skill prima di procedere.

```
REQUIRED SUB-SKILL: siae-git-workflow
```

Pattern SIAE per nuovo dominio:

```bash
# 1. Branch di release dal main
git checkout main && git pull origin main
git checkout -b release/{SPRINT_ID}

# 2. Feature branch per il setup
git checkout -b feature/{SPRINT_ID}/setup-{dominio}-domain

# 3. Commit scaffolding iniziale
git add .
git commit -m "chore(iac): setup initial repo structure for {dominio} domain"

# 4. Push entrambi i branch
git push origin release/{SPRINT_ID}
git push origin feature/{SPRINT_ID}/setup-{dominio}-domain
```

> Pre-flight card 🔴 ALTO obbligatoria per entrambi i push — segui `siae-git-workflow`.

---

## Vincoli Inviolabili

| # | Vincolo | Motivazione |
|---|---------|-------------|
| V1 | `prevent_destroy = true` su tutti i Glue Catalog Database | Cancellazione accidentale perde il catalogo tabelle in produzione |
| V2 | Solo azioni IAM esplicite, mai wildcard | Least privilege non è opzionale — violazione MAJOR in code review |
| V3 | `get_env("ENV", "dev")` nei terragrunt.hcl dei moduli | Default "dev" sicuro per esecuzioni locali senza ENV settato |
| V4 | Partizioni `year/month/day` obbligatorie nel bronze | Senza partizioni, query full-scan costose in Athena/Glue |
| V5 | `tables_definition/bronze/{dominio}.yaml` sempre presente | Richiesto da `local.{dominio}_tables_def` nel terragrunt.hcl |
| V6 | Naming `{env}_{dominio}_bronze` (non-prod) / `{dominio}_bronze` (prod) | Isolamento ambienti nel Glue Catalog |
| V7 | Non committare file `.yaml` generati da `.tmpl` | Contengono secrets e valori di ambiente — solo `.tmpl` in git |
| V8 | Policy IAM bronze include azioni crawler lifecycle | Senza `StartCrawler`, `GetCrawler` il crawler non può essere gestito |
| V9 | `project_name: datalake` fisso in `config.yaml` per tutti i repo `datalake-{dominio}-iac` | Uniformità nei prefix risorse AWS tra tutti i domini del data lake SIAE |

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realtà |
|----------|---------|
| "Il `prevent_destroy` lo aggiungo dopo" | Dopo il primo `terraform apply` potrebbe già esserci dati reali. Mettilo subito. |
| "Uso `glue:Get*` che è più semplice" | Le wildcard IAM sono una vulnerabilità. Code review lo boccerà sempre. |
| "Il default ENV lo metto 'sviluppo'" | Il default deve essere "dev" — "sviluppo" è il branch git, non il nome dell'ambiente. |
| "Il `tables_definition` lo creo quando ho le tabelle" | Il `terragrunt.hcl` lo referenzia subito. Senza il file, `terraform plan` fallisce. |
| "I workflow li copio senza controllare il tag-management" | Il job `tag-management` viene spesso rimosso per errore — verifica sempre. |
| "Il file `.yaml` generato dal `.tmpl` lo commitто per comodità" | Può contenere credenziali o valori segreti passati dalla CI. Mai in git. |
| "Le azioni crawler le aggiungo se serve" | Il crawler non può girare senza `StartCrawler` nella policy. Fallisce in silenzio. |
| "La naming convention del Glue DB non importa" | `dev_zucchetti_bronze` vs `zucchetti_bronze` — senza prefisso env si sovrascrivono i dati prod. |
| "Il `project_name` lo metto uguale al dominio (es. `zucchetti`)" | Il valore è **sempre `datalake`** per tutti i repo `datalake-{dominio}-iac`. Usare il nome del dominio è sbagliato e genera prefix risorse non standard. |

---

## Classificazione Rischio Operazioni

| Operazione | Rischio | Card |
|---|---|---|
| Lettura/analisi struttura repo | 🟢 Sicuro | No |
| Scrittura `config.yaml`, `chart/Chart.yaml` | 🟢 Sicuro | No |
| Scrittura `live/_envs/*.tmpl` | 🟢 Sicuro | No |
| Scrittura `live/bronze/terragrunt.hcl` | 🟢 Sicuro | No |
| Scrittura `live/silver/terragrunt.hcl` | 🟢 Sicuro | No |
| Scrittura moduli `_input.tf`, `_local.tf`, `_output.tf` | 🟢 Sicuro | No |
| Scrittura `bronze.tf` / `silver.tf` con IAM | 🟡 Medio | No |
| Modifica policy IAM esistente | 🔴 Critico | Si |
| `sed -i` aggiornamento versione `siae-gh-actions` su workflow CI/CD | 🔴 Critico | Si |
| `git push` branch | 🔴 Alto | Si (siae-git-workflow) |
| `terraform apply` | 🚨 Critico | Si (siae-iac) |

---

## Risorse Aggiuntive

- [reference/repo-structure.md](reference/repo-structure.md) — Struttura completa directory e file template
- [reference/bronze-module.md](reference/bronze-module.md) — Template completo modulo bronze (Terraform)
- [reference/silver-module.md](reference/silver-module.md) — Template completo modulo silver (Terraform)
