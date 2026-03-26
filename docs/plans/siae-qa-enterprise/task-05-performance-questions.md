# Task 05 — Domanda L4 performance/SLA in tutti i tipi [PENDING]

**File:** `skills/siae-qa/reference/question-trees.md`
**Sezione:** tutti i tipi, aggiungere sezione L4 dopo L3
**Cluster:** B — Coverage enterprise

---

## Obiettivo

Aggiungere una domanda di livello L4 (performance/SLA) a tutti i tipi di requisito.
Questa è la dimensione enterprise più critica: completamente assente da tutti i 6 tipi attuali.

---

## Step 1 — Leggi il file

Leggi `skills/siae-qa/reference/question-trees.md` intero.

---

## Step 2 — Aggiungi L4 a Frontend (FE)

Dopo la domanda L3/6 di FE (quella su API error handling), aggiungi:

```markdown
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
```

---

## Step 3 — Aggiungi L4 a Backend Microservice (BE)

Dopo la domanda L3/6 di BE, aggiungi:

```markdown
### L4 — Performance / SLA
7. "Qual è il throughput atteso su questo endpoint in condizioni normali (req/s)?
   Qual è il picco previsto (es. campagna, scadenza fiscale, batch notturno)?
   Esiste un SLA di latenza definito (es. p99 < 300ms, p95 < 200ms)?"
   > SKIP SE: gli AC specificano "nessun SLA", throughput atteso, o latenza target

8. "Questo endpoint partecipa a una catena di chiamate sincrone? Se sì, qual è il
   budget di latenza allocato a questo servizio nel contesto dell'intera chain?"
   > SKIP SE: l'endpoint è chiamato in modo isolato senza chain di servizi
```

---

## Step 4 — Aggiungi L4 a ETL / Data Pipeline

Dopo la domanda L3/6 di ETL, aggiungi:

```markdown
### L4 — SLA di completamento / Freshness
7. "Entro quanto tempo il job deve completare l'elaborazione dell'intera finestra temporale?
   Qual è l'impatto downstream se il job è in ritardo di 1h / 4h / 24h?
   I consumer del layer gold hanno SLA di freshness definiti (es. 'dati disponibili entro le 8:00')?
   > SKIP SE: gli AC specificano la finestra di completamento e/o il SLA di freshness downstream

8. "Qual è il volume massimo di record atteso per singola esecuzione?
   Il job è stato testato su dataset di dimensione production (o stimato equivalente)?"
   > SKIP SE: gli AC indicano volume atteso e confermano il test su dati rappresentativi
```

---

## Step 5 — Aggiungi L4 a Database

Dopo la domanda L3/5 di Database, aggiungi:

```markdown
### L4 — Performance migration / Zero-downtime
6. "La migration è stata stimata in termini di tempo di esecuzione su un dataset
   di dimensione production? Qual è il tempo di lock stimato su tabelle live?
   Esiste una strategia zero-downtime (expand-contract, online migration)?"
   > SKIP SE: gli AC specificano la strategia zero-downtime approvata o la finestra di manutenzione

7. "Dopo la migration, le query esistenti (incluse quelle del codice applicativo in produzione)
   mantengono le stesse performance? Sono stati analizzati i piani di esecuzione delle query critiche?"
   > SKIP SE: la migration è puramente additive (aggiunge colonne nullable) senza impatto sulle query
```

---

## Step 6 — Aggiungi L4 a Auth / Security

Dopo la domanda L3/5 di Auth, aggiungi:

```markdown
### L4 — Rate limiting / Security SLA
6. "L'endpoint di autenticazione è soggetto a rate limiting per prevenire
   brute force e credential stuffing? Qual è la soglia (es. max 5 tentativi/min per IP)?
   Cosa restituisce il sistema quando la soglia è superata (429 + Retry-After)?"
   > SKIP SE: gli AC specificano il rate limiting con soglia e comportamento

7. "Questa feature espande la superficie di attacco (nuovi endpoint pubblici,
   nuovi dati sensibili esposti)? È inclusa nello scope del prossimo DAST / penetration test?"
   > SKIP SE: la feature non espone nuovi endpoint pubblici e non introduce nuovi dati sensibili
```

---

## Step 7 — Aggiungi nota introduttiva al file

All'inizio del file, dopo la riga "Ogni albero è strutturato su 3 livelli:", sostituisci con:

```markdown
Ogni albero è strutturato su 4 livelli:
- **L1 — Flusso principale:** verifica/completa la comprensione del happy path
- **L2 — Edge case specifici del tipo:** scenari limite propri di quel dominio
- **L3 — Integrazioni / dipendenze:** chi chiama? cosa chiama? dipendenze esterne?
- **L4 — Performance / SLA:** throughput, latenza, freshness, zero-downtime
```

---

## Step 8 — Commit

```bash
git add skills/siae-qa/reference/question-trees.md
git commit -m "feat(siae-qa): add L4 performance/SLA questions to all existing types"
```
