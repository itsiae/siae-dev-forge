# M2 — State Machine & Business Logic Bug Detector

## Albero Decisionale Validazione

```
Il ramo non gestito è raggiungibile da input utente?
  NO → skip (dead code)
  SÌ → Il risultato è visibile (crash / dato errato / blocco)?
         SÌ crash/exception       → CRITICAL
         SÌ dato errato (no crash) → HIGH
         SÌ side-effect silente   → MEDIUM
         NO (solo interno)        → skip
```

---

## S1 — Enum/Costanti senza Exhaustive Match

**Grep:**
```
Java:       switch\s*\(.*[sS]tatus\|switch\s*\(.*[sS]tate
TypeScript: switch\s*\(.*[sS]tate\|switch\s*\(.*[sS]tatus
Python:     match\s+.*:\s*\n.*case\s
```

**Validazione (CONFERMATO se):**
1. Estrai tutti i valori dell'enum/costante definiti nel progetto
2. Estrai tutti i `case` presenti nello switch/if-chain
3. Diff: se un valore enum manca dai case E non c'è `default` che lo gestisce correttamente
4. E il valore mancante è impostabile da un'azione utente o API → **BUG**

**Falsificatori:** `default` case con comportamento corretto, valore mai impostato nella codebase.

**Trigger utente:** Admin/API porta l'entità nello stato non gestito → UI non mostra nulla o crasha.

---

## S2 — Transizioni di Stato senza Guard

**Grep:**
```
Java:       (set|update)Status\s*\(|this\.state\s*=\s*
TypeScript: \.status\s*=\s*['"]\|setState\(\|\.state\s*=\s*
Python:     self\.state\s*=\s*\|self\._status\s*=
```

**Validazione (CONFERMATO se):**
1. Metodo che cambia stato (es. `completePayment()`)
2. Nessun check dello stato corrente prima della transizione
3. Esiste almeno uno stato invalido da cui la transizione è chiamabile

**Falsificatori:** `@Secured`, `@PreAuthorize`, guard delegato al caller con contratto, DB constraint.

**Trigger utente:** Doppio-click su "Conferma", refresh della pagina, replay di una request vecchia.

---

## S3 — Operazione Critica senza Precondition Check

**Grep (operazioni critiche):**
```
Java:       (delete|remove|send|charge|publish|finalize|archive)\s*\(
TypeScript: (delete|remove|send|charge|publish|archive)\s*\(
Python:     (delete|remove|send|charge|publish|archive)\s*\(
```

**Validazione (CONFERMATO se):**
1. Metodo esegue operazione irreversibile (delete, send, charge)
2. Non c'è check dello stato corrente nel blocco di apertura del metodo — ovvero: nessun guard prima del primo statement non-dichiarativo (assegnazioni, return, throw, chiamate). Guard equivalenti validi: check su stato/status entity, `@PreAuthorize`, `if (entity.status != X)`, `Objects.requireNonNull`. Se il guard è presente ovunque **prima della prima operazione critica** → falsificato.
3. L'endpoint che chiama questo metodo è raggiungibile dall'utente

**Falsificatori:** `@PreAuthorize`, guard sullo stato dell'entità prima dell'operazione critica (indipendentemente dalla riga), soft-delete.

**Trigger utente:** Admin cancella risorsa PUBLISHED → risorsa scompare per i clienti senza avviso.

---

## S4 — If Incompleto con Side Effect Critico

**Grep:**
```
if\s*\(\s*.*status.*==\|if\s*\(\s*.*state.*==
```
Poi verifica: il blocco `if` è seguito da codice critico (save/update/delete/send) SENZA `else`.

**Validazione (CONFERMATO se):**
1. `if (condition) { ... }` senza `else`
2. Immediatamente dopo il `if`, c'è `save()` / `send()` / `update()` eseguito sempre
3. Quando la condizione è falsa, il side effect avviene comunque in modo non inteso

**Falsificatori:** il codice dopo il `if` è intenzionalmente eseguito in tutti i casi (documentato).

**Trigger utente:** Submit di un form con stato non approvato → record salvato comunque nel DB.

---

## B1 — Divisione per Zero

**Grep:**
```
Java:       \s/\s[^/]|\.divide\(|quotient\s*=
TypeScript: \s/\s[^/]|Math\.floor\s*\(.*\/
Python:     \s/\s[^0-9/]|\/\/\s*[^/]
```

**Validazione (CONFERMATO se):**
1. Il denominatore proviene da: `collection.size()` / `array.length` / input utente
2. Nessun guard `if (denominator === 0)` o `if (list.isEmpty())` prima della divisione
3. Il risultato è usato in output visibile (report, prezzo, contatore)

**Falsificatori:** costante hardcoded, valore sempre > 0 per natura business (es. `100%`).

**Trigger utente:** Applica filtri che restituiscono 0 risultati → report crasha con ArithmeticException.

---

## B2 — Date Comparison senza Timezone

**Grep:**
```
Java:       LocalDateTime\.parse\(|LocalDate\.now\(\)\|LocalDateTime\.now\(\)
TypeScript: new Date\(.*\)\s*[<>]|Date\.now\(\)\s*[<>]|\\.getTime\(\)
Python:     datetime\.now\(\)\s*[<>]|strptime.*\s*[<>]
```

**Validazione (CONFERMATO se):**
1. Due date confrontate provengono da sorgenti con timezone diversa (user input vs server now())
2. Nessuna normalizzazione a UTC prima del confronto (`ZonedDateTime`, `moment.tz`, `pytz`)
3. Il confronto determina un'azione business critica (deadline, pagamento, scadenza)

**Falsificatori:** entrambe le date costruite dallo stesso `Instant.now()` UTC, timestamp in ms.

