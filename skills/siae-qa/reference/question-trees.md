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

## L0 — Flusso (trasversale a tutti i tipi)

> Queste domande identificano le tappe del flusso utente per l'ordinamento in Fase 4c.
> Si pongono PRIMA delle domande specifiche del tipo, ma SOLO se la struttura
> sequenziale non è già ricavabile dagli AC (Given/When/Then multipli, elenco numerato).
> Se il flusso è già esplicito negli AC, salta le domande L0 e procedi con L1.

**L0.1 — Tappe del flusso (universale)**
"Questa Story fa parte di un flusso utente più ampio?
Se sì, quali sono le tappe che un utente deve completare in sequenza per raggiungere l'obiettivo?
(es. registrazione → login → azione principale → conferma → notifica)"

> SKIP SE: gli AC contengono almeno 2 step Given/When/Then in sequenza, oppure
> un elenco numerato di passi, oppure frasi con "prima ... poi ...", "dopo aver ...",
> "una volta che ...", "a seguito di ..."

**L0.2 — Entry point del flusso (universale)**
"Da quale stato parte l'utente/sistema prima di eseguire l'azione principale?
(es. utente non autenticato, utente loggato con carrello vuoto, record in stato BOZZA,
job in attesa di trigger, file non ancora caricato)"

> SKIP SE: lo stato iniziale è esplicitamente descritto negli AC o nel Given della story

**L0.3 — Exit condition del flusso (universale)**
"Come sa l'utente/sistema che il flusso è completato con successo?
Cosa cambia nello stato del sistema alla fine del flusso?
(es. record in stato PUBBLICATO, email inviata, file in stato PROCESSED)"

> SKIP SE: la condizione finale è esplicitamente descritta negli AC o nel Then della story

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

## Notification / Messaging

**Segnali di inferenza:** "email transazionale", "push notification", "SMS", "notifica in-app",
"template email", "opt-out", "unsubscribe", "FCM", "APNs", "SES", "SendGrid", "Twilio",
"notification center", "delivery receipt", "bounce", "webhook push"

**Confidence trigger:**
- HIGH: 2+ segnali tra FCM/APNs/SES/SendGrid/Twilio, oppure "email transazionale"
- MEDIUM: "notifica" + uno tra "email"/"push"/"SMS", oppure "opt-out" + canale specificato

### L1 — Flusso principale
1. "Il trigger della notifica è sincrono (risposta API immediata) o asincrono (evento da coda)?
   Se asincrono, come l'utente o il sistema chiamante sa che la notifica è stata inviata?"
   > SKIP SE: gli AC specificano il trigger e la modalità di feedback (sincrono/asincrono)

2. "Il template del messaggio è statico o personalizzato con dati utente?
   Quali campi vengono interpolati? C'è un fallback se un campo è null o mancante?"
   > SKIP SE: gli AC specificano i campi del template con gestione null

### L2 — Edge case specifici Notification
3. "Cosa succede se la consegna fallisce (token FCM scaduto, bounce email, SMS non raggiungibile)?
   Il sistema ritenta automaticamente? Quante volte? Con quale backoff?
   Il fallimento è silenzioso o segnalato all'utente/sistema?"
   > SKIP SE: gli AC specificano la policy di retry e notifica su fallimento

4. "La stessa notifica può essere inviata più volte per lo stesso evento
   (es. retry di rete, doppio evento, doppio click)? Il sistema deduplica?"
   > SKIP SE: gli AC specificano la politica di deduplicazione notifiche

5. "L'utente può fare opt-out per uno o più canali (email, push, SMS)?
   Il sistema rispetta l'opt-out immediatamente o alla prossima esecuzione?
   Un opt-out su un canale blocca anche gli altri canali?"
   > SKIP SE: gli AC specificano la gestione opt-out con timing e granularità canale

### L3 — Integrazioni / dipendenze
6. "Esiste un ambiente sandbox/test per i provider esterni (SES sandbox mode, FCM test token)?
   Come si verifica la consegna effettiva nei test di integrazione senza inviare notifiche reali?"
   > SKIP SE: gli AC specificano l'ambiente di test già configurato (sandbox, mock, test device)

