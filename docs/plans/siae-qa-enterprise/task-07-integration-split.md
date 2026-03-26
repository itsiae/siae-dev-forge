# Task 07 — Split Integration → REST/Sync + Event/Async [PENDING]

**File:** `skills/siae-qa/reference/question-trees.md` + `skills/siae-qa/XRAY-TEMPLATES.md`
**Sezione:** tree "Integration / External" → diviso in 2 tipi distinti
**Cluster:** B — Coverage enterprise

---

## Obiettivo

Dividere il tipo monolitico "Integration / External" in due tipi specializzati:
- **Integration REST / Sync**: chiamate HTTP/gRPC verso servizi esterni
- **Integration Event / Async**: messaggistica asincrona (Kafka, SQS, SNS, EventBridge)

---

## Step 1 — Leggi il tree corrente

Leggi `skills/siae-qa/reference/question-trees.md` sezione `## Integration / External`.

---

## Step 2 — Sostituisci il tree monolitico con i due specializzati

**RIMUOVI** tutta la sezione `## Integration / External` e **SOSTITUISCI** con:

```markdown
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
```

---

## Step 3 — Aggiorna XRAY-TEMPLATES.md sezione segnali

Il task-01 ha già aggiornato la tabella segnali con la divisione.
Verifica che i due tipi siano presenti nella tabella. Se task-01 non è stato eseguito,
aggiornare la tabella manualmente (vedi task-01 per il contenuto esatto).

---

## Step 4 — Aggiorna SKILL.md sezione Phase 0

Leggi `skills/siae-qa/SKILL.md` sezione `### 0a — Inferisci il tipo`.

Aggiungi nota sulla divisione Integration:

```markdown
**Nota Integration split:** se la story ha segnali di "Integration REST/Sync"
e "Integration Event/Async" contemporaneamente, assegna il tipo primario al paradigma
dominante nel testo della story, e registra l'altro come tag secondario.
Esempi: "chiama API esterna e pubblica evento Kafka" → PRIMARY: REST, SECONDARY: [Event]
        "consumer Kafka che chiama API di conferma" → PRIMARY: Event, SECONDARY: [REST]
```

---

## Step 5 — Commit

```bash
git add skills/siae-qa/reference/question-trees.md skills/siae-qa/SKILL.md
git commit -m "feat(siae-qa): split Integration type into REST/Sync and Event/Async with specialized trees"
```
