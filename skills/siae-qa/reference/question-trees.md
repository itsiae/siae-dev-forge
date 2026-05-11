# Question Trees — siae-qa Smart Req Typing

Ogni albero è strutturato su 3 livelli:
- **L1 — Flusso principale:** verifica/completa la comprensione del happy path
- **L2 — Edge case specifici del tipo:** scenari limite propri di quel dominio
- **L3 — Integrazioni / dipendenze:** chi chiama? cosa chiama? dipendenze esterne?

Claude fa UNA domanda alla volta.
**Salta ogni domanda già rispondibile dagli AC/description/commenti esistenti.**

---

## Frontend (FE)

**Segnali di inferenza:** "componente", "pagina", "form", "UI", "Vue", "Angular",
"React", "click", "visualizza", "render", "responsive", "upload", "drag"

### L1 — Flusso principale
1. "Il form/componente ha stati di caricamento (loading/skeleton)?
   Cosa mostra all'utente mentre aspetta i dati dall'API?"
2. "Quali campi sono obbligatori? Ci sono campi con formato specifico
   (email, IBAN, data, codice fiscale) che richiedono validazione?"

### L2 — Edge case specifici FE
3. "Cosa mostra la pagina se la lista di dati è vuota?
   C'è un empty state dedicato o si nasconde il componente?"
4. "La feature deve funzionare su mobile? Ci sono breakpoint critici
   (es. < 768px) dove il layout cambia significativamente?"
5. "Cosa succede se l'utente naviga via durante un'operazione in corso
   (upload in corso, form non salvato)? C'è una guardia di navigazione?"

### L3 — Integrazioni / dipendenze
6. "Da quale API recupera i dati? Cosa mostra se l'API risponde
   con errore 500 o timeout? C'è un messaggio di errore dedicato?"

---

## Backend Microservice (BE)

**Segnali di inferenza:** "API", "endpoint", "service", "REST", "controller",
"Spring", "Lambda", "validazione", "business rule", "handler", "mapper"

### L1 — Flusso principale
1. "Quali metodi HTTP espone questo endpoint? Quali status code restituisce
   per il caso di successo e per ogni caso di errore previsto?"
2. "Quali campi del payload sono obbligatori?
   Ci sono vincoli di formato o range (es. importo > 0, ISRC pattern)?"
3. "Per i vincoli numerici di range, sono **strict** (es. `importo > 0`,
   esclusivo) o **non-strict** (es. `quantita >= 0`, inclusivo)?
   E qual e' il **tipo** del campo (decimal/integer/date/timestamp)?
   La risposta determina se Matrix A genera un EDGE auto alla frontiera bassa
   (`0.01` per decimal vs `1` per integer vs data successiva)."

### L2 — Edge case specifici BE
3. "L'operazione è idempotente? Cosa succede se viene chiamata due volte
   con lo stesso payload (es. doppio click, retry automatico del client)?"
4. "Ci sono regole business che bloccano l'operazione?
   (es. stato record incompatibile, quota superata, record già esistente)"
5. "Come gestisce una dipendenza esterna assente o lenta?
   C'è circuit breaker, timeout configurato o retry con backoff?"

### L3 — Integrazioni / dipendenze
6. "Chi chiama questo endpoint (client FE, altro microservizio, scheduler)?
   Il contratto API è già definito in un file OpenAPI/Swagger?"

---

## ETL / Data Pipeline

**Segnali di inferenza:** "Glue", "PySpark", "pipeline", "trasformazione",
"bronze", "silver", "gold", "job", "ETL", "medallion", "crawler", "Athena"

### L1 — Flusso principale
1. "Qual è la trasformazione principale?
   Da quale layer (bronze/silver/gold) parte e quale layer produce?"
2. "Qual è la chiave di deduplicazione dei record?
   Come vengono gestiti i duplicati (drop, keep-first, keep-last, merge)?"
3. "La pipeline è idempotente? Se sì, qual è la chiave di MERGE/UPSERT
   (es. id_ripartizione, business key composta, hash payload)?
   Cosa succede se viene rieseguita con lo stesso input
   (no-op idempotente vs upsert con update)?"

### L2 — Edge case specifici ETL
4. "Cosa succede con record nulli o malformati nella sorgente?
   Vengono scartati (drop), messi in quarantena (dead-letter) o il job fallisce?"
