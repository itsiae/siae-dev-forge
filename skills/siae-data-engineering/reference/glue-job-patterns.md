# Glue Job Patterns — Classi Base e Template

> Basato su pattern reali estratti da `datalake-anagrafica-dipendenti-etl` e repo analoghi.

---

## Architettura a classi base

Ogni repo ETL ha un file `glue-jobs/src/libs/custom_classes.py` con due classi base.
I singoli job ereditano da entrambe e variano solo il mapping delle colonne.

```
custom_classes.py
  ├─ IcebergGlueJob         → SparkConf Iceberg, env_prefix, catalogo Glue
  └─ DatePartitionedGlueJob → delta window, partition pushdown, dedup CDC

ogni_tabella.py
  └─ class NomeJob(IcebergGlueJob, DatePartitionedGlueJob)
       └─ varia solo: bronze_table, silver_table, silver_table_pk, ApplyMapping
```

---

## Classe `IcebergGlueJob`

Configura Spark con il supporto Apache Iceberg tramite il catalogo Glue AWS.

**Parametri letti** (`getResolvedOptions`):
- `iceberg_job_catalog_warehouse` — path S3 del warehouse Iceberg
- `environment` — `dev`, `qa`, `prod`

**Cosa fa:**
- Calcola `env_prefix`: `f"{environment}_"` se non prod, stringa vuota per prod
- Configura `SparkConf` con catalogo `job_catalog` → `GlueCatalog` + `S3FileIO`
- Abilita estensioni Iceberg per supporto `MERGE INTO`
- Imposta `spark.sql.sources.partitionOverwriteMode = dynamic`

```python
class IcebergGlueJob:
    def __init__(self):
        self.args = getResolvedOptions(sys.argv, [
            "JOB_NAME",
            "iceberg_job_catalog_warehouse",
            "environment"
        ])
        self.environment = self.args["environment"]
        self.env_prefix = f"{self.environment}_" if self.environment != "prod" else ""
        self.job_name = self.args["JOB_NAME"]

        # SparkConf con catalogo Iceberg
        conf = SparkConf()
        conf.set("spark.sql.catalog.job_catalog", "org.apache.iceberg.spark.SparkCatalog")
        conf.set("spark.sql.catalog.job_catalog.warehouse", self.args["iceberg_job_catalog_warehouse"])
        conf.set("spark.sql.catalog.job_catalog.catalog-impl", "org.apache.iceberg.aws.glue.GlueCatalog")
        conf.set("spark.sql.catalog.job_catalog.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
        conf.set("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")
        conf.set("spark.sql.iceberg.handle-timestamp-without-timezone", "true")
        # ... SparkContext e GlueContext inizializzati con questa conf
```

---

## Classe `DatePartitionedGlueJob`

Gestisce la finestra temporale delta (sliding window) per il processing incrementale.

**Parametri letti** (`getResolvedOptions`):
- `last_silver_update_time` — epoch Unix inizio finestra
- `next_silver_update_time` — epoch Unix fine finestra
- `force_no_window` — `"1"` per full reload

**Cosa fa:**
- **`force_no_window = 1`**: forza la finestra da `0` a `32503680000` (anno 3000) → full reload
- **Protezione**: se la finestra e' `-1` (non impostata), lancia `RuntimeError`
- **`create_partition_condition()`**: genera il pushdown predicate ottimizzato sulle partizioni `year/month/day`
- **`get_delta_incremental_df()`**: dedup CDC con `ROW_NUMBER() OVER (PARTITION BY PK ORDER BY last_commit_time DESC, last_transact_id DESC)` → ritorna solo `rn = 1`

```python
class DatePartitionedGlueJob:
    def __init__(self):
        args = getResolvedOptions(sys.argv, [
            "last_silver_update_time",
            "next_silver_update_time",
            "force_no_window"
        ])
        force = int(args["force_no_window"])
        if force == 1:
            self.last_silver_update_time = 0
            self.next_silver_update_time = 32503680000  # anno 3000
        else:
            self.last_silver_update_time = int(args["last_silver_update_time"])
            self.next_silver_update_time = int(args["next_silver_update_time"])

        if self.last_silver_update_time == -1:
            raise RuntimeError("last_silver_update_time is -1: window not set")

    def create_partition_condition(self):
        """Genera push_down_predicate ottimizzato per le partizioni year/month/day."""
        # Converte epoch → date per determinare il range di partizioni
        # Gestisce 4 casi: anni diversi, stessi anni mesi diversi, etc.
        # Ritorna stringa SQL per il predicate pushdown
        ...

    def get_delta_incremental_df(self, df, pk_columns):
        """Dedup CDC: mantiene solo l'operazione piu' recente per PK nella finestra."""
        pk_str = ", ".join(pk_columns)
        df.createOrReplaceTempView("delta_raw")
        return self.spark.sql(f"""
            SELECT * FROM (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY {pk_str}
                    ORDER BY last_commit_time DESC, last_transact_id DESC
                ) as rn
                FROM delta_raw
            ) WHERE rn = 1
        """).drop("rn")
```

