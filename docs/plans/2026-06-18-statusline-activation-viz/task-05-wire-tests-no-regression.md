# Task 05 — Wiring test in run-all.sh + no-regression

**Stato:** [PENDING]
**File:** `tests/run-all.sh`
**Stima:** Umano ~0.5 · Augmented ~0.25

## Contesto
`run-all.sh` invoca i test esplicitamente per path (no auto-discovery). I 4 test nuovi vanno cablati o non girano in CI ([[feedback_tdd_unit_vs_integration_gap]]).

## Azioni

### 1. Cabla i 5 test
Individua la sezione test bash (pattern blocchi `if bash "${PLUGIN_ROOT}/tests/..." >/dev/null 2>&1; then echo PASS; TOTAL_PASS=$((TOTAL_PASS + 1)); else echo FAIL; TOTAL_FAIL=$((TOTAL_FAIL + 1)); fi`, già usato per i test statusline di PR #339 intorno a riga ~1229). Aggiungi 5 blocchi col pattern identico per:
```
tests/statusline/test_statusline_version_label.sh
tests/statusline/test_statusline_git_cache_perrepo.sh
tests/statusline/test_statusline_telemetry_health.sh
tests/zero-loss/unit/test_logger_perl_fsync.sh
tests/zero-loss/unit/test_writepath_zeroloss_crossplatform.sh   # aggiornato in task-01: VERIFICATO non ancora cablato (grep "test_writepath" in run-all.sh = 0 match) → cablalo qui per far girare T3b/T9b aggiornate in CI
```
Usa la forma esatta con spazi `$((TOTAL_PASS + 1))` come gli altri blocchi del file.

> `test_writepath_zeroloss_crossplatform.sh` **NON è attualmente in run-all.sh** (verificato: 0 match). Cablalo per garantire che le T3b/T9b aggiornate da task-01 girino nella suite. `test_json_field_portable.sh` non è impattato da D2 → non obbligatorio cablarlo qui (fuori scope). Prima di aggiungere, ri-grep per evitare doppi.

### 2. No-regression
```bash
bash tests/run-all.sh 2>&1 | tail -40
```
- I 4 nuovi test PASS.
- Suite zero-loss verde (T3b/T9b aggiornati passano col tier perl).
- Nessun test preesistente passa da PASS a FAIL.
- I 3 test statusline di PR #339 (`test_statusline_python_warning`, `test_statusline_plugin_update`) ancora verdi col nuovo label versione (il loro grep è su riga 2, non sul label esatto — verificare).
- Nota nota: la full-suite locale può abortire su macOS per il bug pre-esistente Library/Caches ([[reference_testing_bash_statusline_hooks]]); usare l'invocazione diretta dei nuovi test come evidenza, non solo il conteggio full-suite.

## Criteri di completamento
- [ ] 4 nuovi test cablati col pattern esistente
- [ ] 4 nuovi test PASS via invocazione runner
- [ ] suite zero-loss verde (incl. T3b/T9b aggiornati)
- [ ] zero regressioni sui test statusline di PR #339
