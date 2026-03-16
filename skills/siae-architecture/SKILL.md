---
name: siae-architecture
description: >
  ALWAYS use when evaluating architectural patterns, creating C4 diagrams, or choosing between design approaches (microservizi vs monolite, CQRS, event-driven).
  Trigger: pattern architetturale, C4 model, HLD, bounded context, CQRS, microservizi vs monolite, scelta architetturale, resilienza.
---

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨  DevForge  ·  Architecture                       ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Flexible | **Fase SDLC:** 2. Design

---

> 📊 **Dai repo itsiae:** I servizi progettati senza C4 diagram hanno 2.3x piu' richieste di chiarimento durante l'onboarding di nuovi developer.
> Fonte: analisi su 816 repository GitHub itsiae (60 Java, 44 HCL, 23 Python, 22 TypeScript).

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

| 🔴 ALTO (difficile da annullare) — 🔨 DevForge · siae-architecture |
|:---|
| **⚠️ WARNING** |
| 🏗️ Contesto: `Modifica architettura sistema esistente in produzione SIAE` |
| **▼ Azione** |
| 1. ⚠️ Modifica architettura → `sistema esistente` |
| 💡 Perche': Modificare architettura esistente impatta sistemi dipendenti, integrations e contratti API. |
| 🚫 Se NO: La modifica non viene applicata. Documentare la decisione come ADR con stato Rejected. |

1. **Solo pattern reali** — non proporre architetture non presenti nel catalogo (sezione 2).
   Ogni design deve mappare su uno o piu' dei 5 pattern documentati.
2. **IaC obbligatoria** — ogni risorsa AWS va gestita con Terragrunt (pattern 2.4).
3. **C4 obbligatorio** — ogni HLD deve includere almeno Livello 1 (Context) e Livello 2 (Container).
4. **Servizi approvati** — usare solo i servizi nella AWS Service Map (sezione 3).
   Per servizi non in lista, richiedere approvazione esplicita.

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-architecture |
|:---|
| 🏗️ Contesto: `Selezione libreria o dipendenza esterna per progetto SIAE` |
| **▼ Azione** |
| 1. 📦 Aggiunta dipendenza → `pom.xml / package.json / requirements.txt` |
| 💡 Perche': Librerie esterne introducono rischi di licenza, CVE e debito tecnico. |
| 🚫 Se NO: Non aggiungere la dipendenza. Rivalutare se esiste un servizio AWS o modulo interno equivalente. |

5. **Diagrammi in Mermaid** — tutti i diagrammi architetturali devono essere in sintassi Mermaid,
   renderizzabili in GitHub e Confluence.

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-architecture |
|:---|
| 🏗️ Contesto: `Pubblicazione ADR su Confluence per decisione architetturale SIAE` |
| **▼ Azione** |
| 1. 📄 Pubblicazione ADR → `Confluence / docs/architecture/` |
| 💡 Perche': Un ADR pubblicato e' un artefatto ufficiale che impatta tutti i team. |
| 🚫 Se NO: L ADR rimane in stato Draft locale. Richiedere revisione al tech lead prima di procedere. |

## Limiti Operativi

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Tentativi fix per errore | 2 | Fermati. Diagnosi diversa necessaria. |
| File modificati per singolo step | 5 | Se devi toccare piu' file, decomponi in sub-task. |
| Output max per raccomandazione | 200 righe | Prioritizza. Top 5 issue, non lista esaustiva. |

---

## REQUIRED SUB-SKILL: siae-verification

Invoca `siae-verification` prima di dichiarare il design architetturale completo.

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "Abbiamo gia' un pattern uguale altrove" | Il contesto cambia. Il pattern va validato per questo caso. |
| "E' solo un CRUD, non serve architettura" | I CRUD diventano complessi. L'ADR previene il debito tecnico. |
| "Lo decidiamo durante l'implementazione" | Le decisioni architetturali in corso d'opera costano di piu'. |
| "Il team conosce gia' il sistema" | La conoscenza tacita non scala. Documentala. |
| "Aggiorniamo l'ADR dopo il rilascio" | Dopo il rilascio non si aggiorna mai. |
| "Non abbiamo tempo per HLD" | Il tempo risparmiato ora viene perso nel refactoring. |
| "L'architettura e' ovvia" | Ovvia per te. Non per chi entra nel team dopo. |

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Analisi requisiti non funzionali | 🟢 Sicuro | No |
| Proposta pattern architetturale | 🟢 Sicuro | No |
| Confronto trade-off tra opzioni | 🟢 Sicuro | No |
| Scrittura ADR in docs/architecture/ | 🟢 Sicuro | No |
| Scelta librerie/dipendenze esterne | 🟡 Medio | Si |
| Pubblicazione ADR su Confluence | 🟡 Medio | Si |
| Modifica architettura di sistema esistente | 🔴 Alto | Si |
