# Stack: Data platform (dbt / Airflow / Spark / SQL)

## Stack id

`data-platform`

## Manifest fingerprints

- File globs: `**/dbt_project.yml`, `**/profiles.yml`, `**/models/**/*.sql`, `**/dags/*.py`, `**/spark-defaults.conf`, `**/airflow.cfg`, `**/*.ipynb`, `**/glue_job/*.py`, `**/notebooks/**/*.py`, `**/sql/**/*.sql`.
- Content patterns: `dbt_project.yml` `name:` key; `from airflow import DAG` import; `pyspark.sql.SparkSession.builder` instantiation.
- Negative match: a Python repo without dbt / Airflow / Spark / Glue signals dispatches to `python.md` instead.

## Analysis-unit granularity

- **dbt project**: each `dbt_project.yml` is one analysis unit.
- **Airflow DAGs folder**: each DAG file is treated as an entry point WITHIN the unit; the unit is the folder containing `dags/` and `airflow.cfg`.
- **Glue / Spark batch repo**: each `glue_job/*.py` or top-level `pyspark` script is an entry point WITHIN the unit; the unit is the repository root.
- See [../repo_granularity.md](../repo_granularity.md).

## Parser

- Regex fallback for `dbt_project.yml` (YAML), Airflow DAGs (Python AST + regex for `DAG(...)` calls), Spark scripts (Python AST).
- SQL files: lightweight tokenization (CTE detection, top-level `SELECT` / `INSERT` / `UPDATE` / `MERGE` / `DELETE`); no full SQL AST in v1.
- Notebooks (`*.ipynb`): JSON-parsed; only cells with `cell_type=code` are analyzed; Markdown cells are ignored.

## Entry-point kinds detected

| Surface | `entry_point.kind` | Detection signal |
|---|---|---|
| dbt model | `dbt-model` | a `.sql` file under `models/` referenced by `dbt_project.yml`; each is one entry point |
| dbt test | NOT an entry point | recorded under `dbt-tests` in `coverage.md` |
| Airflow DAG | `scheduled-job` | `DAG(dag_id='<id>', schedule_interval='<expr>', ...)` invocation |
| Airflow `@task` | step within a DAG | not an entry point by itself; aggregated under the DAG's entry |
| Spark batch job | `batch-runner` | `SparkSession.builder.appName('<n>').getOrCreate()` + a `main()` or top-level execution |
| Spark Structured Streaming | `message-consumer` | `spark.readStream...` + `.start()` |
| AWS Glue job | `batch-runner` | `glueContext.create_dynamic_frame.from_catalog(...)` or `getResolvedOptions(sys.argv, [...])` |
| AWS Glue trigger | `scheduled-job` | trigger defined in IaC (see `terraform-hcl.md`); cross-stack bridge |
| Notebook executed as a job (Databricks job, SageMaker processing) | `batch-runner` | notebook referenced from IaC or job config |
| dbt source / seed | NOT an entry point | recorded as a data dependency |

## Inputs typing

- dbt: `{{ var('<name>') }}` references → captured as inputs; types inferred from `dbt_project.yml` `vars:`.
- Airflow: `Variable.get('<name>')` / `params={'k': 'v'}` → inputs; types are string unless `cast` is applied.
- Spark: command-line args (`getResolvedOptions`) → inputs; option name + Python type after cast.
- SQL: parameter binding via `{{ ref() }}`, `{{ source() }}`, `{{ this }}` recorded as identifier references, not typed inputs.

## Side-effect detection

- dbt: every materialized model (`materialized='table'` / `'incremental'` / `'view'`) writes to the warehouse — side effect.
- Airflow: each operator's `execute()` is potentially a side effect; the most common (`PostgresOperator`, `BigQueryOperator`, `S3CopyObjectOperator`, `EmrAddStepsOperator`) is recognized by import.
- Spark: `df.write.mode('append'|'overwrite').save(path|table)` is the canonical side effect.
- Glue: `glueContext.write_dynamic_frame.from_catalog(...)` / `from_options(...)`.

## Cross-stack bridge hints

- dbt `source()` references → cross-reference with the upstream ingestion job (often Airflow / Glue).
- Airflow `S3KeySensor` waiting on a path → cross-reference with the producer Lambda / Glue job.
- Spark reads from / writes to S3 paths → cross-reference with `terraform-hcl` bucket definitions.
- dbt warehouse credentials in `profiles.yml` → cross-reference with `aws-serverless` Secrets Manager entries.
- See [../cross_stack_bridges.md](../cross_stack_bridges.md).

## Bug-patterns row pointer

See [../bug_patterns.md](../bug_patterns.md) — rows where column
`data-platform` = `MUST-if-applicable`. Specifically: incremental dbt
model with a missing `unique_key` causing duplicate fact rows visible to
the user, Airflow DAG with `catchup=True` re-running on a config change
(double side effect), Spark non-deterministic `orderBy(rand())` before
`limit` producing different results per run, Glue bookmark disabled
causing reprocessing, dbt source freshness threshold missing leading to
silent stale data, SQL `MERGE` with non-unique join keys producing
non-deterministic results.

## Empty-input branch

If a unit is detected as `data-platform` but contains no models, DAGs,
or jobs (e.g. only seed CSVs), the unit is recorded in `coverage.md`
with skip reason `no-entry-points`. Notebooks without execution metadata
(`metadata.kernelspec` missing) are excluded with `out-of-scope`.
