# Testing PySpark — Guida per Glue Job ETL

> I repo ETL SIAE attualmente non hanno test. Questa guida stabilisce
> il pattern per aggiungere test ai repo esistenti e ai nuovi job.
>
> Framework: **pytest** + **PySpark** via Docker container AWS Glue.
>
> Validato su `datalake-anagrafica-dipendenti-etl`: 28 test, 12s, tutti verdi.

---

## Principio

I Glue job girano su Spark. Spark gira anche in local mode senza cluster.
Questo significa che **tutta la logica di trasformazione e' testabile localmente**
senza account AWS, senza Glue reale, senza S3.

Cosa **si testa**:
- Trasformazioni PySpark (mapping, dedup, sanitize, merge logic)
- Logica delle classi base (`create_partition_condition`, `get_delta_incremental_df`)
- Soft delete, standardizzazione, data quality checks

Cosa **non si testa** (richiede integrazione AWS):
- Connessione al Glue Catalog reale
- Lettura/scrittura S3
- Step Function orchestration
- EventBridge trigger

---

## Setup — Docker (approccio primario)

L'immagine Docker ufficiale `amazon/aws-glue-libs` contiene gia' tutto:
Java, Spark, PySpark, e le librerie `awsglue`. **Non serve installare nulla localmente**
tranne Docker.

### Prerequisiti

- Docker installato e running
- Nessun altro requisito (no Java, no Spark, no PySpark locale)

### Esecuzione test

```bash
# Dalla directory glue-jobs/
docker run --rm \
  --entrypoint /usr/bin/bash \
  -v "$(pwd):/home/glue_user/workspace" \
  -e "DISABLE_SSL=true" \
  amazon/aws-glue-libs:glue_libs_4.0.0_image_01 \
  -c "pip3 install -q pytest && cd /home/glue_user/workspace && python3 -m pytest tests/ -v"
```

**Oppure** usa lo script helper:

```bash
chmod +x tests/run-tests.sh
./tests/run-tests.sh
```

### Dettagli immagine Docker

| Aspetto | Valore |
|---------|--------|
| Immagine | `amazon/aws-glue-libs:glue_libs_4.0.0_image_01` |
| Python | 3.10 |
| Spark | 3.3.0 (Glue 4.0) |
| Java | 8 (Corretto) |
| `awsglue` | Disponibile (DynamicFrame, GlueContext, etc.) |
| Dimensione | ~2.5 GB (primo pull lento, poi cached) |
| Tempo test | ~12s per 28 test (init Spark ~8s, test ~4s) |

**Note sull'entrypoint:** l'immagine ha un entrypoint custom che avvia lo Spark History Server.
Per i test, sovrascrivilo con `--entrypoint /usr/bin/bash`.

### Script `tests/run-tests.sh`

```bash
#!/bin/bash
# Run PySpark tests inside AWS Glue Docker container.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GLUE_JOBS_DIR="$(dirname "$SCRIPT_DIR")"

docker run --rm \
  --entrypoint /usr/bin/bash \
  -v "${GLUE_JOBS_DIR}:/home/glue_user/workspace" \
  -e "DISABLE_SSL=true" \
  amazon/aws-glue-libs:glue_libs_4.0.0_image_01 \
  -c "pip3 install -q pytest && cd /home/glue_user/workspace && python3 -m pytest tests/ -v $*"
```

---

## Setup alternativo — PySpark locale

Se preferisci non usare Docker, puoi installare PySpark localmente.
Richiede **Java 8 o 11** (non 17+) e **Python 3.10** (non 3.14).

```
# requirements-test.txt
pytest>=7.0
pyspark==3.3.4    # stessa versione di Glue 4.0
```

**Limitazione:** le librerie `awsglue` non sono disponibili localmente.
I test devono replicare la logica senza importare `awsglue`.

---

## Struttura directory

