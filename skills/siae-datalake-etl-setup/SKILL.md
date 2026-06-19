---
name: siae-datalake-etl-setup
description: >
  Use when setting up a new datalake ETL repo (datalake-{dominio}-etl) from a reference repo.
  Trigger: "setup repo etl", "nuovo dominio etl", "crea repo datalake etl",
  "scaffolding etl", "datalake-{nome}-etl", "setup da riferimento", "clona struttura etl".
---

# SIAE Datalake ETL Setup

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗    ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║    ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║    ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝    ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝     ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝      ║
║          🔨 DevForge · SIAE DATALAKE ETL SETUP                ║
║         "Il codice si forgia. Il developer cresce."            ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Flexible | **Fase SDLC:** 2. Setup & Scaffolding

---

> 📊 **Dai repo itsiae:** I repo datalake-*-etl seguono la stessa struttura: modulo silver-{dominio}
> con Glue job PySpark, Step Function, EventBridge Scheduler e Terragrunt DRY.
> Il repo di riferimento **canonico** è `datalake-sport-etl` — pattern senza crawler Bronze dedicato,
> Step Function che inizia direttamente da `RetrieveTablesToUpdate`.
> Standardizzare il setup da questo riferimento riduce il bootstrap da ore a minuti.
> Fonte: pattern validato su `datalake-sport-etl`, `datalake-zucchetti-etl` e `datalake-bm-utilizzazioni-etl`.

---

## ⚠️ Nota critica: scegli il repo di riferimento corretto

Non tutti i repo `datalake-*-etl` hanno la stessa struttura. Prima di iniziare, verifica:

| Pattern | Caratteristiche | Repo esempio |
|---|---|---|
| **Semplice (consigliato)** | Niente crawler Bronze dedicato, SFN inizia da `RetrieveTablesToUpdate`, variabili `STEPFUN_CRON_SCHEDULE`/`STEPFUN_CRON_STATUS` | `datalake-sport-etl` |
| **Con crawler** | Step Function separata per crawler Bronze, variabile `BRONZE_{DOMINIO}_CRAWLER_NAME`, SFN inizia da `StartBronzeCrawler` | `datalake-performing-etl`, `datalake-pmo-etl` |

**Il pattern semplice (senza crawler) è il default indipendentemente dal repo di riferimento scelto.** Anche se si usa `datalake-pmo-etl` o `datalake-performing-etl` come riferimento (es. per struttura Glue o IAM), la Step Function deve comunque iniziare da `RetrieveTablesToUpdate` — rimuovere gli step crawler dal JSON. Il pattern con crawler si adotta solo se il dominio target richiede esplicitamente un crawler Bronze dedicato.

---

## Input Richiesti

| Parametro | Descrizione | Esempio |
|---|---|---|
| `repo-riferimento` | Nome del repo ETL di riferimento (default: `datalake-sport-etl`) | `datalake-sport-etl` |
| `repo-target` | Path locale del repo ETL da configurare | `datalake-zucchetti-etl` |
| `dominio` | Nome dominio del repo target (usato per naming risorse) | `zucchetti` |
| `glue-jobs` | Lista nomi Glue job da creare (kebab-case) | `trasferte` |
| `gh-actions-version` | Versione siae-gh-actions da usare nei workflow (default: `v3.0.0`) | `v3.0.0` |

Se un parametro obbligatorio manca, chiedi prima di procedere. `gh-actions-version` ha default `v3.0.0` — non chiedere se non fornito, usa il default direttamente.

---

## Checklist Progress

```
Datalake ETL Setup Progress:
- [ ] Step 1: Raccolta e validazione parametri
- [ ] Step 2: Analisi struttura repo di riferimento (sport-etl)
- [ ] Step 3: Aggiornamento config.yaml e chart/Chart.yaml
- [ ] Step 4: Aggiornamento live/_envs/ (dev/qa/prod .tmpl)
- [ ] Step 5: Creazione live/shared/terragrunt.hcl
- [ ] Step 6: Creazione live/silver-{dominio}/terragrunt.hcl
- [ ] Step 7: Creazione modules/silver-{dominio}/ (_input, _local, _output, .tf)
- [ ] Step 8: Creazione glue-definitions.yaml
- [ ] Step 9: Creazione orchestration/ (silver-etl.json, new_db_silver_mapping.json)
- [ ] Step 10: Copia glue-jobs/src/libs/ e configs/
- [ ] Step 11: Aggiornamento workflow GitHub Actions alla versione target
- [ ] Step 12: Rimozione scaffolding example
- [ ] Step 13: Aggiornamento README.md
- [ ] Step 14: Primo commit
```

