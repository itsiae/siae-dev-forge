# AWS Architecture Patterns — SIAE

Pattern architetturali AWS dettagliati con diagrammi PlantUML.
Estratti dai repository reali dell'organizzazione `itsiae`.

---

## 1. Lambda + API Gateway

Pattern per API serverless (TypeScript/Node.js).

### Architettura

```plantuml
@startuml Lambda_APIGateway
skinparam defaultFontName Arial
skinparam shadowing false
skinparam componentStyle rectangle
left to right direction

actor "Client / SPA" as Client
rectangle "API Gateway" as APIGW
rectangle "Lambda Function" as Lambda
database "PostgreSQL RDS" as RDS
database "DynamoDB" as DDB
rectangle "Secrets Manager" as SM
rectangle "Cognito User Pool" as Cognito

Client --> APIGW : HTTPS
APIGW --> Lambda : Proxy
Lambda --> RDS : Query
Lambda --> DDB : Cache / Session
Lambda --> SM : Secrets
APIGW --> Cognito : Auth
@enduml
```

### Componenti

| Componente       | Ruolo                                              |
|------------------|----------------------------------------------------|
| API Gateway      | Endpoint HTTPS, throttling, request validation     |
| Lambda           | Business logic (Express.js + serverless-http)      |
| Cognito          | Autenticazione OAuth2/OIDC, JWT validation         |
| PostgreSQL (RDS) | Persistenza relazionale (Drizzle ORM)              |
| DynamoDB         | Dati chiave-valore, sessioni, cache applicativa    |
| Secrets Manager  | Credenziali DB, API key, rotazione automatica      |

### Flusso di deploy

```plantuml
@startuml Lambda_Deploy
skinparam defaultFontName Arial
skinparam shadowing false
skinparam componentStyle rectangle
left to right direction

rectangle "GitHub Push" as GH
rectangle "esbuild Bundle" as Build
rectangle "ZIP Artifact" as Zip
rectangle "aws lambda\nupdate-function-code" as Deploy
rectangle "API Gateway Stage" as APIGW

GH --> Build : Actions
Build --> Zip
Zip --> Deploy
Deploy --> APIGW
@enduml
```

---

## 2. Glue ETL Pipeline

Pattern per pipeline dati con architettura Medallion.

### Architettura

```plantuml
@startuml Glue_ETL
skinparam defaultFontName Arial
skinparam shadowing false
skinparam componentStyle rectangle
top to bottom direction

rectangle "EventBridge Rule" as EB
rectangle "Step Functions" as SF
rectangle "Glue Job: Ingest" as Ingest
rectangle "Glue Job: Transform" as Transform
database "S3: bronze/" as Bronze
database "S3: silver/" as Silver
rectangle "Glue Data Catalog" as GC
rectangle "Athena" as Athena

EB --> SF : Trigger
SF --> Ingest : Step 1
SF --> Transform : Step 2
Ingest --> Bronze : Write
Transform --> Bronze : Read
Transform --> Silver : Write
Silver --> GC : Catalog
GC --> Athena : Query
@enduml
```

### Componenti

| Componente       | Ruolo                                              |
|------------------|----------------------------------------------------|
| EventBridge      | Trigger schedulato (cron) o event-driven            |
| Step Functions   | Orchestrazione sequenziale con retry e error handling|
| Glue Job         | Trasformazione PySpark (Glue 4.0, Python 3.11)    |
| S3 bronze/       | Dati grezzi, formato originale o Parquet            |
| S3 silver/       | Dati puliti, validati, deduplicated, Parquet        |
| Glue Data Catalog| Metadati tabelle, schema, partizioni               |
| Athena           | Query SQL ad-hoc su dati S3 via Catalog             |

### Struttura S3

```
s3://siae-datalake-{env}/
  bronze/
    {source}/{entity}/{year}/{month}/{day}/
      data-{timestamp}.parquet
  silver/
    {domain}/{entity}/
      data.parquet  (partitioned by date)
```

---

## 3. OpenShift Microservice

Pattern per microservizi Java su OpenShift.

### Architettura