```
datalake-{domain}-etl/
├── modules/silver-{domain}/
│   └── glue-jobs/
│       ├── src/
│       │   ├── libs/custom_classes.py
│       │   ├── dipendenti.py
│       │   └── ...
│       └── tests/
│           ├── conftest.py                  # SparkSession fixture
│           ├── run-tests.sh                 # Script Docker helper
│           ├── test_partition_condition.py   # Test logica partizioni (puro Python)
│           ├── test_dedup_cdc.py            # Test dedup CDC (Spark SQL)
│           ├── test_transformations.py      # Test sanitize, soft delete, mapping
│           └── fixtures/                    # (opzionale) dati di input campione
│               └── bronze_sample.json
```

---

## SparkSession fixture

La fixture crea una SparkSession locale. Viene inizializzata una sola volta
per sessione (~8s) e riutilizzata da tutti i test.

```python
# tests/conftest.py
import pytest
from pyspark.sql import SparkSession


@pytest.fixture(scope="session")
def spark():
    """SparkSession locale per test PySpark."""
    session = (
        SparkSession.builder
        .master("local[2]")
        .appName("glue-etl-tests")
        .config("spark.sql.sources.partitionOverwriteMode", "dynamic")
        .config("spark.driver.memory", "1g")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )
    yield session
    session.stop()
```

**Note:**
- `scope="session"` — crearla costa ~8s nel container Docker, riusala tra tutti i test
- `local[2]` — 2 thread bastano per testare parallelismo minimo
- `shuffle.partitions=2` — riduce overhead per piccoli dataset di test
- **Non serve Iceberg nel conftest** per i test di trasformazione. Se servono test MERGE Iceberg, aggiungi la configurazione catalogo (vedi sezione dedicata sotto)

---

## Test delle classi base

### Test `create_partition_condition`

```python
# tests/test_custom_classes.py
import pytest
from datetime import datetime


class TestPartitionCondition:
    """Testa la generazione del push_down_predicate per le partizioni year/month/day."""

    def test_same_day(self):
        """Finestra che copre un solo giorno."""
        # epoch per 2026-03-12 00:00:00 e 2026-03-12 23:59:59
        start = int(datetime(2026, 3, 12).timestamp())
        end = int(datetime(2026, 3, 12, 23, 59, 59).timestamp())
        condition = create_partition_condition_standalone(start, end)
        assert "year='2026'" in condition
        assert "month='03'" in condition
        assert "day='12'" in condition

    def test_cross_month(self):
        """Finestra che attraversa il confine del mese."""
        start = int(datetime(2026, 2, 28).timestamp())
        end = int(datetime(2026, 3, 2).timestamp())
        condition = create_partition_condition_standalone(start, end)
        assert "month='02'" in condition
        assert "month='03'" in condition

    def test_cross_year(self):
        """Finestra che attraversa il confine dell'anno."""
        start = int(datetime(2025, 12, 30).timestamp())
        end = int(datetime(2026, 1, 2).timestamp())
        condition = create_partition_condition_standalone(start, end)
        assert "year='2025'" in condition
        assert "year='2026'" in condition
```

**Nota:** per testare metodi delle classi base senza istanziare il Glue context,
estrai la logica pura in funzioni standalone o usa un wrapper di test.

### Test `get_delta_incremental_df` (dedup)

