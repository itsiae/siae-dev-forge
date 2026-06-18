# Task 04 — Wiring test in run-all.sh + no-regression full suite

**Stato:** [PENDING]
**File toccati:** `tests/run-all.sh`
**AC coperti:** garanzia che i 3 nuovi test girino in CI + no-regression globale
**Stima:** Umano ~0.5 · Augmented ~0.25

## Contesto

`tests/run-all.sh` invoca ogni test esplicitamente per path (no auto-discovery, verificato).
I 3 test nuovi (task 01-03) NON girerebbero finché non vengono cablati qui. Senza questo task
i test esistono ma sono morti in CI ([[feedback_tdd_unit_vs_integration_gap]]).

## Azioni

### 1. Cabla i 3 nuovi test in run-all.sh

Individua la sezione dei test hook/bash (pattern esistente, es. righe ~1136-1225 con blocchi
`if bash "${PLUGIN_ROOT}/tests/.../X.sh" >/dev/null 2>&1; then PASS else FAIL`). Aggiungi tre
blocchi analoghi, seguendo **esattamente** lo stesso pattern già presente:

```bash
if bash "${PLUGIN_ROOT}/tests/statusline/test_statusline_python_warning.sh" >/dev/null 2>&1; then
  echo "  PASS  tests/statusline/test_statusline_python_warning.sh"; TOTAL_PASS=$((TOTAL_PASS+1))
else
  echo "  FAIL  tests/statusline/test_statusline_python_warning.sh"; TOTAL_FAIL=$((TOTAL_FAIL+1))
fi

if bash "${PLUGIN_ROOT}/tests/hooks/test_session_start_plugin_update.sh" >/dev/null 2>&1; then
  echo "  PASS  tests/hooks/test_session_start_plugin_update.sh"; TOTAL_PASS=$((TOTAL_PASS+1))
else
  echo "  FAIL  tests/hooks/test_session_start_plugin_update.sh"; TOTAL_FAIL=$((TOTAL_FAIL+1))
fi

if bash "${PLUGIN_ROOT}/tests/statusline/test_statusline_plugin_update.sh" >/dev/null 2>&1; then
  echo "  PASS  tests/statusline/test_statusline_plugin_update.sh"; TOTAL_PASS=$((TOTAL_PASS+1))
else
  echo "  FAIL  tests/statusline/test_statusline_plugin_update.sh"; TOTAL_FAIL=$((TOTAL_FAIL+1))
fi
```

> Verifica i nomi reali delle variabili contatore in run-all.sh (`TOTAL_PASS`/`TOTAL_FAIL`
> confermati a riga ~32-33) e allinea i blocchi al pattern esatto del file (alcuni usano
> `TOTAL_PASS=$((TOTAL_PASS + 1))` con spazi).

### 2. No-regression full suite

Esegui l'intera suite e confronta con la baseline pre-modifica:

```bash
bash tests/run-all.sh 2>&1 | tail -30
```

- I 3 nuovi test devono comparire come PASS.
- Nessun test preesistente deve passare da PASS a FAIL.
- Conta i PASS/FAIL totali e confronta con la baseline catturata PRIMA delle modifiche
  (cattura baseline all'inizio del task: `git stash && bash tests/run-all.sh | grep -c PASS`,
  poi `git stash pop`). Delta atteso: +3 PASS, 0 nuovi FAIL.

## Criteri di completamento

- [ ] 3 nuovi test cablati in run-all.sh col pattern esistente
- [ ] `bash tests/run-all.sh` mostra i 3 nuovi test come PASS
- [ ] Zero regressioni: nessun test preesistente passa a FAIL (delta = +3 PASS, +0 FAIL)
- [ ] Conteggio totale verificato contro baseline pre-modifica
