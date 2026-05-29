# Phase 7 — Repair Loop

## Purpose
Riparare test che falliscono (o moduli sotto threshold) con un loop bounded,
deterministico, anti-thrash. Massimizza il throughput per coverage gain e
abortisce best-effort quando il progresso si ferma.

---

## Budget

- **max_iter = min(10, max(3, ceil(len(batch-plan.json.batches) × 1.5)))**
  (letto all'ingresso Phase 7; batch-plan.json assente → fallback 3)
- **max 1 full coverage run per iterazione** (re-run solo i test modificati
  fino a fine iter; coverage full solo a chiusura)
- **hard cap 10 iter (budget contesto)**
- **early-abort autonomous** (vedi sotto)

Budget init (eseguire all'ingresso Phase 7, nessun coverage run extra):
```python
import json, math, pathlib
bp = pathlib.Path(".code-coverage/batch-plan.json")
d = json.loads(bp.read_text()) if bp.exists() else {}
n = len(d.get("batches", d.get("pending_batches", []))) if d else 0
MAX_ITER = min(10, max(3, math.ceil(n * 1.5))) if n else 3
# Log: [phase7] max_iter=<MAX_ITER> batches=<n>
```

---

## Algorithm

### Step 1 — Categorize failures

Per ogni test fallito in `coverage-stdout.log`:

```bash
python3 skills/code-coverage/scripts/categorize_failure.py < <(
  awk '/FAIL|×|AssertionError/,/^$/' "$REPO/.code-coverage/coverage-stdout.log"
)
```

Output JSON: lista di `{test_path, error_signature, category}` dove
`category ∈ {1..6}` mappata su `assets/repair-strategies.json`.

### Step 2 — Group by error_signature

Raggruppa i failure per `error_signature`. Se:

- `count >= max(2, 30% del totale failures)`
- AND categoria è in `repair-strategies.json.systemic_eligible`

→ applica il fix **a livello config UNA volta** (es. `vitest.config.ts`,
`tsconfig.json`, `jest.setup.ts`). Log: `[phase7] systemic-fix cat=<n> count=<m>`.

Altrimenti → per-file scoped `Edit` su ciascun test (NO full-file regen).

### Step 3 — Re-run modified tests (no coverage)

```bash
# Esempio Vitest
npx vitest run <test_path_1> <test_path_2> ...
```

NO `--coverage` fino a fine iter (riduce wall-time del loop).

### Step 4 — Full coverage UNA volta a fine iter

```bash
bash skills/code-coverage/lib/phase6-coverage.sh "$REPO"
```

Aggiorna `coverage-report.json`.

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

Per iter > 3 usa `parse_coverage.py --view repair` (payload ridotto) invece di --view full,
così le iter extra abilitate da max_iter scaling non saturano il contesto.

### Step 6 — Autonomous early-abort

Trigger SOLO al termine di iter==1:

```python
if iter == 1:
    if global_cov_now < 30 and any(m["lines_pct"] < 40 for m in P1_modules):
        # Repository pathologically uncoverable, riduci budget rimanente
        loop_max_remaining = 2  # 1 retry only
```

Razionale: se dopo 1 iter completa siamo sotto 30% globale E un P1 è sotto
40%, il problema è strutturale (es. test env broken, mock missing, build error
mascherato come test failure). Continuare 2 iter altre brucia token senza
guadagno atteso > 5pp.

---

## Stalled Files reporting

Se max iter raggiunto SENZA convergenza, emetti in Block 8:

```markdown
### Stalled Files

| Path | Last error signature | Iterations attempted | Suggested manual action |
|------|----------------------|----------------------|--------------------------|
| ... | ... | 3 | ... |
```

`Suggested manual action` viene da `repair-strategies.json.manual_hints[category]`
quando definito.

---

## Anti-pattern (mai fare)

- Full-file rewrite di un test su un singolo assert failure.
- Modificare il modulo sorgente per soddisfare il test (è violazione del
  contratto "never modify production source", Phase 0 principio 1).
- Loop oltre max_iter calcolato (hard cap 10) senza cambio strategia.
- Re-run completo (`--coverage`) ad ogni Edit (wall-time esplode).

---

## Lazy-load asset

Al primo failure della session, carica `assets/anti-patterns.md` ONCE per
mostrare alla LLM i 3 BAD/GOOD pair. Non ricaricarlo nelle iter successive.
