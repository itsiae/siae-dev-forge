# M4 — Async & Race Condition Bug Detector

## Regola Fondamentale

Una race condition è un bug CONFERMATO solo se:
- La finestra temporale è > 10ms (altrimenti improbabile in produzione)
- Il trigger è un pattern d'uso reale dell'utente (navigazione rapida, doppio click, submit doppio)
- Il risultato è osservabile (stato UI errato, dato corrotto, eccezione)

---

## FRONTEND — Race Patterns

### FE-RC1: useEffect senza AbortController

**Grep:**
```
useEffect\s*\(\s*\(\s*\)\s*=>\s*\{[^}]*fetch\(
useEffect\s*\(\s*\(\s*\)\s*=>\s*\{[^}]*axios\.[a-z]+\(
useEffect\s*\(\s*async
```

**Conferma bug:**
1. `useEffect` contiene un fetch asincrono
2. Non c'è `return () => controller.abort()` o `return () => { mounted = false }`
3. Il componente è in una route navigabile (non un singleton permanente)

**Finestra temporale:** 100-500ms (latenza API standard).

**Trigger utente:** Apre pagina A → naviga rapidamente a pagina B → response di A arriva → setState su componente smontato.

**Effetto:** "Warning: Can't perform a React state update on an unmounted component" / stato stantio in B.

**Falsificatori:** AbortController con cleanup, flag `let mounted = true` con check prima di setState,
React Query / SWR (gestiscono automaticamente il cleanup).

---

### FE-RC2: Promise.all con stato condiviso non sequenziato

**Grep:**
```
Promise\.all\s*\(\s*\[.*fetch\|Promise\.all\s*\(\s*\[.*axios
useEffect.*Promise\.all
```

**Conferma bug:**
1. `Promise.all([call1, call2])` che modifica lo stesso stato/store
2. Le due call hanno latenze diverse (request A < request B)
3. Non c'è sequencing esplicito (nessun `await call1; await call2`)

**Finestra temporale:** Differenza di latenza tra le due API (tipicamente 50-500ms).

**Trigger utente:** Componente montato → due fetch paralleli → quello più lento arriva per secondo → sovrascrive stato del primo con dati parziali.

**Effetto:** UI mostra dati incompleti o sovrascrittura dell'update corretto.

**Falsificatori:** `useReducer` con stato atomico, fetch sequenziale con `await`, flag separati per ogni risultato.

---

### FE-RC3: Optimistic Update senza Rollback

**Grep:**
```
set\w+\s*\(.*prev.*=>\s*\[\.\.\.prev|setState\s*\(.*\.\.\.state
dispatch\s*\(.*optimistic\|optimisticUpdate\s*\(
```
Cerca la pattern: `setState(ottimistico)` immediatamente seguita da `api.call().catch(err => {` senza
rollback dello stato nel `.catch()`.

**Conferma bug:**
1. Stato aggiornato ottimisticamente (prima della risposta API)
2. Il `.catch()` non ripristina lo stato precedente
3. L'API può fallire con input reali (es. quota esaurita, conflitto, 402, 409)

**Finestra temporale:** Sempre presente se l'API può fallire.

**Trigger utente:** Clicca "Aggiungi al carrello" → API fallisce (credito insufficiente) → item appare nel carrello ma non è salvato.

**Effetto:** Stato UI ≠ stato backend → inconsistenza visibile al refresh.

**Falsificatori:** `.catch(err => { setState(previousState); showError(err); })`, SWR/React Query con `mutate` e rollback automatico.

---

### FE-RC4: Debounce/Throttle con Closure Stantia

**Grep:**
```
useMemo\s*\(\s*\(\s*\)\s*=>\s*debounce\s*\(.*\[\s*\]
useCallback\s*\(.*debounce\s*\(.*\[\s*\]
```
Pattern: `useMemo(() => debounce(fn, 300), [])` con `[]` — la funzione cattura
state/props della prima render e non si aggiorna.

**Conferma bug:**
1. `debounce` / `throttle` wrappato in `useMemo` / `useCallback` con deps `[]`
2. Dentro la funzione debounced si accede a stato React che cambia
3. Il risultato usa il valore vecchio dello stato (closure stantia)

**Finestra temporale:** Ogni volta che lo stato cambia + l'utente è nel debounce window.

**Trigger utente:** Utente digita in un campo di ricerca → cambia un filtro → i risultati della ricerca usano il filtro vecchio.

**Effetto:** Risultati di ricerca stantii, non aggiornati con lo stato corrente.

**Falsificatori:** Ref come escape hatch (`const stateRef = useRef(state); stateRef.current = state`), hook `useDebounce` con deps corrette.

---

## BACKEND — Concurrency Patterns

### BE-CC1: Read-then-Write senza Transazione (Check-Then-Act)

**Grep:**
```
public\s+\w+\s+\w+\s*\([^)]*\)\s*\{[^}]*repository\.find
```
Verifica: il metodo ha `@Transactional`? Se no, cerca sequenza find → condizione → save/update.

**Conferma bug:**
1. Metodo `public` senza `@Transactional`
2. Sequenza: `entity = repo.findById(id)` → `if (entity.value >= threshold)` → `repo.save(entity)`
3. L'operazione è finanziaria, di inventario, o di accesso a risorsa limitata

**Finestra temporale:** Due request concorrenti (tipico con frontend SPA che fa retry).

**Trigger utente:** Due tab aperti che inviano la stessa operazione quasi simultaneamente → double-spend / double-booking.

**Effetto:** Invariante business violata (balance negativo, prenotazione doppia).