---

## Step 1 — Raccolta e Validazione Parametri

🟢 SICURO

Verifica che tutti i parametri siano presenti. Proponi `datalake-sport-etl` come repo di riferimento
se non specificato, spiegando brevemente il motivo (pattern semplice, senza crawler Bronze dedicato).

Dalla coppia `repo-riferimento` / `repo-target`, deriva automaticamente:
- `{DOMINIO}` = estratto dal nome repo target: `datalake-{dominio}-etl`
- `{MODULO}` = `silver-{dominio}` (es. `silver-zucchetti`)
- `{SILVER_CONFIG_KEY}` = `silver_{dominio}` (chiave nei .tmpl)
- `{UPDATE_ATTR}` = `last_silver_{dominio}_update_time`

Dalla lista `glue-jobs`, deriva per ogni job:
- `{nome-job}` = nome kebab-case fornito (es. `trasferte`)
- `{nome_tabella_silver}` = nome job con trattini sostituiti da underscore

Mostra il riepilogo derivazioni e chiedi conferma prima di procedere.

---

## Step 2 — Analisi Struttura Repo di Riferimento

🟢 SICURO

Leggi in parallelo i file chiave del repo di riferimento via `gh api`:

```bash
gh api repos/itsiae/{repo-riferimento}/contents/live/_envs/dev.tmpl | python3 -c "import sys,json,base64; d=json.load(sys.stdin); print(base64.b64decode(d['content']).decode())"
```

File da leggere:
```
live/_envs/dev.tmpl
live/_envs/prod.tmpl
live/silver-{dominio-ref}/terragrunt.hcl
modules/silver-{dominio-ref}/_input.tf
modules/silver-{dominio-ref}/glue-jobs.tf
modules/silver-{dominio-ref}/stepfunction-orchestration.tf
modules/silver-{dominio-ref}/orchestration/silver-etl.json
```

Elenca i file presenti nella directory orchestration:
```bash
gh api repos/itsiae/{repo-riferimento}/contents/modules/silver-{dominio-ref}/orchestration | python3 -c "import sys,json; [print(v['name']) for v in json.load(sys.stdin)]"
```

**Identifica il pattern** prima di procedere:
- Se `silver-etl.json` ha `"StartAt": "RetrieveTablesToUpdate"` → pattern **semplice** (sport)
- Se `silver-etl.json` ha `"StartAt": "StartBronzeCrawler"` → pattern **con crawler**

Vedi [reference/naming-substitutions.md](reference/naming-substitutions.md) per la mappa completa.

---

## Step 3 — config.yaml e chart/Chart.yaml

🟢 SICURO

**config.yaml** — aggiorna `project_name` e `repository_name`:
```yaml
project_name: datalake-{dominio}-etl
repository_name: datalake-{dominio}-etl
```

**chart/Chart.yaml** — aggiorna `name` e `template.repository`:
```yaml
name: datalake-{dominio}-etl
template:
  repository: datalake-{dominio}-etl
```

---

## Step 4 — live/_envs/ (dev/qa/prod .tmpl)

🟢 SICURO

Crea `live/_envs/{env}.tmpl` dal riferimento (sport-etl). Il pattern sport usa:
- Variabili orchestrazione: `$STEPFUN_CRON_SCHEDULE` e `$STEPFUN_CRON_STATUS` (non `$CRON_SCHED`)
- Nessun campo `bronze_crawler_name` — il dominio non ha crawler Bronze dedicato
- Chiave config module: `silver_{dominio}:` (es. `silver_zucchetti:`)

Sostituzioni da applicare:

