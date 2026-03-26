# SIAE QA — Template Xray e Esempi Test Case

## Table of Contents

- [Tabella Segnali Req Typing](#tabella-segnali-req-typing)
- [Template Req Profile Card](#template-req-profile-card)
- [Formato Test Case Step-Based](#formato-test-case-step-based)
- [Prefissi di Categoria](#prefissi-di-categoria)
- [Regola Multi-Step](#regola-multi-step)
- [Riepilogo Copertura](#riepilogo-copertura)
- [Template Matrice Scenari](#template-matrice-scenari)
- [Domande Elicitazione per Categoria](#domande-elicitazione-per-categoria)
- [Mappatura ID Sequenziali e Chiavi Jira Xray](#mappatura-id-sequenziali-e-chiavi-jira-xray)
- [Tier 3 CSV Export](#tier-3-csv-export)
- [Checklist di Verifica](#checklist-di-verifica)

---

## Tabella Segnali Req Typing

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

**Confidence:**
- **HIGH (>= 90%):** 2+ segnali forti convergenti sullo stesso tipo
- **MEDIUM (60-89%):** 1 segnale forte o 2+ deboli
- **LOW (< 60%):** segnali ambigui, assenti, o convergenti su tipi diversi (→ valutare tipo composito)

**Nota per Integration split:** se la story ha segnali sia di "Integration REST/Sync" che di
"Integration Event/Async", assegna il tipo primario in base al segnale con maggiore forza contestuale
e registra l'altro come tag secondario (vedi sezione Primary Type + Secondary Tags).

---

## Template Req Profile Card

```
REQ PROFILE:
  Tipo:       [Frontend / BE / ETL / Database / Auth / Integration]
  Confidence: [HIGH / MEDIUM / LOW]
  Segnali:    [elenco segnali usati dall'inferenza]
  Stack:      [tecnologie rilevate]
```

Dopo le domande del tree (0c), aggiorna la card:

```
REQ PROFILE (aggiornato):
  Tipo:       [tipo]
  Scenari L1: [lista scenari flusso principale]
  Scenari L2: [lista edge case contestuali]
  Scenari L3: [lista scenari integrazione/dipendenze]
```

---

## Formato Test Case Step-Based

Per ogni scenario della matrice (4a), genera 1+ Test Case con questo formato:

| Campo | Contenuto |
|-------|-----------|
| ID | Numero sequenziale (1, 2, 3...) |
| Test Type | `Manual` |
| Team Competenza | `QA` |
| ID JIRA Story | `{PROJ-XXX}` — **obbligatorio** |
| User Story Description | Summary della Story Jira |
| Scenario (descrizione) | Titolo del Test Case — includi la categoria: es. `[EDGE] ...`, `[NEG] ...`, `[PROFILO] ...` |
| Step scenario | Numero step (1, 2, 3...) |
| Action | Cosa fa l'utente/sistema in questo step |
| Expected Result | Risultato atteso per questo step — **nel CSV il nome colonna e' `Expceted Result`** (typo storico del template importatore Xray SIAE) |
| Data | Dati di test specifici (vuoto se non necessario) |
| Automazione | `Y` se esiste test automatizzato per questo TC, `N` altrimenti |
| NRT | `Y` (default — il TC e' un Non-Regression Test) |

---

## Prefissi di Categoria

- Nessun prefisso = scenario positivo (happy path)
- `[EDGE]` = edge case (limite, vuoto, volume estremo)
- `[NEG]` = scenario negativo / alternativo (errore, input non valido, dipendenza assente)
- `[PROFILO]` = scenario specifico di ruolo / profilazione

---

## Regola Multi-Step

Stesso ID = stesso Test Case con step multipli. I metadati (tipo, team, Jira, descrizione scenario) si ripetono **solo nella prima riga**. Le righe successive dello stesso TC hanno solo: ID, step numero, Action, Expected Result.

---

## Riepilogo Copertura

**Riepilogo prima dell'export:** mostra la tabella completa al developer con la distribuzione per categoria. Il developer puo' modificare i valori di `Automazione` e `NRT` prima di procedere all'export.

```
Riepilogo copertura:
  Positivi:    N TC
  Edge case:   N TC
  Negativi:    N TC
  Profilazioni: N TC
  TOTALE:      N TC
```

---

## Template Matrice Scenari

Output atteso della fase 4a — matrice scenari compilata prima della generazione:

```
Categoria              | Scenari identificati                          | Fonte      | Count
-----------------------|-----------------------------------------------|------------|------
Positivi (happy path)  | [lista da AC + varianti]                      | AC         | N
Edge case              | [lista da domande o da AC]                    | AC/Dev/Scan| N
Alternativi/negativi   | [lista da domande o da AC]                    | AC/Dev/Scan| N
Profilazioni/ruoli     | [lista da domande, o "N/A - confermato + motivo"] | Dev     | N
```

Legenda Fonte:
- `AC` — derivato dagli Acceptance Criteria
- `Dev` — emerso dalle domande al developer
- `Scan` — derivato dalla Phase 0-bis Code Scan (se eseguita)

Se per una categoria il developer conferma N/A su categoria con minimo > 0:
→ Registra `⚠️ RISCHIO ACCETTATO: [categoria] N/A — Motivo: [motivo dichiarato]`
→ Il motivo è obbligatorio. Non accettare "N/A" senza motivazione.

---

## Domande Elicitazione per Categoria

**Categoria 1 — Scenari positivi (happy path)**
Hai gia' questo dagli AC. Verifica solo che siano completi.
Domanda tipo: "L'AC descrive il caso principale. C'e' qualche variante del flusso positivo che vuoi coprire esplicitamente?"

**Categoria 2 — Edge case**
Valori limite, stati vuoti, volumi estremi, timing. Se non emergono dagli AC, chiedi:
- "Cosa succede con input al limite del range valido? (es. importo = 0, lista vuota, data = oggi)"
- "Ci sono condizioni di gara o sequenze di eventi inattesi da coprire?"
- "Il sistema e' idempotente? Cosa succede se l'operazione viene eseguita due volte?"

**Categoria 3 — Scenari alternativi / negativi**
Flussi di errore, input non validi, permessi mancanti. Se non emergono dagli AC, chiedi:
- "Quali input non validi deve rifiutare il sistema? Con quale messaggio/comportamento?"
- "Cosa succede se una dipendenza esterna e' assente o risponde con errore?"
- "Ci sono stati del sistema che impediscono l'operazione? (es. record gia' esistente, stato non compatibile)"

**Categoria 4 — Profilazioni / ruoli**
Utenti diversi con permessi o dati diversi. Se la Story tocca autorizzazioni o ruoli, chiedi:
- "Quale tipo di utente esegue questa operazione? Ci sono altri ruoli che possono o non possono farlo?"
- "Il comportamento cambia in base al profilo? (es. autore vs editore, admin vs operatore)"
- "Ci sono dati sensibili che solo alcuni ruoli possono vedere?"

---

## Mappatura ID Sequenziali e Chiavi Jira Xray

**Passo post-export — Mappatura ID sequenziali → chiavi Jira Xray [OBBLIGATORIO se si usa siae-automation]**

Dopo l'import del CSV (o la creazione MCP), Xray assegna a ogni TC una chiave Jira propria (`PROJ-XXX`).
Questa chiave e' diversa dall'ID sequenziale usato nel CSV (`1`, `2`, `3`).

Se prevedi di usare `siae-automation` per generare test Cypress o Appium, **devi raccogliere questa mappatura** prima di chiudere la skill:

```
Mappatura TC — {STORY_ID}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ID CSV  →  Chiave Xray   Scenario
  1       →  PROJ-456      Verifica login credenziali valide
  2       →  PROJ-457      [EDGE] Login con campo vuoto
  3       →  PROJ-458      [NEG] Login con password errata
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Tier 1 (MCP):** la chiave viene restituita dalla risposta del tool di creazione — raccoglila automaticamente.
**Tier 3 (CSV):** chiedi al developer di aprire Xray dopo l'import e comunicare le chiavi assegnate. Non procedere con siae-automation finche' non hai questa mappatura.

Salva la mappatura come output della skill: sara' l'input di Fase 1 di siae-automation.

---

## Tier 3 CSV Export

- Genera il file CSV con separatore `;` (semicolon) — **mai virgola**
- Formato esatto: vedi `reference/xray-csv-template.md`
- Header obbligatorio in prima riga
- Mostra il CSV all'utente e spiega come importarlo: Xray → Test → Import CSV

---

## Checklist di Verifica

Prima di dichiarare la skill completata:

- [ ] Phase 0 eseguita: tipo requisito inferito e Req Profile Card mostrata
- [ ] Confidence HIGH → tree lanciato senza conferma tipo | MEDIUM/LOW → conferma ricevuta
- [ ] Domande del tree skippate se risposta gia' presente in AC/description
- [ ] Req Profile Card aggiornata con scenari L1/L2/L3 prima di procedere a Phase 4a
- [ ] AC letti da Jira (o forniti esplicitamente dal developer)
- [ ] Test Strategy Confluence cercata (trovata o WARNING registrato)
- [ ] Test Plan generato/creato con campi obbligatori
- [ ] Matrice scenari compilata (4 categorie valutate: positivi, edge, negativi, profilazioni)
- [ ] Ogni categoria ha scenari identificati o "N/A — confermato dal developer"
- [ ] Ogni AC ha almeno 1 Test Case step-based
- [ ] Presenti TC per scenari positivi, edge case, negativi e profilazioni (se applicabili)
- [ ] I titoli Scenario usano i prefissi `[EDGE]`, `[NEG]`, `[PROFILO]` dove appropriato
- [ ] Ogni step ha sia `Action` che `Expected Result` (nel CSV usa la colonna `Expceted Result` — typo template)
- [ ] Il campo `ID JIRA Story` e' presente in tutti i Test Case
- [ ] Riepilogo copertura per categoria mostrato al developer prima dell'export
- [ ] Campi `Automazione` e `NRT` verificati con il developer
- [ ] Export effettuato (MCP / CSV) o spiegato come farlo
- [ ] Mappatura ID sequenziali → chiavi Jira Xray raccolta (se si prevede di usare siae-automation)
- [ ] Tier usato annunciato nella pre-flight card di apertura

**Non riesci a spuntare tutte le caselle? Il workflow non e' completo. Ricomincia dalla fase bloccata.**
