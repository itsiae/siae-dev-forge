---
name: siae-glue-pytest
description: >
  Guida la creazione di test Python (pytest) + pipeline CI coverage per i Glue job
  di un modulo datalake-{dominio}-etl SIAE, replicando il pattern standard del
  reusable workflow itsiae/siae-gh-actions/pytest-coverage.yaml. I test girano
  localmente senza cluster Glue (stub awsglue + SparkSession locale) e in CI con
  gate di coverage bloccante.
  Trigger: test python glue job, pytest glue, coverage glue jobs, ci python coverage,
  test custom_classes, stub awsglue, pytest-coverage workflow, test pyspark locale,
  aggiungere test python a modulo etl, soglia coverage 70, TEST_COVERAGE_PERCENTAGE.
---

# SIAE Glue Pytest

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨  DevForge  ·  SIAE Glue Pytest                   ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Flexible | **Fase SDLC:** 5. Testing
>
> **Template canonico:** `datalake-codifica-etl` (branch `main`,
> `modules/silver-codifica/glue-jobs`). I file in `references/` sono copiati da
> li' e rappresentano il **superset** (include `_parse_timestamp`/ISO-8601 e
> `mergeSchema`): parti da questi e **pota** secondo la lib target (Step 2).
> Pattern applicato anche su `datalake-allocazione-analitica-etl`
> (`silver-bm-allocazione`, dove `_parse_timestamp` e' assente → test potati).
> Usa `pytest` + `pytest-cov` con stub `awsglue` via `sys.modules` e SparkSession
> locale (`local[2]`). Nessun cluster Glue, nessuna AWS call.

---

> 📊 **Dai repo itsiae:** la soglia di coverage e' **bloccante per i deploy futuri**.
> Ogni nuovo repo Python (Glue job o Lambda) deve avere i test; su quanto gia'
> deployato, vanno aggiunti a ogni nuova release/hotfix. Un test pytest gira in
> <1 minuto e cattura regressioni di logica (finestra delta, partition pruning,
> dedup multi-pk) prima del deploy su Glue.

## Differenza con `siae-glue-iac-test`

| | `siae-glue-iac-test` | `siae-glue-pytest` (questa) |
|---|---|---|
| Testa | **infrastruttura** (Terraform plan: IAM, S3, worker) | **codice Python** (logica PySpark, classi, lib) |
| Tool | `terraform test` + `mock_provider` | `pytest` + `pytest-cov` + stub awsglue + Spark locale |
| Output | `.tftest.hcl` | suite `tests/` + workflow CI + gate coverage |
| Linguaggio | HCL | Python |

Sono complementari: l'IaC test verifica che la risorsa venga pianificata, il
pytest verifica che il codice del job sia corretto. Usa **entrambe** su un job nuovo.

## Panoramica

Questa skill guida la creazione di:
1. La toolchain del modulo (`requirements.txt`, `.coveragerc`).
2. La suite `tests/` (conftest con stub + 4 file di test).
3. Il caller del reusable workflow CI (`ci-python-coverage.yaml`).
4. Il README del modulo + entry `.gitignore`.

**Cosa testano:** logica Python pura della libreria (`custom_classes.py`) +
import/`__init__`/`run()` dei job con Glue mockato.
**Cosa NON testano:** esecuzione reale su Glue, correttezza dati, MERGE Iceberg
(coperto dal deploy in ambiente dev — out of scope CI).

---

Copia questa checklist e traccia il progresso:

```
Glue Pytest Progress:
- [ ] Step 1: Verifica prerequisiti (modulo, src/, custom_classes.py, glue_version)
- [ ] Step 2: ISPEZIONA la lib reale del modulo (le librerie DIVERGONO tra repo!)
- [ ] Step 3: requirements.txt + .coveragerc
- [ ] Step 4: tests/conftest.py (stub awsglue + fixture spark)
- [ ] Step 5: test_iceberg_glue_job.py + test_date_partitioned_glue_job.py (adattati alla lib)
- [ ] Step 6: test_jobs_smoke.py + test_jobs_classes.py (classi reali dai job)
- [ ] Step 7: README modulo + .gitignore + ci-python-coverage.yaml
- [ ] Step 8: pytest locale, coverage >= soglia, pulizia artefatti
- [ ] Step 9: Commit
```

---

## 1. Prerequisiti da Verificare PRIMA di scrivere i test

**Non procedere se uno di questi manca:**

| Check | Come verificare | Se mancante |
|-------|----------------|-------------|
| Modulo con Glue job | `ls modules/silver-*/glue-jobs/src/*.py` | Crea i job prima (skill `siae-data-engineering`) |
| Libreria condivisa | `ls modules/silver-*/glue-jobs/src/libs/custom_classes.py` | Verifica che i job usino `IcebergGlueJob`/`DatePartitionedGlueJob` |
| Glue/Python version | `grep glue_version modules/silver-*/glue-definitions.yaml` | Glue 5.0 → Python 3.11 |
| Reusable workflow disponibile | `itsiae/siae-gh-actions/.github/workflows/pytest-coverage.yaml@v3.0.0` | Standard SIAE, gia' in uso |

---

## 2. ⚠️ REGOLA #1 — ISPEZIONA la libreria reale, NON copiare i test alla cieca

**Le `custom_classes.py` DIVERGONO tra repo e talvolta tra moduli dello stesso repo.**
Copiare i test del repo template senza leggere la lib target = test che falliscono.
Verificato sul campo: differenze reali riscontrate fra `codifica`, `silver-bm-allocazione`
e `silver-allocazione-analitica`.

Prima di scrivere `test_*.py`, esegui questo confronto:

```bash
MOD=modules/silver-{domain}/glue-jobs
# Confronta la lib target col template (se hai il repo template a fianco)
diff <(git -C ../datalake-codifica-etl show origin/main:modules/silver-codifica/glue-jobs/src/libs/custom_classes.py) \
     $MOD/src/libs/custom_classes.py
```

Punti da verificare nella lib target (decidono quali test scrivere):

| Aspetto | Cosa controllare | Impatto sui test |
|---------|------------------|------------------|
| `_parse_timestamp` esiste? | `grep -n "_parse_timestamp" $MOD/src/libs/custom_classes.py` | Se **assente** (usa `datetime.fromtimestamp(int(...))`): NIENTE test ISO-8601; input invalido → `ValueError` generico (`int()`), non "Unable to parse" |
| `mergeSchema` in `iceberg_config`? | `grep -n "mergeSchema" ...` | Includi l'assert `spark.sql.parquet.mergeSchema == "true"` solo se presente |
| `print` vs `logger`? | `grep -nE "print\(|logger\." ...` | I test `capsys` su FileNotFound/JSON malformato funzionano solo se la lib usa `print` su quei rami |
| Colonne richieste da `get_delta_incremental_df` | leggi `required_columns` | Allinea le `createDataFrame([...])` di test alle colonne reali (es. `last_commit_time`/`last_transact_id` vs `commit_time`) |
| `get_incremental_dataframe` colonne | leggi il check `all(column in ...)` | Stessa cosa per l'happy path |

Poi ispeziona i job per il smoke/class test:

```bash
grep -nE "^class |def run|primary_key|isEmpty|create_dynamic_frame|ApplyMapping" $MOD/src/*.py
```

| Aspetto | Impatto |
|---------|---------|
| Nome classe per ogni file | popola `JOB_SPECS = [(file, ClassName), ...]` |
| `primary_keys` (plurale) o `primary_key` (singolare) | l'assert `hasattr(job, "primary_keys") or hasattr(job, "primary_key")` copre entrambi |
| `self.spark.sql(...).isEmpty()` vs `.limit(1).rdd.isEmpty()` | configura il mock per **entrambi** i pattern (vedi `_build_glue_context_mock`) |
| usa `get_incremental_dataframe` nel `run()`? | il `mapped_df.columns` mock deve contenere le colonne richieste |

---

## 3. Toolchain del modulo

### `requirements.txt`
```
pyspark==3.5.1
```
> Glue 5.0 usa Spark 3.5. `pytest`/`pytest-cov` sono installati dal reusable
> workflow, non vanno qui. Aggiungi altre deps runtime SOLO se i job le importano
> davvero (`grep "^import\|^from" src/*.py`) — es. `boto3`, `python-dateutil`.

### `.coveragerc`
Template: [`references/coveragerc.ini`](references/coveragerc.ini) (rinominalo in `.coveragerc` nel modulo).
```ini
[run]
source = src
omit =
    tests/*
    configs/*
    */__init__.py

[report]
exclude_lines =
    pragma: no cover
    raise NotImplementedError
    if __name__ == .__main__.:
```
> `source = src` limita la misura al codice di produzione, escludendo `configs/`
> e i test stessi.

---

## 4. `tests/conftest.py` — copialo as-is

Questo file e' **indipendente dal dominio** (cambia solo `appName`). Risolve i
due problemi non banali della mail di Federico:
1. `awsglue.*` non e' installabile via pip → stub via `sys.modules`.
2. PySpark locale richiede `PYSPARK_PYTHON` allineato al driver e
   `spark.driver.bindAddress=127.0.0.1`.

Template completo in [`references/conftest.py`](references/conftest.py).
Crea anche `tests/__init__.py` (vuoto).

---

## 5. Test della libreria (`custom_classes.py`) — target 90%+

Due file, **da adattare** secondo lo Step 2:

- `tests/test_iceberg_glue_job.py` — `IcebergGlueJob`: env_prefix dev/prod,
  chiavi iceberg_config, custom_spark_config, set_spark_configs (file ok /
  mancante / JSON malformato). Template: [`references/test_iceberg_glue_job.py`](references/test_iceberg_glue_job.py).
  → rimuovi l'assert `mergeSchema` se la lib non lo setta.

- `tests/test_date_partitioned_glue_job.py` — `DatePartitionedGlueJob`: finestra
  delta, `force_no_window` (+ verifica che la partition condition diventi `"1=1"`),
  `RuntimeError` su window mancante, `create_partition_condition` (4 casi + sql_label),
  `get_incremental_dataframe` (happy / missing-col / **DataFrame vuoto**) e
  `get_delta_incremental_df` (happy/missing-col/empty-pk/dedup) con DataFrame
  Spark reali. Template: [`references/test_date_partitioned_glue_job.py`](references/test_date_partitioned_glue_job.py).
  → se NON c'e' `_parse_timestamp`: rimuovi i test ISO-8601 e usa `pytest.raises(ValueError)`
  generico per l'input invalido.

  > **Edge case obbligatori** (lezione da code review): (1) partition condition
  > `"1=1"` dopo `force_no_window=1`; (2) `get_incremental_dataframe` con DataFrame
  > a 0 righe ma schema corretto → risultato vuoto, non eccezione (frequente nei
  > job incrementali con finestra senza dati).

---

## 6. Smoke + class test dei job — per spingere la coverage globale

- `tests/test_jobs_smoke.py` — import dinamico di ogni `.py` (i nomi con `-` non
  sono module name validi → `importlib.util.spec_from_file_location`) e assert
  che la classe attesa esista. `test_all_jobs_listed` verifica anche il **check
  inverso** (`actual - expected == set()`): se un nuovo job in `src/` non viene
  censito in `JOB_SPECS` resterebbe senza test e farebbe scendere la coverage
  silenziosamente. Template: [`references/test_jobs_smoke.py`](references/test_jobs_smoke.py).

- `tests/test_jobs_classes.py` — istanzia ogni job class e chiama `run()` con
  Glue mockato e `isEmpty()=True` (salta il MERGE). Copre `__init__` + parte
  iniziale di `run()`. Template: [`references/test_jobs_classes.py`](references/test_jobs_classes.py).

> **Honest coverage (mail Federico):** "non scriviamo test inutili solo per
> arrivare al numero". Il blocco MERGE resta scoperto di proposito — e' SQL
> Iceberg testabile solo a runtime. Tipicamente si arriva a **~80%** con
> lib al 100% e job al 78-80%, sopra la soglia senza gonfiare.

In tutti e quattro i file di test, aggiorna `JOB_SPECS` con le coppie
`(filename, ClassName)` reali estratte allo Step 2.

---

## 7. CI, README e .gitignore

### `.github/workflows/ci-python-coverage.yaml`
Caller del reusable — cambia SOLO il path in `modules:`.
Template: [`references/ci-python-coverage.yaml`](references/ci-python-coverage.yaml).

```yaml
on:
  pull_request:
    paths:
      - 'modules/silver-{domain}/glue-jobs/**'
      - '.github/workflows/ci-python-coverage.yaml'
  push:
    branches: ['release/**']   # NON main: evita doppio update di TEST_COVERAGE_PERCENTAGE
  workflow_dispatch:
jobs:
  coverage:
    uses: itsiae/siae-gh-actions/.github/workflows/pytest-coverage.yaml@v3.0.0
    with:
      modules: |
        modules/silver-{domain}/glue-jobs
      python_version: '3.11'
      min_coverage_threshold: 70
    secrets: inherit
```

### `.gitignore` — aggiungi (se non gia' presenti)
```
# Python test artifacts
*.egg-info/
.coverage
.pytest_cache/
.venv/
venv/
__pycache__/
coverage.xml
```

### README modulo
`modules/silver-{domain}/glue-jobs/README.md` con istruzioni run locale +
note sullo stub awsglue. Template: [`references/README.md`](references/README.md).

---

## 8. Esecuzione locale

```bash
cd modules/silver-{domain}/glue-jobs
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest pytest-cov
pytest tests/ --cov=. --cov-config=.coveragerc --cov-fail-under=70
```

> Serve **Java JDK** (PySpark). I runner GitHub Actions Ubuntu ce l'hanno gia'.
> Se 3.11 non e' disponibile in locale, 3.9/3.10 vanno bene per il check locale
> (pyspark 3.5.1 e' compatibile); la CI usa comunque 3.11.

### Output atteso (GREEN)
```
NN passed in XXs
Required test coverage of 70% reached. Total coverage: 82.40%
```

### PULIZIA OBBLIGATORIA prima del commit
```bash
rm -rf .venv .coverage .pytest_cache src/__pycache__ src/libs/__pycache__ tests/__pycache__
git status --short    # deve mostrare SOLO file sorgente
```

---

## 9. Troubleshooting

| Errore | Causa | Fix |
|--------|-------|-----|
| `ModuleNotFoundError: awsglue` | stub non caricato prima dell'import | `_stub_awsglue()` deve girare a import-time in conftest (gia' cosi' nel template) |
| `Java gateway process exited` | JDK assente | installa `default-jdk`, verifica `java -version` |
| `PYTHON_VERSION_MISMATCH` worker/driver | piu' interpreti nel PATH | il conftest setta `PYSPARK_PYTHON=sys.executable` — gia' gestito |
| `assert ... mergeSchema` fallisce | lib senza `mergeSchema` | rimuovi l'assert (Step 2) |
| test `_parse_timestamp` / ISO-8601 falliscono | lib senza quel metodo | rimuovi quei test, usa `ValueError` generico (Step 2) |
| `Missing mandatory columns` inatteso | colonne di test non allineate alla lib | leggi `required_columns` reale e allinea `createDataFrame` |
| coverage sotto soglia | MERGE non coperto + lib incompleta | aggiungi test mirati sulla lib (non sui job); NON gonfiare |
| `.venv` compare in `git status` | gitignore mancante | aggiungi entry Step 7 |

---

## 10. Limiti Operativi

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Tentativi per test rosso | 2 | Rileggi la lib reale (Step 2), non il template |
| Coverage gonfiata artificialmente | vietato | Solo test con valore reale (indicazione Federico) |
| Modifica codice di produzione | minimale | Refactor solo se serve per testabilita', preservando il comportamento Glue 5.0 |

---

REQUIRED SUB-SKILL: siae-verification

Invoca `siae-verification` (pytest verde + coverage sopra soglia con evidenza)
prima di dichiarare i test completati.

---

## Classificazione Rischio Operazioni

| Operazione | Rischio | Card |
|------------|---------|------|
| Scrittura file `tests/`, requirements, workflow | 🟢 Sicuro | No |
| `pytest` locale (Spark locale, no AWS) | 🟢 Sicuro | No |
| `pip install` in venv isolato | 🟢 Sicuro | No |
| Refactor `custom_classes.py` / job `src/` | 🟡 Medio | Si — preserva comportamento runtime |
| Commit/push/PR | 🟡 Medio | Vedi `siae-git-workflow` |