**Trigger utente:** Utente in CET submette deadline "18:00" → server UTC valuta come 16:00 → scadenza 2h prima.

---

## B3 — Float/Double per Importi Finanziari

**Grep:**
```
Java:       double\s+\w*(price|amount|total|fee|cost)\|float\s+\w*(price|amount|total)
TypeScript: :\s*number.*price\|const\s+(price|amount|total)\s*=\s*[0-9]+\.[0-9]
Python:     (price|amount|total|fee)\s*=\s*float\|[0-9]+\.[0-9]+.*\*\s*(price|amount)
```

**STEP ZERO — Classificazione dominio (OBBLIGATORIO, eseguire in ordine):**

**Step Z1 — Verifica classe contenitrice (priorità massima):**
Se la classe/servizio di appartenenza contiene uno dei seguenti → **CONFERMATO finanziario** → procedi alla validazione:
```
BigDecimal | MonetaryAmount | Money | Wallet | Invoice | Payment | Billing | Ledger
Order | Cart | Checkout | Pricing | Tariff | Fee | Tax | Refund | Subscription
```
Se la classe/servizio contiene uno dei seguenti → **SCARTA** (dominio non-finanziario):
```
Geo | Location | Map | Coordinate | Physics | Sensor | Analytics | Metric | Report
Statistics | Dashboard | Chart | Graph | Telemetry | Monitoring
```

**Step Z2 — Verifica nome variabile (solo se Z1 è ambiguo):**
Scarta se il nome variabile/campo/metodo contiene (match esatto della parola, non substring):
```
lat | lon | latitude | longitude | coordinate | angle | bearing | heading
radius | distance | temperature | altitude | elevation | percentage | ratio
weight | score | rating | probability | sensor | metric | coefficient
```
Attenzione: `priceLatency` contiene `lat` ma è finanziario → in caso di conflitto tra Z1 e Z2, Z1 ha priorità.

**Step Z3 — Caso ambiguo residuo:**
Se dopo Z1 e Z2 il dominio è ancora ambiguo → classifica come **SUSPECT** (non CONFIRMED).
Non riportare mai CONFIRMED per B3 su sola base del nome variabile senza verifica della classe.

**Validazione (CONFERMATO se — dopo le esclusioni):**
1. Variabile per importo dichiarata come `double`/`float`/`number`
2. Usata in operazioni aritmetiche (+, -, *, /)
3. Risultato presentato all'utente o salvato in DB senza arrotondamento esplicito

**Falsificatori:** `BigDecimal` (Java), `Decimal` (Python), centesimi interi (long/int),
`Math.round(x * 100) / 100` con precisione costante, `Intl.NumberFormat`.

**Trigger utente:** Sconto del 10% su 1.000 articoli → errore centesimale nel totale fattura.

---

## B4 — .find() / Optional.get() senza Null-Check

**Grep:**
```
Java:       \.findFirst\(\)\.get\(\)\|Optional\.get\(\)\|\.orElse\(null\)\.
TypeScript: \.find\(.*\)\.(name\|id\|value\|[a-z])\|\.find\(.*\)\?\.[^?]
Python:     next\(.*filter\(.*\)\)\s*\.\|list\(filter\(.*\)\)\[0\]
```

**Validazione (CONFERMATO se):**
1. Risultato di `.find()` / `Optional.get()` acceduto senza null-check
2. La collezione su cui si fa find può restituire 0 risultati con input reale
3. L'accesso al campo avviene sulla riga immediatamente successiva senza guard

**Falsificatori:** `.orElseThrow()`, `if (result.isPresent())`, `?.` optional chain, `findById()` con `@NotNull` garantito.

**Trigger utente:** Ricerca per ID inesistente → NullPointerException / TypeError "Cannot read property of undefined".

---

## B5 — Off-by-One Inconsistente

**Grep:**
Cerca la stessa variabile (es. `age`, `count`, `page`) confrontata con `>` in un posto
e `>=` in un altro, su rami di codice che controllano la stessa risorsa.

**Validazione (CONFERMATO se):**
1. Stessa variabile con `>N` in un contesto e `>=N` in un altro
2. Entrambi i contesti governano accesso alla stessa funzionalità
3. Il boundary è un requisito business preciso (maggiore età, limite piano, soglia)

**Falsificatori:** i due controlli governano aspetti diversi intenzionalmente documentati.

**Trigger utente:** Utente di esattamente 18 anni vede il prodotto ma non può acquistarlo (o viceversa).

---

## B6 — Operazione su Lista Vuota senza Guard

**Grep:**
```
Java:       list\.get\(0\)\|list\.stream\(\)\.findFirst\(\)\.get\(\)
TypeScript: \[0\]\.|\[0\]\?\.?[a-z]\|\.at\(0\)\.
Python:     \[0\]\.[a-z]\|\[0\]\['
```

**Validazione (CONFERMATO se):**
1. Accesso all'indice 0 di una lista
2. La lista proviene da `.filter()`, `WHERE` query, o `stream().filter()`
3. Nessun guard equivalente nello stesso blocco sintattico che contiene l'accesso. Guard equivalenti: `isEmpty()`, `size() == 0`, `length === 0`, `length < 1`, `list == null`, `.isPresent()`. Guard nel blocco padre (scope che wrappa l'accesso) → falsificato. Non contare le righe: conta il blocco `{}` che contiene l'accesso.

**Falsificatori:** lista costruita con elementi hardcoded, `Optional.of()` con elemento garantito, guard equivalente nel blocco sintattico corrente o padre.

**Trigger utente:** Applica filtri avanzati → nessun risultato → `IndexOutOfBoundsException` / `TypeError`.
