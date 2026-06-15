# Task 04 — link README + no-regression

**Stato:** PENDING
**Dipende da:** task-03 (URL Pages nota)
**File:** `README.md`, suite test

## Obiettivo
Linkare la documentazione API navigabile dal README e confermare nessuna regressione.

## Attività
1. Aggiungere al README (sezione documentazione/API) una riga con la URL del sito Pages privato
   (da `gh api repos/itsiae/siae-dev-forge/pages --jq .html_url`), con nota "accessibile solo ai membri dell'org itsiae".
   Se task-03 è andato in fallback markdown → linkare invece `docs/api/telemetry-insights-api.md`.
2. No-regression: eseguire la suite test esistente (`tests/zero-loss/unit/*.sh` + `pytest tests/zero-loss`)
   + il nuovo `tests/docs/test_api_docs_site.sh` → 0 fail.
3. Verificare che `test_count_consistency.py::test_readme_version_matches_plugin` resti verde (il link non tocca la riga Versione).

## Criteri di accettazione (design AC 6)
README linka la URL Pages (o il markdown in fallback); suite verde; nessuna regressione introdotta.

## No-regression
Modifica additiva al README; nessun impatto su codice/hook.
