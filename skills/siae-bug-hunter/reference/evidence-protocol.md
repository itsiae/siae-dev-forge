# V6 — Evidence & Determinism Protocol

## Principio Assoluto

```
UN BUG SENZA EVIDENZA NEL CODICE NON È UN BUG. È UN'ALLUCINAZIONE.
Nessuna inferenza probabilistica. Nessun "potrebbe". Solo codice letto.
```

---

## Three-Condition Gate

Ogni candidato bug deve superare TUTTE e 3 le condizioni per essere riportato.

### Condition A — Citation (Localizzazione)

```
✅ VALIDO:   File: src/api/UserService.ts, Riga 42
             Codice: response.data.user.name (senza null-check)
❌ INVALIDO: "UserService potrebbe avere un null pointer"
❌ INVALIDO: "C'è un rischio di null reference in questa area"
```

**Formato minimo:**
- File: path relativo al progetto
- Riga: numero esatto
- Codice: almeno 5 caratteri letterali dal file

### Condition B — Literal Pattern (Evidenza Testuale)

```
✅ VALIDO:   "riga 42: accesso diretto a response.data.user.name
             senza optional chain, response tipizzato any"
✅ VALIDO:   "riga 42: variabile price dichiarata come double,
             usata in operazione aritmetica a riga 45"
❌ INVALIDO: "il codice non controlla i null"
❌ INVALIDO: "manca gestione degli errori"
```

**Test di validità:** La descrizione è specifica di questo file e questa riga?
Se potrebbe essere scritta uguale per 100 codebase diversi → troppo generica → SUSPECT.

### Condition C — Reachable Path (Tracciabilità Utente)

```
✅ VALIDO:   "Percorso: GET /api/users/{id} → UserController.getUser()
             → UserService.getProfile() → riga 42 → crash su name=null"
✅ VALIDO:   "Raggiungibile da: form Submit → POST /api/orders
             → OrderService.create() → riga 88 → divisione per zero"
❌ INVALIDO: "Il bug esiste nel codice"
❌ INVALIDO: "Se qualcuno chiama questa funzione, potrebbe crashare"
```

**Domande di validazione per C:**
- Chi/cosa chiama questa funzione? (endpoint HTTP, scheduled job, event handler)
- Quale input specifico triggera il percorso buggy?
- Il percorso passa per dead code? (se sì → scarta)

---

## Scala di Confidenza (3 livelli)

### CONFIRMED ⚫
Tutte le 3 condizioni + tutti i falsificatori falliti + input specifico noto.

**Criteri:**
- A + B + C tutte verificate direttamente nel codice
- Almeno un input specifico che triggera il bug è identificabile
- Nessuno dei 7 falsificatori protegge questo percorso

**Posizione nel report:** Lista principale, ordinata per severità.

---

### PROBABLE 🟡
Condizioni A + B presenti. C determinata con l'algoritmo seguente:

**Algoritmo Condition C — 3 livelli (stop al primo che si applica):**

```
Livello 1 — CONFIRMED (C soddisfatta):
  La call chain verso un endpoint HTTP pubblico è tracciabile in ≤ 3 livelli di indirezione
  nel codice sorgente (grep del nome funzione nel codice non-test).
  **Definizione di "livello":** una singola invocazione di metodo leggibile nel codice sorgente
  non-test, tra il controller HTTP (annotato @RequestMapping/@GetMapping/app.get()/router.get()
  o equivalente) e la riga target. Esclusi dal conteggio: costruttori, iniezioni di dipendenza
  (@Autowired, constructor injection), chiamate a getter/setter senza logica.
  Esempio: controller → service → utility:riga → 2 livelli → CONFIRMED

Livello 2 — PROBABLE (C inferita):
  (a) La funzione ha visibilità public/protected E
  (b) Esiste almeno UNA chiamata nel codice sorgente non-test (grep del nome funzione) E
  (c) La call chain verso un endpoint HTTP supera 3 livelli OPPURE non è direttamente tracciabile
  → PROBABLE

Livello 3 — SUSPECT (C non verificabile):
  La funzione è public ma NESSUNA chiamata è trovata nel codice sorgente (escluso test/)
  OPPURE la funzione è private/package-private senza caller tracciabile
  → SUSPECT (solo appendice, non contare nel riepilogo)
```

**Criteri aggiuntivi:**
- Non si ha l'input specifico che triggera il percorso con certezza
- Falsificatore F4 (try-catch) presente ma contenimento parziale

**Posizione nel report:** Sezione separata "Bugs Probabili", con etichetta `[PROBABLE]`.
**Nota:** richiedere conferma con test manuale prima di aprire issue.

---

### SUSPECT 🔴
Solo Condition A presente. Pattern ambiguo, potrebbero esserci protezioni non visibili.

**Criteri:**
- Riga citata ma il contesto non è sufficiente per escludere protezioni a monte
- Es: "riga 42 contiene `.name`, potrebbe essere null — ma non ho letto il caller"

**Posizione nel report:** SOLO appendice "Sospetti — Review Manuale".
**Non contare come bug nel riepilogo.**

---

## 7 Falsificatori — Sequenza Obbligatoria

**Applica i falsificatori IN SEQUENZA. Fermati al primo che regge.**
Non applicarli tutti in parallelo: il primo che falsifica chiude il candidato.