| Riferimento (sport) | Target (nuovo dominio) |
|---|---|
| `silver_sport:` | `silver_{dominio}:` |
| `# Silver Sport vars module` | `# Silver {dominio} vars module` |

**Differenza tra ambienti per `force_no_window`:**
- `dev.tmpl` → `force_no_window: 1`
- `qa.tmpl` → `force_no_window: 0` (simula il comportamento prod)
- `prod.tmpl` → `force_no_window: 0`

Mantieni invariati tutti i placeholder `$VARIABILE`.

---

## Step 5 — live/shared/terragrunt.hcl

🟢 SICURO

Copia identico dal riferimento — il modulo shared è generico, non contiene il dominio.
Verifica che gli input corrispondano agli output del modulo `modules/shared/`.

---

## Step 6 — live/silver-{dominio}/terragrunt.hcl

🟢 SICURO

Crea `live/silver-{dominio}/terragrunt.hcl` dal riferimento sostituendo:

| Riferimento (sport) | Target |
|---|---|
| `module = "silver-sport"` | `module = "silver-{dominio}"` |
| `local.stage.silver_sport` | `local.stage.silver_{dominio}` |

**Non aggiungere** `bronze_{dominio}_crawler_name` — il pattern sport non lo ha.

Il blocco `dependency "shared"` rimane identico.

---

## Step 7 — modules/silver-{dominio}/

🟢 SICURO

Crea la directory `modules/silver-{dominio}/` con i seguenti file:

**`_input.tf`** — copia da riferimento sostituendo il nome del modulo nei commenti.
**Non aggiungere** la variabile `bronze_{dominio}_crawler_name` — non presente nel pattern sport.

La variabile `config` deve avere questa struttura (senza `bronze_crawler`):
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

**`_local.tf`** — identico (usa `var.env`, `var.module` generici).

**`_output.tf`** — copia identico.

---

## Step 8 — glue-jobs.tf e glue-jobs-custom-libraries-upload.tf

🟢 SICURO

Copia `glue-jobs.tf` dal riferimento sostituendo:
- Il nome della risorsa CloudWatch: `silver_anagrafiche_glue_etl` → `silver_{dominio}_glue_etl`
- Il riferimento alla risorsa nel `default_arguments`: `aws_cloudwatch_log_group.silver_anagrafiche_glue_etl.name` → `aws_cloudwatch_log_group.silver_{dominio}_glue_etl.name`

**Non includere** l'argomento `--last_iac_upload_job_timestamp` — non presente nel pattern sport.

Copia `glue-jobs-custom-libraries-upload.tf` identico.

---

## Step 9 — glue-definitions.yaml

🟢 SICURO

Crea `modules/silver-{dominio}/glue-definitions.yaml` con una entry per ogni job:

```yaml
jobs:
  - job_name: "{nome-job}"
    description: "ETL that populates the {nome_underscored} table in the silver layer"
    dev_number_of_workers: 2
    qa_number_of_workers: 2
    prod_number_of_workers: 10
    worker_type: "G.1X"
    glue_version: "5.0"
    execution_class: "FLEX"
    enable_gluejob_sparkui: "true"
    max_concurrent_runs: 1
    timeout_min: 120
    file_name: "{nome-job}"
```

---

## Step 10 — stepfunction-orchestration.tf ed eventbridge-etl-scheduler.tf

🟢 SICURO

**stepfunction-orchestration.tf** — copia dal riferimento sostituendo:
- `scope = "sport"` → `scope = "{dominio}"`
- **Non aggiungere** `crawler_name` nel `templatefile` — pattern sport non lo ha

IAM policy `glue-jobs-permissions`: usa le azioni minime necessarie (least privilege):
```hcl
"Action" : ["glue:StartJobRun", "glue:GetJobRun", "glue:BatchStopJobRun"],
"Resource" : ["arn:aws:glue:${var.region}:${var.account_id}:job/${local.prefix}-*"]
```
Il `Resource` è già scoped al prefisso del modulo tramite `${local.prefix}-*` — non usare `*` globale.

**Non aggiungere** policy `crawler-permissions` — non presente nel pattern sport.

**eventbridge-etl-scheduler.tf** — copia identico.

---