### L4 — Deliverability / Volume
7. "Qual è il volume di notifiche atteso per questo evento (per singola esecuzione, per ora, per giorno)?
   Esiste un rate limit imposto dal provider (es. SES: 14 email/sec in sandbox)?
   C'è un SLA di consegna entro X minuti/ore?"
   > SKIP SE: gli AC specificano volume atteso e eventuali SLA di consegna

---

## Batch / Scheduler

**Segnali di inferenza:** "batch", "cron", "scheduler", "Quartz", "EventBridge rule",
"job periodico", "elaborazione notturna", "elaborazione massiva", "finestra temporale",
"trigger scheduled", "AWS Batch", "Step Functions scheduled", "import massivo", "export massivo"

**Confidence trigger:**
- HIGH: "batch" + "cron"/"scheduler"/"periodico", oppure nome tool esplicito (Quartz, AWS Batch)
- MEDIUM: "job" + "periodico"/"notturno"/"settimanale"/"mensile"

### L1 — Flusso principale
1. "Qual è la frequenza di esecuzione (cron expression o frequenza in parole)?
   Il job ha una finestra temporale massima di completamento oltre la quale
   viene considerato in timeout e fallito?"
   > SKIP SE: gli AC specificano la frequenza e la finestra di completamento

2. "I dati processati sono un sottoinsieme (es. record del giorno precedente, delta)
   o l'intero dataset? Come viene determinato il range di elaborazione
   (timestamp, campo stato, watermark)?"
   > SKIP SE: gli AC specificano il range di dati e il criterio di selezione

### L2 — Edge case specifici Batch
3. "Cosa succede se il job precedente è ancora in esecuzione quando scatta il nuovo trigger?
   Il sistema blocca il nuovo trigger, esegue in parallelo, o genera un alert?
   Esiste un meccanismo di lock (database lock, SFN execution check)?"
   > SKIP SE: gli AC specificano il comportamento su overlap di esecuzioni

4. "Il job gestisce correttamente i giorni limite: fine mese (28/29/30/31),
   fine anno (31 dicembre), cambio ora legale (ora doppia/mancante)?
   Ci sono calcoli di date o window temporali sensibili a questi boundary?"
   > SKIP SE: gli AC specificano che il job non ha calcoli di date sensibili ai boundary

5. "Se il job fallisce a metà elaborazione, i record già processati vengono committati
   (checkpoint) o si fa rollback completo? È possibile riprendere dal punto di
   interruzione (restart from checkpoint)?"
   > SKIP SE: gli AC specificano la strategia di recovery e checkpointing

### L3 — Integrazioni / dipendenze
6. "Il job dipende da dati prodotti da un altro job o sistema upstream
   (es. file SFTP arrivato, layer ETL aggiornato, API chiamabile)?
   Come si comporta se i dati upstream non sono pronti all'ora di trigger?"
   > SKIP SE: gli AC specificano le dipendenze upstream e il comportamento su dati assenti

### L4 — SLA completamento / Monitoring
7. "Entro quanto tempo il job deve completare per rispettare i downstream (report, BI, utenti)?
   Esiste un alert se il job supera la finestra di completamento o fallisce silenziosamente?
   Chi riceve la notifica di fallimento e in quale formato?"
   > SKIP SE: gli AC specificano la finestra di completamento e il meccanismo di alert

---

## Report / Export

**Segnali di inferenza:** "report", "export", "PDF", "Excel", "XLSX", "CSV export",
"rendiconto", "estratto conto", "stampa", "download", "JasperReports", "Apache POI",
"generazione documento", "template report", "BI", "dashboard export"

**Confidence trigger:**
- HIGH: "PDF"/"Excel"/"XLSX" + "report"/"export"/"rendiconto", oppure nome tool (JasperReports, POI)
- MEDIUM: "export" o "download" senza formato specificato

### L1 — Flusso principale
1. "Quali dati vengono inclusi nel report? Ci sono filtri applicabili dall'utente
   (intervallo date, categoria, entità, stato)?
   Il report riflette i dati al momento della generazione (snapshot) o è sempre live?"
   > SKIP SE: gli AC specificano il perimetro dati e il comportamento snapshot/live

