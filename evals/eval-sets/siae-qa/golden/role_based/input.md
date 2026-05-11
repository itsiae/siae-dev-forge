# Story AUTH-330 — Controllo accessi opere per ruolo

## Contesto

Il backend `sport-opere-service` espone tre endpoint sulla risorsa `opere` e
applica un controllo accessi basato sul claim `role` del JWT Cognito:

- `POST /opere` — crea una nuova opera (status atteso 201)
- `GET /opere/{id}` — legge una opera (status atteso 200)
- `DELETE /opere/{id}` — elimina una opera (status atteso 204)

## Ruoli e azioni permesse

| Ruolo   | CREATE (POST) | READ (GET) | DELETE |
|---------|---------------|------------|--------|
| admin   | si            | si         | si     |
| editor  | si            | si         | no     |
| viewer  | no            | si         | no     |

## Acceptance Criteria

### AC-RBAC
Quando un utente con ruolo X invoca un endpoint:
- se il ruolo permette l'azione: status code di successo come da tabella.
- se il ruolo non permette l'azione: status code `403 Forbidden` con body
  `{"error":"FORBIDDEN","role":"<role>","action":"<action>"}` e nessuna
  modifica sulla risorsa (per i write).

JWT con `role` claim e' obbligatorio: la verifica della firma e dell'audience
e' fuori dallo scope di questa story.
