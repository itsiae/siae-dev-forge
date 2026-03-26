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
| Test Level | `Unit` / `Integration` / `System` / `E2E` / `Performance` / `Security` — derivato automaticamente (vedi regole) |
| Priority | `P1-Critical` / `P2-High` / `P3-Medium` / `P4-Low` — derivato automaticamente (vedi regole) |
| Classification | `Functional` / `Non-Functional` / `Security` / `Regression` — derivato automaticamente |
| Exec Timing | `Pre-Deploy` / `Post-Deploy-Smoke` / `Sprint` / `Nightly` / `Release` — derivato automaticamente |
| Owner | `QA-Manual` / `QA-Automated` / `Dev-Auto` / `DevOps` — derivato automaticamente |

> I 5 campi enterprise sono opzionali e retrocompatibili con l'importatore Xray SIAE.
> Vengono aggiunti in coda al CSV — le colonne sconosciute sono ignorate dall'import standard
> ma preservate nel file per filtering, reporting, e configurazione custom field Xray.

---

**Regole di granularità step (vedi SKILL.md) — riepilogo rapido:**

| Regola | Applicazione |
|--------|-------------|
| A | 1 step = 1 azione atomica. Mai combinare due azioni in un step. |
| B | Navigazione = sempre step separato e primo della sequenza. |
| C | Expected Result deve essere pass/fail senza interpretazione. Mai "funziona" o "ok". |
| D | Precondizioni dati → campo `Data`, non step 1. |

**Esempi di Expected Result validi:**

| Tipo | Expected Result valido |
|------|----------------------|
| FE | "La pagina mostra la lista con N elementi visibili. Il campo totale mostra '€ X.XX'." |
| BE | "HTTP 201. Body: `{id: '<uuid>', createdAt: '<ISO8601>'}`. Header `Location: /api/v1/resource/<id>`." |
| ETL | "Job termina con status SUCCESS. Tabella silver.X contiene N record. 0 record in dead-letter." |
| DB | "Migration applicata. `SELECT COUNT(*) FROM flyway_schema_history WHERE success = true` restituisce N." |
| Auth | "HTTP 403. Body: `{error: 'Forbidden', message: 'Accesso negato: ruolo insufficiente'}`." |
| Integration | "Il sistema ritorna HTTP 200 dopo max 500ms. Il body contiene il campo `correlationId`." |

---

## Regole di Derivazione Automatica — 5 Campi Enterprise

Questi campi vengono popolati automaticamente dalla skill durante la Fase 4b.
Il developer può modificarli nel riepilogo copertura prima dell'export.

### Test Level

| Condizione | Valore |
|-----------|--------|
| Tipo = FE + scenario positivo o EDGE | `E2E` |
| Tipo = FE + scenario NEG (validazione) | `Integration` |
| Tipo = BE + qualsiasi scenario | `Integration` |
| Tipo = ETL o Batch | `System` |
| Tipo = DB | `Integration` |
| Tipo = Auth + categoria profilazione | `Security` |
| Tipo = Auth + scenario positivo/EDGE | `Integration` |
| Scenario derivato da domanda L4 performance | `Performance` |
| Default (nessuna delle sopra) | `System` |

### Priority

| Condizione | Valore |
|-----------|--------|
| Auth + profilazione + accesso non autorizzato → 403 | `P1-Critical` |
| Auth + dati sensibili + isolamento tenant | `P1-Critical` |
| Scenario positivo + tipo Auth | `P1-Critical` |
| Scenario positivo + tipo BE/FE/Integration | `P2-High` |
| Scenario NEG + dipendenza esterna assente | `P2-High` |
| Scenario EDGE + qualsiasi tipo | `P3-Medium` |
| Scenario NEG + input non valido (validazione form) | `P3-Medium` |
| Scenario positivo + tipo ETL/DB/Batch/Report | `P3-Medium` |
| Scenario profilazione (non Auth) | `P3-Medium` |
| Default | `P3-Medium` |

### Classification

