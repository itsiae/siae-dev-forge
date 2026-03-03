# Factory Configurations — Riferimento

Questo documento descrive le configurazioni note per ciascuna factory SIAE.
Viene usato dalla skill `siae-onboarding` come riferimento per la detection
automatica e per l'applicazione delle regole di progetto.

---

## 1. Digital

La factory Digital sviluppa applicazioni web rivolte all'utente finale,
con architettura a microservizi e deploy su AWS.

### Frontend

| Aspetto | Dettaglio |
|---------|-----------|
| **Framework** | Vue.js 3 con Composition API (`<script setup>`) |
| **Build** | Vite |
| **Linguaggio** | TypeScript (strict mode) |
| **Test** | Vitest, copertura minima **70%** |
| **Hosting** | AWS S3 + CloudFront |
| **Auth** | Firebase Authentication |
| **Analytics** | Google Analytics 4 (gtag) |
| **State management** | Pinia |
| **Stile** | SCSS con design tokens SIAE |
| **Linting** | ESLint + Prettier |
| **Static analysis** | Qodana |

### Backend — Spring Boot

| Aspetto | Dettaglio |
|---------|-----------|
| **Framework** | Spring Boot 2.x |
| **Build** | Maven. Parent POM: `it.siae:spring-boot-2-parent-pom` |
| **Linguaggio** | Java 17+ |
| **Test** | JUnit 5 + Mockito |
| **Librerie** | MapStruct (mapping), Lombok (boilerplate), Jackson (JSON) |
| **Database** | PostgreSQL (RDS) |
| **Deploy** | ECS Fargate o Lambda (a seconda del servizio) |
| **API style** | REST con OpenAPI 3.0 spec |
| **Static analysis** | Qodana con profilo SIAE |

### Backend — Express.js Lambda

| Aspetto | Dettaglio |
|---------|-----------|
| **Runtime** | Node.js 20.x su AWS Lambda |
| **Framework** | Express.js via `serverless-http` |
| **Linguaggio** | TypeScript (strict mode) |
| **ORM** | Drizzle ORM |
| **Build** | esbuild (singolo bundle per Lambda) |
| **Test** | Jest, unit test obbligatori per handler e service |
| **API Gateway** | AWS API Gateway v2 (HTTP API) |
| **Database** | PostgreSQL (RDS) via Drizzle |
| **Static analysis** | ESLint + Prettier. Qodana |

### Infrastruttura Digital

- **CDN**: CloudFront con S3 origin per assets statici
- **Database**: PostgreSQL su Amazon RDS
- **Storage**: S3 per file uploads e assets
- **Secrets**: AWS Secrets Manager
- **Networking**: VPC dedicata per ambiente

---

## 2. Core Platforms

La factory Core Platforms gestisce i sistemi centrali SIAE, con deploy
su OpenShift e una pipeline Maven-based.

### Stack

| Aspetto | Dettaglio |
|---------|-----------|
| **Framework** | Spring Boot 2.x |
| **Build** | Maven. Parent POM: `it.siae:spring-boot-2-parent-pom` |
| **Linguaggio** | Java 17+ |
| **Test** | JUnit 5 + Mockito |
| **Librerie** | MapStruct, Lombok, Jackson |
| **Database** | Oracle / PostgreSQL |
| **Deploy** | OpenShift (container orchestration) |
| **Packaging** | Helm charts per deploy su OpenShift |
| **API style** | REST e/o SOAP (sistemi legacy) |
| **Static analysis** | Qodana |

### Pipeline CI/CD

```
maven build -> unit test -> Qodana -> docker build -> helm package -> deploy
```

- Le Helm charts risiedono nella directory `charts/` del repository
- I valori per ambiente sono in `charts/values-<ambiente>.yaml`
- Il deploy su OpenShift avviene tramite ArgoCD o pipeline custom

### Ambienti OpenShift

| Ambiente | Namespace pattern | Note |
|----------|-------------------|------|
| sviluppo | `<app>-dev` | Deploy automatico su push in `develop` |
| collaudo | `<app>-coll` | Deploy su tag `v*.*.*-rc.*` |
| certificazione | `<app>-cert` | Deploy su tag `v*.*.*-cert.*` |
| produzione | `<app>-prod` | Deploy su tag `v*.*.*` con approvazione |

---

## 3. Data Platform

La factory Data Platform gestisce le pipeline dati SIAE, con architettura
Medallion su AWS Glue e orchestrazione via Step Functions.

### Stack

| Aspetto | Dettaglio |
|---------|-----------|
| **Linguaggio** | Python 3.9+ |
| **Framework** | PySpark su AWS Glue |
| **Architettura** | Medallion: bronze (raw) -> silver (curated) |
| **Orchestrazione** | AWS Step Functions |
| **Storage** | S3 (data lake) con partitioning by date |
| **Catalogo** | AWS Glue Data Catalog |
| **Test** | pytest con pyspark testing utilities |
| **Linting** | flake8, black (formatter), isort |
| **Static analysis** | Qodana |

