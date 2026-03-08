---
name: siae-iac
description: >
  Pattern Infrastructure as Code SIAE: Terraform + Terragrunt. Trigger:
  scrittura file .tf, .hcl, terragrunt.hcl, modifica infrastruttura AWS.
  Basato su pattern reali da 44 repo HCL itsiae.
---

# SIAE Infrastructure as Code

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨  DevForge  ·  SIAE IaC Patterns                  ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Flexible | **Fase SDLC:** 4. Implementation

---

## Panoramica

Pattern IaC da 44 repo HCL itsiae (enterpriseplatform-core-iaac, dataplatform-datalake-iaac, etc.). Guida scrittura `.tf`, `.hcl`, `terragrunt.hcl` secondo convenzioni SIAE.

**Trigger**: file .tf/.hcl, terragrunt.hcl, modifica infrastruttura AWS, nuovi moduli TF, setup ambienti.

---

## 1. Terragrunt Pattern

### Struttura live/ + modules/ mirror

```
repo-root/
├── config.yaml                  # Configurazione globale
├── live/
│   ├── _envs/                   # Template per environment
│   │   ├── sviluppo.hcl
│   │   ├── collaudo.hcl
│   │   ├── certificazione.hcl
│   │   └── produzione.hcl
│   ├── sviluppo/
│   │   └── terragrunt.hcl       # Include _envs/sviluppo.hcl
│   ├── collaudo/
│   │   └── terragrunt.hcl
│   ├── certificazione/
│   │   └── terragrunt.hcl
│   └── produzione/
│       └── terragrunt.hcl
└── modules/
    ├── vpc/
    ├── storage/
    ├── secrets/
    ├── iam-roles/
    ├── bus/
    ├── email/
    └── errors-management/
```

### Config globale e _envs/

`config.yaml` alla root, letto con `yamldecode(file(find_in_parent_folders("config.yaml")))`. I file in `_envs/` definiscono variabili per-environment (account ID, VPC CIDR, sizing), inclusi via `read_terragrunt_config()`.

---

## 2. Convenzioni File Terraform

### Meta file (prefisso underscore)

| File          | Contenuto                          |
|---------------|-------------------------------------|
| `_input.tf`   | Tutte le `variable` del modulo     |
| `_local.tf`   | Blocchi `locals`                   |
| `_output.tf`  | Tutti gli `output`                 |

### Resource file

Naming: `{servizio}-{risorsa}.tf`

Esempi:
- `lambda-ingestion.tf` — Lambda di ingestion
- `glue-etl-bronze.tf` — Glue job per layer bronze
- `s3-datalake.tf` — Bucket S3 data lake
- `iam-roles-lambda.tf` — Ruoli IAM per Lambda
- `apigw-rest-api.tf` — API Gateway REST

---

## 3. Remote State

### Pattern S3 + DynamoDB

```hcl
remote_state {
  backend = "s3"
  config = {
    bucket         = "${local.config.project}-terraform-state"
    key            = "${local.config.env}-${local.config.repo_name}-terraform-state"
    region         = local.config.aws_region
    encrypt        = true
    dynamodb_table = "${local.config.project}-terraform-lock"
  }
}
```

Bucket S3 shared tra ambienti, key univoca per env+repo, DynamoDB lock, encryption sempre abilitata.

---

## 4. Struttura Moduli

Organizzazione per dominio infrastrutturale:

| Modulo              | Responsabilita'                                |
|---------------------|------------------------------------------------|
| `vpc`               | VPC, subnet, route tables, NAT, security groups|
| `storage`           | S3 buckets, lifecycle rules, replication        |
| `secrets`           | Secrets Manager, SSM Parameter Store            |
| `iam-roles`         | IAM roles, policies, instance profiles          |
| `bus`               | EventBridge, SQS, SNS                           |
| `email`             | SES configuration, templates                    |
| `errors-management` | CloudWatch alarms, SNS alerting, dashboards     |

Ogni modulo ha: `_input.tf`, `_local.tf`, `_output.tf` + resource file specifici.

**🚨 Quando la risorsa modificata è IAM — pre-flight card CRITICO aggiuntiva:**