## Step 11 — orchestration/silver-etl.json e new_db_silver_mapping.json

🟢 SICURO

**silver-etl.json** — copia dal riferimento sostituendo:
- `"update_attr_name": "last_silver_sport_update_time"` → `"last_silver_{dominio}_update_time"`
- `"silver_mapping"` nei due step `RetrieveTablesToUpdate` e `UpdateSilverCommitTime`:
  ```json
  "silver_mapping": {
    "{nome-job}": ["{nome_tabella_silver}"]
  }
  ```
- `scope` nei `DetailType` è già gestito dalla variabile Terraform `${scope}`

Il file si chiama **`silver-etl.json`** (invariato). Inizia da `"StartAt": "RetrieveTablesToUpdate"` — nessuno step crawler.

> ⚠️ **`--force_no_window` nell'ASL deve essere sempre `"0"` hardcoded** — non passarlo come variabile templatefile. Il valore in `.tmpl` agisce solo sui `default_arguments` del Glue job al deploy. Iniettarlo nell'ASL farebbe eseguire la Step Function senza finestra temporale ad ogni schedulazione (incluso dev), causando la riscrittura dell'intero datalake.

**`new_db_silver_mapping.json`** — crea con il mapping dei job del dominio:
```json
{
  "{nome-job}": ["{nome_tabella_silver}"]
}
```

**Nota:** il file si chiama `new_db_silver_mapping.json` (non `silver-mapping.json`) — nome adottato nel pattern sport.

---

## Step 12 — glue-jobs/src/libs/ e configs/

🟢 SICURO

Copia identici dal riferimento:
- `glue-jobs/src/libs/__init__.py`
- `glue-jobs/src/libs/custom_classes.py`
- `glue-jobs/configs/dev/app_conf.json`
- `glue-jobs/configs/dev/log4j2.properties`
- `glue-jobs/configs/qa/app_conf.json`
- `glue-jobs/configs/qa/log4j2.properties`
- `glue-jobs/configs/prod/app_conf.json`
- `glue-jobs/configs/prod/log4j2.properties`

**⚠️ Il file `glue-jobs/src/{nome-job}.py` NON va creato qui.**
È codice di produzione — va implementato con `siae-tdd` in una sessione dedicata.
Segnalalo esplicitamente all'utente al termine del setup.

---

## Step 13 — Aggiornamento Workflow GitHub Actions

🟢 SICURO

Aggiorna tutti i file in `.github/workflows/` che referenziano `itsiae/siae-gh-actions`.
La versione corrente di riferimento è **`v3.0.0`**.

```bash
sed -i 's/@v[0-9]\+\.[0-9]\+\.[0-9]\+/@{gh-actions-version}/g' .github/workflows/*.yaml
```

Dove `{gh-actions-version}` è il parametro ricevuto in input, default **`v3.0.0`** se non specificato.

Verifica con `grep -rn "uses:" .github/workflows/` che tutte le versioni siano allineate.

---

## Step 14 — Rimozione Scaffolding Example

🔴 CRITICO — Mostra pre-flight card prima di eseguire

| 🔴 CRITICO (Rimozione scaffolding) — 🔨 DevForge · siae-datalake-etl-setup |
|:---|
| **⚠️ OPERAZIONE LOCALE IRREVERSIBILE — DELETE SU FILE SYSTEM** |
| 📋 Risorsa: `modules/example/`, `live/example/`, `chart/` · 🌍 Ambiente: `locale (repo-target)` |
| **▼ Azioni** |
| 1. `rm -rf modules/example/` — rimuove tutti i file dello scaffolding modulo example |
| 2. `rm -rf live/example/` — rimuove tutti i file Terragrunt di esempio |
| 3. `rm -rf chart/` — rimuove la directory chart se non presente nel repo di riferimento sport-etl |
| 💡 Perché: la rimozione è irreversibile senza git; se eseguita su branch sbagliato o prima di un commit, i file sono persi senza possibilità di rollback semplice |
| 🚫 Se NO: lo scaffolding rimane nel repo e potrebbe confondere i deploy Terraform futuri |

