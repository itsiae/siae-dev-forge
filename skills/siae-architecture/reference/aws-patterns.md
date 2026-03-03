# AWS Architecture Patterns — SIAE

Pattern architetturali AWS dettagliati con diagrammi Mermaid.
Estratti dai repository reali dell'organizzazione `itsiae`.

---

## 1. Lambda + API Gateway

Pattern per API serverless (TypeScript/Node.js).

### Architettura

```mermaid
graph LR
    Client[Client / SPA] -->|HTTPS| APIGW[API Gateway]
    APIGW -->|Proxy| Lambda[Lambda Function]
    Lambda -->|Query| RDS[(PostgreSQL RDS)]
    Lambda -->|Cache / Session| DDB[(DynamoDB)]
    Lambda -->|Secrets| SM[Secrets Manager]
    APIGW -->|Auth| Cognito[Cognito User Pool]

    style Client fill:#e1f5fe
    style APIGW fill:#fff3e0
    style Lambda fill:#fff3e0
    style RDS fill:#e8f5e9
    style DDB fill:#e8f5e9
    style SM fill:#fce4ec
    style Cognito fill:#fce4ec
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

```mermaid
graph LR
    GH[GitHub Push] -->|Actions| Build[esbuild Bundle]
    Build --> Zip[ZIP Artifact]
    Zip --> Deploy[aws lambda update-function-code]
    Deploy --> APIGW[API Gateway Stage]

    style GH fill:#f3e5f5
    style Build fill:#fff3e0
    style Zip fill:#fff3e0
    style Deploy fill:#e8f5e9
    style APIGW fill:#e8f5e9
```

---

## 2. Glue ETL Pipeline

Pattern per pipeline dati con architettura Medallion.

### Architettura

```mermaid
graph TD
    EB[EventBridge Rule] -->|Trigger| SF[Step Functions]
    SF -->|Step 1| Ingest[Glue Job: Ingest]
    SF -->|Step 2| Transform[Glue Job: Transform]
    Ingest -->|Write| Bronze[S3: bronze/]
    Transform -->|Read| Bronze
    Transform -->|Write| Silver[S3: silver/]
    Silver -->|Catalog| GC[Glue Data Catalog]
    GC -->|Query| Athena[Athena]

    style EB fill:#fff3e0
    style SF fill:#fff3e0
    style Ingest fill:#e1f5fe
    style Transform fill:#e1f5fe
    style Bronze fill:#e8f5e9
    style Silver fill:#e8f5e9
    style GC fill:#f3e5f5
    style Athena fill:#f3e5f5
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

```mermaid
graph LR
    LB[OpenShift Route / Ingress] -->|HTTPS| SVC[Service]
    SVC --> Pod1[Pod: Spring Boot]
    SVC --> Pod2[Pod: Spring Boot]
    Pod1 -->|JDBC| RDS[(PostgreSQL RDS)]
    Pod2 -->|JDBC| RDS
    Pod1 -->|Publish| SNS[SNS Topic]
    SNS -->|Subscribe| SQS[SQS Queue]
    SQS -->|Consume| OtherSvc[Other Microservice]
    Pod1 -->|Metrics| Prom[Prometheus]
    Prom --> Graf[Grafana]

    style LB fill:#e1f5fe
    style SVC fill:#e1f5fe
    style Pod1 fill:#fff3e0
    style Pod2 fill:#fff3e0
    style RDS fill:#e8f5e9
    style SNS fill:#f3e5f5
    style SQS fill:#f3e5f5
    style OtherSvc fill:#fff3e0
    style Prom fill:#fce4ec
    style Graf fill:#fce4ec
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

```mermaid
graph LR
    GH[GitHub Push] -->|Actions| Maven[Maven Build + Test]
    Maven --> Docker[Docker Build]
    Docker --> Registry[Container Registry]
    Registry --> Helm[Helm Upgrade]
    Helm --> OCP[OpenShift Cluster]

    style GH fill:#f3e5f5
    style Maven fill:#fff3e0
    style Docker fill:#fff3e0
    style Registry fill:#e8f5e9
    style Helm fill:#e8f5e9
    style OCP fill:#e1f5fe
```

---

## 4. S3 + CloudFront SPA

Pattern per applicazioni frontend Vue.js.

### Architettura

```mermaid
graph LR
    User[Browser] -->|HTTPS| CF[CloudFront]
    CF -->|Origin| S3[S3 Bucket - Static Assets]
    CF -->|API Proxy| APIGW[API Gateway]
    User -->|Auth| Cognito[Cognito]
    User -->|Feature Flags| Firebase[Firebase Remote Config]

    style User fill:#e1f5fe
    style CF fill:#fff3e0
    style S3 fill:#e8f5e9
    style APIGW fill:#fff3e0
    style Cognito fill:#fce4ec
    style Firebase fill:#f3e5f5
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

```mermaid
graph LR
    GH[GitHub Push] -->|Actions| Build[npm run build - Vite]
    Build --> Sync[aws s3 sync dist/]
    Sync --> Invalidate[CloudFront Invalidation]

    style GH fill:#f3e5f5
    style Build fill:#fff3e0
    style Sync fill:#e8f5e9
    style Invalidate fill:#e8f5e9
```
