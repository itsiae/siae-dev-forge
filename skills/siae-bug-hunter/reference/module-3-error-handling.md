# M3 — Error Handling Gap Detector

## Regola Fondamentale

Un gap di error handling è un bug se:
1. Il percorso è raggiungibile dall'utente (endpoint pubblico, form, navigazione)
2. L'errore produce un **silent failure** — l'utente non riceve feedback
   o il sistema entra in stato incoerente senza che l'utente lo sappia

---

## FRONTEND — Gap Patterns

### FE-1: Promise senza .catch()

**Grep:**
```
\.then\s*\((?!.*\.catch)   ← then senza catch nella stessa chain
await\s+fetch\s*\(         ← async senza try/catch wrapper
```

**Conferma bug:** La promise è in un event handler o `useEffect`/`mounted`
che non ha try/catch esterno. L'errore diventa unhandled rejection.

**Impatto:** Network error → UI freeze / blank senza messaggio all'utente.

**Falsificatori:** global `window.addEventListener('unhandledrejection', ...)`,
`process.on('unhandledRejection', ...)`, try/catch nel caller a monte.

---

### FE-2: fetch() senza response.ok check

**Grep:**
```
fetch\(.*\)\.then\s*\(\s*r\s*=>\s*r\.json\(\)
await fetch\(.*\)\s*;\s*\n.*\.json\(\)
```
Pattern: `fetch(url).then(r => r.json())` senza `if (!r.ok)` intermediario.

**Conferma bug:** BE ritorna 400/422/500 → FE tenta `.json()` sull'error response
→ o il JSON di errore viene processato come dato valido, o il parse crasha.

**Impatto:** Validazione BE fallita → FE mostra dato errato / crasha su `.json()` parsing.

**Falsificatori:** `.then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })`,
`axios` (ha già this check), wrapper globale su fetch.

---

### FE-3: JSON.parse() senza try/catch

**Grep:**
```
JSON\.parse\s*\((?![^;]*try)
JSON\.parse\s*\(\s*localStorage\|JSON\.parse\s*\(\s*sessionStorage
```

**Conferma bug:** Il valore parsato proviene da `localStorage`, `sessionStorage`,
`URL params`, o `API response` senza garanzia di formato.

**Impatto:** Dato corrotto/malformato nel storage → crash applicativo all'avvio.

**Falsificatori:** try/catch wrapper attorno al JSON.parse, schema validation prima del parse.

---

### FE-4: Error Boundary assente su componenti con API call

**Grep (React only):**
```
class.*extends React\.Component  → nessun componentDidCatch / static getDerivedStateFromError
```
Componente che esegue fetch/useQuery ma non è wrappato da `<ErrorBoundary>`.

**Conferma bug:** Runtime error nel componente → albero DOM si smonta senza fallback UI.

**Impatto:** Crash del componente → pagina bianca senza messaggio.

**Falsificatori:** `<ErrorBoundary>` parent nel router, Suspense boundary.

---

## BACKEND — Gap Patterns

### BE-1: catch(Exception) con solo log, nessuna risposta al client

**Grep:**
```
catch\s*\(\s*Exception\s+\w+\s*\)\s*\{[^}]*logger\.[^}]*\}
catch\s*\(\s*\w+\s*\)\s*\{\s*log\.[^}]*\}\s*return\s*(null|;)
```

**Conferma bug:** Il metodo che cattura è chiamato da un controller HTTP.
L'eccezione viene loggata ma il metodo ritorna `null` o `void` → il controller
risponde 200 OK con body vuoto.

**Impatto:** Operazione fallita → utente riceve "successo" → dato mancante.

**Falsificatori:** global `@ControllerAdvice` / `@ExceptionHandler` che intercetta,
re-throw dell'eccezione dopo il log.

---

### BE-2: Eccezione di validazione → HTTP 500

**Grep:**
```
throw new (RuntimeException|IllegalArgumentException|IllegalStateException)\(
```
Verifica: esiste un `@ExceptionHandler` che mappa questa eccezione a 400/422?
Se non esiste → Spring/Express ritorna 500.

**Conferma bug:** Input utente invalido → BE lancia RuntimeException senza @ExceptionHandler
→ utente vede "Internal Server Error" invece di messaggio di validazione.

**Impatto:** UX rotta — utente non capisce cosa ha sbagliato.

**Falsificatori:** `@ControllerAdvice` con handler per questa eccezione,
`@ResponseStatus(HttpStatus.BAD_REQUEST)` sull'eccezione stessa.

---

### BE-3: NullPointerException silente

**Grep:**
```
\.get\(\)\.get\w*\(\)\|getUser\(\)\.\w*\(\)\|findById\(.*\)\.\w*\(\)
```
Catena di `.get()` senza null-check intermedi su oggetti Optional o nullable.

**Conferma bug:** La NullPointerException non è gestita → Spring ritorna 500.

**Impatto:** Utente vede errore 500 generico, endpoint crashato.

**Falsificatori:** `Optional.orElseThrow()`, `Objects.requireNonNull()`, null-check esplicito.

---

### BE-4: Violazione DB constraint → HTTP 500

**Grep:**
```
catch\s*\(\s*(SQLException|DataIntegrityViolationException|ConstraintViolationException)
```
Verifica: il catch traduce l'eccezione in una risposta 409/400 con messaggio comprensibile?
Se non c'è handler → 500.

**Conferma bug:** Inserimento duplicato (UNIQUE constraint) → stack trace nel response.

**Impatto:** Utente vede 500 invece di "Questo valore esiste già".

**Falsificatori:** `@ExceptionHandler(DataIntegrityViolationException.class)` con 409 response.

---

## BFF — Gap Patterns

### BFF-1: Errore downstream swallowed

**Grep:**
```
catch\s*\(.*\)\s*\{[^}]*(return|resolve)\s*\(\s*\{[^}]*(success|ok)\s*:\s*false
microservice\.call.*catch.*return.*\{\}
```

**Conferma bug:** Il BFF cattura l'errore del microservizio downstream e ritorna
un oggetto neutro `{}` o `{ success: false }` con HTTP 200.
Il FE non distingue successo da failure.

**Impatto:** Operazione fallita in silenzio → utente crede sia andata a buon fine.

**Falsificatori:** il BFF propaga il codice di errore HTTP originale, il FE ha logica
che controlla `success: false` nel body.

---

### BFF-2: HTTP 200 con error body annidato

**Grep:**
```
res\.status\s*\(\s*200\s*\).*json\s*\(.*error\s*:
response\.status\s*=\s*200.*body.*error
```

**Conferma bug:** `res.status(200).json({ error: "...", success: false })`.
Client HTTP (axios, fetch) considera 200 come successo e non entra nel catch.
Il FE deve ispezionare il body per capire se c'è stato un errore.

**Impatto:** Se il FE non controlla `body.error`, l'errore passa inosservato.

**Falsificatori:** Il FE ha middleware che controlla `response.data.error` e lancia eccezione.

---

### BFF-3: Timeout non propagato

**Grep:**
```
fetch\s*\(.*timeout.*\).*catch.*return.*\{\}
axios\s*\(.*timeout.*\).*catch.*\{\s*return\s*(null|\{\})
```

**Conferma bug:** Il BFF fa fetch verso microservizio con timeout, il timeout viene
catturato e restituisce un oggetto vuoto `{}` con HTTP 200.

**Impatto:** L'operazione è incompleta ma l'utente vede successo → stato incoerente.

**Falsificatori:** Il BFF ritorna HTTP 504 Gateway Timeout, il FE gestisce il timeout.
