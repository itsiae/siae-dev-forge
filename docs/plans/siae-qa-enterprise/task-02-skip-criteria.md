# Task 02 — Skip-criteria espliciti per ogni domanda del tree [PENDING]

**File:** `skills/siae-qa/reference/question-trees.md`
**Sezione:** tutte le domande di tutti i tipi
**Cluster:** A — Determinismo

---

## Obiettivo

Per ogni domanda del question tree, aggiungere un blocco `> SKIP SE:` con pattern espliciti
(keyword o frasi) che devono essere presenti testualmente negli AC/description per qualificare
lo skip automatico. Se nessun pattern è trovato, la domanda è obbligatoria — senza giudizio LLM.

---

## Step 1 — Leggi il file corrente

Leggi `skills/siae-qa/reference/question-trees.md` intero.

---

## Step 2 — Sostituisci l'intera sezione introduttiva

Dopo la riga `Claude fa UNA domanda alla volta.` e prima di `---`, aggiungi:

```markdown
**SKIP-CRITERIA — Regola obbligatoria:**
Per ogni domanda è definito un blocco `> SKIP SE:` con keyword esplicite.
Una domanda si salta SOLO se almeno uno dei pattern indicati è presente testualmente
negli AC, description, o commenti della story. NON valutare semanticamente.
Se il pattern non è trovato letteralmente → la domanda è obbligatoria.
```

---

## Step 3 — Aggiungi SKIP SE per ogni domanda Frontend (FE)

Per ogni domanda L1/L2/L3, aggiungi il blocco skip-criteria DOPO il testo della domanda.

```markdown
### L1 — Flusso principale
1. "Il form/componente ha stati di caricamento (loading/skeleton)?
   Cosa mostra all'utente mentre aspetta i dati dall'API?"
   > SKIP SE: gli AC contengono "loading", "skeleton", "spinner", "stato di caricamento",
   > "mentre aspetta", "indicatore di progresso"

2. "Quali campi sono obbligatori? Ci sono campi con formato specifico
   (email, IBAN, data, codice fiscale) che richiedono validazione?"
   > SKIP SE: gli AC elencano esplicitamente i campi obbligatori con il loro formato
   > (es. "campo X è obbligatorio", "formato YYYY-MM-DD", "validazione email")

### L2 — Edge case specifici FE
3. "Cosa mostra la pagina se la lista di dati è vuota?
   C'è un empty state dedicato o si nasconde il componente?"
   > SKIP SE: gli AC contengono "lista vuota", "empty state", "nessun risultato",
   > "stato vuoto", "messaggio quando non ci sono"

4. "La feature deve funzionare su mobile? Ci sono breakpoint critici
   (es. < 768px) dove il layout cambia significativamente?"
   > SKIP SE: gli AC specificano breakpoint o dicono esplicitamente "solo desktop",
   > "non richiesta versione mobile", oppure "responsive: no"

5. "Cosa succede se l'utente naviga via durante un'operazione in corso
   (upload in corso, form non salvato)? C'è una guardia di navigazione?"
   > SKIP SE: gli AC menzionano "guardia di navigazione", "beforeRouteLeave",
   > "conferma prima di uscire", "dati non salvati", "dialog di conferma navigazione"

### L3 — Integrazioni / dipendenze
6. "Da quale API recupera i dati? Cosa mostra se l'API risponde
   con errore 500 o timeout? C'è un messaggio di errore dedicato?"
   > SKIP SE: gli AC specificano il comportamento su errore API con messaggio esplicito
   > (es. "in caso di errore mostra 'Servizio non disponibile'")
```

---

## Step 4 — Aggiungi SKIP SE per ogni domanda Backend Microservice (BE)

```markdown
### L1 — Flusso principale
1. "Quali metodi HTTP espone questo endpoint? Quali status code restituisce
   per il caso di successo e per ogni caso di errore previsto?"
   > SKIP SE: gli AC elencano esplicitamente metodi HTTP e status code
   > (es. "POST /api/v1/...", "restituisce 201 in caso di successo", "404 se non trovato")

2. "Quali campi del payload sono obbligatori?
   Ci sono vincoli di formato o range (es. importo > 0, ISRC pattern)?"
   > SKIP SE: gli AC elencano esplicitamente campi obbligatori con vincoli
   > (es. "campo amount è obbligatorio e deve essere > 0")

### L2 — Edge case specifici BE
3. "L'operazione è idempotente? Cosa succede se viene chiamata due volte
   con lo stesso payload (es. doppio click, retry automatico del client)?"
   > SKIP SE: gli AC contengono "idempotente", "idempotency", "stesso risultato se ripetuto",
   > "HTTP PUT sicuro da ripetere", "retry-safe"

4. "Ci sono regole business che bloccano l'operazione?
   (es. stato record incompatibile, quota superata, record già esistente)"
   > SKIP SE: gli AC elencano esplicitamente le condizioni di blocco con comportamento atteso
   > (es. "se il record è in stato LOCKED restituisce 409")

5. "Come gestisce una dipendenza esterna assente o lenta?
   C'è circuit breaker, timeout configurato o retry con backoff?"
   > SKIP SE: gli AC menzionano "circuit breaker", "timeout", "retry", "fallback",
   > "comportamento in caso di indisponibilità del servizio X"

### L3 — Integrazioni / dipendenze
6. "Chi chiama questo endpoint (client FE, altro microservizio, scheduler)?
   Il contratto API è già definito in un file OpenAPI/Swagger?"
   > SKIP SE: gli AC indicano esplicitamente il caller (es. "chiamato dal frontend",
   > "invocato da scheduler ogni ora") o menzionano un file OpenAPI esistente
```