---

## Template Job Concreto

Ogni job ha questa struttura. L'**unica parte che varia** tra job e' il `ApplyMapping`.

```python
from libs.custom_classes import IcebergGlueJob, DatePartitionedGlueJob
from awsglue.transforms import ApplyMapping
from pyspark.sql.functions import current_timestamp, when, lit

class NomeTabella(IcebergGlueJob, DatePartitionedGlueJob):
    def __init__(self):
        IcebergGlueJob.__init__(self)
        DatePartitionedGlueJob.__init__(self)

        self.sc = SparkContext()
        self.glueContext = GlueContext(self.sc)
        self.spark = self.glueContext.spark_session
        self.job = Job(self.glueContext)
        self.logger = self.glueContext.get_logger()

        # ─── Configurazione specifica del job ───
        self.bronze_db = f"{self.env_prefix}bronze_{domain}"
        self.bronze_table = "nome_tabella"
        self.silver_db = f"{self.env_prefix}{domain}_silver"
        self.silver_table = "nome_tabella"
        self.silver_table_pk = ["codice"]  # PK per dedup CDC

        self.job.init(self.job_name, self.args)

    def sanitize_string(self, df):
        """Trim + replace stringa vuota con NULL su tutte le colonne string."""
        for col_name, col_type in df.dtypes:
            if col_type == "string":
                df = df.withColumn(col_name, when(
                    trim(col(col_name)) == "", lit(None)
                ).otherwise(trim(col(col_name))))
        return df

    def standardize_data(self, df):
        """Pipeline di standardizzazione. Chiamare dopo il mapping."""
        df = self.sanitize_string(df)
        return df

    def run(self):
        self.logger.info(f"JOB | START | window [{self.last_silver_update_time} - {self.next_silver_update_time}]")

        # 1. Read bronze via Glue Catalog con push_down_predicate
        predicate = self.create_partition_condition()
        dyf = self.glueContext.create_dynamic_frame.from_catalog(
            database=self.bronze_db,
            table_name=self.bronze_table,
            push_down_predicate=predicate
        )

        # 2. ApplyMapping — UNICA PARTE CHE VARIA TRA JOB
        mapped = ApplyMapping.apply(frame=dyf, mappings=[
            ("op", "string", "last_op", "string"),
            ("commit_time", "string", "last_commit_time", "string"),
            ("transact_id", "string", "last_transact_id", "string"),
            ("codice", "string", "codice", "string"),
            ("descrizione", "string", "descrizione", "string"),
            # ... altre colonne specifiche della tabella
            ("year", "string", "year", "string"),
            ("month", "string", "month", "string"),
            ("day", "string", "day", "string"),
        ]).toDF()

        # 3. Dedup CDC
        df = self.get_delta_incremental_df(mapped, self.silver_table_pk)
        df = df.drop("year", "month", "day")

        # 4. Standardize
        df = self.standardize_data(df)

        # 5. Add metadata
        df = df.withColumn("last_updated_at", current_timestamp())
        df = df.withColumn("deleted", when(col("last_op") == "D", lit(1)).otherwise(lit(0)))

        # 6. MERGE INTO Iceberg
        if not df.isEmpty():
            # Allinea colonne al target Iceberg
            target_cols = self.spark.table(
                f"job_catalog.{self.silver_db}.{self.silver_table}"
            ).columns
            df = df.select(*target_cols)
            df.createOrReplaceTempView("increment")

            pk_condition = " AND ".join([
                f"target.{pk} = increment.{pk}" for pk in self.silver_table_pk
            ])
            self.spark.sql(f"""
                MERGE INTO job_catalog.{self.silver_db}.{self.silver_table} AS target
                USING increment
                ON {pk_condition}
                WHEN MATCHED AND increment.last_op = 'D' THEN UPDATE SET
                    deleted = 1, last_op = 'D', last_updated_at = increment.last_updated_at
                WHEN MATCHED AND increment.last_op != 'D' THEN UPDATE SET *
                WHEN NOT MATCHED THEN INSERT *
            """)

        self.job.commit()

if __name__ == "__main__":
    job = NomeTabella()
    job.run()
```

---

## Regole per nuovi job

1. **Eredita dalle classi base** — non copiare metodi. Se serve un nuovo metodo condiviso, aggiungilo a `custom_classes.py`
2. **1 file = 1 tabella** — naming: `{nome_tabella}.py` (snake_case, match col nome tabella bronze)
3. **Definisci il job in `glue-definitions.yaml`** — worker, timeout, per-ambiente
4. **Solo il mapping varia** — tutto il resto (init, read, dedup, standardize, merge) e' identico
5. **PK esplicita** — `silver_table_pk` deve essere sempre definita e coerente col dominio
6. **Cast consistenti** — se un campo e' `integer` in una tabella del dominio, deve esserlo in tutte
