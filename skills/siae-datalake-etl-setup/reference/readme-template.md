# README Template — datalake-{dominio}-etl

Usa questo template per generare il README del nuovo repo ETL.
Sostituisci tutti i placeholder `{...}` con i valori del dominio target.

---

```markdown
# 🚀 itsiae/datalake-{dominio}-etl

> Repository IaC per il dominio **{Dominio}** del Data Lake SIAE. Gestisce il deploy del layer ETL silver tramite AWS Glue, Step Functions e Terragrunt su architettura Medallion.

---

## 📚 Indice

- [Panoramica](#-panoramica)
- [✨ Funzionalità Principali](#-funzionalità-principali)
- [🏗️ Architettura](#️-architettura)
- [🛠️ Prerequisiti](#️-prerequisiti)
- [🚀 Come Iniziare](#-come-iniziare)
- [📂 Struttura del Progetto](#-struttura-del-progetto)
- [🔄 Flusso CI/CD](#-flusso-cicd)
- [🤝 Contribuire](#-contribuire)
- [🛡️ Sicurezza](#️-sicurezza)
- [⚖️ Licenza](#️-licenza)

---

## 📖 Panoramica

`datalake-{dominio}-etl` contiene l'infrastruttura as code per il processo ETL del dominio
**{Dominio}** nel Data Lake SIAE. Il repository gestisce il provisioning del modulo
`silver-{dominio}`: {descrizione job ETL}, orchestrato da una Step Function e schedulato
via EventBridge Scheduler.

Repository correlati:
- [`itsiae/datalake-{dominio}-iac`](https://github.com/itsiae/datalake-{dominio}-iac) — infrastruttura bronze/silver
- [`itsiae/siae-gh-actions`](https://github.com/itsiae/siae-gh-actions) — workflow CI/CD riutilizzabili

---

## ✨ Funzionalità Principali

- **Glue Job ETL silver-{dominio}**: job PySpark su AWS Glue 5.0 con Apache Iceberg.
- **Orchestrazione Step Functions**: avvia crawler bronze, recupera tabelle da aggiornare,
  lancia Glue job in parallelo, notifica via EventBridge.
- **Scheduling EventBridge**: trigger cron configurabile per ambiente.
- **Struttura Terragrunt DRY**: separazione `modules/` (logica) e `live/` (configurazione).
- **Automazione CI/CD**: pipeline GitHub Actions `{gh-actions-version}` per plan e apply.
- **IAM Least Privilege**: policy esplicite per ogni risorsa, nessun wildcard.

---

## 🏗️ Architettura

```mermaid
graph TD
    EB[EventBridge Scheduler] -->|cron| SF[Step Function\nsilver-{dominio}-orchestration]
    SF -->|StartCrawler| CR[Glue Crawler\nbronze-{dominio}]
    CR -->|cataloga| BC[(Bronze S3\nParquet CDC)]
    SF -->|RETRIEVE| LM[Lambda\nsilver-updates-manager]
    LM -->|tabelle da aggiornare| SF
    SF -->|startJobRun| GJ[Glue Job\n{nome-job}]
    GJ -->|legge| BC
    GJ -->|merge Iceberg| SC[(Silver S3\nApache Iceberg)]
    SF -->|PutEvents| EBUS[EventBridge Bus\nsilver-notification]
```

---

## 🛠️ Prerequisiti

- [AWS CLI](https://aws.amazon.com/cli/) con credenziali per l'account target
- [Terraform](https://www.terraform.io/downloads.html) >= 1.5
- [Terragrunt](https://terragrunt.gruntwork.io/docs/getting-started/install/) >= 0.50
- `make` · `git`

---

## 🚀 Come Iniziare

1. **Clona il repository**:
   ```bash
   git clone https://github.com/itsiae/datalake-{dominio}-etl.git
   cd datalake-{dominio}-etl
   ```
2. **Verifica `config.yaml`**: già configurato per il dominio `{dominio}`.
3. **Non committare i file `.yaml`** generati dalla CI/CD dai `.tmpl`.

```bash
make help       # mostra tutti i comandi
make plan_dev   # plan su collaudo
make qa         # deploy su collaudo
```

---

## 📂 Struttura del Progetto

```
datalake-{dominio}-etl/
├── config.yaml
├── live/
│   ├── terragrunt.hcl
│   ├── _envs/
│   │   ├── dev.tmpl
│   │   ├── qa.tmpl
│   │   └── prod.tmpl
│   ├── shared/
│   │   └── terragrunt.hcl
│   └── silver-{dominio}/
│       └── terragrunt.hcl
├── modules/
│   ├── shared/
│   └── silver-{dominio}/
│       ├── _input.tf
│       ├── _local.tf
│       ├── _output.tf
│       ├── glue-definitions.yaml
│       ├── glue-jobs.tf
│       ├── glue-jobs-custom-libraries-upload.tf
│       ├── eventbridge-etl-scheduler.tf
│       ├── stepfunction-orchestration.tf
│       ├── orchestration/
│       │   ├── silver-etl.json
│       │   └── silver-mapping.json
│       └── glue-jobs/
│           ├── src/
│           │   ├── {nome-job}.py
│           │   └── libs/
│           │       └── custom_classes.py
│           └── configs/
│               ├── dev/
│               ├── qa/
│               └── prod/
├── .github/workflows/
└── utils/deploy-tag.sh
```

---

## 🔄 Flusso CI/CD

| Tag | Ambiente | Workflow |
|---|---|---|
| `rc-PLAN-COLLAUDO` | Collaudo (plan) | `cd-terragrunt-plan-collaudo.yaml` |
| `rc-COLLAUDO` | Collaudo (apply) | `cd-terragrunt-plan-deploy-collaudo.yaml` |
| `rc-PLAN-CERTIFICAZIONE` | Certificazione (plan) | `cd-terragrunt-plan-certificazione.yaml` |
| `rc-CERTIFICAZIONE` | Certificazione (apply) | `cd-terragrunt-plan-deploy-certificazione.yaml` |
| `workflow_dispatch` | Produzione | `cd-terragrunt-plan-deploy-produzione.yaml` |

---

## 🤝 Contribuire

➡️ **[CONTRIBUTING.md](.github/CONTRIBUTING.md)**

## 🛡️ Sicurezza

➡️ **[SECURITY.md](.github/SECURITY.md)**

## ⚖️ Licenza

Licenza proprietaria. ➡️ **[LICENCE.md](LICENCE.md)**
```