```python
# tests/test_custom_classes.py

def test_dedup_keeps_latest_by_commit_time(spark):
    """La dedup deve mantenere solo il record con commit_time piu' recente per PK."""
    data = [
        ("U", "100", "1", "ROSSI", "2026", "03", "12"),   # primo update
        ("U", "200", "2", "ROSSI M.", "2026", "03", "12"), # secondo update (piu' recente)
        ("I", "50", "3", "BIANCHI", "2026", "03", "12"),   # insert diversa PK
    ]
    df = spark.createDataFrame(data, [
        "last_op", "last_commit_time", "last_transact_id",
        "descrizione", "year", "month", "day"
    ])
    # Aggiungi PK
    from pyspark.sql.functions import lit
    df = df.withColumn("codice", lit("001"))
    # Sovrascrivi PK per BIANCHI
    from pyspark.sql.functions import when
    df = df.withColumn("codice", when(
        df.descrizione == "BIANCHI", lit("002")
    ).otherwise(lit("001")))

    # Dedup
    df.createOrReplaceTempView("delta_raw")
    result = spark.sql("""
        SELECT * FROM (
            SELECT *, ROW_NUMBER() OVER (
                PARTITION BY codice
                ORDER BY last_commit_time DESC, last_transact_id DESC
            ) as rn
            FROM delta_raw
        ) WHERE rn = 1
    """).drop("rn")

    assert result.count() == 2
    # Per codice 001, deve restare ROSSI M. (commit_time=200)
    row_001 = result.filter("codice = '001'").collect()[0]
    assert row_001["descrizione"] == "ROSSI M."
    assert row_001["last_commit_time"] == "200"


def test_dedup_handles_delete(spark):
    """Se l'ultima operazione e' D, il dedup deve mantenerla (per soft delete)."""
    data = [
        ("I", "100", "1", "001"),
        ("U", "200", "2", "001"),
        ("D", "300", "3", "001"),  # delete e' l'ultima
    ]
    df = spark.createDataFrame(data, [
        "last_op", "last_commit_time", "last_transact_id", "codice"
    ])

    df.createOrReplaceTempView("delta_raw")
    result = spark.sql("""
        SELECT * FROM (
            SELECT *, ROW_NUMBER() OVER (
                PARTITION BY codice
                ORDER BY last_commit_time DESC, last_transact_id DESC
            ) as rn
            FROM delta_raw
        ) WHERE rn = 1
    """).drop("rn")

    assert result.count() == 1
    assert result.collect()[0]["last_op"] == "D"
```

---

## Test delle trasformazioni per tabella

### Pattern: bronze fixture → trasformazione → assert silver

```python
# tests/test_dipendenti.py
import json
from pathlib import Path
from pyspark.sql.functions import col, when, lit, trim, current_timestamp


def load_fixture(spark, fixture_name):
    """Carica un file JSON di fixture come DataFrame."""
    fixture_path = Path(__file__).parent / "fixtures" / fixture_name
    data = json.loads(fixture_path.read_text())
    return spark.createDataFrame(data)


def test_apply_mapping_renames_columns(spark):
    """Verifica che il mapping rinomini correttamente le colonne bronze → silver."""
    bronze_data = [{
        "op": "I", "commit_time": "100", "transact_id": "1",
        "cid": "EMP001",
        "nome": "Mario", "cognome": "Rossi",
        "unitaorganizzativa": "IT",
        "datanascita": "1990-01-15",
        "attivo": "1",
        "year": "2026", "month": "03", "day": "12"
    }]
    df = spark.createDataFrame(bronze_data)

    # Applica le stesse rinominazioni del job reale
    df_mapped = df.select(
        col("op").alias("last_op"),
        col("commit_time").alias("last_commit_time"),
        col("transact_id").alias("last_transact_id"),
        col("cid"),
        col("nome"),
        col("cognome"),
        col("unitaorganizzativa").alias("unita_organizzativa"),
        col("datanascita").alias("data_nascita"),
        col("attivo").cast("integer"),
    )

    assert "unita_organizzativa" in df_mapped.columns
    assert "unitaorganizzativa" not in df_mapped.columns
    row = df_mapped.collect()[0]
    assert row["attivo"] == 1
    assert row["unita_organizzativa"] == "IT"


def test_sanitize_string_trims_and_nullifies(spark):
    """sanitize_string deve trimmmare e sostituire stringhe vuote con null."""
    data = [
        ("  Mario  ", ""),
        ("Rossi", "   "),
        (None, "valido"),
    ]
    df = spark.createDataFrame(data, ["nome", "cognome"])

    # Applica sanitize
    for col_name, col_type in df.dtypes:
        if col_type == "string":
            df = df.withColumn(col_name, when(
                trim(col(col_name)) == "", lit(None)
            ).otherwise(trim(col(col_name))))

    rows = df.collect()
    assert rows[0]["nome"] == "Mario"       # trimmed
    assert rows[0]["cognome"] is None        # empty → null
    assert rows[1]["cognome"] is None        # whitespace → null
    assert rows[2]["nome"] is None           # null resta null
    assert rows[2]["cognome"] == "valido"    # invariato


def test_soft_delete_flag(spark):
    """Record con op='D' deve avere deleted=1, gli altri deleted=0."""
    data = [
        ("I", "001"),
        ("U", "002"),
        ("D", "003"),
    ]
    df = spark.createDataFrame(data, ["last_op", "codice"])
    df = df.withColumn("deleted", when(col("last_op") == "D", lit(1)).otherwise(lit(0)))

    rows = {r["codice"]: r["deleted"] for r in df.collect()}
    assert rows["001"] == 0
    assert rows["002"] == 0
    assert rows["003"] == 1
```

