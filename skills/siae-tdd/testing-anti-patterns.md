# Anti-Pattern nei Test

**Carica questo riferimento quando:** stai scrivendo o modificando test, aggiungendo mock, o sei tentato di aggiungere metodi test-only al codice di produzione.

## Panoramica

I test devono verificare il comportamento reale, non il comportamento dei mock. I mock sono uno strumento per isolare, non la cosa da testare.

**Principio fondamentale:** Testa cosa fa il codice, non cosa fanno i mock.

**Seguire il TDD rigoroso previene questi anti-pattern.**

## Le Leggi di Ferro

```
1. NON testare mai il comportamento dei mock
2. NON aggiungere mai metodi test-only alle classi di produzione
3. NON mockare mai senza capire le dipendenze
```

---

## Anti-Pattern 1: Testare il Comportamento dei Mock

**La violazione:**
```typescript
// ❌ SBAGLIATO: Stiamo testando che il mock esiste
test('renders sidebar', () => {
  render(<Page />);
  expect(screen.getByTestId('sidebar-mock')).toBeInTheDocument();
});
```

**Perche' e' sbagliato:**
- Stai verificando che il mock funzioni, non che il componente funzioni
- Il test passa quando il mock c'e', fallisce quando non c'e'
- Non dice nulla sul comportamento reale

**Il fix:**
```typescript
// ✅ CORRETTO: Testa il componente reale, o non mockarlo
test('renders sidebar', () => {
  render(<Page />);  // Non mockare la sidebar
  expect(screen.getByRole('navigation')).toBeInTheDocument();
});
```

### Gate Function

```
PRIMA di asserire su qualsiasi elemento mock:
  Chiediti: "Sto testando il comportamento reale del componente o solo l'esistenza del mock?"

  SE stai testando l'esistenza del mock:
    STOP — Elimina l'asserzione o rimuovi il mock

  Testa il comportamento reale
```

---

## Anti-Pattern 2: Metodi Test-Only nel Codice di Produzione

**La violazione:**
```java
// ❌ SBAGLIATO: destroy() usato solo nei test
public class SessionService {
    // Sembra un'API di produzione!
    public void destroy(String sessionId) {
        workspaceManager.destroyWorkspace(sessionId);
    }
}

// Nel test
@AfterEach
void tearDown() { sessionService.destroy(sessionId); }
```

**Perche' e' sbagliato:**
- Classe di produzione inquinata con codice test-only
- Pericoloso se chiamato accidentalmente in produzione
- Viola YAGNI e la separazione delle responsabilita'
- Confonde il lifecycle dell'oggetto con quello dell'entita'

**Il fix:**
```java
// ✅ CORRETTO: Le utility di test gestiscono il cleanup
// SessionService non ha destroy() — e' stateless in produzione

// In TestUtils.java
public static void cleanupSession(String sessionId, WorkspaceManager wm) {
    wm.destroyWorkspace(sessionId);
}

// Nel test
@AfterEach
void tearDown() { TestUtils.cleanupSession(sessionId, workspaceManager); }
```

### Gate Function

```
PRIMA di aggiungere qualsiasi metodo a una classe di produzione:
  Chiediti: "Questo metodo e' usato solo dai test?"

  SE si':
    STOP — Non aggiungerlo alla classe di produzione
    Mettilo nelle utility di test

  Chiediti: "Questa classe possiede il lifecycle di questa risorsa?"

  SE no':
    STOP — Classe sbagliata per questo metodo
```

---

## Anti-Pattern 3: Mockare Senza Capire le Dipendenze

**La violazione:**
```python
# ❌ SBAGLIATO: Il mock rompe la logica del test
def test_detects_duplicate_record():
    # Il mock impedisce la scrittura su S3 da cui il test dipende!
    with patch('glue_job.s3_client.put_object') as mock_s3:
        mock_s3.return_value = None

        process_record(record)
        process_record(record)  # Dovrebbe sollevare DuplicateError — ma non lo fa!
```

**Perche' e' sbagliato:**
- Il metodo mockato aveva un side effect da cui il test dipendeva
- Over-mocking "per sicurezza" rompe il comportamento reale
- Il test passa per la ragione sbagliata o fallisce misteriosamente

**Il fix:**
```python
# ✅ CORRETTO: Mocka al livello giusto
def test_detects_duplicate_record():
    # Mocka solo la parte lenta/esterna, preserva il comportamento che il test verifica
    with patch('glue_job.dynamodb_client.get_item') as mock_dynamo:
        mock_dynamo.return_value = {'Item': None}  # Simula DB vuoto

        process_record(record)   # Primo record scritto
        process_record(record)   # Duplicato rilevato ✓
```

### Gate Function

