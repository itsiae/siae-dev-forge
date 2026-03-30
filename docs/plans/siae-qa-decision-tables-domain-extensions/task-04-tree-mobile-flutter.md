# Task 04 — Albero Mobile/Flutter in question-trees.md

**Stato:** [PENDING]
**File:** `skills/siae-qa/reference/question-trees.md`
**Dipendenze:** nessuna

---

## Obiettivo

Aggiungere l'albero domande `Mobile / Flutter` in `question-trees.md`,
seguendo esattamente il pattern L1/L2/L3 degli alberi esistenti.

---

## Step 1 — Verifica che Mobile/Flutter non esista già

Cerca in `skills/siae-qa/reference/question-trees.md`:
```
Mobile / Flutter
```

Se trovato → il task è già applicato. Marca `[DONE]` e fermati.
Se non trovato → procedi a Step 2.

---

## Step 2 — Individua il punto di inserimento

Il file termina con l'albero `## Integration / External`.
L'ultimo testo dell'albero Integration è:
```
5. "Esiste un ambiente di staging o sandbox dell'esterno per i test?
   O si usa un mock/stub/WireMock in locale?"
```

Il nuovo albero va aggiunto **dopo** l'ultima riga del file, preceduto da `---`.

---

## Step 3 — Aggiungi l'albero Mobile/Flutter

Usa Edit per aggiungere il seguente blocco alla fine del file:

```markdown

---

## Mobile / Flutter

**Segnali di inferenza:** "Flutter", "Dart", "Riverpod", "app mobile", "iOS", "Android",
"widget", "schermata", "notifica push", "deep link", "ObjectBox", "Amplify", "offline"

### L1 — Flusso principale
1. "Questa schermata richiede permessi OS (camera, location, notifiche, contatti)?
   Cosa mostra l'app se l'utente nega il permesso al primo lancio?
   E se lo revoca successivamente dalle impostazioni del dispositivo?"
2. "La schermata ha stati di caricamento? Cosa mostra mentre aspetta dati dal backend
   (skeleton loader, spinner, empty state)?
   Cosa mostra se la chiamata al backend fallisce con errore o timeout?"

### L2 — Edge case specifici Mobile
3. "Cosa succede se l'utente manda l'app in background durante questa operazione
   (es. form non salvato, upload in corso, pagamento in elaborazione)
   e torna in foreground dopo 5+ minuti? Lo stato viene ripristinato o perso?"
4. "Il comportamento cambia se il dispositivo è offline o passa da WiFi a 4G/5G
   durante l'operazione? C'è una modalità offline supportata o si mostra un errore
   con possibilità di retry?"

### L3 — Integrazioni / dipendenze
5. "La schermata è raggiungibile tramite deep link o tap su notifica push?
   Come si comporta se l'app non è in memoria (cold start da link esterno)
   rispetto al caso in cui l'app è già aperta in foreground?"
```

---

## Step 4 — Output atteso

```
Run: grep -n "Mobile / Flutter" skills/siae-qa/reference/question-trees.md
Output atteso: una riga con "## Mobile / Flutter"
```

Se il grep trova il testo → task completato.
Aggiorna lo stato a `[DONE]` in `overview.md`.