---

## Test data quality

```python
# tests/test_data_quality.py

def test_pk_not_null_validation(spark):
    """Il quality check deve rilevare record con PK null."""
    data = [
        ("001", "Mario"),
        (None, "Rossi"),   # PK null!
        ("003", "Bianchi"),
    ]
    df = spark.createDataFrame(data, ["codice", "nome"])

    null_pk_count = df.filter(col("codice").isNull()).count()
    assert null_pk_count == 1, "Deve rilevare 1 record con PK null"


def test_dedup_ratio_within_bounds(spark):
    """Il rapporto dedup non deve essere anomalo (< 10% di record unici = problema)."""
    data = [("U", str(i), str(i), "001") for i in range(100)]  # 100 update sulla stessa PK
    data.append(("I", "200", "200", "002"))  # 1 insert su altra PK
    df = spark.createDataFrame(data, [
        "last_op", "last_commit_time", "last_transact_id", "codice"
    ])

    count_pre = df.count()  # 101
    df.createOrReplaceTempView("delta_raw")
    df_dedup = spark.sql("""
        SELECT * FROM (
            SELECT *, ROW_NUMBER() OVER (
                PARTITION BY codice
                ORDER BY last_commit_time DESC, last_transact_id DESC
            ) as rn FROM delta_raw
        ) WHERE rn = 1
    """).drop("rn")
    count_post = df_dedup.count()  # 2

    ratio = count_post / count_pre
    # In questo caso il ratio e' basso (2/101 = 2%) — segnalare come anomalia
    assert count_post == 2
    assert ratio < 0.1  # soglia per warning
```

---

## Test MERGE INTO Iceberg

Per testare il MERGE end-to-end serve una tabella Iceberg locale.