### Architettura Medallion

```
Sorgente -> [Ingestion] -> Bronze (raw, append-only)
                              |
                              v
                        [Trasformazione]
                              |
                              v
                        Silver (curated, deduplicated, typed)
```

- **Bronze**: dati grezzi, schema-on-read, partitioning per data ingestion
- **Silver**: dati puliti, schema enforcement, deduplicati, tipizzati
- Ogni layer e' un prefisso S3 dedicato: `s3://<bucket>/bronze/`, `s3://<bucket>/silver/`

### Naming Glue Jobs

| Tipo | Pattern | Esempio |
|------|---------|---------|
| Ingestion | `<dominio>_ingestion_<sorgente>` | `anagrafica_ingestion_sap` |
| Trasformazione | `<dominio>_transform_<entita>` | `anagrafica_transform_autori` |
| Export | `<dominio>_export_<destinazione>` | `royalties_export_pagamenti` |

### Orchestrazione Step Functions

- Ogni pipeline ha una Step Function dedicata
- Gli step Glue usano l'integrazione nativa `.sync`
- Error handling con `Catch` e `Retry` su ogni step
- Notifica SNS su fallimento della pipeline

---

## 4. DevOps/Infra

La factory DevOps/Infra gestisce l'infrastruttura come codice per tutti
gli ambienti SIAE, con Terraform e Terragrunt.

### Stack

| Aspetto | Dettaglio |
|---------|-----------|
| **IaC tool** | Terraform + Terragrunt |
| **Linguaggio** | HCL |
| **Struttura file** | `_input.tf` (variables), `_local.tf` (locals), `_output.tf` (outputs) |
| **State** | S3 backend con DynamoDB lock |
| **Provider** | AWS (primario), con moduli per CloudFront, RDS, ECS, Glue, etc. |
| **Validazione** | `terraform validate`, `terraform plan`, tflint, checkov |
| **Static analysis** | Qodana |

### Struttura Repository

```
infrastructure/
  _envcommon/           # Moduli Terragrunt condivisi tra ambienti
  sviluppo/
    account.hcl
    <regione>/
      <servizio>/
        terragrunt.hcl
  collaudo/
    account.hcl
    <regione>/
      <servizio>/
        terragrunt.hcl
  certificazione/
    ...
  produzione/
    ...
  terragrunt.hcl        # Root config
```

### Naming Risorse

| Tipo | Pattern | Esempio |
|------|---------|---------|
| Modulo | `<servizio>-<componente>` | `ecs-cluster`, `rds-postgres` |
| Risorsa | `<tipo>_<servizio>_<componente>` | `aws_ecs_service_api` |
| Variabile | `<contesto>_<nome>` | `vpc_cidr`, `db_instance_class` |
| Output | `<risorsa>_<attributo>` | `cluster_arn`, `db_endpoint` |

### CI/CD per IaC

```
terraform fmt -check -> terraform validate -> tflint -> checkov -> terraform plan
```

- Il `terraform plan` viene mostrato come commento sulla PR
- Il `terraform apply` richiede approvazione manuale in produzione
- Pipeline definita con GitHub Actions da `itsiae/siae-gh-actions` (v2.x)
- Makefile nella root per comandi comuni (`make plan`, `make apply`, `make fmt`)

---

## Matrice Stack per Factory

| Stack | Digital | Core Platforms | Data Platform | DevOps/Infra |
|-------|---------|---------------|---------------|--------------|
| Java / Spring Boot | Backend API | Core services | - | - |
| TS Frontend (Vue.js) | Web app | - | - | - |
| TS Backend (Lambda) | Microservizi | - | - | - |
| Python / PySpark | - | - | ETL / Glue | - |
| Terraform + Terragrunt | - | - | - | Infra |
| PostgreSQL | DB primario | DB (anche Oracle) | - | - |
| OpenShift | - | Deploy target | - | - |
| AWS (ECS/Lambda/S3) | Deploy target | - | Glue/S3/SF | Target infra |

---

## Regole CI/CD Comuni

Tutte le factory condividono:

1. **GitHub Actions** riutilizzabili dal repository `itsiae/siae-gh-actions` (versione `v2.x`)
2. **Deploy tag-based**: il push di un tag semantico triggera il deploy sull'ambiente corrispondente
3. **Qodana** come quality gate obbligatorio su ogni PR
4. **4 ambienti**: sviluppo, collaudo, certificazione, produzione
5. **Branch protection** su `main`: PR obbligatoria con almeno 1 review approvata
