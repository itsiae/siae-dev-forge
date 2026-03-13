# Data Quality Checklist

> Validazioni obbligatorie, metriche, e logging strutturato per ogni Glue job.
>
> Questa checklist colma un gap reale: i repo ETL attuali non hanno
> data quality checks sistematici. Queste regole stabiliscono lo standard
> per i nuovi job e il refactoring dei job esistenti.

---

## Validazioni obbligatorie

### 1. PK non null

Prima del MERGE, verifica che la primary key non contenga null:

```python
null_pk_count = df.filter(col(pk_column).isNull()).count()
if null_pk_count > 0:
    self.logger.error(f"JOB | QUALITY | {null_pk_count} record con PK null — ABORT")
    raise ValueError(f"Found {null_pk_count} records with null PK: {pk_column}")
```

**Perche':** un MERGE con PK null corrompe la tabella silver (record orfani, match errati).

### 2. Conteggio record pre/post dedup

Logga il numero di record prima e dopo la deduplicazione:

```python
count_pre = df_mapped.count()
df_dedup = self.get_delta_incremental_df(df_mapped, self.silver_table_pk)
count_post = df_dedup.count()
self.logger.info(f"JOB | QUALITY | pre_dedup={count_pre} post_dedup={count_post} dedup_ratio={count_post/max(count_pre,1):.2%}")
```

**Perche':** un rapporto dedup anomalo (es. 10% di record unici su 100k) indica problemi a monte (duplicati nel bronze, finestra troppo ampia).

### 3. Conteggio per tipo operazione

Logga il breakdown per tipo di operazione CDC:

```python
op_counts = df_dedup.groupBy("last_op").count().collect()
for row in op_counts:
    self.logger.info(f"JOB | QUALITY | op={row['last_op']} count={row['count']}")
```

**Perche':** un numero anomalo di DELETE o un'assenza totale di INSERT puo' indicare problemi nel sistema sorgente.

### 4. Schema alignment check

Verifica che tutte le colonne del target Iceberg siano presenti nel DataFrame:

```python
target_cols = set(spark.table(f"job_catalog.{silver_db}.{silver_table}").columns)
source_cols = set(df.columns)
missing = target_cols - source_cols
extra = source_cols - target_cols
if missing:
    self.logger.error(f"JOB | QUALITY | colonne mancanti nel source: {missing}")
    raise ValueError(f"Missing columns: {missing}")
if extra:
    self.logger.warn(f"JOB | QUALITY | colonne extra nel source (ignorate): {extra}")
```

---

## Metriche da loggare

Ogni job deve loggare queste metriche con il prefisso `JOB | METRICS |`:

| Metrica | Formato | Quando |
|---------|---------|--------|
| `window_start` | epoch | Inizio run |
| `window_end` | epoch | Inizio run |
| `records_read` | int | Dopo lettura bronze |
| `records_after_dedup` | int | Dopo deduplicazione |
| `records_inserted` | int | Dopo MERGE (se possibile) |
| `records_updated` | int | Dopo MERGE (se possibile) |
| `records_soft_deleted` | int | Dopo MERGE (se possibile) |
| `is_empty` | bool | Se il DataFrame e' vuoto (nessun dato nella finestra) |
| `duration_seconds` | float | Fine run |

```python
import time

start_time = time.time()
self.logger.info(f"JOB | METRICS | window_start={self.last_silver_update_time} window_end={self.next_silver_update_time}")

# ... processing ...

if df.isEmpty():
    self.logger.info("JOB | METRICS | is_empty=true records_read=0")
else:
    self.logger.info(f"JOB | METRICS | records_read={count_pre} records_after_dedup={count_post}")

elapsed = time.time() - start_time
self.logger.info(f"JOB | METRICS | duration_seconds={elapsed:.1f}")
```

---

## Logging strutturato

### Formato

Tutti i log devono seguire il pattern: `JOB | {CATEGORY} | {key}={value} ...`

| Category | Uso |
|----------|-----|
| `START` | Inizio job con parametri |
| `QUALITY` | Validazioni e anomalie |
| `METRICS` | Metriche numeriche |
| `STANDARDIZE` | Info sulla standardizzazione dati |
| `MERGE` | Info sul MERGE Iceberg |
| `END` | Fine job con esito |

### Log4j2 per-ambiente

| Ambiente | Livello root | Livello applicativo |
|----------|-------------|---------------------|
| dev | error | **info** (logger `Glue`) |
| qa | error | **warn** (minimo raccomandato) |
| prod | error | **warn** (minimo raccomandato) |

**Regola:** in qa/prod il livello INFO dell'applicativo puo' essere disabilitato per ridurre i costi CloudWatch, ma **WARN deve restare attivo** per catturare anomalie senza fallire il job.

---

## Codice pulito

### Import

Importa solo cio' che usi. Pattern corretto:

```python
# SI — import specifici
from pyspark.sql.functions import col, when, lit, trim, current_timestamp

# NO — import wildcard o non usati
from pyspark.sql.functions import *
from pyspark.sql.types import IntegerType, LongType, DecimalType  # se non usati
```

### No codice morto

- Rimuovi metodi commentati — se non servono, non devono esserci
- Rimuovi import non usati
- Se un metodo e' "commentato per dopo", crea un ticket e cancellalo

### Metodi nella classe base

Se un metodo e' usato da piu' di un job, appartiene a `libs/custom_classes.py`:

```python
# SI — nella classe base
class IcebergGlueJob:
    def sanitize_string(self, df): ...

# NO — copiato in ogni job
class AreDipendenti(IcebergGlueJob, DatePartitionedGlueJob):
    def sanitize_string(self, df): ...  # DUPLICATO!
```

---

## Checklist per code review ETL

- [ ] PK validation presente (null check)
- [ ] Conteggio record pre/post dedup loggato
- [ ] Metriche `JOB | METRICS |` presenti
- [ ] Nessun import non usato
- [ ] Nessun metodo duplicato (deve essere nella classe base)
- [ ] Nessun codice commentato
- [ ] Cast dei tipi consistenti con le altre tabelle del dominio
- [ ] `force_no_window` non e' `1` in prod (a meno di approvazione esplicita)
- [ ] Log4j2 con almeno WARN attivo in qa/prod