```python
# tests/test_merge.py

def test_merge_inserts_new_records(spark, silver_db):
    """MERGE deve inserire record nuovi (NOT MATCHED)."""
    # Crea tabella target vuota
    spark.sql(f"""
        CREATE TABLE test_catalog.{silver_db}.dipendenti (
            codice STRING, nome STRING, last_op STRING,
            last_commit_time STRING, last_transact_id STRING,
            last_updated_at TIMESTAMP, deleted INT
        ) USING iceberg
    """)

    # Dati incrementali
    data = [("001", "Mario", "I", "100", "1", 0)]
    df = spark.createDataFrame(data, [
        "codice", "nome", "last_op", "last_commit_time", "last_transact_id", "deleted"
    ])
    df = df.withColumn("last_updated_at", current_timestamp())
    df.createOrReplaceTempView("increment")

    spark.sql(f"""
        MERGE INTO test_catalog.{silver_db}.dipendenti AS target
        USING increment
        ON target.codice = increment.codice
        WHEN MATCHED AND increment.last_op = 'D' THEN UPDATE SET
            deleted = 1, last_op = 'D', last_updated_at = increment.last_updated_at
        WHEN MATCHED AND increment.last_op != 'D' THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)

    result = spark.table(f"test_catalog.{silver_db}.dipendenti")
    assert result.count() == 1
    assert result.collect()[0]["nome"] == "Mario"


def test_merge_updates_existing_records(spark, silver_db):
    """MERGE deve aggiornare record esistenti (MATCHED, non delete)."""
    spark.sql(f"""
        CREATE TABLE test_catalog.{silver_db}.dipendenti (
            codice STRING, nome STRING, last_op STRING,
            last_commit_time STRING, last_transact_id STRING,
            last_updated_at TIMESTAMP, deleted INT
        ) USING iceberg
    """)

    # Insert iniziale
    initial = [("001", "Mario", "I", "100", "1", 0)]
    spark.createDataFrame(initial, [
        "codice", "nome", "last_op", "last_commit_time", "last_transact_id", "deleted"
    ]).withColumn("last_updated_at", current_timestamp()) \
     .writeTo(f"test_catalog.{silver_db}.dipendenti").append()

    # Update
    update = [("001", "Mario Rossi", "U", "200", "2", 0)]
    df = spark.createDataFrame(update, [
        "codice", "nome", "last_op", "last_commit_time", "last_transact_id", "deleted"
    ]).withColumn("last_updated_at", current_timestamp())
    df.createOrReplaceTempView("increment")

    spark.sql(f"""
        MERGE INTO test_catalog.{silver_db}.dipendenti AS target
        USING increment ON target.codice = increment.codice
        WHEN MATCHED AND increment.last_op = 'D' THEN UPDATE SET
            deleted = 1, last_op = 'D', last_updated_at = increment.last_updated_at
        WHEN MATCHED AND increment.last_op != 'D' THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)

    result = spark.table(f"test_catalog.{silver_db}.dipendenti")
    assert result.count() == 1
    assert result.collect()[0]["nome"] == "Mario Rossi"


def test_merge_soft_deletes(spark, silver_db):
    """MERGE deve fare soft delete (deleted=1) e non cancellare fisicamente."""
    spark.sql(f"""
        CREATE TABLE test_catalog.{silver_db}.dipendenti (
            codice STRING, nome STRING, last_op STRING,
            last_commit_time STRING, last_transact_id STRING,
            last_updated_at TIMESTAMP, deleted INT
        ) USING iceberg
    """)

    # Insert iniziale
    spark.createDataFrame(
        [("001", "Mario", "I", "100", "1", 0)],
        ["codice", "nome", "last_op", "last_commit_time", "last_transact_id", "deleted"]
    ).withColumn("last_updated_at", current_timestamp()) \
     .writeTo(f"test_catalog.{silver_db}.dipendenti").append()

    # Delete
    df = spark.createDataFrame(
        [("001", "Mario", "D", "300", "3", 1)],
        ["codice", "nome", "last_op", "last_commit_time", "last_transact_id", "deleted"]
    ).withColumn("last_updated_at", current_timestamp())
    df.createOrReplaceTempView("increment")

    spark.sql(f"""
        MERGE INTO test_catalog.{silver_db}.dipendenti AS target
        USING increment ON target.codice = increment.codice
        WHEN MATCHED AND increment.last_op = 'D' THEN UPDATE SET
            deleted = 1, last_op = 'D', last_updated_at = increment.last_updated_at
        WHEN MATCHED AND increment.last_op != 'D' THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)

    result = spark.table(f"test_catalog.{silver_db}.dipendenti")
    assert result.count() == 1  # record ancora presente
    row = result.collect()[0]
    assert row["deleted"] == 1
    assert row["last_op"] == "D"
```

---

## Fixture files

Esempio di fixture JSON per dati bronze:

