# Story RIP-205 — POST /ripartizioni

## Contesto

Microservizio `sport-ripartizioni-service` espone un endpoint REST per creare
nuove ripartizioni opera. Storage relazionale PostgreSQL. Stack: Spring Boot 3.

## Endpoint

`POST /ripartizioni`

Headers:
- `Content-Type: application/json`
- `Idempotency-Key: <UUID>` (opzionale ma raccomandato per i client retry-safe)

Body:
```json
{
  "autore_id": "string (UUID, FK ad autori)",
  "opera_id": "string (UUID, FK ad opere)",
  "importo": "number (decimal, EUR)",
  "stato_iniziale": "string enum: PENDING | APPROVED"
}
```

Response:
- `201 Created` con location header `/ripartizioni/{id}` se POST nuovo.
- `200 OK` con stesso payload se la stessa Idempotency-Key e' gia' stata processata.
- `404 Not Found` se `autore_id` non esiste nella tabella `autori`.
- `400 Bad Request` se body malformato o importo <= 0.

## Acceptance Criteria

### AC1 - Happy path
Dato un autore esistente e opera esistente, quando il client POST con payload
valido (importo > 0) allora il servizio risponde `201`, scrive una nuova
ripartizione e nella response il campo `id` e' valorizzato.

### AC2 - Validazione importo > 0
Dato un payload con `importo = 0` o negativo, quando il client POST allora il
servizio risponde `400` con error code `IMPORTO_NON_VALIDO` e NON scrive su DB.

### AC3 - Idempotenza
Dato un client che invia la stessa Idempotency-Key due volte con stesso body,
quando arriva la seconda richiesta allora il servizio risponde `200` (non `201`)
con lo stesso `id` della prima e non duplica la riga su DB.

### AC4 - Autore inesistente
Dato un payload con `autore_id` che non esiste in `autori`, quando il client
POST allora il servizio risponde `404` con error code `AUTORE_NOT_FOUND`.
