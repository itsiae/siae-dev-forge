# Testing Anti-Patterns — Quick Reference

I 12 anti-pattern piu' comuni nel testing. Per ogni pattern: cosa evitare e come correggere.

---

## 1. Test After Code

**Problema:** Scrivi il codice, poi aggiungi test a posteriori. I test finiscono per confermare l'implementazione invece di validare il comportamento atteso.

```java
// SBAGLIATO — test scritto dopo, ricalca l'implementazione
@Test void calculate() {
    assertEquals(42, service.calculate(6, 7)); // "funziona, basta cosi'"
}

// GIUSTO — test-first, definisci il contratto prima
@Test void shouldMultiplyTwoPositiveNumbers() {
    assertEquals(42, calculator.multiply(6, 7));
    assertEquals(0, calculator.multiply(0, 5));
    assertEquals(-6, calculator.multiply(-2, 3));
}
```

## 2. Mock Everything

**Problema:** Mock di ogni dipendenza, incluse classi semplici e value object. Il test verifica solo che i mock sono cablati, non il comportamento reale.

```typescript
// SBAGLIATO — mock di una funzione pura
const formatDate = jest.fn().mockReturnValue("2026-01-01");
expect(formatDate("2026-01-01T00:00:00Z")).toBe("2026-01-01");

// GIUSTO — mock solo I/O e dipendenze esterne
const repository = mock<UserRepository>();
when(repository.findById("u1")).thenResolve(aUser);
const result = await service.getProfile("u1");
expect(result.name).toBe("Mario Rossi");
```

## 3. Testing Implementation Details

**Problema:** Il test si lega a dettagli interni (nomi di metodi privati, ordine di chiamate). Ogni refactor rompe i test senza cambiare il comportamento.

```python
# SBAGLIATO — verifica metodo interno
mock_repo.save.assert_called_once_with(expected_entity)

# GIUSTO — verifica l'effetto osservabile
result = service.create_order(order_request)
assert result.status == "CREATED"
saved = repo.find_by_id(result.id)
assert saved is not None
```

## 4. God Test

**Problema:** Un singolo test verifica 10 cose diverse. Quando fallisce, non sai quale comportamento e' rotto.

```java
// SBAGLIATO — test monolitico
@Test void testUserService() {
    // crea utente, verifica salvataggio, verifica email,
    // verifica ruoli, verifica audit log, verifica cache...
}

// GIUSTO — un comportamento per test
@Test void shouldSendWelcomeEmailOnRegistration() { /* ... */ }
@Test void shouldAssignDefaultRoleToNewUser() { /* ... */ }
@Test void shouldLogRegistrationInAuditTrail() { /* ... */ }
```

## 5. Flaky Test (Sleep / Race Condition)

**Problema:** Il test usa `sleep()` o dipende da timing. Passa 9 volte su 10, poi fallisce in CI e nessuno si fida piu' della suite.

```typescript
// SBAGLIATO
await sendAsyncEvent();
await new Promise(r => setTimeout(r, 2000));
expect(getResult()).toBeDefined();

// GIUSTO — condition-based waiting (vedi condition-based-waiting.md)
await sendAsyncEvent();
await waitFor(() => expect(getResult()).toBeDefined(), { timeout: 5000 });
```

## 6. Test Without Assertion

**Problema:** Il test esegue codice ma non verifica nulla. Passa sempre, dando falsa sicurezza.

```python
# SBAGLIATO — nessuna assertion
def test_process_payment():
    service.process_payment(amount=100, currency="EUR")
    # "se non lancia eccezione, funziona"

# GIUSTO — assertion esplicita
def test_process_payment_creates_transaction():
    tx = service.process_payment(amount=100, currency="EUR")
    assert tx.status == "COMPLETED"
    assert tx.amount == 100
```

## 7. Copy-Paste Test

**Problema:** Test duplicati con variazioni minime. Quando cambia il contratto, devi aggiornare N copie.

```java
// SBAGLIATO — 5 test identici con dati diversi

// GIUSTO — test parametrizzato
@ParameterizedTest
@CsvSource({"100,EUR,true", "0,EUR,false", "-1,EUR,false"})
void shouldValidatePaymentAmount(int amount, String currency, boolean expected) {
    assertEquals(expected, validator.isValid(new Payment(amount, currency)));
}
```

## 8. Commenting Out Failing Tests

**Problema:** Un test fallisce, lo commenti "temporaneamente". Resta commentato per mesi, il bug che segnalava rientra in produzione.

```typescript
// SBAGLIATO
// it("should reject expired tokens", () => { ... }); // TODO: fix later

// GIUSTO — se il test e' valido, fixalo. Se non lo e', cancellalo.
it.todo("should reject expired tokens"); // almeno e' visibile nel report
```

## 9. Testing Getters/Setters

**Problema:** Test di metodi triviali senza logica. Spreco di tempo, zero valore, inflaziona la coverage.

```java
// SBAGLIATO
@Test void testGetName() {
    user.setName("Mario");
    assertEquals("Mario", user.getName());
}

// GIUSTO — testa comportamento con logica
@Test void shouldNormalizePhoneNumberOnSet() {
    contact.setPhone("+39 06 1234567");
    assertEquals("0039061234567", contact.getPhone());
}
```

## 10. Ignoring Edge Cases

**Problema:** Test solo per il happy path. I bug in produzione arrivano quasi sempre dai casi limite.

```python
# SBAGLIATO — solo happy path
def test_divide():
    assert calculator.divide(10, 2) == 5

# GIUSTO — edge cases espliciti
def test_divide_by_zero_raises():
    with pytest.raises(ZeroDivisionError):
        calculator.divide(10, 0)

def test_divide_negative_numbers():
    assert calculator.divide(-10, 2) == -5
```

## 11. Hard-Coded Test Data Without Meaning

**Problema:** Valori magici come `"abc"`, `123`, `"test"` senza contesto. Impossibile capire cosa il test sta verificando.

```typescript
// SBAGLIATO
const result = validate("abc", 123, true);
expect(result).toBe(false);

// GIUSTO — nomi che spiegano l'intento
const EXPIRED_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...";
const VALID_USER_ID = "USR-00042";
const result = validate(EXPIRED_TOKEN, VALID_USER_ID);
expect(result).toBe(false); // token scaduto -> rifiutato
```

## 12. Testing Framework Instead of Business Logic

**Problema:** Il test verifica che Spring/Express/Django funzioni, non che il tuo codice sia corretto.

```java
// SBAGLIATO — stai testando Spring MVC
@Test void controllerReturns200() {
    mockMvc.perform(get("/api/users")).andExpect(status().isOk());
}

// GIUSTO — testa la logica di business in isolamento
@Test void shouldFilterInactiveUsersFromList() {
    var users = List.of(activeUser, inactiveUser);
    var result = userService.getActiveUsers(users);
    assertThat(result).containsExactly(activeUser);
}
```

---

> **Regola d'oro:** ogni test deve rispondere alla domanda _"quale comportamento si rompe se questo test fallisce?"_ Se non sai rispondere, il test va riscritto.