```json
// tests/fixtures/bronze_dipendenti.json
[
  {
    "op": "I", "commit_time": "100", "transact_id": "1",
    "cid": "EMP001", "nome": "Mario", "cognome": "Rossi",
    "unitaorganizzativa": "IT", "attivo": "1",
    "datanascita": "1990-01-15",
    "year": "2026", "month": "03", "day": "12"
  },
  {
    "op": "U", "commit_time": "200", "transact_id": "2",
    "cid": "EMP001", "nome": "Mario", "cognome": "Rossi",
    "unitaorganizzativa": "HR", "attivo": "1",
    "datanascita": "1990-01-15",
    "year": "2026", "month": "03", "day": "12"
  },
  {
    "op": "I", "commit_time": "150", "transact_id": "3",
    "cid": "EMP002", "nome": "Laura", "cognome": "Bianchi",
    "unitaorganizzativa": "FIN", "attivo": "1",
    "datanascita": "1985-06-20",
    "year": "2026", "month": "03", "day": "12"
  }
]
```

---

## Esecuzione

### Con Docker (raccomandato)

```bash
# Dalla directory glue-jobs/
./tests/run-tests.sh

# Solo un file
./tests/run-tests.sh -k "test_partition_condition"

# Solo un test specifico
./tests/run-tests.sh -k "test_dedup_keeps_latest"

# Verbose con output dettagliato
./tests/run-tests.sh -v --tb=short
```

### Performance

| Metrica | Valore |
|---------|--------|
| Primo run (pull immagine) | ~2-5 min (download 2.5 GB, una tantum) |
| Run successivi | ~12s per 28 test |
| Init SparkSession | ~8s (una volta per sessione) |
| Singolo test | <0.5s |

**Nota:** l'immagine Docker e' cached dopo il primo pull. I run successivi
partono in ~2s + tempo Spark init.

---

## Cosa testare per ogni nuovo job

| Test | Priorita' | Descrizione |
|------|-----------|-------------|
| Mapping colonne | **Alta** | Verifica rename, cast, colonne output corrette |
| Dedup CDC | **Alta** | Verifica che ROW_NUMBER mantenga il record giusto |
| Soft delete | **Alta** | Verifica deleted=1 per op='D' |
| Sanitize string | Media | Trim + empty → null |
| PK not null | Media | Validazione pre-MERGE |
| MERGE insert | Media | Nuovo record inserito correttamente |
| MERGE update | Media | Record esistente aggiornato |
| MERGE soft delete | Media | Record marcato deleted, non cancellato |
| Schema alignment | Bassa | Colonne allineate al target |
| Empty DataFrame | Bassa | Job non fallisce se la finestra e' vuota |

---

## Limitazioni del testing Docker locale

| Aspetto | Docker locale | AWS Glue |
|---------|---------------|----------|
| Spark engine | Identico (PySpark 3.3) | Identico (Glue 4.0 = Spark 3.3) |
| `awsglue` lib | Disponibile nel container | Disponibile |
| DynamicFrame | Disponibile ma senza catalogo reale | Connesso al Glue Catalog |
| Iceberg | Configurabile con catalogo Hadoop locale | Catalogo Glue + S3 |
| S3 I/O | Filesystem locale (mount volume) | S3 reale |
| push_down_predicate | Non testabile (no Catalog reale) | Funziona |
| Glue Catalog API | Non connesso | Connesso |
| Worker scaling | `local[2]` | G.1X × N worker |
| Costi | Zero | Pay per DPU-hour |

**Approccio consigliato:** testa la logica di trasformazione creando DataFrame
con `spark.createDataFrame()` per simulare il risultato di
`create_dynamic_frame.from_catalog().toDF()`. La logica business e' identica
una volta che il dato e' un DataFrame.

La partition condition, la dedup CDC, la sanitizzazione, il soft delete, e il
mapping colonne sono tutti testabili al 100% senza connessione AWS.
