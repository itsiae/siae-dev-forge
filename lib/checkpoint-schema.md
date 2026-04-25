# Checkpoint Schema — Standard DevForge

Formato standard per output strutturato delle skill.

## Regole

- Ogni step significativo emette 1 checkpoint
- Formato: `[SKILL-NAME:STEP-ID] Descrizione`
- Campi key:value, no testo narrativo
- Emesso in chat visibile all'utente (non in log silenzioso)

## Esempi canonici

```
[BRAINSTORM:INTAKE] Analisi completata
  Stack: Java/Spring Boot
  Pattern: REST microservice
  Confidence: HIGH (3/3 fonti concordanti)
  File analizzati: 7
  Lacune: nessuna
```

```
[TDD:RED] Test fallente scritto
  File: tests/test_validator.py
  Test: test_invalid_isrc_format
  Run: pytest -k test_invalid_isrc_format
  Output: FAILED (ValidationException)
```

```
[VERIFICATION:ASSERT] Claim verificato
  Claim: "endpoint /users ritorna 200"
  Comando: curl localhost:8080/users
  Output: HTTP/1.1 200 OK
  Evidenza: salvata in .devforge-verification-log
```

Le skill individuali possono definire step-id specifici ma devono seguire
il formato chiave:valore e la riga di intestazione.