⏸️ **ATTENDI CONFERMA ESPLICITA** — mostra la card e NON eseguire finché l'utente
risponde esplicitamente ("sì, procedi" / "no, annulla"). Silenzio ≠ consenso.

**Solo dopo "sì, procedi"**, esegui:

Prima di rimuovere, verifica che non ci siano riferimenti a `example` nel codice:
```bash
grep -rn "example" live/ modules/ --include="*.tf" --include="*.hcl" | grep -v "example/"
```

Se il grep non restituisce risultati, rimuovi:
- `modules/example/` (tutti i file)
- `live/example/` (tutti i file)
- `chart/` — **da rimuovere** se non presente nel repo di riferimento sport-etl

---

## Step 15 — README.md

🟢 SICURO

Aggiorna `README.md` con le informazioni specifiche del dominio.
Vedi [reference/readme-template.md](reference/readme-template.md) per il template completo.

---

## Step 16 — GitHub Env Sync

🔴 CRITICO — Mostra pre-flight card prima di eseguire

| 🔴 CRITICO (GitHub Env Sync) — 🔨 DevForge · siae-datalake-etl-setup |
|:---|
| **⚠️ OPERAZIONE REMOTA — WRITE/UPDATE SU GITHUB ENVIRONMENTS (VARIABILI AWS CI/CD)** |
| 📋 Risorsa: `itsiae/datalake-{dominio}-etl` · 🌍 Ambiente: `collaudo`, `certificazione`, `produzione` |
| **▼ Azioni** |
| 1. Copia/aggiorna le variabili GitHub Actions da `datalake-sport-etl` verso il repo target |
| 2. Variabili interessate: `AWS_ENV`, `AWS_ORG_ACCOUNT`, `AWS_REGION`, `AWS_ROLE`, `AWS_TARGET_ACCOUNT_ID`, `BRONZE_DATALAKE_BUCKET_ID`, `SILVER_DATALAKE_BUCKET_ID`, `DYNAMO_BRONZE_TABLE_UPDATE_ID`, `EVENTBRIDGE_DATALAKE_BUS_ID`, `EVENTBRIDGE_DATAPLATFORM_ERRORS_ID`, `GLUE_PACKAGES_BUCKET_ID`, `GLUE_SPARKUI_BUCKET_ID`, `LOGS_RETENTION_DAYS`, `OPEN_LINEAGE_DOMAIN_ID`, `SILVER_UPDATES_MANAGER_LAMBDA_ARN`, `STEPFUN_CRON_SCHEDULE`, `STEPFUN_CRON_STATUS`, `VPC_STAGE` |
| 💡 Perché: le variabili GitHub environments controllano i parametri AWS (account, region, ruoli IAM, bucket) usati dalle pipeline CI/CD; una modifica errata può rompere i deploy su tutti gli ambienti |
| 🚫 Se NO: le variabili CI/CD rimangono quelle di default del repo template e i deploy falliranno |

⏸️ **ATTENDI CONFERMA ESPLICITA** — mostra la card e NON eseguire finché l'utente
risponde esplicitamente ("sì, procedi" / "no, annulla"). Silenzio ≠ consenso.

**Solo dopo "sì, procedi"**, esegui tramite sub-skill:

```
REQUIRED SUB-SKILL: siae-github-env-sync
```

Dopo il commit iniziale, sincronizza le variabili GitHub Actions dalla repo di riferimento
(`datalake-sport-etl`) verso il repo target per tutti gli ambienti (`collaudo`, `certificazione`, `produzione`).

Le variabili del pattern sport includono (senza `BRONZE_*_CRAWLER_NAME`):
- `AWS_ENV`, `AWS_ORG_ACCOUNT`, `AWS_REGION`, `AWS_ROLE`, `AWS_TARGET_ACCOUNT_ID`
- `BRONZE_DATALAKE_BUCKET_ID`, `SILVER_DATALAKE_BUCKET_ID`
- `DYNAMO_BRONZE_TABLE_UPDATE_ID`
- `EVENTBRIDGE_DATALAKE_BUS_ID`, `EVENTBRIDGE_DATAPLATFORM_ERRORS_ID`
- `GLUE_PACKAGES_BUCKET_ID`, `GLUE_SPARKUI_BUCKET_ID`
- `LOGS_RETENTION_DAYS`
- `OPEN_LINEAGE_DOMAIN_ID`
- `SILVER_UPDATES_MANAGER_LAMBDA_ARN`
- `STEPFUN_CRON_SCHEDULE`, `STEPFUN_CRON_STATUS`
- `VPC_STAGE`

