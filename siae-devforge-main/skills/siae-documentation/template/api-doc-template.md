# API Documentation — [Nome Servizio]

> **Base URL**: `https://api.siae.it/v1/{servizio}`
> **Auth**: Bearer token (Cognito JWT)
> **Versione API**: 1.0
> **Data**: YYYY-MM-DD

---

## Autenticazione
[Come ottenere il token, header format, scadenza]

## Endpoint

### `POST /resource`
**Descrizione**: [cosa fa]

**Request**:
```json
{
  "field": "value"
}
```

**Response 201**:
```json
{
  "id": "uuid",
  "field": "value",
  "createdAt": "ISO-8601"
}
```

**Error Responses**:
| Status | Codice | Descrizione |
|--------|--------|-------------|
| 400 | VALIDATION_ERROR | Campo obbligatorio mancante |
| 401 | UNAUTHORIZED | Token mancante o scaduto |
| 403 | FORBIDDEN | Permessi insufficienti |
| 404 | NOT_FOUND | Risorsa non trovata |
| 500 | INTERNAL_ERROR | Errore interno server |
