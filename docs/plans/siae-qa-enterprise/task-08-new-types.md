# Task 08 — 5 nuovi tipi applicativi [PENDING]

**File:** `skills/siae-qa/reference/question-trees.md` + `skills/siae-qa/XRAY-TEMPLATES.md`
**Dipende da:** task-07 (usa la struttura Integration split come riferimento di formato)
**Cluster:** B — Coverage enterprise

---

## Obiettivo

Aggiungere 5 nuovi tipi di requisito con question tree completi (L1/L2/L3/L4)
e i relativi segnali di inferenza nella tabella XRAY-TEMPLATES.md.

---

## Step 1 — Aggiungi i 5 nuovi tipi a question-trees.md

Leggi `skills/siae-qa/reference/question-trees.md`. Aggiungi in fondo al file:

```markdown
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
```

---

## Step 2 — Aggiorna checklist in XRAY-TEMPLATES.md

Leggi `skills/siae-qa/XRAY-TEMPLATES.md` sezione "Checklist di Verifica".

Aggiungi:
```markdown
- [ ] Se tipo è uno dei 5 nuovi (Notification/Batch/Report/Feature Flag/File Processing):
      question tree specifico del tipo usato (non tree generico FE/BE)
```

---

## Step 3 — Commit

```bash
git add skills/siae-qa/reference/question-trees.md skills/siae-qa/XRAY-TEMPLATES.md
git commit -m "feat(siae-qa): add 5 new req types (Notification, Batch, Report, FeatureFlag, FileProcessing)"
```
