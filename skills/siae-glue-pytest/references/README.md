# silver-codifica — Glue Jobs

Glue ETL job per il livello silver del dominio Codifica. Pattern Medallion
(bronze → silver). Runtime: AWS Glue 5.0 (Python 3.11, Spark 3.5, Iceberg).

## Struttura

```
glue-jobs/
├── src/                       # codice sorgente Glue
│   ├── *.py                   # 7 job script
│   └── libs/custom_classes.py # IcebergGlueJob + DatePartitionedGlueJob
├── configs/                   # configurazioni per-ambiente (dev/qa/prod)
├── tests/                     # test pytest
├── requirements.txt           # deps Python runtime
└── .coveragerc                # config coverage limitata a src/
```

## Test locale

Requisiti: Python 3.11, Java 11/17 (per PySpark).

```bash
cd modules/silver-codifica/glue-jobs
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pytest pytest-cov
pytest tests/ --cov=. --cov-config=.coveragerc --cov-fail-under=70
```

Output atteso: `Required test coverage of 70% reached.`

### Note

- I package `awsglue.*` non sono installabili via pip; vengono stubati via
  `sys.modules` in `tests/conftest.py`. Lo stub fa "passare" qualsiasi chiamata
  su `awsglue.transforms.*` o `awsglue.context.*` — il test non valida la
  correttezza delle chiamate, solo l'integrità del codice Python e il flow.
- PySpark richiede Java; in CI il runner GitHub Actions Ubuntu ha già JDK.
- Per debug singolo test: `pytest tests/test_iceberg_glue_job.py::test_init_dev_env_prefix -v`.

## CI

Workflow: [`.github/workflows/ci-python-coverage.yaml`](../../.github/workflows/ci-python-coverage.yaml).

Trigger:
- `pull_request` con modifiche in `modules/silver-codifica/glue-jobs/**`
- `push` su `release/**`
- `workflow_dispatch` manuale

Coverage gate: 70% (line-rate, fail-under). Usa il reusable workflow
`itsiae/siae-gh-actions/.github/workflows/pytest-coverage.yaml@v3.0.0`.