```plantuml
@startuml OpenShift_Microservice
skinparam defaultFontName Arial
skinparam shadowing false
skinparam componentStyle rectangle
left to right direction

rectangle "OpenShift Route\n/ Ingress" as LB
rectangle "Service" as SVC
rectangle "Pod: Spring Boot" as Pod1
rectangle "Pod: Spring Boot" as Pod2
database "PostgreSQL RDS" as RDS
rectangle "SNS Topic" as SNS
rectangle "SQS Queue" as SQS
rectangle "Other Microservice" as OtherSvc
rectangle "Prometheus" as Prom
rectangle "Grafana" as Graf

LB --> SVC : HTTPS
SVC --> Pod1
SVC --> Pod2
Pod1 --> RDS : JDBC
Pod2 --> RDS : JDBC
Pod1 --> SNS : Publish
SNS --> SQS : Subscribe
SQS --> OtherSvc : Consume
Pod1 --> Prom : Metrics
Prom --> Graf
@enduml
```

### Componenti

| Componente       | Ruolo                                              |
|------------------|----------------------------------------------------|
| OpenShift Route  | Ingress HTTPS, TLS termination                     |
| Service          | Load balancing interno tra pod                      |
| Pod (Spring Boot)| Business logic, REST API, JPA/Hibernate            |
| PostgreSQL (RDS) | Persistenza relazionale                             |
| SNS + SQS        | Comunicazione asincrona tra microservizi            |
| Prometheus       | Raccolta metriche (Micrometer exporter)            |
| Grafana          | Dashboard e alerting                                |

### Flusso di deploy

```plantuml
@startuml OpenShift_Deploy
skinparam defaultFontName Arial
skinparam shadowing false
skinparam componentStyle rectangle
left to right direction

rectangle "GitHub Push" as GH
rectangle "Maven Build + Test" as Maven
rectangle "Docker Build" as Docker
rectangle "Container Registry" as Registry
rectangle "Helm Upgrade" as Helm
rectangle "OpenShift Cluster" as OCP

GH --> Maven : Actions
Maven --> Docker
Docker --> Registry
Registry --> Helm
Helm --> OCP
@enduml
```

---

## 4. S3 + CloudFront SPA

Pattern per applicazioni frontend Vue.js.

### Architettura

```plantuml
@startuml SPA_CloudFront
skinparam defaultFontName Arial
skinparam shadowing false
skinparam componentStyle rectangle
left to right direction

actor "Browser" as User
rectangle "CloudFront" as CF
database "S3 Bucket\nStatic Assets" as S3
rectangle "API Gateway" as APIGW
rectangle "Cognito" as Cognito
rectangle "Firebase\nRemote Config" as Firebase

User --> CF : HTTPS
CF --> S3 : Origin
CF --> APIGW : API Proxy
User --> Cognito : Auth
User --> Firebase : Feature Flags
@enduml
```

### Componenti

| Componente         | Ruolo                                            |
|--------------------|--------------------------------------------------|
| CloudFront         | CDN, HTTPS, caching, SPA routing (error pages)  |
| S3                 | Hosting statico (HTML, JS, CSS, assets)          |
| Cognito            | Autenticazione utenti, JWT tokens                |
| API Gateway        | Backend API (proxied via CloudFront path pattern)|
| Firebase RC        | Feature flags e configurazione runtime           |

### CloudFront Configuration

```
Behaviors:
  /api/*    -> API Gateway origin (no cache)
  /*        -> S3 origin (cache 1 year for hashed assets)

Error Pages:
  403 -> /index.html (200) — SPA client-side routing
  404 -> /index.html (200) — SPA client-side routing
```

### Flusso di deploy

```plantuml
@startuml SPA_Deploy
skinparam defaultFontName Arial
skinparam shadowing false
skinparam componentStyle rectangle
left to right direction

rectangle "GitHub Push" as GH
rectangle "npm run build\nVite" as Build
rectangle "aws s3 sync dist/" as Sync
rectangle "CloudFront\nInvalidation" as Invalidate

GH --> Build : Actions
Build --> Sync
Sync --> Invalidate
@enduml
```