5. "Il job è idempotente? Se viene rieseguito sullo stesso intervallo temporale,
   sovrascrive i dati o li duplica?"
6. "C'è un volume soglia (es. 0 record letti, > N record anomali)
   oltre il quale il job deve fallire o generare un alert?"
7. "Quali soglie scatenano alert? (count assoluto es. 0 record letti,
   ratio es. drop_ratio > 30%, drift es. count(silver) deviates from
   count(bronze) - count(dropped) > 5)? Ogni soglia ha severity diversa?"
8. "I timestamp hanno timezone esplicita (TIMESTAMPTZ in Postgres,
   timezone-aware datetime in Python/PySpark) o naive (TIMESTAMP)?
   Quale timezone canonica (UTC, Europe/Rome, source-specific)?
   Come si gestisce DST transitions e timezone mismatch tra sorgenti?"

### L3 — Integrazioni / dipendenze
9. "Il job dipende da job o layer upstream? Come si comporta se upstream
   non ha prodotto dati per questa finestra temporale?"
10. "Esistono side-effect asincroni della pipeline?
    (CloudWatch alarm su quality degradation, SNS notification, audit log entry,
    downstream trigger su altro Glue job). Per ognuno: window di propagation,
    come verificare che il side-effect e' avvenuto/non avvenuto."

---

## Database

**Segnali di inferenza:** "migration", "schema", "query", "tabella", "indice",
"DDL", "flyway", "liquibase", "ALTER TABLE", "stored procedure", "view"

### L1 — Flusso principale
1. "La migration è reversibile? Esiste (o va creato) uno script di rollback
   testato che riporta allo stato precedente?"
2. "La migration modifica dati esistenti (UPDATE/DELETE su righe)
   o solo struttura (DDL puro senza toccare dati)?"

### L2 — Edge case specifici DB
3. "Ci sono vincoli di integrità referenziale (FK) da verificare
   prima o dopo la migration? Quali tabelle correlate potrebbero rompersi?"
4. "La migration è safe su tabelle con milioni di righe?
   Usa LOCK TABLE? Ha un impatto stimato sul tempo di downtime?"

### L3 — Integrazioni / dipendenze
5. "I servizi applicativi che leggono/scrivono su questa tabella
   sono compatibili con il nuovo schema PRIMA del deploy applicativo?"

---

## Auth / Security

**Segnali di inferenza:** "login", "logout", "ruolo", "permesso", "token",
"autenticazione", "RBAC", "JWT", "SSO", "autorizzazione", "profilo utente"

### L1 — Flusso principale
1. "Quali ruoli/profili possono eseguire questa operazione?
   Chi NON deve poterla eseguire? Il blocco è silenzioso (403) o con messaggio?"
2. "Il token di autenticazione ha un TTL?
   Cosa succede se scade durante una sessione attiva?"

### L2 — Edge case specifici Auth
3. "Un utente può agire su risorse di un altro utente?
   C'è isolamento per tenant, organizzazione o codice autore?"
4. "L'endpoint è soggetto a rate limiting?
   Cosa restituisce il sistema quando la soglia viene superata?"

### L3 — Integrazioni / dipendenze
5. "Le azioni di questo tipo vengono registrate in un log di audit?
   Chi ha fatto cosa, quando, da quale IP?"

---

## Integration / External

**Segnali di inferenza:** "webhook", "chiamata esterna", "API terza parte",
"evento", "Kafka", "SQS", "SNS", "notifica", "callback", "polling"

### L1 — Flusso principale
1. "Cosa fa il sistema se l'API/servizio esterno non risponde entro il timeout?
   C'è retry automatico con backoff? Quanti tentativi?"
2. "Come si gestisce un payload inatteso o un codice di errore sconosciuto
   proveniente dall'esterno? Il sistema ignora, logga o fallisce?"

### L2 — Edge case specifici Integration
3. "Il sistema è resiliente a risposte parziali
   (es. solo alcuni record restituiti, paginazione incompleta)?"
4. "L'evento/messaggio può arrivare out-of-order o duplicato?
   Il consumer è idempotente?"

### L3 — Integrazioni / dipendenze
5. "Esiste un ambiente di staging o sandbox dell'esterno per i test?
   O si usa un mock/stub/WireMock in locale?"
