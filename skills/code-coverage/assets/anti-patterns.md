# Anti-Patterns Gallery — 3 BAD / GOOD pairs

> Lazy-load: caricato SOLO se Phase 5 o Phase 7 hanno fail rate ≥1 nella session corrente.

## Anti-pattern 1: Weak assertions

### BAD
```typescript
it('processes input', () => {
  const result = process({ id: 1 })
  expect(result).toBeTruthy()  // Coverage hit ma zero behavioral guarantee
})
```

### GOOD
```typescript
it('processes input and returns enriched object', () => {
  const result = process({ id: 1 })
  expect(result).toEqual({
    id: 1,
    processed: true,
    timestamp: expect.any(Number)
  })
})
```

**Razionale**: `toBeTruthy()` passa anche per oggetti random/wrong-shape. Asserisci la struttura attesa.

---

## Anti-pattern 2: Self-mock (mock del SUT)

### BAD
```typescript
vi.mock('./payment-service')  // stiamo testando payment-service, non un suo client!
import { processPayment } from './payment-service'

it('processes payment', () => {
  vi.mocked(processPayment).mockResolvedValue({ status: 'OK' })
  const result = processPayment({ amount: 10 })
  expect(result).toEqual({ status: 'OK' })  // tautologia
})
```

### GOOD
```typescript
vi.mock('./database')  // mock SOLO le dependency esterne del SUT
import { processPayment } from './payment-service'
import { db } from './database'

it('processes payment and persists', async () => {
  vi.mocked(db.save).mockResolvedValue(true)
  const result = await processPayment({ amount: 10 })
  expect(result.status).toBe('OK')
  expect(db.save).toHaveBeenCalledWith(expect.objectContaining({ amount: 10 }))
})
```

**Razionale**: mockare il SUT trasforma il test in tautologia che verifica il mock, non il codice.

---

## Anti-pattern 3: Async test senza await

### BAD
```typescript
it('fetches user data', () => {
  fetchUser(1).then(user => {
    expect(user.id).toBe(1)  // test passa anche se assert fallisce dentro Promise
  })
})
```

### GOOD
```typescript
it('fetches user data', async () => {
  const user = await fetchUser(1)  // async/await garantisce wait + propaga errori
  expect(user.id).toBe(1)
})

// Alternative valida con expect.assertions:
it('fetches user data (Promise style)', () => {
  expect.assertions(1)
  return fetchUser(1).then(user => {
    expect(user.id).toBe(1)
  })
})
```

**Razionale**: `Promise` non-awaited fa terminare il test prima dell'assert. Vitest/Jest non sa che il test ha aspettative pendenti senza `expect.assertions(N)` o `await`.