**Non sono presenti** `CRON_SCHED`, `CRON_SCHED_STATUS`, `BRONZE_*_CRAWLER_NAME` — questi appartengono al pattern con crawler (pmo/performing).

---

## Step 17 — Primo Commit

🔴 ALTO — pre-flight card obbligatoria

```
REQUIRED SUB-SKILL: siae-git-workflow
```

Messaggio commit convenzionale:
```
chore(setup): initial repo setup for {dominio}-etl domain
```

---

## Fallback Obbligatori

### Repo di riferimento non trovato
Se il repo di riferimento non esiste su GitHub o localmente:
1. Chiedi il path corretto all'utente
2. Non procedere con assunzioni

### Pattern con crawler richiesto esplicitamente
Se il dominio target richiede un crawler Bronze dedicato:
1. Usa `datalake-performing-etl` come riferimento invece di sport
2. Aggiungi `bronze_{dominio}_crawler_name` negli input, nelle variabili e nel templatefile
3. Le variabili CI/CD useranno `CRON_SCHED`/`CRON_SCHED_STATUS` e `BRONZE_{DOMINIO}_CRAWLER_NAME`

### File Python del Glue job richiesto dall'utente
Se l'utente chiede di creare anche il file `.py`:
1. Spiega che è codice di produzione e richiede `siae-tdd`
2. Proponi di farlo in una sessione dedicata dopo il setup IaC

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|---|---|---|
| Lettura repo di riferimento via gh api | 🟢 Sicuro | No |
| Scrittura file Terraform/Terragrunt | 🟢 Sicuro | No |
| Scrittura _envs/*.tmpl | 🟢 Sicuro | No |
| Aggiornamento workflow versioni | 🟢 Sicuro | No |
| Rimozione scaffolding example | 🔴 Critico | Sì (gate inline Step 14) |
| Scrittura README.md | 🟢 Sicuro | No |
| GitHub Env Sync | 🔴 Critico | Sì (gate inline Step 16 + siae-github-env-sync) |
| git commit + push | 🔴 Alto | Sì (siae-git-workflow) |

---

## Vincoli

1. **MAI** creare il file `.py` del Glue job — è codice di produzione, richiede `siae-tdd`
2. **MAI** sostituire `$VARIABILE` nei `.tmpl` con valori reali — sono placeholder CI/CD
3. **DEFAULT a pattern sport** (senza crawler) — usa pattern con crawler solo se richiesto esplicitamente
4. **IAM SFN `glue:*` vietato** — usa sempre `["glue:StartJobRun", "glue:GetJobRun", "glue:BatchStopJobRun"]` con `Resource` scoped su `${local.prefix}-*`
5. **`new_db_silver_mapping.json`** è il nome corretto del file mapping nel pattern sport (non `silver-mapping.json`)
6. **`STEPFUN_CRON_SCHEDULE`/`STEPFUN_CRON_STATUS`** sono le variabili corrette nel pattern sport
7. **SEMPRE** verificare che `force_no_window: 0` in prod e `1` in dev/qa
8. **GATE CRITICO OBBLIGATORIO** — pre-flight card con conferma esplicita per: rimozione file locali (`rm -rf`), env sync GitHub (variabili AWS CI/CD), git push; silenzio ≠ consenso
9. **`--force_no_window: "0"` nell'ASL JSON sempre hardcoded** — non iniettare il valore da templatefile variable; il campo `.tmpl` è usato esclusivamente dai `default_arguments` Glue al deploy, non dalla Step Function a runtime

---

## Risorse Aggiuntive

- [reference/naming-substitutions.md](reference/naming-substitutions.md) — mappa completa sostituzioni dominio
- [reference/readme-template.md](reference/readme-template.md) — template README per repo datalake-etl
