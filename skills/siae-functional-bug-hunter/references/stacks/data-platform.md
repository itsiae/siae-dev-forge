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

## Stack-specific patterns (additive on-demand)

These patterns extend `bug_patterns.md` for PySpark / SparkSQL join and
window correctness bugs that a manual QA tester would catch (duplicate
rows visible in BI, partial reports, regression on segmented metrics)
and that generic patterns miss.

### BP-026 — nullable-join-key-loss

- **Actor primitive**: report_consumer (or downstream_service for
  materialised tables)
- **Trigger** (regex, ALL of):
  - `\.join\(\s*\w+\s*,\s*(?:on\s*=\s*)?["'][\w,]+["']` (DataFrame join
    by column name)
  - AND no upstream `\.filter\(\s*(F\.)?col\("\w+"\)\.isNotNull\(\)\)`
    or `\.dropna\(subset=` on the join key
  - AND no `\.fillna\(\{"\w+":` on the join key
- **Functional manifestation**: when the join key column contains nulls,
  Spark SQL semantics drop those rows for inner joins (data loss visible
  as "missing" entities in the report) OR multiplies them on outer joins
  if the other side also has nulls in that key (duplicate rows). End user
  observes count mismatch between input row count and report row count.
- **Severity hint**: HIGH for revenue / royalty reports, MEDIUM for
  exploratory data.
- **Evidence template**: `src/.../*.py:L# — join on "<col>" without
  upstream null guard; <col> nullable per source schema (see
  <source.parquet>).`
- **Reproduction-rate target**: `deterministic`.
- **Repro steps (ISTQB voice)**:
  1. data engineer prepares the source partition for date D with at least
     one row where `<col>` IS NULL;
  2. data engineer runs the job on date D;
  3. report consumer opens the downstream BI dashboard;
  4. report consumer compares the count of source rows for date D against
     the count in the dashboard;
  5. report consumer observes a count mismatch (rows dropped from inner
     join, OR rows duplicated from outer join).

### BP-027 — window-missing-partition-by

- **Actor primitive**: report_consumer
- **Trigger** (regex):
  - `Window(?:Spec)?\.orderBy\(` OR `Window(?:Spec)?\(\)\.orderBy\(`
  - AND no `\.partitionBy\(` on the same `Window` builder chain
  - AND the window is used by `row_number\(\)|rank\(\)|dense_rank\(\)|lag\(|lead\(|sum\(|avg\(|count\(`
- **Functional manifestation**: the analytic function is computed across
  the entire dataset instead of per group → ranks / running totals leak
  across segments, top-N per category becomes top-N global. End user sees
  the same entity appearing in multiple groups OR a single group hogging
  the entire top-N.
- **Severity hint**: HIGH (silently wrong numbers in BI).
- **Evidence template**: `src/.../*.py:L# — Window.orderBy(...) without
  partitionBy; intended grouping by "<expected_col>" inferred from
  surrounding column refs.`
- **Reproduction-rate target**: `deterministic`.
- **Repro steps (ISTQB voice)**:
  1. data engineer ingests a dataset with at least two distinct values of
     the intended grouping column (e.g. two `genre` values);
  2. data engineer runs the job;
  3. report consumer opens the "top N by group" report;
  4. report consumer observes that the ranks are continuous across groups
     (e.g. genre A has positions 1, 3, 5 and genre B has positions 2, 4,
     6) instead of restarting per group.

## Empty-input branch

If a unit is detected as `data-platform` but contains no models, DAGs,
or jobs (e.g. only seed CSVs), the unit is recorded in `coverage.md`
with skip reason `no-entry-points`. Notebooks without execution metadata
(`metadata.kernelspec` missing) are excluded with `out-of-scope`.
