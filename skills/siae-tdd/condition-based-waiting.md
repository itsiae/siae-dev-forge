# Condition-Based Waiting — Eliminare Test Flaky da setTimeout

Tecnica per test asincroni instabili che usano `setTimeout` arbitrari.

---

## Il Problema: Sleep Fisso

```typescript
// ❌ FRAGILE: Il timing è un'ipotesi, non una certezza
await new Promise(r => setTimeout(r, 50));
const result = getResult();
expect(result).toBeDefined();
```

**Perché fallisce:**
- 50ms può bastare sulla macchina locale, non in CI sotto carico
- 50ms può essere eccessivo in test suite veloci (rallenta inutilmente)
- Non documenta COSA si aspetta — è un "aspetta e spera"

---

## La Soluzione: waitFor

```typescript
// ✅ CORRETTO: Attende esattamente la condizione che serve
await waitFor(() => getResult() !== undefined);
const result = getResult();
expect(result).toBeDefined();
```

---

## Implementazione `waitFor` — TypeScript

```typescript
/**
 * Attende finché la condizione ritorna un valore truthy.
 * Fa polling ogni 10ms fino al timeout.
 *
 * @param condition - Funzione che ritorna il valore atteso (o falsy se non ancora pronto)
 * @param description - Descrizione per il messaggio di timeout
 * @param timeoutMs - Timeout massimo in millisecondi (default: 5000)
 */
async function waitFor<T>(
    condition: () => T | undefined | null | false,
    description: string,
    timeoutMs = 5000
): Promise<T> {
    const startTime = Date.now();
    while (true) {
        const result = condition();
        if (result) return result;
        if (Date.now() - startTime > timeoutMs) {
            throw new Error(`Timeout (${timeoutMs}ms) in attesa di: ${description}`);
        }
        await new Promise(r => setTimeout(r, 10)); // polling ogni 10ms
    }
}
```

**Uso nei test:**

```typescript
// Aspetta che un elemento appaia nel DOM
const element = await waitFor(
    () => document.querySelector('.result-panel'),
    'result panel visibile'
);
expect(element).toBeTruthy();

// Aspetta che un servizio elabori un evento
const processed = await waitFor(
    () => eventBus.processed.includes('ORDER_CREATED'),
    'evento ORDER_CREATED processato'
);
expect(processed).toBe(true);

// Aspetta con timeout custom
const data = await waitFor(
    () => cache.get('user:123'),
    'dati utente in cache',
    10_000  // 10 secondi per operazioni lente
);
```

---

## Implementazione `waitFor` — Python

```python
import asyncio
import time
from typing import Callable, TypeVar, Optional

T = TypeVar('T')

async def wait_for_condition(
    condition: Callable[[], Optional[T]],
    description: str,
    timeout_seconds: float = 5.0,
    poll_interval_seconds: float = 0.01
) -> T:
    """
    Attende finché condition() ritorna un valore truthy.

    Args:
        condition: Funzione che ritorna il valore atteso (None/False se non pronto)
        description: Descrizione per il messaggio di errore
        timeout_seconds: Timeout massimo
        poll_interval_seconds: Intervallo di polling (default 10ms)
    """
    start_time = time.time()
    while True:
        result = condition()
        if result:
            return result
        if time.time() - start_time > timeout_seconds:
            raise TimeoutError(
                f"Timeout ({timeout_seconds}s) in attesa di: {description}"
            )
        await asyncio.sleep(poll_interval_seconds)


# Versione sincrona (per test non-async)
def wait_for_sync(
    condition: Callable[[], Optional[T]],
    description: str,
    timeout_seconds: float = 5.0,
    poll_interval_seconds: float = 0.01
) -> T:
    start_time = time.time()
    while True:
        result = condition()
        if result:
            return result
        if time.time() - start_time > timeout_seconds:
            raise TimeoutError(
                f"Timeout ({timeout_seconds}s) in attesa di: {description}"
            )
        time.sleep(poll_interval_seconds)
```

**Uso nei test Python:**

```python
# Test asincrono
async def test_evento_processato():
    bus = EventBus()
    bus.publish("ORDER_CREATED", {"id": "123"})

    processed = await wait_for_condition(
        lambda: "ORDER_CREATED" in bus.processed,
        "evento ORDER_CREATED processato"
    )
    assert processed is True

# Test sincrono con thread
def test_cache_popolata():
    cache = Cache()
    thread = threading.Thread(target=lambda: cache.load("user:123"))
    thread.start()

    result = wait_for_sync(
        lambda: cache.get("user:123"),
        "dati utente caricati in cache"
    )
    assert result["name"] == "Mario Rossi"
```

---

## Java — `Awaitility`

Per Java, usa la libreria `Awaitility` (standard de-facto per test asincroni):

```xml
<!-- pom.xml -->
<dependency>
    <groupId>org.awaitility</groupId>
    <artifactId>awaitility</artifactId>
    <scope>test</scope>
</dependency>
```

```java
import static org.awaitility.Awaitility.*;
import static java.util.concurrent.TimeUnit.*;

// Attende che la condizione sia vera
await()
    .atMost(5, SECONDS)
    .until(() -> eventBus.isProcessed("ORDER_CREATED"));

// Con polling personalizzato
await()
    .pollInterval(10, MILLISECONDS)
    .atMost(10, SECONDS)
    .untilAsserted(() ->
        assertThat(cache.get("user:123")).isNotNull()
    );
```

---

## Regola

| Pattern | Verdict |
|---------|---------|
| `setTimeout(fn, N)` in un test | ❌ Fragile — sostituire con `waitFor` |
| `sleep(N)` in un test | ❌ Fragile — sostituire con `waitFor` |
| `waitFor(() => condition)` | ✅ Stabile |
| `Awaitility.await().until(condition)` | ✅ Stabile |

Un test che usa sleep non è un test affidabile. È una scommessa sul timing.