2. "Il formato di output è fisso (es. solo PDF) o l'utente può scegliere (PDF/Excel/CSV)?
   Il contenuto è identico tra i formati o la struttura cambia per formato?"
   > SKIP SE: gli AC specificano formato/i e struttura per formato

### L2 — Edge case specifici Report
3. "Qual è il volume massimo atteso (righe nel CSV, pagine nel PDF)?
   Il sistema ha un limite configurato? Cosa succede se il limite viene superato
   (troncamento, errore, paginazione automatica, esportazione a batch)?"
   > SKIP SE: gli AC specificano volume massimo e comportamento su superamento

4. "I dati possono contenere caratteri speciali (virgolette, punto e virgola, newline,
   unicode, emoji) che potrebbero rompere il parsing CSV o la formattazione Excel?"
   > SKIP SE: gli AC specificano la gestione dei caratteri speciali o confermano che
   > "i dati sono sempre ASCII puro"

5. "Il report include calcoli aggregati (somme, medie, totali, percentuali)?
   I calcoli sono eseguiti lato server o delegati a Excel/browser?
   Cosa succede con valori null o zero nel denominatore?"
   > SKIP SE: gli AC specificano i calcoli con comportamento su null/zero

### L3 — Integrazioni / dipendenze
6. "La generazione è sincrona (l'utente aspetta) o asincrona (riceve notifica/link quando pronto)?
   Se asincrona, qual è il meccanismo di notifica (polling, webhook, email, push)?
   Per quanto tempo il file generato rimane disponibile per il download?"
   > SKIP SE: gli AC specificano il modello sincrono/asincrono con retention del file

### L4 — Performance generazione
7. "Qual è il tempo massimo accettabile per la generazione?
   Esiste un SLA (es. 'report pronto entro 30 secondi' o 'entro 10 minuti per export massivi')?
   È stato testato su dataset di dimensione production?"
   > SKIP SE: gli AC specificano il tempo massimo e il dataset di riferimento

---

## Feature Flag / Configuration

**Segnali di inferenza:** "feature flag", "feature toggle", "LaunchDarkly", "Unleash",
"AWS AppConfig", "canary", "rollout progressivo", "A/B test", "configurazione dinamica",
"kill switch", "abilitazione per tenant", "dark launch", "parametro di sistema"

**Confidence trigger:**
- HIGH: nome tool esplicito (LaunchDarkly, Unleash, AppConfig), oppure "feature flag" + "toggle"
- MEDIUM: "canary"/"rollout progressivo" + "configurazione", oppure "kill switch"

### L1 — Flusso principale
1. "Il flag è binario (on/off) o ha valori multipli (percentage rollout, per-tenant, per-ruolo)?
   Chi può modificare il flag in produzione?
   Esiste un audit trail delle modifiche al flag?"
   > SKIP SE: gli AC specificano il tipo di flag e i permessi di modifica

2. "Cosa vede un utente con flag OFF rispetto a uno con flag ON?
   Sono due percorsi applicativi completamente distinti o solo differenze UI?
   Il flag OFF mostra un messaggio esplicito o nasconde silenziosamente la feature?"
   > SKIP SE: gli AC descrivono il comportamento per entrambi gli stati del flag

### L2 — Edge case specifici Feature Flag
3. "Cosa succede a una sessione utente già attiva quando il flag viene modificato?
   La nuova configurazione è applicata immediatamente (hot reload),
   al prossimo refresh della pagina, o al prossimo login?"
   > SKIP SE: gli AC specificano il timing di applicazione della modifica flag

4. "Se il servizio di feature flag non è raggiungibile (timeout, outage),
   qual è il comportamento di default (fail open = feature abilitata,
   fail closed = feature disabilitata)? Il comportamento è configurabile?"
   > SKIP SE: gli AC specificano il comportamento di fallback esplicitamente

5. "Se il flag abilita una feature che scrive dati in un nuovo schema,
   cosa succede ai dati scritti se il flag viene poi disabilitato?
   Il rollback del flag è data-safe?"
   > SKIP SE: gli AC specificano la compatibilità dati tra stato ON e stato OFF