| Condizione | Valore |
|-----------|--------|
| NRT = Y | `Regression` (può coesistere con Functional — usa `Functional,Regression`) |
| Scenario derivato da domanda L4 performance | `Non-Functional` |
| Tipo Auth + scenario profilazione accesso negato | `Security` |
| Qualsiasi altro scenario | `Functional` |

### Exec Timing

| Condizione | Valore |
|-----------|--------|
| DB migration + scenario rollback | `Pre-Deploy` |
| Scenario monitoring/observability (L4) | `Post-Deploy-Smoke` |
| Automazione = Y + Test Level in (Unit, Integration) | `Nightly` |
| NRT = Y + Automazione = N | `Sprint` |
| Auth + profilazione con P1-Critical | `Release` |
| Default | `Sprint` |

### Owner

| Condizione | Valore |
|-----------|--------|
| Automazione = Y + Test Level = Unit | `Dev-Auto` |
| Automazione = Y + Test Level in (Integration, E2E, System) | `QA-Automated` |
| Test Level = Performance | `DevOps` |
| Automazione = N | `QA-Manual` |
| Default | `QA-Manual` |

---

### Header CSV esteso (retrocompatibile)

````
ID;Test Type;Team Competenza;ID JIRA Story;User Story Description;Scenario (descrizione);Step scenario;Action;Expceted Result;Data;Automazione;NRT;Test Level;Priority;Classification;Exec Timing;Owner
````

Le ultime 5 colonne sono opzionali. Per generare CSV solo con i campi legacy (compatibile
con il configuratore Xray esistente senza modifiche), omettile. Per generare il CSV esteso
con tutti i campi enterprise, includile.

La skill chiede al developer durante il riepilogo:
"Vuoi includere i 5 campi enterprise nel CSV (Test Level, Priority, Classification, Timing, Owner)?
Sono retrocompatibili con il tuo importatore Xray."

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
  Positivi:      N TC  (P2-High: X | P3-Medium: Y)
  Edge case:     N TC  (P2-High: X | P3-Medium: Y)
  Negativi:      N TC  (P2-High: X | P3-Medium: Y)
  Profilazioni:  N TC  (P1-Critical: X | P3-Medium: Y)
  TOTALE:        N TC

  Test Level:    Unit: X | Integration: Y | System: Z | E2E: W | Performance: V | Security: U
  Automazione:   Y: N | N: M
  NRT:           Y: N | N: M
  Owner:         QA-Manual: X | QA-Automated: Y | Dev-Auto: Z | DevOps: W
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
- [ ] Phase 0-bis eseguita (o skip esplicito documentato con motivo)
- [ ] Se Code Scan eseguito: Code Profile Card mostrata al developer
- [ ] Se Code Scan eseguito: scenari candidati confermati/scartati prima di Fase 4a
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
- [ ] Se tipo è uno dei 5 nuovi (Notification/Batch/Report/Feature Flag/File Processing):
      question tree specifico del tipo usato (non tree generico FE/BE)
- [ ] Fase 4c eseguita se ≥ 2 tappe identificabili, oppure skip documentato (story a singola tappa)
- [ ] Se Fase 4c eseguita: output presentato con header di sezione per tappa
- [ ] Se Fase 4c eseguita: riepilogo per tappa mostrato accanto al riepilogo per categoria
- [ ] 5 campi enterprise derivati automaticamente per ogni TC (Test Level, Priority, Classification, Exec Timing, Owner)
- [ ] Developer ha confermato o modificato i campi enterprise prima dell'export
- [ ] Header CSV include le 5 colonne enterprise (se developer ha scelto CSV esteso)
- [ ] RRS parziale calcolato e mostrato al developer dopo il riepilogo copertura
- [ ] Coverage_Score e Critical_Coverage_Score mostrati con formula trasparente
- [ ] Gate di rilascio comunicato al developer con decisione consigliata

**Non riesci a spuntare tutte le caselle? Il workflow non e' completo. Ricomincia dalla fase bloccata.**
