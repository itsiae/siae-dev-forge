# Task 01 — Allineamento segnali inferenza [PENDING]

**File:** `skills/siae-qa/XRAY-TEMPLATES.md`
**Sezione:** "Tabella Segnali Req Typing"
**Cluster:** A — Determinismo

---

## Obiettivo

Allineare la tabella segnali in XRAY-TEMPLATES.md con i segnali presenti nei question tree
e aggiungere tecnologie moderne mancanti. Risolvere la discrepanza che causa LOW confidence
su story che dovrebbero essere HIGH.

---

## Step 1 — Leggi la sezione corrente

Leggi `skills/siae-qa/XRAY-TEMPLATES.md` righe 1-35 (sezione "Tabella Segnali Req Typing").

---

## Step 2 — Sostituisci la tabella segnali

Individua il blocco:
```
| Tipo | Segnali (summary, AC, description, label, stack) |
```

Sostituisci l'intera tabella con la versione aggiornata:

```markdown
| Tipo | Segnali (summary, AC, description, label, stack) |
|------|--------------------------------------------------|
| **Frontend (FE)** | "componente", "pagina", "form", "UI", "Vue", "Angular", "React", "click", "visualizza", "render", "responsive", "upload", "drag", "Next.js", "Nuxt", "SSR", "hydration", "Svelte", "web component", "Ionic", "Capacitor", "PWA", "service worker", "offline", "micro-frontend", "module federation", "Storybook", "design system" |
| **Backend Microservice (BE)** | "API", "endpoint", "service", "REST", "controller", "Spring", "Lambda", "validazione", "business rule", "handler", "mapper", "GraphQL", "resolver", "mutation", "subscription", "gRPC", "protobuf", "NestJS", "FastAPI", "Quarkus", "Micronaut", "OpenAPI", "Swagger", "contract test", "cold start", "provisioned concurrency" |
| **ETL / Data Pipeline** | "Glue", "PySpark", "pipeline", "trasformazione", "bronze", "silver", "gold", "job", "ETL", "medallion", "crawler", "Athena", "dbt", "model dbt", "Databricks", "Delta Lake", "Delta table", "Flink", "streaming job", "Airbyte", "Fivetran", "CDC", "Debezium", "Iceberg", "Hudi" |
| **Database** | "migration", "schema", "query", "tabella", "indice", "DDL", "flyway", "liquibase", "ALTER TABLE", "stored procedure", "view", "DynamoDB", "MongoDB", "Cosmos DB", "partition key", "Alembic", "revision", "read replica", "sharding" |
| **Auth / Security** | "login", "logout", "ruolo", "permesso", "token", "autenticazione", "RBAC", "JWT", "SSO", "autorizzazione", "profilo utente", "OAuth2", "OIDC", "refresh token", "scope", "claims", "MFA", "OTP", "TOTP", "2FA", "API key", "client credentials", "Cognito", "user pool", "SAML" |
| **Integration REST / Sync** | "chiamata esterna", "API terza parte", "REST client", "HTTP client", "timeout", "retry", "circuit breaker", "Feign", "RestTemplate", "WebClient", "OpenFeign", "Pact", "consumer-driven contract", "gRPC client" |
| **Integration Event / Async** | "webhook", "evento", "Kafka", "SQS", "SNS", "notifica", "callback", "polling", "EventBridge", "event bus", "AMQP", "RabbitMQ", "ActiveMQ", "saga", "outbox pattern", "consumer", "producer", "topic", "queue", "dead letter", "DLQ" |
| **Notification / Messaging** | "email transazionale", "push notification", "SMS", "notifica in-app", "template email", "opt-out", "unsubscribe", "FCM", "APNs", "SES", "SendGrid", "Twilio", "notification center", "delivery receipt", "bounce", "webhook push" |
| **Batch / Scheduler** | "batch", "cron", "scheduler", "Quartz", "EventBridge rule", "job periodico", "elaborazione notturna", "elaborazione massiva", "finestra temporale", "trigger scheduled", "AWS Batch", "Step Functions scheduled", "import massivo", "export massivo" |
| **Report / Export** | "report", "export", "PDF", "Excel", "XLSX", "CSV export", "rendiconto", "estratto conto", "stampa", "download", "JasperReports", "Apache POI", "generazione documento", "template report", "BI", "dashboard export" |
| **Feature Flag / Configuration** | "feature flag", "feature toggle", "LaunchDarkly", "Unleash", "AWS AppConfig", "canary", "rollout progressivo", "A/B test", "configurazione dinamica", "kill switch", "abilitazione per tenant", "dark launch" |
| **File Processing / Async Upload** | "upload file", "import file", "caricamento massivo", "bulk import", "file processing", "chunked upload", "multipart", "presigned URL", "S3 upload", "file validation", "file parser", "SFTP", "FTP", "file watcher", "async processing", "polling status" |
```

---

## Step 3 — Aggiorna la sezione Confidence (stessa sezione)

Dopo la tabella, aggiorna la sezione **Confidence** per riflettere i tipi separati:

```markdown
**Confidence:**
- **HIGH (>= 90%):** 2+ segnali forti convergenti sullo stesso tipo
- **MEDIUM (60-89%):** 1 segnale forte o 2+ deboli
- **LOW (< 60%):** segnali ambigui, assenti, o convergenti su tipi diversi (→ valutare tipo composito)

**Nota per Integration split:** se la story ha segnali sia di "Integration REST/Sync" che di
"Integration Event/Async", assegna il tipo primario in base al segnale con maggiore forza contestuale
e registra l'altro come tag secondario (vedi sezione Primary Type + Secondary Tags).
```

---

## Step 4 — Verifica

Leggi la sezione aggiornata e verifica che:
- [ ] Tutti i 12 tipi sono presenti (inclusi i 6 nuovi: Notification, Batch, Report, Feature Flag, File Processing, e i 2 Integration split)
- [ ] "upload" e "drag" sono presenti in Frontend
- [ ] "SSO" è presente in Auth/Security
- [ ] Integration è divisa in due righe separate

---

## Step 5 — Commit

```bash
git add skills/siae-qa/XRAY-TEMPLATES.md
git commit -m "feat(siae-qa): align inference signals + add modern tech + split Integration type"
```