```
PRIMA di mockare qualsiasi metodo:
  STOP — Non mockare ancora

  1. Chiediti: "Quali side effect ha il metodo reale?"
  2. Chiediti: "Questo test dipende da qualcuno di quei side effect?"
  3. Chiediti: "Capisco completamente cosa serve a questo test?"

  SE dipende dai side effect:
    Mocka a un livello piu' basso (la vera operazione lenta/esterna)
    O usa test double che preservano il comportamento necessario
    NON mockare il metodo ad alto livello da cui il test dipende

  SE non sei sicuro di cosa serve al test:
    Esegui il test con l'implementazione reale PRIMA
    Osserva cosa deve succedere davvero
    POI aggiungi il mocking minimo al livello giusto
```

---

## Anti-Pattern 4: Mock Incompleti

**La violazione:**
```python
# ❌ SBAGLIATO: Mock parziale — solo i campi che pensi di usare
mock_glue_response = {
    'JobRunId': 'jr_123',
    'JobRunState': 'SUCCEEDED'
    # Mancano: StartedOn, CompletedOn, ExecutionTime — usati dal codice downstream
}

# Piu' tardi: rompe quando il codice accede a response['ExecutionTime']
```

**Perche' e' sbagliato:**
- **I mock parziali nascondono assunzioni strutturali** — hai mockato solo i campi che conosci
- **Il codice downstream puo' dipendere da campi non inclusi** — fallimenti silenziosi
- **Il test passa ma l'integrazione fallisce** — falsa sicurezza
- **La confidence del test e' bassa** — non prova nulla sul comportamento reale

**La regola di ferro:** Mocka la struttura dati COMPLETA come esiste nella realta', non solo i campi usati dal test immediato.

**Il fix:**
```python
# ✅ CORRETTO: Rispecchia la completezza dell'API reale
mock_glue_response = {
    'JobRunId': 'jr_123',
    'JobRunState': 'SUCCEEDED',
    'StartedOn': datetime(2024, 1, 15, 10, 0, 0),
    'CompletedOn': datetime(2024, 1, 15, 10, 5, 0),
    'ExecutionTime': 300,
    'ErrorMessage': None
    # Tutti i campi che la vera API Glue restituisce
}
```

### Gate Function

```
PRIMA di creare risposte mock:
  Controlla: "Quali campi restituisce l'API reale?"

  Azioni:
    1. Esamina la risposta reale da docs/esempi AWS/SIAE
    2. Includi TUTTI i campi che il sistema potrebbe consumare a valle
    3. Verifica che il mock corrisponda completamente allo schema reale

  Se non sei sicuro: includi tutti i campi documentati
```

---

## Anti-Pattern 5: Test come Afterthought

**La violazione:**
```
✅ Implementazione completata
❌ Nessun test scritto
"Pronto per il testing"
```

**Perche' e' sbagliato:**
- Il testing e' parte dell'implementazione, non un follow-up opzionale
- Il TDD avrebbe previsto questo
- Non puoi dichiarare "completo" senza test

**Il fix:**
```
Ciclo TDD:
1. Scrivi il test che fallisce (RED)
2. Implementa per farlo passare (GREEN)
3. Refactora
4. POI dichiarai completo
```

---

## Quando i Mock Diventano Troppo Complessi

**Segnali di allarme:**
- Il setup del mock e' piu' lungo della logica del test
- Stai mockando tutto per far passare il test
- I mock mancano di metodi che i componenti reali hanno
- Il test si rompe quando cambia il mock

**Considera:** I test di integrazione con componenti reali sono spesso piu' semplici dei mock complessi.

---

## Il TDD Previene Questi Anti-Pattern

**Perche' il TDD aiuta:**
1. **Scrivi il test prima** → Ti forza a pensare a cosa stai davvero testando
2. **Vedi fallire il test** → Conferma che il test verifica comportamento reale, non mock
3. **Implementazione minima** → Nessun metodo test-only si insinua nel codice
4. **Dipendenze reali** → Vedi cosa serve al test prima di mockare

**Se stai testando il comportamento di un mock, hai violato il TDD** — hai aggiunto mock senza aver visto il test fallire contro il codice reale.

---

## Quick Reference

| Anti-Pattern | Fix |
|--------------|-----|
| Asserzioni su elementi mock | Testa il componente reale o rimuovi il mock |
| Metodi test-only nel codice di produzione | Sposta nelle utility di test |
| Mock senza capire le dipendenze | Capisci prima le dipendenze, mocka minimalmente |
| Mock incompleti | Rispecchia completamente la struttura reale dell'API |
| Test come afterthought | TDD — test prima |
| Mock troppo complessi | Considera i test di integrazione |

## Red Flags

- Asserzioni che cercano TestId con suffisso `-mock`
- Metodi chiamati solo da file di test
- Il setup del mock e' > 50% del test
- Il test fallisce quando rimuovi il mock
- Non riesci a spiegare perche' il mock e' necessario
- Stai mockando "per sicurezza"

## La Regola Finale

**I mock sono strumenti per isolare, non cose da testare.**

Se il TDD rivela che stai testando il comportamento di un mock, sei andato storto.

Fix: Testa il comportamento reale o metti in discussione perche' stai mockando.
