---
name: siae-dms-rename-column
description: >
  Use when the user wants to rename a column in an AWS DMS task mapping rules JSON file.
  Trigger: rinomina colonna DMS, rename column mapping, aggiungi regola DMS, rinomina campo,
  add-column remove-column DMS, mapping rules colonna, rinomina colonna task DMS.
---

# DMS Rename Column — DevForge

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗    ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║    ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║    ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝    ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝     ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝      ║
║         🔨 DevForge · DMS RENAME COLUMN                       ║
║         "Il codice si forgia. Il developer cresce."            ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Flexible | **Fase SDLC:** Configurazione / Ingestion

---

## Quando si Applica

**Sempre:**
- L'utente vuole rinominare una colonna nel file JSON di mapping di un task AWS DMS
- L'utente vuole aggiungere una coppia di regole `add-column` + `remove-column`
- Il file di mapping segue il pattern `{rules: [...]}` con `rule-type: transformation`

**Eccezioni (chiedi esplicitamente):**
- Il file di mapping non è un JSON standard AWS DMS
- L'utente vuole rinominare colonne su più tabelle con nomi diversi contemporaneamente

---

## Istruzioni

### Step 1 — Raccolta Parametri

🟢 SICURO

Chiedi all'utente i seguenti parametri obbligatori prima di procedere:

1. **`column_name`** — Nome della colonna originale da rinominare (es. `deleted`)
2. **`new_column_name`** — Nome della nuova colonna destinazione (es. `deleted_src`)
3. **`table_name`** — Nome della tabella target (es. `uti`, oppure `%` per tutte)
4. **`schema_name`** — Nome dello schema (es. `%public`, oppure `%`)
5. **`mapping_file`** — Path del file JSON di mapping (es. `modules/bm-utilizzazioni/mapping/bm-utilizzazioni-1.json`)

Se l'utente ha già fornito uno o più parametri nel messaggio originale, non richiederli nuovamente.

### Step 2 — Calcolo rule-id

🟢 SICURO

Leggi il file di mapping e individua il `rule-id` più alto presente tra le regole `transformation` esistenti.

I nuovi `rule-id` devono essere:
- `rule-id` regola `add-column` = `max_rule_id + 1`
- `rule-id` regola `remove-column` = `max_rule_id + 2`

Se il file è vuoto o non ha transformation, parti da `237917589`.

### Step 3 — Inserimento Regole nel File

🔴 CRITICO — Mostra pre-flight card prima di eseguire

| 🔴 CRITICO (Modifica regole DMS mapping) — 🔨 DevForge · siae-dms-rename-column |
|:---|
| **⚠️ OPERAZIONE REMOTA — WRITE/UPDATE SU AWS DMS REPLICATION TASK** |
| 📋 Risorsa: `<mapping_file>` · 🌍 Ambiente: `<ambiente>` |
| **▼ Azioni** |
| 1. Aggiungi regola `add-column` → rinomina `<column_name>` in `<new_column_name>` sulla tabella `<table_name>` (schema `<schema_name>`) |
| 2. Aggiungi regola `remove-column` → rimuove la colonna originale `<column_name>` dal mapping DMS |
| 💡 Perché: Le regole DMS definiscono la replicazione delle colonne da DB sorgente a DB target. Una modifica errata può causare perdita di dati o interruzione della replicazione — l'operazione è di fatto applicata al sistema remoto al prossimo riavvio del task DMS. |
| 🚫 Se NO: Il file di mapping non viene modificato e la colonna non sarà rinominata nel task DMS. |

⏸️ **ATTENDI CONFERMA ESPLICITA** — mostra la card e NON eseguire finché l'utente
risponde esplicitamente ("sì, procedi" / "no, annulla"). Silenzio ≠ consenso.

**Solo dopo "sì, procedi"**, esegui:

Le regole vanno inserite **in cima** all'array `rules`, prima di qualsiasi altra regola `transformation` generica (quelle con `table-name: "%"`).

Il pattern da usare è il seguente (vedi [reference/dms-mapping-pattern.md](reference/dms-mapping-pattern.md) per dettagli):

```json
{
  "rule-type": "transformation",
  "rule-id": "<rule_id_add>",
  "rule-name": "add_<new_column_name>",
  "rule-target": "column",
  "object-locator": {
    "schema-name": "<schema_name>",
    "table-name": "<table_name>"
  },
  "rule-action": "add-column",
  "value": "<new_column_name>",
  "expression": "$<column_name>",
  "data-type": {
    "type": "string",
    "length": 999999
  }
},
{
  "rule-type": "transformation",
  "rule-id": "<rule_id_remove>",
  "rule-name": "remove_original_<column_name>",
  "rule-target": "column",
  "object-locator": {
    "schema-name": "<schema_name>",
    "table-name": "<table_name>",
    "column-name": "<column_name>"
  },
  "rule-action": "remove-column"
}
```

### Step 4 — Verifica

🟢 SICURO

Dopo l'inserimento, verifica che:

- [ ] Le due nuove regole si trovano **prima** delle regole con `table-name: "%"`
- [ ] I `rule-id` delle nuove regole sono inferiori a quelli delle regole generiche sottostanti
- [ ] `expression` usa il prefisso `$` seguito dal nome colonna originale
- [ ] `value` contiene il nome della nuova colonna
- [ ] `column-name` nella regola `remove-column` corrisponde alla colonna originale
- [ ] Il JSON è sintatticamente valido (nessuna virgola mancante o in eccesso)

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Raccolta parametri | 🟢 Sicuro | No |
| Lettura file mapping per calcolo rule-id | 🟢 Sicuro | No |
| Inserimento regole nel file JSON | 🔴 Critico | Si |
| Verifica struttura file risultante | 🟢 Sicuro | No |

---

## Vincoli

1. **SEMPRE** inserire le regole in cima all'array `rules`, prima delle trasformazioni generiche
2. **SEMPRE** usare `$<column_name>` (con prefisso `$`) nel campo `expression`
3. **MAI** usare `rule-id` già esistenti nel file — calcola sempre il max e incrementa
4. **SEMPRE** aggiungere prima `add-column` e poi `remove-column` — l'ordine è semanticamente rilevante per DMS
5. **PRE-FLIGHT OBBLIGATORIA** per l'inserimento nel file (rischio 🔴 CRITICO) — attendere conferma esplicita ("sì, procedi") prima di modificare il file

---

## Risorse Aggiuntive

- [reference/dms-mapping-pattern.md](reference/dms-mapping-pattern.md) — Pattern completo delle regole DMS con esempi e note sui campi
