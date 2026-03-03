---
name: siae-architecture
description: >
  Pattern architetturali SIAE e modello C4 per design di sistema. Trigger:
  design sistema/componente, scelta architetturale, HLD, valutazione pattern.
  Basato su pattern reali estratti da 816 repo itsiae.
---

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨  DevForge  ·  Architecture                      ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 1. Modello C4

Il modello C4 (Context, Container, Component, Code) e' lo standard per documentare architetture in SIAE.
Ogni livello aggiunge dettaglio progressivo; usa il livello minimo necessario per la decisione in corso.

| Livello | Nome        | Cosa mostra                                       | Quando usarlo                                      |
|---------|-------------|---------------------------------------------------|---------------------------------------------------|
| **1**   | Context     | Sistema + attori esterni + sistemi adiacenti      | Kickoff progetto, allineamento stakeholder         |
| **2**   | Container   | Applicazioni, DB, message broker, deployment unit | Design di alto livello (HLD), review architetturale|
| **3**   | Component   | Moduli interni di un singolo container            | Design dettagliato, code review di modulo          |
| **4**   | Code        | Classi, interfacce, strutture dati                | Documentazione tecnica, onboarding sviluppatori    |

> Riferimento template Mermaid: `reference/c4-template.md`

---

## 2. Pattern Architetturali SIAE

Tutti i pattern seguenti sono estratti da repo reali dell'organizzazione `itsiae` (816 repository).
Non proporre pattern non presenti in questo catalogo.

### 2.1 Microservizi Java

| Aspetto       | Dettaglio                                                  |
|---------------|------------------------------------------------------------|
| Runtime       | Spring Boot 3.x su OpenShift (container OCI)               |
| Build         | Maven con parent POM custom SIAE (`siae-parent`)           |
| Packaging     | Helm chart per deploy su OpenShift                          |
| API           | REST (OpenAPI 3.0), versionamento via URL path (`/v1/`)    |
| Persistenza   | PostgreSQL (RDS) o Oracle, JPA/Hibernate                   |
| Osservabilita'| Micrometer + Prometheus, log JSON strutturato              |
| CI/CD         | GitHub Actions -> build Maven -> push image -> Helm upgrade|

**Quando sceglierlo:** servizi con logica di dominio complessa, requisiti di transazionalita', integrazione con sistemi legacy SIAE.

### 2.2 Serverless TypeScript

| Aspetto       | Dettaglio                                                  |
|---------------|------------------------------------------------------------|
| Runtime       | Node.js 20.x su AWS Lambda                                 |
| Framework     | Express.js + `serverless-http` adapter                     |
| Build         | esbuild (bundle + minify + tree-shaking)                   |
| API           | API Gateway (REST o HTTP API) + Lambda proxy               |
| Persistenza   | Drizzle ORM + PostgreSQL (RDS) oppure DynamoDB             |
| IaC           | Terragrunt (vedi pattern 2.4)                              |
| CI/CD         | GitHub Actions -> esbuild -> zip -> deploy Lambda          |

**Quando sceglierlo:** API leggere, webhook handler, BFF per frontend, servizi event-driven con carico variabile.

### 2.3 Data Pipeline Python

| Aspetto       | Dettaglio                                                  |
|---------------|------------------------------------------------------------|
| Architettura  | Medallion Architecture (bronze -> silver)                  |
| Runtime       | AWS Glue 4.0 (PySpark), Python 3.11                       |
| Orchestrazione| AWS Step Functions (state machine JSON/ASL)                |
| Trigger       | Amazon EventBridge (schedule o event pattern)              |
| Storage       | S3 (datalake con prefissi bronze/ silver/), Parquet        |
| Catalogo      | AWS Glue Data Catalog + Athena per query ad-hoc            |
| CI/CD         | GitHub Actions -> upload script S3 -> update Glue job      |

**Quando sceglierlo:** ingestione dati da sorgenti esterne, trasformazioni batch, alimentazione datawarehouse, reportistica.

### 2.4 IaC Pattern (Terragrunt)

| Aspetto       | Dettaglio                                                  |
|---------------|------------------------------------------------------------|
| Tool          | Terragrunt + Terraform                                     |
| Struttura     | `live/` (ambienti) + `modules/` (moduli riusabili), mirror |
| Configurazione| `config.yaml` per ambiente, iniettato via `read_terragrunt_config()` |
| State         | S3 bucket + DynamoDB table per locking                     |
| Ambienti      | `live/dev/`, `live/uat/`, `live/prod/`                     |
| CI/CD         | GitHub Actions con OIDC federation (no secret statiche)    |

**Quando sceglierlo:** qualsiasi infrastruttura AWS nuova. Sempre. Non usare CloudFormation o CDK.

### 2.5 Frontend SPA

| Aspetto       | Dettaglio                                                  |
|---------------|------------------------------------------------------------|
| Framework     | Vue.js 3 (Composition API) + Pinia (state management)     |
| UI Library    | PrimeVue (componenti + tema SIAE custom)                   |
| Build         | Vite                                                       |
| Hosting       | S3 (static) + CloudFront (CDN + HTTPS)                     |
| Config        | Firebase Remote Config (feature flags, parametri runtime)  |
| Auth          | Amazon Cognito (OAuth2/OIDC)                               |
| CI/CD         | GitHub Actions -> npm build -> sync S3 -> invalidate CF    |

**Quando sceglierlo:** applicazioni web interne SIAE, portali, dashboard, backoffice.

---

## 3. AWS Service Map SIAE

Servizi AWS approvati e in uso nei repository SIAE.

| Categoria   | Servizi                                                       |
|-------------|---------------------------------------------------------------|
| Compute     | Lambda, Glue (PySpark), OpenShift (self-managed su EC2)       |
| Storage     | S3, DynamoDB, PostgreSQL (RDS), Oracle (RDS)                  |
| Messaging   | SNS, SQS, EventBridge                                        |
| Security    | Cognito, KMS, Secrets Manager, IAM OIDC (GitHub Actions)     |
| CDN         | CloudFront                                                    |
| Monitoring  | CloudWatch (Logs, Metrics, Alarms)                            |
| Data        | Glue Data Catalog, Athena                                     |

> Riferimento dettagliato con diagrammi: `reference/aws-patterns.md`

---

## 4. Vincoli

1. **Solo pattern reali** — non proporre architetture non presenti nel catalogo (sezione 2).
   Ogni design deve mappare su uno o piu' dei 5 pattern documentati.
2. **IaC obbligatoria** — ogni risorsa AWS va gestita con Terragrunt (pattern 2.4).
3. **C4 obbligatorio** — ogni HLD deve includere almeno Livello 1 (Context) e Livello 2 (Container).
4. **Servizi approvati** — usare solo i servizi nella AWS Service Map (sezione 3).
   Per servizi non in lista, richiedere approvazione esplicita.
5. **Diagrammi in Mermaid** — tutti i diagrammi architetturali devono essere in sintassi Mermaid,
   renderizzabili in GitHub e Confluence.
