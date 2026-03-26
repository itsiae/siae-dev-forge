# Question Trees — siae-qa Smart Req Typing

Ogni albero è strutturato su 4 livelli:
- **L1 — Flusso principale:** verifica/completa la comprensione del happy path
- **L2 — Edge case specifici del tipo:** scenari limite propri di quel dominio
- **L3 — Integrazioni / dipendenze:** chi chiama? cosa chiama? dipendenze esterne?
- **L4 — Performance / SLA:** throughput, latenza, freshness, zero-downtime

Claude fa UNA domanda alla volta.
**Salta ogni domanda già rispondibile dagli AC/description/commenti esistenti.**

**SKIP-CRITERIA — Regola obbligatoria:**
Per ogni domanda è definito un blocco `> SKIP SE:` con keyword esplicite.
Una domanda si salta SOLO se almeno uno dei pattern indicati è presente testualmente
negli AC, description, o commenti della story. NON valutare semanticamente.
Se il pattern non è trovato letteralmente → la domanda è obbligatoria.

---

## Frontend (FE)

**Segnali di inferenza:** "componente", "pagina", "form", "UI", "Vue", "Angular",
"React", "click", "visualizza", "render", "responsive", "upload", "drag"

### L1 — Flusso principale
1. "Il form/componente ha stati di caricamento (loading/skeleton)?
   Cosa mostra all'utente mentre aspetta i dati dall'API?"
   > SKIP SE: gli AC contengono "loading", "skeleton", "spinner", "stato di caricamento", "mentre aspetta", "indicatore di progresso"

2. "Quali campi sono obbligatori? Ci sono campi con formato specifico
   (email, IBAN, data, codice fiscale) che richiedono validazione?"
   > SKIP SE: gli AC elencano esplicitamente i campi obbligatori con il loro formato (es. "campo X è obbligatorio", "formato YYYY-MM-DD", "validazione email")

### L2 — Edge case specifici FE
3. "Cosa mostra la pagina se la lista di dati è vuota?
   C'è un empty state dedicato o si nasconde il componente?"
   > SKIP SE: gli AC contengono "lista vuota", "empty state", "nessun risultato", "stato vuoto", "messaggio quando non ci sono"

4. "La feature deve funzionare su mobile? Ci sono breakpoint critici
   (es. < 768px) dove il layout cambia significativamente?"
   > SKIP SE: gli AC specificano breakpoint o dicono esplicitamente "solo desktop", "non richiesta versione mobile", oppure "responsive: no"

5. "Cosa succede se l'utente naviga via durante un'operazione in corso
   (upload in corso, form non salvato)? C'è una guardia di navigazione?"
   > SKIP SE: gli AC menzionano "guardia di navigazione", "beforeRouteLeave", "conferma prima di uscire", "dati non salvati", "dialog di conferma navigazione"

### L3 — Integrazioni / dipendenze
6. "Da quale API recupera i dati? Cosa mostra se l'API risponde
   con errore 500 o timeout? C'è un messaggio di errore dedicato?"
   > SKIP SE: gli AC specificano il comportamento su errore API con messaggio esplicito (es. "in caso di errore mostra 'Servizio non disponibile'")

### L4 — Performance / SLA
7. "Ci sono soglie di performance definite per questo componente?
   (es. LCP < 2.5s, TTI < 3.5s, First Contentful Paint < 1.5s).
   Il componente deve funzionare su connessioni lente (3G simulata, < 1 Mbps)
   o su dispositivi low-end (Android entry-level, 2GB RAM)?"
   > SKIP SE: gli AC specificano esplicitamente "nessun requisito di performance",
   > "solo desktop ad alta velocità", o includono già le soglie numeriche

8. "Il componente contiene logica di calcolo pesante (rendering di grandi dataset,
   animazioni, canvas, WebGL)? Ci sono operazioni che potrebbero bloccare il main thread?"
   > SKIP SE: il componente è puramente presentazionale senza logica di calcolo

---

