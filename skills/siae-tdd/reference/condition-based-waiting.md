# Condition-Based Waiting — Eliminare sleep() dai Test

## Perche' sleep() e' un Anti-Pattern

`sleep()` nei test causa tre problemi:
1. **Flakiness** — il tempo necessario varia tra macchine, CI, carico di sistema
2. **Lentezza** — dormi sempre il caso peggiore, anche se il risultato arriva in 10ms
3. **Falsi positivi** — se il timeout e' troppo corto il test fallisce senza motivo

La soluzione: **condition-based waiting** — polling attivo fino a quando la condizione e' vera, con timeout di sicurezza.

---

## Java — Awaitility

```xml
<dependency>
    <groupId>org.awaitility</groupId>
    <artifactId>awaitility</artifactId>
    <scope>test</scope>
</dependency>
```

```java
import static org.awaitility.Awaitility.await;
import static java.util.concurrent.TimeUnit.*;

// SBAGLIATO
Thread.sleep(3000);
assertEquals("PROCESSED", order.getStatus());

// GIUSTO
await()
    .atMost(5, SECONDS)
    .pollInterval(200, MILLISECONDS)
    .untilAsserted(() ->
        assertEquals("PROCESSED", orderRepository.findById(orderId).getStatus())
    );
```

---

## JavaScript / TypeScript — waitFor + Polling

### Con Testing Library (React/DOM)

```typescript
import { waitFor } from "@testing-library/react";

// SBAGLIATO
await new Promise(r => setTimeout(r, 2000));
expect(screen.getByText("Success")).toBeInTheDocument();

// GIUSTO
await waitFor(() => {
    expect(screen.getByText("Success")).toBeInTheDocument();
}, { timeout: 5000, interval: 100 });
```

### Polling generico (backend Node.js)

```typescript
async function pollUntil<T>(
    fn: () => Promise<T>,
    predicate: (result: T) => boolean,
    { timeout = 5000, interval = 200 } = {}
): Promise<T> {
    const deadline = Date.now() + timeout;
    while (Date.now() < deadline) {
        const result = await fn();
        if (predicate(result)) return result;
        await new Promise(r => setTimeout(r, interval));
    }
    throw new Error(`Condition not met within ${timeout}ms`);
}

// Uso
const order = await pollUntil(
    () => orderService.getById(orderId),
    (o) => o.status === "PROCESSED",
    { timeout: 5000 }
);
```

---

## Python — tenacity

```bash
pip install tenacity
```

```python
from tenacity import retry, stop_after_delay, wait_fixed

# SBAGLIATO
time.sleep(3)
assert order.status == "PROCESSED"

# GIUSTO
@retry(stop=stop_after_delay(5), wait=wait_fixed(0.2), reraise=True)
def assert_order_processed(order_id):
    order = repository.find_by_id(order_id)
    assert order.status == "PROCESSED"

assert_order_processed(order_id)
```

---

## Pattern Generico — Retry con Backoff Esponenziale

Quando non hai una libreria dedicata, implementa il pattern base:

```
timeout = 5s
interval = 100ms
max_interval = 2s

while elapsed < timeout:
    if condition() == true:
        return success
    sleep(interval)
    interval = min(interval * 2, max_interval)   # backoff esponenziale

throw TimeoutError
```

Il backoff esponenziale bilancia reattivita' (polling frequente all'inizio) e gentilezza (non martellare il sistema dopo secondi di attesa).

---

> **Regola:** se un test contiene `sleep()` / `Thread.sleep()` / `time.sleep()`, sostituiscilo con condition-based waiting. Nessuna eccezione.
