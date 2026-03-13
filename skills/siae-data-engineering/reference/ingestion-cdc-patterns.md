# Ingestion CDC Patterns — Delta Window, Dedup, Soft Delete

> Basato su pattern reali estratti da `datalake-anagrafica-dipendenti-etl`.

---

## CDC (Change Data Capture)

Il layer bronze contiene eventi CDC grezzi provenienti dai sistemi sorgente.
Ogni record ha:

| Campo | Tipo | Scopo |
|-------|------|-------|
| `op` | string | Operazione: `I` (insert), `U` (update), `D` (delete) |
| `commit_time` | string (epoch) | Timestamp del commit nel sistema sorgente |
| `transact_id` | string | ID transazione nel sistema sorgente |
| `year`, `month`, `day` | string | Partizioni Hive-style (data di ingestion) |
| *payload* | vari | Colonne business della tabella sorgente |

---

## Delta Window — Processing Incrementale

### Concetto

La delta window definisce l'intervallo temporale di dati da processare:
- `last_silver_update_time`: epoch Unix dell'ultimo aggiornamento silver completato
- `next_silver_update_time`: epoch Unix corrente (fine finestra)

Solo i record CDC nel bronze con `commit_time` in questo intervallo vengono processati.

### Flusso gestione timestamp

```
1. Step Function parte (cron EventBridge)
2. Lambda RETRIEVE: legge DynamoDB → last_silver_update_time per ogni tabella
3. Step Function passa i timestamp ai Glue job come parametri
4. Glue job processa solo la finestra [last, next]
5. Lambda UPDATE: scrive next_silver_update_time come nuovo last in DynamoDB
```

### AdjustUpdateTime — Overlap di 1 giorno

La Step Function sottrae 86400 secondi (1 giorno) al `last_silver_update_time`.
Questo crea un overlap intenzionale che protegge da:
- Record CDC arrivati in ritardo (late arriving data)
- Partizioni bronze scritte a cavallo della mezzanotte

La deduplicazione via `ROW_NUMBER()` garantisce che l'overlap non produca duplicati.

### force_no_window — Full Reload

Quando `force_no_window = 1`:
- La finestra diventa `[0, 32503680000]` (anno 3000)
- **TUTTO** il bronze viene processato
- Il MERGE INTO Iceberg sovrascrive i dati esistenti senza duplicati (idempotente)

**Quando usarlo:**
- Prima esecuzione assoluta (tabella silver vuota)
- Recovery da dati corrotti
- Schema change che richiede ricalcolo completo

**Quando NON usarlo:**
- In produzione senza approvazione esplicita (riscrive l'intero datalake)
- Come workaround per bug — identifica e correggi la causa

---

## Push-down Predicate — Ottimizzazione Lettura

Il predicate pushdown filtra le partizioni bronze **prima** della lettura, minimizzando I/O su S3.

```python
predicate = self.create_partition_condition()
dyf = self.glueContext.create_dynamic_frame.from_catalog(
    database=self.bronze_db,
    table_name=self.bronze_table,
    push_down_predicate=predicate
)
```

La funzione `create_partition_condition()` genera una condizione SQL basata sulla finestra:

| Caso | Predicate generato |
|------|--------------------|
| Stessa data | `year='2026' AND month='03' AND day='12'` |
| Stesso mese, giorni diversi | `year='2026' AND month='03' AND day >= '10' AND day <= '12'` |
| Mesi diversi, stesso anno | `year='2026' AND ((month='02' AND day >= '28') OR (month='03'))` |
| Anni diversi | `(year='2025' AND ...) OR (year='2026' AND ...)` |

---

## Deduplicazione CDC

Nella finestra delta possono esserci multiple operazioni sullo stesso record (es. INSERT + UPDATE + UPDATE).
Solo l'operazione piu' recente conta.

### Pattern ROW_NUMBER

```sql
SELECT * FROM (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY {pk_columns}
        ORDER BY last_commit_time DESC, last_transact_id DESC
    ) as rn
    FROM delta_raw
) WHERE rn = 1
```

- `PARTITION BY PK`: raggruppa per chiave primaria
- `ORDER BY commit_time DESC, transact_id DESC`: la piu' recente prima
- `WHERE rn = 1`: mantiene solo l'ultima operazione

### Risultato

Per ogni PK nella finestra, rimane un solo record con:
- L'`op` piu' recente (potrebbe essere I, U, o D)
- Il payload piu' aggiornato

---

## Soft Delete

I record con `op = 'D'` non vengono mai cancellati fisicamente dal silver.

### Implementazione nel MERGE

```sql
MERGE INTO silver_table AS target
USING increment
ON target.pk = increment.pk
WHEN MATCHED AND increment.last_op = 'D' THEN UPDATE SET
    deleted = 1,
    last_op = 'D',
    last_updated_at = increment.last_updated_at
WHEN MATCHED AND increment.last_op != 'D' THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
```

### Colonne metadata silver

| Colonna | Tipo | Scopo |
|---------|------|-------|
| `last_updated_at` | timestamp | Timestamp di elaborazione ETL (non del dato sorgente) |
| `deleted` | integer | `0` = attivo, `1` = soft-deleted |
| `last_op` | string | Ultima operazione CDC (`I`, `U`, `D`) |
| `last_commit_time` | string | Timestamp commit sorgente dell'ultima operazione |
| `last_transact_id` | string | ID transazione sorgente dell'ultima operazione |

### Perche' soft delete

1. **Audit trail**: sapere quando e perche' un record e' stato eliminato
2. **Recovery**: possibilita' di "ripristinare" un record senza riprocessare il bronze
3. **Downstream**: i consumer possono filtrare `WHERE deleted = 0` o includere i deleted per analisi storiche
4. **Compliance**: in ambito dati personali (anagrafica dipendenti), tracciare le cancellazioni e' obbligatorio

---

## Standardizzazione Dati

Dopo il mapping e la deduplicazione, i dati vengono standardizzati:

### sanitize_string

Per ogni colonna di tipo `string`:
1. `trim()` — rimuove spazi iniziali e finali
2. Se la stringa risultante e' vuota (`""`), sostituisci con `NULL`

### Colonne metadata aggiunte

```python
df = df.withColumn("last_updated_at", current_timestamp())
df = df.withColumn("deleted", when(col("last_op") == "D", lit(1)).otherwise(lit(0)))
```

### Schema alignment

Prima del MERGE, il DataFrame viene allineato allo schema del target Iceberg:

```python
target_cols = spark.table(f"job_catalog.{silver_db}.{silver_table}").columns
df = df.select(*target_cols)
```

Questo previene errori da colonne mancanti o in ordine diverso.

---

## Checklist nuovo flusso CDC

- [ ] Definisci la PK silver (`silver_table_pk`)
- [ ] Verifica che il bronze contenga `op`, `commit_time`, `transact_id`
- [ ] Configura il mapping colonne nel `ApplyMapping` (includi i campi CDC)
- [ ] Usa `get_delta_incremental_df()` per la dedup (non scrivere SQL custom)
- [ ] Aggiungi `last_updated_at` e `deleted` come colonne metadata
- [ ] Usa MERGE INTO con i 3 branch (DELETE → soft delete, UPDATE → SET *, INSERT → INSERT *)
- [ ] Testa con `force_no_window=1` su dev per il primo caricamento
- [ ] Verifica che il count post-MERGE sia coerente (non piu' record del previsto)
