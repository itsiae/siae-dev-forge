# Story MIG-101 — Migrazione CSV GENERAL_DATA legacy -> nuovo catalogo opere

## Contesto

Il batch notturno deve migrare il flusso `GENERAL_DATA` dal sistema legacy
(formato CSV semicolon-separated) verso la tabella DynamoDB `Opere`. Sono
coinvolti 10 campi del record sorgente. La logica e' stateless: ogni riga
del CSV produce un item DynamoDB (o un rifiuto in DLQ).

## Campi GENERAL_DATA in scope

| Campo        | Mandatory | Tipo / Lookup                                                          | Note business                                |
|--------------|-----------|-------------------------------------------------------------------------|----------------------------------------------|
| CATEGORY     | Y         | Lookup enumerato: `F` (feature), `S` (single), `null` (non classificato)| `F` -> long-form, `S` -> short-form          |
| EVERGREEN    | Y         | Boolean: `true` o `false`                                              | Se `true` esclude expiry check               |
| DURATION     | Y         | Intero >= 0 (secondi)                                                  | Mandatory; valori negativi -> rifiuto in DLQ |
| ORDER        | N         | Intero >= 1                                                            | Opzionale; null ammesso                      |
| RELEASE_DATE | Y         | Stringa formato ISO8601 `YYYY-MM-DD`                                    | Date prima del 1900-01-01 rifiutate          |
| UNIQUEREF2   | Y         | Stringa fissa `074`                                                    | Valore costante (canale SIAE)                |
| TITLE        | Y         | Stringa 1..255 char                                                    | Trim spazi, NFC normalize                    |
| GENRE        | N         | Lookup enumerato: `POP`, `ROCK`, `CLASSICAL`, `null`                   | Opzionale                                    |
| LANGUAGE     | Y         | Lookup ISO 639-1 (2 char lower)                                        | `it`, `en`, `fr`, ...                        |
| ISWC         | N         | Stringa pattern `T-[0-9]{9}-[0-9]{1}`                                   | Validare checksum                            |

## Regole di accettazione (riassunto)

1. CSV header obbligatorio: i 10 campi sopra in qualsiasi ordine.
2. Righe con almeno un campo mandatory mancante -> DLQ.
3. Lookup violati -> DLQ con motivo.
4. `UNIQUEREF2` diverso da `074` -> DLQ.
5. Output: item DynamoDB `Opere` con stesso `id` del CSV.