| 🚨 CRITICO (irreversibile) — 🔨 DevForge · siae-iac |
|:---|
| ⚠️ AZIONE IRREVERSIBILE — CONFERMA RICHIESTA |
| 🔐 Risorsa IAM: `<role/policy name>` |
| 🌍 Ambiente: `<ambiente>` |
| 📦 Servizi impattati: `<lista servizi>` |
| 1. ⚠️ Azione: Modifica policy IAM (impatta accesso risorse) |
| 📂 `<file .tf>` |
| 💡 Perche': Modifica necessaria per `<motivazione>` |
| 🚫 Se NO: STOP — policy invariata, accessi non modificati |

---

## 5. CI/CD

Deploy tag-based via Makefile + GitHub Actions reusable (trigger su push tag `rc-*`):

| Tag                  | Ambiente        | Comando Makefile          |
|----------------------|-----------------|---------------------------|
| `rc-COLLAUDO`        | Collaudo        | `make deploy-collaudo`    |
| `rc-CERTIFICAZIONE`  | Certificazione  | `make deploy-certificazione` |
| `rc-main`            | Produzione      | `make deploy-produzione`  |

---

## 6. Vincoli Inviolabili

Queste regole sono **OBBLIGATORIE**. Violarne una significa bloccare la review.

| #  | Vincolo                                    | Motivazione                              |
|----|--------------------------------------------|------------------------------------------|
| V1 | No inline IAM policy                       | Usa `aws_iam_policy` separata, riusabile |
| V2 | No hardcoded AMI ID                        | Usa data source `aws_ami` o variabile    |
| V3 | No hardcoded region                        | Leggi da `config.yaml` o variabile       |
| V4 | Usa `for_each`, mai `count`                | `for_each` e' stabile su add/remove      |
| V5 | No `terraform apply` senza plan review     | Sempre `plan` -> review -> `apply`       |
| V6 | Pin provider versions                      | `required_providers` con `~>` constraint |
| V7 | Tag obbligatori su ogni risorsa            | `Environment`, `Project`, `ManagedBy`    |
| V8 | No secret in variabili TF                  | Usa Secrets Manager o SSM                |

**🚨 Operazione CRITICA — pre-flight card OBBLIGATORIA prima di `terraform apply`:**

| 🚨 CRITICO (irreversibile) — 🔨 DevForge · siae-iac |
|:---|
| ⚠️ AZIONE IRREVERSIBILE — CONFERMA RICHIESTA |
| 🏗️ Ambiente: `<dev|collaudo|produzione>` |
| 📋 Plan output: `<N> to add, <N> to change, <N> to destroy` |
| 🎫 Ticket: `<PROJ-NNN>` |
| 1. ⚠️ Azione: Applicazione modifiche infrastruttura AWS |
| 📂 `<modulo terraform>` |
| 💡 Perche': Plan verificato, risorse da creare/modificare |
| 🚫 Se NO: STOP — nessuna modifica applicata all'infrastruttura |

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "E' solo un ambiente di test, non serve Terragrunt" | Gli ambienti di test diventano produzione. La struttura si porta dietro. |
| "Il modulo e' piccolo, metto tutto in main.tf" | main.tf non strutturato e' impossibile da riusare e testare. |
| "Il remote state lo configuro dopo" | Il remote state va configurato per primo. Migrarlo dopo e' rischioso. |
| "Non serve il lock del provider" | Senza lock, una patch del provider rompe l'infrastruttura in silenzio. |
| "Le variabili le hardcodo per ora" | Le variabili hardcoded finiscono in git. Le credenziali non devono. |
| "L'IAM policy la faccio admin per semplicita'" | Least privilege non e' optional. Le policy permissive creano vulnerabilita'. |
| "Il terraform apply lo faccio senza plan" | Senza plan non sai cosa verra' distrutto. Sempre plan prima di apply. |
| "Encryption at rest non serve in dev" | I dati di dev spesso contengono PII reali. Cifra sempre. |

## Classificazione Rischio Operazioni

| Operazione                    | Rischio   | Card       |
|-------------------------------|-----------|------------|
| Lettura/analisi file .tf      | 🟢 Sicuro | No         |
| Creazione/modifica file .tf   | 🟡 Medio  | No         |
| Modifica terragrunt.hcl       | 🟡 Medio  | No         |
| terraform plan                | 🟡 Medio  | No         |
| `terraform apply`             | 🚨 Critico| Si         |
| Modifica IAM policy / security group | 🚨 Critico | Si |
| Tag deploy (rc-*)             | 🚨 Critico| No         |
