# DMS Mapping Pattern — Rinomina Colonna

## Struttura File Mapping

I file di mapping DMS seguono questa struttura:

```json
{
  "rules": [
    { ...regole transformation specifiche per tabella... },
    { ...regole transformation generiche (table-name: "%")... },
    { ...regole selection... }
  ]
}
```

**Ordine obbligatorio nell'array `rules`:**
1. Regole `transformation` specifiche per tabella (table-name esplicito, es. `"uti"`)
2. Regole `transformation` generiche (table-name: `"%"`)
3. Regole `selection`

## Pattern Rinomina: add-column + remove-column

### Regola 1 — add-column

```json
{
  "rule-type": "transformation",
  "rule-id": "237917589",
  "rule-name": "add_<new_column_name>",
  "rule-target": "column",
  "object-locator": {
    "schema-name": "%public",
    "table-name": "uti"
  },
  "rule-action": "add-column",
  "value": "<new_column_name>",
  "expression": "$<column_name>",
  "data-type": {
    "type": "string",
    "length": 999999
  }
}
```

**Campi chiave:**
- `value` → nome della nuova colonna da creare
- `expression` → `$<nome_colonna_originale>` (il `$` è obbligatorio, referenzia la colonna sorgente)
- `data-type.length` → usare `999999` come default per uniformità con le altre regole

### Regola 2 — remove-column

```json
{
  "rule-type": "transformation",
  "rule-id": "237917590",
  "rule-name": "remove_original_<column_name>",
  "rule-target": "column",
  "object-locator": {
    "schema-name": "%public",
    "table-name": "uti",
    "column-name": "<column_name>"
  },
  "rule-action": "remove-column"
}
```

**Campi chiave:**
- `column-name` nell'`object-locator` → specifica la colonna originale da eliminare
- Nessun campo `value`, `expression` o `data-type` — non necessari per `remove-column`

## Convenzioni Naming rule-name

| Azione | Pattern | Esempio |
|--------|---------|---------|
| add-column | `add_<new_column_name>` | `add_deleted_src` |
| remove-column | `remove_original_<column_name>` | `remove_original_deleted` |

## Calcolo rule-id

I `rule-id` in questo progetto usano lo stile `237917589` (numeri grandi progressivi).

Per calcolare i nuovi `rule-id`:
1. Leggere tutti i `rule-id` presenti nel file
2. Trovare il valore massimo
3. `rule-id_add = max + 1`
4. `rule-id_remove = max + 2`

## Esempio Completo

Rinomina della colonna `deleted` → `deleted_src` sulla tabella `uti` schema `%public`:

```json
{
  "rules": [
    {
      "rule-type": "transformation",
      "rule-id": "237917589",
      "rule-name": "add_deleted_src",
      "rule-target": "column",
      "object-locator": {
        "schema-name": "%public",
        "table-name": "uti"
      },
      "rule-action": "add-column",
      "value": "deleted_src",
      "expression": "$deleted",
      "data-type": {
        "type": "string",
        "length": 999999
      }
    },
    {
      "rule-type": "transformation",
      "rule-id": "237917590",
      "rule-name": "remove_original_deleted",
      "rule-target": "column",
      "object-locator": {
        "schema-name": "%public",
        "table-name": "uti",
        "column-name": "deleted"
      },
      "rule-action": "remove-column"
    }
  ]
}
```