## Backend Microservice (BE)

**Segnali di inferenza:** "API", "endpoint", "service", "REST", "controller",
"Spring", "Lambda", "validazione", "business rule", "handler", "mapper"

### L1 — Flusso principale
1. "Quali metodi HTTP espone questo endpoint? Quali status code restituisce
   per il caso di successo e per ogni caso di errore previsto?"
   > SKIP SE: gli AC elencano esplicitamente metodi HTTP e status code (es. "POST /api/v1/...", "restituisce 201 in caso di successo", "404 se non trovato")

2. "Quali campi del payload sono obbligatori?
   Ci sono vincoli di formato o range (es. importo > 0, ISRC pattern)?"
   > SKIP SE: gli AC elencano esplicitamente campi obbligatori con vincoli (es. "campo amount è obbligatorio e deve essere > 0")

### L2 — Edge case specifici BE
3. "L'operazione è idempotente? Cosa succede se viene chiamata due volte
   con lo stesso payload (es. doppio click, retry automatico del client)?"
   > SKIP SE: gli AC contengono "idempotente", "idempotency", "stesso risultato se ripetuto", "HTTP PUT sicuro da ripetere", "retry-safe"

4. "Ci sono regole business che bloccano l'operazione?
   (es. stato record incompatibile, quota superata, record già esistente)"
   > SKIP SE: gli AC elencano esplicitamente le condizioni di blocco con comportamento atteso (es. "se il record è in stato LOCKED restituisce 409")

5. "Come gestisce una dipendenza esterna assente o lenta?
   C'è circuit breaker, timeout configurato o retry con backoff?"
   > SKIP SE: gli AC menzionano "circuit breaker", "timeout", "retry", "fallback", "comportamento in caso di indisponibilità del servizio X"

### L3 — Integrazioni / dipendenze
6. "Chi chiama questo endpoint (client FE, altro microservizio, scheduler)?
   Il contratto API è già definito in un file OpenAPI/Swagger?"
   > SKIP SE: gli AC indicano esplicitamente il caller (es. "chiamato dal frontend", "invocato da scheduler ogni ora") o menzionano un file OpenAPI esistente

### L4 — Performance / SLA
7. "Qual è il throughput atteso su questo endpoint in condizioni normali (req/s)?
   Qual è il picco previsto (es. campagna, scadenza fiscale, batch notturno)?
   Esiste un SLA di latenza definito (es. p99 < 300ms, p95 < 200ms)?"
   > SKIP SE: gli AC specificano "nessun SLA", throughput atteso, o latenza target

8. "Questo endpoint partecipa a una catena di chiamate sincrone? Se sì, qual è il
   budget di latenza allocato a questo servizio nel contesto dell'intera chain?"
   > SKIP SE: l'endpoint è chiamato in modo isolato senza chain di servizi

---

## ETL / Data Pipeline

**Segnali di inferenza:** "Glue", "PySpark", "pipeline", "trasformazione",
"bronze", "silver", "gold", "job", "ETL", "medallion", "crawler", "Athena"

### L1 — Flusso principale
1. "Qual è la trasformazione principale?
   Da quale layer (bronze/silver/gold) parte e quale layer produce?"
   > SKIP SE: gli AC specificano esplicitamente il layer sorgente e target (es. "legge da bronze e scrive su silver", "trasforma da raw a curated")

2. "Qual è la chiave di deduplicazione dei record?
   Come vengono gestiti i duplicati (drop, keep-first, keep-last, merge)?"
   > SKIP SE: gli AC specificano la chiave di deduplicazione e la policy (es. "deduplica per id + timestamp, tieni l'ultimo")

### L2 — Edge case specifici ETL
3. "Cosa succede con record nulli o malformati nella sorgente?
   Vengono scartati (drop), messi in quarantena (dead-letter) o il job fallisce?"
   > SKIP SE: gli AC specificano la policy su record invalidi (es. "i record con campo X null vengono scartati", "dead-letter queue per anomalie")

