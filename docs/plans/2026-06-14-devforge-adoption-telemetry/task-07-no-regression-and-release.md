# Task 07 — No-regression, registrazione test, version bump

**Goal:** registrare i 5 nuovi test bash nel runner, eseguire l'intera suite + pytest,
verificare il count consistency (hook count invariato) e l'assenza di modifiche infra,
bumpare la versione dual-source. Copre AC9, AC10.

**File coinvolti:**
- Modifica: `tests/run-all.sh` (registra 5 nuovi `.test.sh` + 1 pytest)
- Modifica: `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` (version bump)

**Dipendenza:** Task 01-06 completati.

## Step 1 — Verifica RED: i nuovi test non sono nel runner

Run:
```bash
cd "$(git rev-parse --show-toplevel)"
for t in test_adoption_emit test_stop_gate_task_adoption_wiring \
         test_session_start_enforcement_off test_post_commit_no_verify test_post_commit_task_id; do
  grep -q "$t" tests/run-all.sh && echo "PRESENTE $t" || echo "MANCANTE $t"
done
```
Output atteso: 5× `MANCANTE` (non ancora registrati).

## Step 2 — Verifica count consistency PRIMA del bump

Run: `python3 -m pytest tests/test_count_consistency.py -v`
Output atteso: `passed` — Layer 1 NON aggiunge file hook in `hooks/` (solo `lib/adoption-emit.sh`,
escluso dal conteggio hook; e modifiche a hook esistenti). Il conteggio hook resta invariato
→ nessun aggiornamento di descrizione count richiesto in plugin.json/marketplace.json.

## Step 3 — Registra i 5 test nel runner

In `tests/run-all.sh`, nella sezione hook-tests (dopo il blocco
`test_net_resilience_wiring.sh`, ~riga 1169), aggiungi per OGNI nuovo test questo blocco
(sostituendo `<NOME>` e la descrizione):

```bash
if bash "${PLUGIN_ROOT}/tests/hooks/<NOME>.sh" >/dev/null 2>&1; then
  echo "  PASS  tests/hooks/<NOME>.sh"
  TOTAL_PASS=$((TOTAL_PASS + 1))
else
  echo "  FAIL  tests/hooks/<NOME>.sh"
  TOTAL_FAIL=$((TOTAL_FAIL + 1))
fi
```

> NB: i file test creati nei Task 02-06 seguono la convenzione `test_*.sh` (NON `*.test.sh`).
> Il path completo è `tests/hooks/<NOME>.sh`, es. `tests/hooks/test_adoption_emit.sh`.

I 5 nomi (file `tests/hooks/<NOME>.sh`):
- `test_adoption_emit`
- `test_stop_gate_task_adoption_wiring`
- `test_session_start_enforcement_off`
- `test_post_commit_no_verify`
- `test_post_commit_task_id`

E aggiungi un blocco per il test Python (dopo i 5 sopra):

```bash
if python3 -m pytest "${PLUGIN_ROOT}/tests/test_task_adoption_meta.py" -q >/dev/null 2>&1; then
  echo "  PASS  tests/test_task_adoption_meta.py"
  TOTAL_PASS=$((TOTAL_PASS + 1))
else
  echo "  FAIL  tests/test_task_adoption_meta.py"
  TOTAL_FAIL=$((TOTAL_FAIL + 1))
fi
```

## Step 4 — Verifica GREEN: registrati + suite verde

Run:
```bash
cd "$(git rev-parse --show-toplevel)"
for t in test_adoption_emit test_stop_gate_task_adoption_wiring \
         test_session_start_enforcement_off test_post_commit_no_verify test_post_commit_task_id; do
  grep -q "$t" tests/run-all.sh && echo "PRESENTE $t" || echo "MANCANTE $t"
done
```
Output atteso: 5× `PRESENTE`.

Run suite nuova (rapida):
```bash
for t in test_adoption_emit test_stop_gate_task_adoption_wiring \
         test_session_start_enforcement_off test_post_commit_no_verify test_post_commit_task_id; do
  bash "tests/hooks/$t.sh" >/dev/null 2>&1 && echo "PASS $t" || echo "FAIL $t"
done
python3 -m pytest tests/test_task_adoption_meta.py -q
```
Output atteso: 5× `PASS` + pytest `passed`.

Run suite completa:
```bash
bash tests/run-all.sh
```
Output atteso: nessuna nuova `FAIL` rispetto al baseline pre-Layer-1 (i 6 nuovi check PASS).

## Step 5 — Verifica AC9 (zero modifiche infra) + version bump + commit

Verifica AC9 (nessuna modifica a Lambda/Terraform da Layer 1):
```bash
git diff --name-only main...HEAD -- infra/telemetry/ | grep -q . && echo "ERRORE: infra modificata" || echo "OK: infra/telemetry invariata"
```
Output atteso: `OK: infra/telemetry invariata`.

Bump versione (dual-source, memoria `plugin_version_dual_source`): `1.86.0` → `1.87.0` in
ENTRAMBI i file:
- `.claude-plugin/plugin.json` → `"version": "1.87.0"`
- `.claude-plugin/marketplace.json` → `"version": "1.87.0"`

Run count consistency finale: `python3 -m pytest tests/test_count_consistency.py -v` → `passed`.

```bash
git add tests/run-all.sh .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "chore(release): registra test Layer 1 telemetria adoption + bump 1.87.0 (task-07)"
```

## Criteri di accettazione
- [ ] I 5 test bash + 1 pytest sono registrati in `run-all.sh` ed eseguiti.
- [ ] `tests/run-all.sh` non introduce nuove FAIL rispetto al baseline.
- [ ] `test_count_consistency.py` PASS (hook count invariato — nessun nuovo hook) (AC10).
- [ ] `git diff main...HEAD -- infra/telemetry/` vuoto (AC9).
- [ ] Versione `1.87.0` allineata in plugin.json + marketplace.json.