```
F1 → F2 → F3 → F4 → F5 → F6 → F7 → Nessuno regge → CONFIRMED
```

### F1 — Optional Chain / Null Guard / Safe Access a Monte
```typescript
// TS — FALSIFICATO
const name = response?.data?.user?.name;

// Java — FALSIFICATO (tutti i seguenti)
optional.orElseThrow(() -> new EntityNotFoundException(...));
optional.orElseGet(() -> defaultUser);
optional.orElse(User.ANONYMOUS);
optional.ifPresent(u -> process(u));
```
Optional chaining `?.`, `orElseThrow()`, `orElseGet()`, `orElse(nonNull)`, `ifPresent()` → scarta.

### F2 — Type System Garantisce Non-Nullability
```typescript
// TypeScript strict mode
const user: NonNullable<UserType> = getUser();  // tipo garantisce non-null
const name = user.name;  // ← safe per type contract
```
`NonNullable<T>`, Kotlin `!!` con certezza, `@NonNull` Lombok con costruttore → scarta.

### F3 — Runtime Guard Esplicito
```java
if (response.getData() != null && response.getData().getUser() != null) {
    String name = response.getData().getUser().getName();  // protected
}
```
Guard esplicito prima dell'accesso → scarta.

### F4 — Try-Catch che Contiene il Danno
```typescript
try {
    const name = response.data.user.name;  // riga 42
} catch (e) {
    logger.error("handled gracefully");
    return fallback;
}
```
Il crash è contenuto e il fallback è ragionevole → **declassa a PROBABLE** (non scarta:
il try-catch nasconde il bug ma non lo risolve; l'utente potrebbe vedere il fallback errato).

### F5 — Dead Code / Feature Flag Always-False
```typescript
if (LEGACY_PATH_ENABLED) {  // sempre false in prod
    const name = response.data.user.name;  // riga 42
}
```
Se il feature flag è sempre false in produzione → scarta. Richiede verifica del valore del flag.

### F6 — Type Narrowing / Type Guard
```typescript
if (typeof user === 'object' && user !== null) {
    const name = user.name;  // riga 42 — protetto
}
```
Type guard esplicito prima dell'accesso → scarta.

### F7 — Exception Re-throw dopo Log
```java
} catch (Exception e) {
    logger.error("Failed", e);
    throw e;           // ← re-throw: l'eccezione sale al @ControllerAdvice
}
```
Se `throw e` o `throw new ...` è **l'unico statement non-log** nel blocco catch
(tutto il contenuto tra `{` e `}` di questo catch specifico, escluse righe di `logger.*` o `log.*`)
→ l'eccezione è propagata correttamente al caller/handler globale → scarta.

---

## Processo di Validazione Completo

```
CANDIDATO da M1-M5
       │
       ▼
  [A] File:riga citato?
  NO  → SCARTATO
  SÌ  ↓
       ▼
  [B] Pattern descritto testualmente?
  NO  → SUSPECT (solo appendice)
  SÌ  ↓
       ▼
  [C] Percorso utente tracciabile?
  NO  → SUSPECT (solo appendice)
  SÌ  ↓
       ▼
  SEQUENZA FALSIFICATORI (fermarsi al primo che regge):
  F1 (optional/safe access)    → SCARTATO
  F2 (type system non-null)    → SCARTATO
  F3 (runtime guard esplicito) → SCARTATO
  F4 (try-catch con fallback)  → PROBABLE
  F5 (dead code/flag false)    → SCARTATO
  F6 (type narrowing)          → SCARTATO
  F7 (exception re-throw)      → SCARTATO
  Nessuno regge                → CONFIRMED
```

**Regola di dubbio:** se un falsificatore è applicabile ma il suo valore è incerto
(es. feature flag il cui valore non è nel codice sorgente) → non scartare, declassa a PROBABLE.

---

## Affermazioni Vietate

La skill NON può usare queste formulazioni:

| Vietato | Alternativa corretta |
|---|---|
| "Potrebbero esserci null pointer" | "src/api/User.ts:42 — accesso `.name` senza `?.`" |
| "Il codice è vulnerabile a..." | "POST /api/users → riga 88 accetta SQL string non sanitizzata" |
| "Manca validazione" | "Campo `email` ha `required: true` in FE ma `@NotNull` assente in UserDto.java:12" |
| "Potrebbe crashare se..." | "Input `' OR '1'='1'` a riga 33 non è sanitizzato → SQL injection" |
| "C'è un memory leak" | Non riportare senza evidenza di allocazione senza rilascio + ciclo infinito |
| "Non è state-safe" | "HashMap non-concurrent a ConfigCache.java:12, accesso senza synchronized" |

---

## Checklist Pre-Report (obbligatoria)

Prima di inserire qualsiasi bug nel report finale:

```
□ Ho citato il file con path relativo e il numero di riga?
□ Il codice a quella riga contiene esattamente il pattern che descrivo?
□ Ho tracciato il percorso utente che raggiunge quella riga?
□ Ho testato i 7 falsificatori? Nessuno lo protegge?
□ La descrizione NON contiene "potrebbe", "potenziale", "teoricamente"?
□ Ho scelto il livello corretto (CONFIRMED/PROBABLE/SUSPECT)?
□ Se SUSPECT, è SOLO in appendice?
```