4. "Il job è idempotente? Se viene rieseguito sullo stesso intervallo temporale,
   sovrascrive i dati o li duplica?"
   > SKIP SE: gli AC contengono "idempotente", "rieseguibile", "sovrascrive", "overwrite mode", "non duplica se rieseguito"

5. "C'è un volume soglia (es. 0 record letti, > N record anomali)
   oltre il quale il job deve fallire o generare un alert?"
   > SKIP SE: gli AC specificano soglie numeriche esplicite (es. "se meno di 100 record → fallisce", "alert se error rate > 5%")

### L3 — Integrazioni / dipendenze
6. "Il job dipende da job o layer upstream? Come si comporta se upstream
   non ha prodotto dati per questa finestra temporale?"
   > SKIP SE: gli AC specificano il comportamento su dati upstream assenti (es. "se il layer bronze non ha dati → skip silenzioso", "attende fino a 2h")

### L4 — SLA di completamento / Freshness
7. "Entro quanto tempo il job deve completare l'elaborazione dell'intera finestra temporale?
   Qual è l'impatto downstream se il job è in ritardo di 1h / 4h / 24h?
   I consumer del layer gold hanno SLA di freshness definiti (es. 'dati disponibili entro le 8:00')?"
   > SKIP SE: gli AC specificano la finestra di completamento e/o il SLA di freshness downstream

8. "Qual è il volume massimo di record atteso per singola esecuzione?
   Il job è stato testato su dataset di dimensione production (o stimato equivalente)?"
   > SKIP SE: gli AC indicano volume atteso e confermano il test su dati rappresentativi

---

## Database

**Segnali di inferenza:** "migration", "schema", "query", "tabella", "indice",
"DDL", "flyway", "liquibase", "ALTER TABLE", "stored procedure", "view"

### L1 — Flusso principale
1. "La migration è reversibile? Esiste (o va creato) uno script di rollback
   testato che riporta allo stato precedente?"
   > SKIP SE: gli AC menzionano esplicitamente lo script di rollback o indicano "migration irreversibile — approvata da DBA"

2. "La migration modifica dati esistenti (UPDATE/DELETE su righe)
   o solo struttura (DDL puro senza toccare dati)?"
   > SKIP SE: gli AC specificano esplicitamente il tipo di modifica (es. "solo DDL — nessun dato modificato", "UPDATE su tutte le righe della tabella X")

### L2 — Edge case specifici DB
3. "Ci sono vincoli di integrità referenziale (FK) da verificare
   prima o dopo la migration? Quali tabelle correlate potrebbero rompersi?"
   > SKIP SE: gli AC documentano le FK impattate con esito atteso

4. "La migration è safe su tabelle con milioni di righe?
   Usa LOCK TABLE? Ha un impatto stimato sul tempo di downtime?"
   > SKIP SE: gli AC specificano la strategia zero-downtime o la finestra di manutenzione accettata

### L3 — Integrazioni / dipendenze
5. "I servizi applicativi che leggono/scrivono su questa tabella
   sono compatibili con il nuovo schema PRIMA del deploy applicativo?"
   > SKIP SE: gli AC specificano la strategia di deploy coordinato (es. "expand-contract", "backward compatible", "deploy atomico schema + applicativo")

### L4 — Performance migration / Zero-downtime
6. "La migration è stata stimata in termini di tempo di esecuzione su un dataset
   di dimensione production? Qual è il tempo di lock stimato su tabelle live?
   Esiste una strategia zero-downtime (expand-contract, online migration)?"
   > SKIP SE: gli AC specificano la strategia zero-downtime approvata o la finestra di manutenzione

7. "Dopo la migration, le query esistenti (incluse quelle del codice applicativo in produzione)
   mantengono le stesse performance? Sono stati analizzati i piani di esecuzione delle query critiche?"
   > SKIP SE: la migration è puramente additiva (aggiunge colonne nullable) senza impatto sulle query

---

## Auth / Security