**Falsificatori:** `@Transactional(isolation = SERIALIZABLE)`, `@Lock(LockModeType.PESSIMISTIC_WRITE)`,
UPDATE atomico in SQL (`UPDATE ... WHERE balance >= amount`).

---

### BE-CC2: Singleton con Stato Mutabile non Thread-Safe

**Grep:**
```
@Service.*\n[^@]*private\s+static\s+(Map|List|Set|HashMap|ArrayList)\s*<
@Component.*\n[^@]*private\s+(Map|List|Set|HashMap|ArrayList)\s*<
```
Pattern: `@Service` / `@Component` con `HashMap` / `ArrayList` non `Concurrent*`.

**Conferma bug:**
1. Spring bean singleton con `Map<>/List<>` mutabile come field
2. Metodi `public` che modificano la struttura (`put`, `remove`, `add`, `clear`)
3. Assenza di `synchronized`, `ConcurrentHashMap`, `CopyOnWriteArrayList`, `ReentrantLock`

**Finestra temporale:** Qualsiasi richiesta concorrente (inevitabile in produzione).

**Trigger utente:** Due utenti accedono allo stesso servizio simultaneamente → race su HashMap → `ConcurrentModificationException` o dato corrotto.

**Effetto:** Exception 500 / dato letto durante modifica incompleta.

**Falsificatori:** `ConcurrentHashMap`, `synchronized void method()`, `@Scope("prototype")`, `volatile` + copy-on-write.

---

### BE-CC3: Multipli .save() senza @Transactional

**Grep:**
```
@(Post\|Put\|Patch)Mapping[^@]*\n(?:(?!@Transactional)[^@])*repository\.save
```
Cerca handler HTTP con multipli `repository.save()` / `repo.save()` senza `@Transactional`.

**Conferma bug:**
1. Handler `@PostMapping`/`@PutMapping` senza `@Transactional`
2. Almeno 2 operazioni di persistenza sequenziali (save A + save B)
3. Se il secondo save fallisce, il primo è già committato → stato incoerente

**Finestra temporale:** Qualsiasi failure del secondo save (violazione constraint, timeout).

**Trigger utente:** Crea ordine con items → errore al save del secondo item → ordine esiste ma è vuoto.

**Effetto:** Entità orfane nel DB / stato incompleto visibile all'utente al reload.

**Falsificatori:** `@Transactional(rollbackFor = Exception.class)` sul metodo, CascadeType.PERSIST con save singolo.

---

### BE-CC4: Lazy Loading JPA fuori Contesto Transazionale

**Grep:**
```
@OneToMany\s*\(.*fetch\s*=\s*FetchType\.LAZY
@ManyToOne\s*\(.*fetch\s*=\s*FetchType\.LAZY
```
Poi verifica: la relation lazy è acceduta fuori da un metodo `@Transactional`.

**Conferma bug:**
1. Entity con relazione `FetchType.LAZY` (default per `@OneToMany`)
2. Metodo che ritorna l'entity senza `@Transactional` (o con `readOnly=true` che chiude la sessione)
3. Nel controller / template / serializzatore si accede alla relazione lazy

**Trigger utente:** Accede a pagina dettaglio → endpoint carica entity → template accede a `entity.getRelatedItems()` → sessione Hibernate già chiusa → LazyInitializationException.

**Effetto:** HTTP 500 con `LazyInitializationException: could not initialize proxy`.

**Falsificatori:** Fetch join JPQL (`JOIN FETCH`), `@EntityGraph`, `Hibernate.initialize()` dentro `@Transactional`, DTO projection via MapStruct/record/interface projection (il lazy proxy non viene mai navigato se il mapping avviene dentro la transazione del service layer).

---

### BE-CC5: N+1 Query JPA in Loop

**Grep:**
```
for\s*\(.*:\s*\w+List\|for\s*\(.*:\s*\w+s\)\s*\{[^}]*\.get
\.forEach\s*\(.*->\s*\{[^}]*\.get\w+\(\)
stream\(\)\.map\(.*->\s*\w+\.get\w+\(\)\s*\.\w+
```
Poi verifica: il campo acceduto nel loop è una relazione `@OneToMany` / `@ManyToOne` lazy.

**Conferma bug:**
1. Metodo `@Transactional` con lista di entity caricata tramite `findAll()` / `findByX()`
2. Loop sulla lista che accede a una relazione lazy di ciascuna entity (`entity.getItems()`, `entity.getAuthor().getName()`)
3. Nessun `JOIN FETCH` / `@EntityGraph` nella query di caricamento della lista
4. La relazione non è mappata tramite DTO projection che eviti la navigazione lazy

**Finestra:** Una query SQL per ogni elemento della lista (N+1 queries totali).

**Trigger utente:** Apertura pagina lista con 100 elementi → 101 query SQL → timeout o latenza > 5s.

**Effetto:** Degradazione di performance che in produzione con dati reali si manifesta come timeout, connessioni DB esaurite, o risposta parziale.

**Nota:** La skill esclude bug di pura performance senza data corruption. Per questo pattern non pre-classificare la confidenza: riporta il candidato nel formato standard e lascia che il Three-Condition Gate di Phase 3 determini CONFIRMED/PROBABLE/SUSPECT in base alle condizioni A+B+C e ai falsificatori.

**Falsificatori:** `@EntityGraph` sulla query di lista, `JOIN FETCH` nella JPQL, `SELECT new Dto(...)` projection, `@BatchSize(size=N)` come mitigazione parziale (declassa a PROBABLE se presente).