---

## Step 5 — Aggiungi SKIP SE per ETL / Data Pipeline

```markdown
### L1 — Flusso principale
1. "Qual è la trasformazione principale?
   Da quale layer (bronze/silver/gold) parte e quale layer produce?"
   > SKIP SE: gli AC specificano esplicitamente il layer sorgente e target
   > (es. "legge da bronze e scrive su silver", "trasforma da raw a curated")

2. "Qual è la chiave di deduplicazione dei record?
   Come vengono gestiti i duplicati (drop, keep-first, keep-last, merge)?"
   > SKIP SE: gli AC specificano la chiave di deduplicazione e la policy
   > (es. "deduplica per id + timestamp, tieni l'ultimo")

### L2 — Edge case specifici ETL
3. "Cosa succede con record nulli o malformati nella sorgente?
   Vengono scartati (drop), messi in quarantena (dead-letter) o il job fallisce?"
   > SKIP SE: gli AC specificano la policy su record invalidi
   > (es. "i record con campo X null vengono scartati", "dead-letter queue per anomalie")

4. "Il job è idempotente? Se viene rieseguito sullo stesso intervallo temporale,
   sovrascrive i dati o li duplica?"
   > SKIP SE: gli AC contengono "idempotente", "rieseguibile", "sovrascrive",
   > "overwrite mode", "non duplica se rieseguito"

5. "C'è un volume soglia (es. 0 record letti, > N record anomali)
   oltre il quale il job deve fallire o generare un alert?"
   > SKIP SE: gli AC specificano soglie numeriche esplicite
   > (es. "se meno di 100 record → fallisce", "alert se error rate > 5%")

### L3 — Integrazioni / dipendenze
6. "Il job dipende da job o layer upstream? Come si comporta se upstream
   non ha prodotto dati per questa finestra temporale?"
   > SKIP SE: gli AC specificano il comportamento su dati upstream assenti
   > (es. "se il layer bronze non ha dati → skip silenzioso", "attende fino a 2h")
```

---

## Step 6 — Aggiungi SKIP SE per Database

```markdown
### L1 — Flusso principale
1. "La migration è reversibile? Esiste (o va creato) uno script di rollback
   testato che riporta allo stato precedente?"
   > SKIP SE: gli AC menzionano esplicitamente lo script di rollback o indicano
   > "migration irreversibile — approvata da DBA"

2. "La migration modifica dati esistenti (UPDATE/DELETE su righe)
   o solo struttura (DDL puro senza toccare dati)?"
   > SKIP SE: gli AC specificano esplicitamente il tipo di modifica
   > (es. "solo DDL — nessun dato modificato", "UPDATE su tutte le righe della tabella X")

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
   > SKIP SE: gli AC specificano la strategia di deploy coordinato
   > (es. "expand-contract", "backward compatible", "deploy atomico schema + applicativo")
```

---

## Step 7 — Aggiungi SKIP SE per Auth / Security

```markdown
### L1 — Flusso principale
1. "Quali ruoli/profili possono eseguire questa operazione?
   Chi NON deve poterla eseguire? Il blocco è silenzioso (403) o con messaggio?"
   > SKIP SE: gli AC elencano esplicitamente i ruoli abilitati e il comportamento su accesso negato

2. "Il token di autenticazione ha un TTL?
   Cosa succede se scade durante una sessione attiva?"
   > SKIP SE: gli AC specificano il TTL e il comportamento a scadenza
   > (es. "token scade dopo 1h — redirect al login", "silent refresh")

### L2 — Edge case specifici Auth
3. "Un utente può agire su risorse di un altro utente?
   C'è isolamento per tenant, organizzazione o codice autore?"
   > SKIP SE: gli AC specificano esplicitamente l'isolamento tenant o dicono
   > "ogni utente vede solo le proprie risorse"

4. "L'endpoint è soggetto a rate limiting?
   Cosa restituisce il sistema quando la soglia viene superata?"
   > SKIP SE: gli AC specificano rate limit e comportamento su superamento soglia
   > (es. "max 100 req/min — restituisce 429 con Retry-After")

### L3 — Integrazioni / dipendenze
5. "Le azioni di questo tipo vengono registrate in un log di audit?
   Chi ha fatto cosa, quando, da quale IP?"
   > SKIP SE: gli AC menzionano audit log, tracciabilità, o specificano che
   > "l'operazione non richiede tracciamento"
```

---

## Step 8 — Aggiungi SKIP SE per Integration REST / Sync e Integration Event / Async

(Le domande specifiche per questi due tipi saranno definite in task-07-integration-split.md.
Aggiungere i blocchi SKIP SE contestualmente alla creazione delle domande in quel task.)

---

## Step 9 — Aggiungi nota finale

Alla fine del file, aggiungi:

```markdown
---

## Regola SKIP SE — Reminder

Per ogni domanda del tree, il blocco `> SKIP SE:` definisce i pattern di skip deterministici.
**Non valutare semanticamente.** Se nessun pattern è trovato letteralmente negli AC → domanda obbligatoria.
Le domande L0 (flusso trasversale) non hanno skip-criteria: sono sempre obbligatorie se non c'è
struttura sequenziale esplicita negli AC.
```

---

## Step 10 — Commit

```bash
git add skills/siae-qa/reference/question-trees.md
git commit -m "feat(siae-qa): add explicit skip-criteria to every question tree entry"
```