**Segnali di inferenza:** "login", "logout", "ruolo", "permesso", "token",
"autenticazione", "RBAC", "JWT", "SSO", "autorizzazione", "profilo utente"

### L1 — Flusso principale
1. "Quali ruoli/profili possono eseguire questa operazione?
   Chi NON deve poterla eseguire? Il blocco è silenzioso (403) o con messaggio?"
   > SKIP SE: gli AC elencano esplicitamente i ruoli abilitati e il comportamento su accesso negato

2. "Il token di autenticazione ha un TTL?
   Cosa succede se scade durante una sessione attiva?"
   > SKIP SE: gli AC specificano il TTL e il comportamento a scadenza (es. "token scade dopo 1h — redirect al login", "silent refresh")

### L2 — Edge case specifici Auth
3. "Un utente può agire su risorse di un altro utente?
   C'è isolamento per tenant, organizzazione o codice autore?"
   > SKIP SE: gli AC specificano esplicitamente l'isolamento tenant o dicono "ogni utente vede solo le proprie risorse"

4. "L'endpoint è soggetto a rate limiting?
   Cosa restituisce il sistema quando la soglia viene superata?"
   > SKIP SE: gli AC specificano rate limit e comportamento su superamento soglia (es. "max 100 req/min — restituisce 429 con Retry-After")

### L3 — Integrazioni / dipendenze
5. "Le azioni di questo tipo vengono registrate in un log di audit?
   Chi ha fatto cosa, quando, da quale IP?"
   > SKIP SE: gli AC menzionano audit log, tracciabilità, o specificano che "l'operazione non richiede tracciamento"

### L4 — Rate limiting / Security SLA
6. "L'endpoint di autenticazione è soggetto a rate limiting per prevenire
   brute force e credential stuffing? Qual è la soglia (es. max 5 tentativi/min per IP)?
   Cosa restituisce il sistema quando la soglia è superata (429 + Retry-After)?"
   > SKIP SE: gli AC specificano il rate limiting con soglia e comportamento

7. "Questa feature espande la superficie di attacco (nuovi endpoint pubblici,
   nuovi dati sensibili esposti)? È inclusa nello scope del prossimo DAST / penetration test?"
   > SKIP SE: la feature non espone nuovi endpoint pubblici e non introduce nuovi dati sensibili

---

## Integration REST / Sync

**Segnali di inferenza:** "chiamata esterna", "API terza parte", "REST client", "HTTP client",
"timeout", "retry", "circuit breaker", "Feign", "RestTemplate", "WebClient", "OpenFeign",
"Pact", "consumer-driven contract", "gRPC client", "SOAP client", "WireMock"

### L1 — Flusso principale
1. "Cosa fa il sistema se il servizio esterno non risponde entro il timeout configurato?
   Qual è il timeout impostato? C'è un retry automatico con backoff esponenziale?
   Quanti tentativi prima di restituire errore al caller?"
   > SKIP SE: gli AC specificano timeout, numero di retry, e comportamento su fallimento

2. "Come si gestisce un response code inatteso dall'esterno (es. 500, 503, risposta vuota)?
   Il sistema ignora, logga, propaga l'errore al client, o usa un fallback cached?"
   > SKIP SE: gli AC specificano esplicitamente il comportamento per ogni codice di errore

### L2 — Edge case specifici Integration REST
3. "Il sistema è resiliente a risposte parziali
   (es. paginazione incompleta, solo alcuni record restituiti, body truncato)?"
   > SKIP SE: gli AC specificano il comportamento su risposte parziali

4. "Esiste un circuit breaker configurato? In stato OPEN, cosa vede il caller?
   (errore esplicito, dati stale cached, funzionalità degradata/disabilitata)"
   > SKIP SE: gli AC descrivono il comportamento degradato con circuit breaker

5. "Il contratto API del servizio esterno è versionato? Se il provider cambia il formato
   della response, il sistema rileva la breaking change o fallisce silenziosamente?"
   > SKIP SE: gli AC menzionano contract testing, Pact, o versioning esplicito dell'API esterna