### L3 — Integrazioni / dipendenze
6. "Il flag interagisce con altri flag? Esiste una gerarchia o dipendenza tra flag
   che potrebbe creare combinazioni inattese (es. flag A ON + flag B OFF = stato non testato)?
   È documentato il dependency graph dei flag?"
   > SKIP SE: il flag è completamente isolato senza dipendenze da altri flag

### L4 — Rollout safety
7. "Il rollout progressivo ha una percentuale di rollout configurata (es. 5% → 20% → 100%)?
   Esiste un meccanismo di osservazione (metriche, error rate) che triggera il rollback automatico
   se la percentuale supera una soglia di errori?"
   > SKIP SE: gli AC specificano la strategia di rollout con soglie di rollback automatico

---

## File Processing / Async Upload

**Segnali di inferenza:** "upload file", "import file", "caricamento massivo", "bulk import",
"file processing", "chunked upload", "multipart", "presigned URL", "S3 upload",
"file validation", "file parser", "SFTP", "FTP", "file watcher", "async processing", "polling status"

**Confidence trigger:**
- HIGH: "upload"/"import" + "asincrono"/"massivo"/"file", oppure "chunked" + "upload"
- MEDIUM: "upload" o "import" senza indicatori di volume/async

### L1 — Flusso principale
1. "Il file viene caricato in un'unica richiesta HTTP o a chunk (multipart/chunked)?
   Qual è la dimensione massima supportata? Il timeout HTTP è adeguato al volume massimo
   atteso (es. file da 500MB richiedono timeout di almeno 30 minuti)?"
   > SKIP SE: gli AC specificano il metodo di upload, la dimensione massima e il timeout

2. "Quali validazioni vengono eseguite sul file (formato, dimensione, encoding, MIME type, contenuto)?
   La validazione è sincrona (prima dell'upload, lato client) o asincrona (dopo, lato server)?
   Come viene comunicato l'esito all'utente (messaggio inline, email, status polling)?"
   > SKIP SE: gli AC specificano le validazioni e il meccanismo di comunicazione esito

### L2 — Edge case specifici File Processing
3. "Cosa succede se l'upload viene interrotto a metà (connessione persa, browser chiuso, timeout)?
   Il file parziale viene scartato automaticamente?
   È possibile riprendere l'upload da dove si era interrotti (resumable upload)?"
   > SKIP SE: gli AC specificano il comportamento su interruzione e la strategia di resume

4. "Se il file contiene N righe e la riga K è malformata, il sistema:
   elabora le righe 1..K-1 e K+1..N (partial processing)?
   O rigetta l'intero file (all-or-nothing)?
   Il comportamento è configurabile per tipo di errore?"
   > SKIP SE: gli AC specificano la policy su righe malformate (partial vs all-or-nothing)

5. "Il processing è idempotente? Se lo stesso file viene caricato due volte
   (utente clicca due volte, retry automatico), il sistema crea duplicati o deduplica?
   La deduplicazione è basata su hash del file, nome file, o contenuto?"
   > SKIP SE: gli AC specificano la politica di deduplicazione con criterio esplicito

### L3 — Integrazioni / dipendenze
6. "Come l'utente monitora lo stato del processing dopo il caricamento?
   C'è una pagina di status con polling, una notifica push/email al completamento,
   o solo polling manuale? Quanto tempo può richiedere il processing in worst case?"
   > SKIP SE: gli AC specificano il meccanismo di monitoring dello stato con tempi attesi

### L4 — Performance / Storage
7. "Qual è il throughput massimo di file che possono essere in processing contemporaneamente?
   C'è un limite di concorrenza? I file processati vengono archiviati, eliminati, o spostati?
   Qual è la retention policy per i file caricati?"
   > SKIP SE: gli AC specificano la concorrenza massima e la retention policy

---

## Regola SKIP SE — Reminder

Per ogni domanda del tree, il blocco `> SKIP SE:` definisce i pattern di skip deterministici.
**Non valutare semanticamente.** Se nessun pattern è trovato letteralmente negli AC → domanda obbligatoria.
Le domande L0 (flusso trasversale) hanno i propri `> SKIP SE:` condizionati alla presenza
di struttura sequenziale negli AC (Given/When/Then multipli, elenco numerato, connettivi
sequenziali). In assenza di questi pattern sono obbligatorie — non valutare semanticamente.
