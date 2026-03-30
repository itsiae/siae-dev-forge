# Task 06 — Albero Event-driven/Async in question-trees.md

**Stato:** [PENDING]
**File:** `skills/siae-qa/reference/question-trees.md`
**Dipendenze:** Task 05 completato (stesso file — va in sequenza)

---

## Obiettivo

Aggiungere l'albero domande `Event-driven / Async` in `question-trees.md`,
dopo l'albero `IaC / Terraform` aggiunto dal Task 05.

---

## Step 1 — Verifica che Event-driven non esista già

Cerca in `skills/siae-qa/reference/question-trees.md`:
```
Event-driven / Async
```

Se trovato → il task è già applicato. Marca `[DONE]` e fermati.
Se non trovato → procedi a Step 2.

---

## Step 2 — Verifica che Task 05 sia completato

Cerca in `skills/siae-qa/reference/question-trees.md`:
```
IaC / Terraform
```

Se NON trovato → Task 05 non è ancora completato. Blocca con `[BLOCKED]`.

---

## Step 3 — Aggiungi l'albero Event-driven/Async

Usa Edit per aggiungere il seguente blocco alla fine del file:

```markdown

---

## Event-driven / Async

**Segnali di inferenza:** "Kafka", "SQS", "SNS", "consumer", "producer", "evento",
"coda", "DLQ", "dead letter", "Step Functions", "async", "messaggio", "topic",
"subscription", "EventBridge", "stream", "broker"

### L1 — Flusso principale
1. "Il consumer è idempotente? Se lo stesso messaggio arriva due volte
   (at-least-once delivery di Kafka/SQS), il sistema produce effetti doppi
   o li deduplica? Qual è la chiave di deduplication usata
   (es. message ID, correlation ID, campo business univoco)?"
2. "Qual è il comportamento atteso in caso di elaborazione riuscita?
   Il messaggio viene ACKato / eliminato dalla coda automaticamente?
   Viene prodotto un evento downstream? Viene aggiornato lo stato nel DB?"

### L2 — Edge case specifici Event-driven
3. "Cosa finisce in Dead Letter Queue (DLQ)?
   Dopo quanti retry falliti il messaggio viene mandato in DLQ?
   Chi monitora la DLQ (CloudWatch alarm, dashboard) e con quale procedura
   di recovery (reprocess manuale, script automatico, alert al team)?"
4. "Il comportamento è corretto se i messaggi arrivano out-of-order?
   Il consumer assume un ordinamento implicito sugli eventi
   (es. UPDATE prima di INSERT)?
   Cosa succede se arriva prima un evento di aggiornamento di un record
   che non esiste ancora?"

### L3 — Integrazioni / dipendenze
5. "Esiste un ambiente di test con il broker reale (Kafka cluster dedicato,
   SQS in account non-prod) o si usa un mock (LocalStack, Testcontainers,
   embedded Kafka)?
   I test di integrazione girano su infrastruttura dedicata isolata
   o su broker condiviso con altri team?"
```

---

## Step 4 — Output atteso

```
Run: grep -n "Event-driven / Async" skills/siae-qa/reference/question-trees.md
Output atteso: una riga con "## Event-driven / Async"
```

Se il grep trova il testo → task completato.
Aggiorna lo stato a `[DONE]` in `overview.md`.