### L3 — Integrazioni / dipendenze
6. "Esiste un ambiente sandbox o stub (WireMock) del servizio esterno per i test?
   O si mockano le chiamate a livello unitario? Come si verifica il comportamento
   con il servizio reale prima del go-live?"
   > SKIP SE: gli AC specificano l'ambiente di test (sandbox, staging, WireMock) già configurato

### L4 — Performance / SLA
7. "Qual è il timeout configurato per le chiamate a questo servizio?
   C'è un SLA di risposta definito dal provider esterno (SLA contrattuale)?
   L'endpoint è chiamato in sequenza bloccante o in modo asincrono/parallelo?"
   > SKIP SE: gli AC specificano timeout e comportamento asincrono/parallelo

---

## Integration Event / Async

**Segnali di inferenza:** "webhook", "evento", "Kafka", "SQS", "SNS", "notifica asincrona",
"callback", "polling", "EventBridge", "event bus", "AMQP", "RabbitMQ", "ActiveMQ",
"saga", "outbox pattern", "consumer", "producer", "topic", "queue", "dead letter", "DLQ",
"message broker", "event-driven"

### L1 — Flusso principale
1. "Il consumer è idempotente? Se lo stesso messaggio/evento arriva due volte
   (retry automatico, at-least-once delivery), il sistema processa due volte o deduplica?"
   > SKIP SE: gli AC specificano esplicitamente "idempotente", "deduplicazione",
   > o "exactly-once processing garantito dal broker"

2. "Come si gestisce un messaggio con payload non valido o formato inatteso?
   Il consumer: rigetta (NACK), mette in DLQ, processa parzialmente, o fallisce il consumer group?"
   > SKIP SE: gli AC specificano la policy su messaggi malformati

### L2 — Edge case specifici Integration Event
3. "I messaggi possono arrivare out-of-order? Il consumer garantisce l'ordinamento
   o lo ordering è gestito a livello di partition key/shard?
   Cosa succede se un evento arriva dopo che lo stato downstream è già avanzato?"
   > SKIP SE: gli AC specificano che l'ordinamento non è rilevante per questa feature

4. "Cosa succede se il consumer group è in rebalance durante l'elaborazione di un messaggio?
   Il messaggio può essere perso o processato due volte durante il rebalance?"
   > SKIP SE: gli AC specificano la strategia di gestione del rebalance

5. "Se un messaggio non può essere elaborato dopo N tentativi, dove va?
   Esiste una Dead Letter Queue? Chi monitora la DLQ?
   C'è un processo di re-processing manuale per i messaggi in DLQ?"
   > SKIP SE: gli AC specificano la DLQ con monitoring e processo di recovery

### L3 — Integrazioni / dipendenze
6. "Il contratto del canale (topic Kafka, schema SQS, formato evento EventBridge)
   è versionato con schema registry? Se il producer cambia il formato,
   il consumer viene notificato in anticipo o scopre il breaking change in produzione?"
   > SKIP SE: gli AC menzionano schema registry, AsyncAPI spec, o versioning esplicito del contratto

### L4 — Throughput / Consumer lag
7. "Qual è il throughput di messaggi atteso (msg/s in condizioni normali, picco)?
   Qual è il consumer lag massimo tollerabile prima di considerare il consumer in ritardo?
   C'è un alert configurato sul lag del consumer group?"
   > SKIP SE: gli AC specificano throughput atteso e soglia di lag accettabile

---

## Regola SKIP SE — Reminder

Per ogni domanda del tree, il blocco `> SKIP SE:` definisce i pattern di skip deterministici.
**Non valutare semanticamente.** Se nessun pattern è trovato letteralmente negli AC → domanda obbligatoria.
Le domande L0 (flusso trasversale) non hanno skip-criteria: sono sempre obbligatorie se non c'è
struttura sequenziale esplicita negli AC.
