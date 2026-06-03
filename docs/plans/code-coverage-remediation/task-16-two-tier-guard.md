# Task 16 — Two-tier progress guard + strategy ladder

**Goal:** Sostituire il progress guard a singola soglia di Phase 7 con un guard a 2 livelli (locale `delta(N,N-1)<1pp` → cambia strategia; globale `delta(N,0)<5pp` dopo ≥2 iter + classify_intractable conferma → BEST_EFFORT genuino) e una strategy ladder (`LINE → BRANCH_MATRIX → REFLECTION → CLASS_MOCK → TZ_MOCK → FULL_FIXTURE`). Risolve gap 6.10/R9 (abort a 51% quando cambiando strategia si arrivava a target). È documentazione di processo in `phase-7-repair.md` (eseguita dall'LLM, non da uno script).

**WS:** WS-4 · **Dipendenze:** Task 14 (classify_intractable).

## File coinvolti
- Modifica: `skills/code-coverage/references/phase-7-repair.md` (sezione progress guard / Step 5)

## Prerequisito di lettura
Leggi `references/phase-7-repair.md` per individuare il blocco del progress guard attuale (cerca `delta_global` o "progress guard" o "BEST_EFFORT").

## Step 1 — Sostituisci il progress guard
Sostituisci il blocco del guard esistente con la macchina a 2 livelli:

````markdown
### Step 5 — Two-tier progress guard

Variabili (init all'ingresso Phase 7):
  cov_at_start = branch% baseline (fine Phase 6)
  strategy_index = 0   # indice in STRATEGY_LADDER

Dopo ogni iter N:
  delta_local  = branch_now - branch_prev      # iter N vs N-1
  delta_global = branch_now - cov_at_start      # iter N vs baseline
  LOCAL_STALL = 1.0 pp   GLOBAL_ABORT = 5.0 pp

  if delta_local >= LOCAL_STALL:
      → ACTIVE (continua con la stessa strategia)
  elif delta_local < LOCAL_STALL and delta_global >= GLOBAL_ABORT:
      → STALLED_LOCAL: advance_strategy(); se ladder esaurita → BEST_EFFORT
      → log: [phase7] guard=LOCAL stall iter=N delta_local=X delta_global=Y → advancing to <ladder[idx]>
  elif delta_global < GLOBAL_ABORT and iter >= 2:
      → per ogni file stalled: classify_intractable.py
        se almeno uno ∈ {NEEDS_REFLECTION, NEEDS_CLASS_MOCK, NEEDS_TZ_MOCK} → advance_strategy(), continua
        altrimenti → BEST_EFFORT genuino
      → log: [phase7] guard=GLOBAL delta_global=Y < 5pp → BEST_EFFORT

advance_strategy(): strategy_index += 1; se >= len(STRATEGY_LADDER) → segnale BEST_EFFORT.
  Salta un gradino se il suo prerequisito non è soddisfatto da nessun file stalled.

### STRATEGY_LADDER
0. LINE_COVERAGE_TESTS  — happy-path, default ingresso
1. BRANCH_MATRIX_TESTS  — template branch-matrix (Task 07), per ?? / || / && / ?:
2. REFLECTION_TESTS     — private methods via reflection (scan_private_methods.py)
3. CLASS_MOCK_TESTS     — vi.mock factory per classi inline (scan_class_instantiations.py)
4. TZ_MOCK_TESTS        — mockTz helper (scan_tz_usage.py)
5. FULL_FIXTURE_BUILDER — dual-fixture per file branch_operator_count > 40

Ordina i file stalled per branch_gap decrescente quando si avanza di gradino.
````

## Step 2 — Nota budget contesto
Aggiungi in fondo a Step 5:
```markdown
Per iter > 3 usa `parse_coverage.py --view repair` (payload ridotto) invece di --view full,
così le iter extra abilitate da max_iter scaling non saturano il contesto.
```

## Step 3 — Verifica
Run: `grep -q "Two-tier progress guard" skills/code-coverage/references/phase-7-repair.md && echo OK` → `OK`.
Run: `grep -q "STRATEGY_LADDER" skills/code-coverage/references/phase-7-repair.md && echo OK` → `OK`.
Run: `grep -q "classify_intractable" skills/code-coverage/references/phase-7-repair.md && echo OK` → `OK`.

## Step 4 — Commit
```
git add skills/code-coverage/references/phase-7-repair.md
git commit -m "feat(code-coverage): two-tier progress guard + strategy ladder in Phase 7 repair"
```

## Criteri di accettazione
- [ ] Il guard distingue LOCAL stall (cambia strategia) da GLOBAL abort (BEST_EFFORT).
- [ ] La strategy ladder è documentata con i 6 gradini e i rispettivi scanner/template.
- [ ] BEST_EFFORT genuino richiede conferma da `classify_intractable.py` (no NEEDS_* residui).
- [ ] Nota budget per iter>3 con `--view repair`.
