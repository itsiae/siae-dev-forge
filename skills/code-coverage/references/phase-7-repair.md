# Phase 7 — Repair Loop

## Purpose
Riparare test che falliscono (o moduli sotto threshold) con un loop bounded,
deterministico, anti-thrash. Massimizza il throughput per coverage gain e
abortisce best-effort quando il progresso si ferma.

---

## Budget

- **max 3 iterazioni totali**
- **max 1 full coverage run per iterazione** (re-run solo i test modificati
  fino a fine iter; coverage full solo a chiusura)
- **early-abort autonomous** (vedi sotto)

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

### Step 5 — Progress guard

Calcola delta vs iterazione precedente:

```python
delta_global = global_cov_now - global_cov_prev
delta_failing = failing_count_now - failing_count_prev

if delta_global < 0.5 and delta_failing >= 0:
    # No progress → STOP best-effort
    emit_block_8_with_stalled_files()
    exit_repair_loop()
```

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
- Loop > 3 iter (hard cap, no override).
- Re-run completo (`--coverage`) ad ogni Edit (wall-time esplode).

---

## Lazy-load asset

Al primo failure della session, carica `assets/anti-patterns.md` ONCE per
mostrare alla LLM i 3 BAD/GOOD pair. Non ricaricarlo nelle iter successive.
