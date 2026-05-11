# Task 00 — Benchmark Baseline

**Goal:** Raccogliere metriche pre-implementazione su 3 repo benchmark per consentire confronto post-PR8 e validazione policy go/no-go in design doc §5.3.

**SP:** 0.5 (Augmented)
**Fix IDs covered:** (prerequisito infrastrutturale, no fix funzionale)
**Branch:** `feat/code-coverage-opt-baseline`
**Dipendenze:** nessuna (è il primo task)

---

## File coinvolti

**Creazione**:
- `tools/benchmark-skill.sh` (~120 LOC bash)
- `docs/plans/2026-05-09-code-coverage-optimization/baseline-metrics.json` (output)

---

## Step bite-sized

### Step 1 — Scegli i 3 repo benchmark

Selezione fissa per riproducibilità:
- **SMALL**: clone temporaneo di `https://github.com/itsiae/sport-utils-service` (≤15 file source)
- **MEDIUM**: clone temporaneo di `https://github.com/itsiae/digital-channels-sport-fe` (~80 file Vue)
- **LARGE**: clone temporaneo di `https://github.com/itsiae/sport-gestione-licenze-service` (~300 file Java/Spring)

Documenta i 3 repo + commit SHA in `baseline-metrics.json` `repo_pinning` field.

### Step 2 — Crea lo script `tools/benchmark-skill.sh`

Struttura attesa (codice completo):

```bash
#!/usr/bin/env bash
# tools/benchmark-skill.sh — misura metriche skill code-coverage
# Usage: ./tools/benchmark-skill.sh <repo-path> <run-label>

set -euo pipefail

REPO_PATH="${1:?repo path required}"
RUN_LABEL="${2:?run label required (es. baseline | post-pr1)}"
OUT_FILE="${3:-docs/plans/2026-05-09-code-coverage-optimization/baseline-metrics.json}"

START_TS=$(date +%s)
START_TOKENS=0  # populated by Claude API usage telemetry post-run

# 1. Conta approval gate triggers nel log conversazione (manuale per baseline)
GATE_COUNT=0  # scrittura manuale post-run leggendo transcript

# 2. Conta full coverage run (cerca pattern "vitest run --coverage", "pytest --cov", etc. in log)
COVERAGE_RUNS=$(grep -cE '(vitest run --coverage|pytest --cov|mvn test|gradle test|cargo tarpaulin)' "$REPO_PATH/.code-coverage/decisions.log" 2>/dev/null || echo 0)

# 3. Misura iter Phase 7 (cerca "iteration" nel decisions.log)
PHASE7_ITER=$(grep -cE 'iteration [0-9]+' "$REPO_PATH/.code-coverage/decisions.log" 2>/dev/null || echo 0)

# 4. Conta reference file load (cerca "Read references/phase-" nel log)
REF_LOADS=$(grep -cE 'phase-[1-7]-.+\.md' "$REPO_PATH/.code-coverage/decisions.log" 2>/dev/null || echo 0)

# 5. Coverage finale (parse coverage-output.txt o coverage-report.json se esiste)
GLOBAL_PCT=0
P1_PCT=0
if [ -f "$REPO_PATH/.code-coverage/coverage-report.json" ]; then
  GLOBAL_PCT=$(python3 -c "import json; print(json.load(open('$REPO_PATH/.code-coverage/coverage-report.json'))['global_pct'])")
  P1_PCT=$(python3 -c "import json; d=json.load(open('$REPO_PATH/.code-coverage/coverage-report.json')); p1=[m for m in d['modules'] if m.get('priority')=='P1']; print(min((m['lines_pct'] for m in p1), default=0))")
elif [ -f "$REPO_PATH/.code-coverage/coverage-output.txt" ]; then
  GLOBAL_PCT=$(grep -oE 'All files.*?[0-9]+\.[0-9]+' "$REPO_PATH/.code-coverage/coverage-output.txt" | head -1 | grep -oE '[0-9]+\.[0-9]+' | head -1 || echo 0)
fi

# 6. Wall-clock (END_TS - START_TS, ma per baseline wall-clock va misurato dall'invocazione utente)
END_TS=$(date +%s)
WALL_CLOCK=$((END_TS - START_TS))

# 7. Placeholder leakage (grep su test files generati)
PLACEHOLDER_LEAK=$(grep -rE '\{\{[A-Z_]+\}\}' "$REPO_PATH" --include='*.test.*' --include='*test_*.py' 2>/dev/null | wc -l | tr -d ' ')

# 8. Emit JSON entry
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
REPO_NAME=$(basename "$REPO_PATH")

python3 - <<PYEOF
import json
import os

out_path = os.environ.get("OUT_FILE", "$OUT_FILE")
entry = {
    "timestamp": "$TIMESTAMP",
    "run_label": "$RUN_LABEL",
    "repo_name": "$REPO_NAME",
    "repo_path": "$REPO_PATH",
    "metrics": {
        "user_round_trips": $GATE_COUNT,
        "full_coverage_runs": $COVERAGE_RUNS,
        "phase7_iterations": $PHASE7_ITER,
        "reference_loads": $REF_LOADS,
        "global_coverage_pct": $GLOBAL_PCT,
        "p1_min_coverage_pct": $P1_PCT,
        "wall_clock_seconds": $WALL_CLOCK,
        "placeholder_leakage": $PLACEHOLDER_LEAK
    }
}

# Append to JSON list
data = []
if os.path.exists(out_path):
    with open(out_path) as f:
        data = json.load(f)
data.append(entry)
with open(out_path, "w") as f:
    json.dump(data, f, indent=2)
print(f"Appended baseline entry for {entry['repo_name']} ({entry['run_label']})")
PYEOF
```

### Step 3 — Esegui smoke test

Run: `bash tools/benchmark-skill.sh /tmp/sport-utils-service smoke-test` (clone manuale prima).

Output atteso:
```
Appended baseline entry for sport-utils-service (smoke-test)
```

Verifica file output esiste:
```bash
test -f docs/plans/2026-05-09-code-coverage-optimization/baseline-metrics.json && echo "OK"
```

Output atteso: `OK`

### Step 4 — Esegui baseline su 3 repo benchmark

Pre-condizione: skill `code-coverage` invocata su ogni repo prima dello script (per popolare `.code-coverage/`). Per il baseline iniziale invochi manualmente la skill nello stato attuale.

Sequenza:
```bash
git clone https://github.com/itsiae/sport-utils-service /tmp/bench-small
git clone https://github.com/itsiae/digital-channels-sport-fe /tmp/bench-medium
git clone https://github.com/itsiae/sport-gestione-licenze-service /tmp/bench-large

# Invoca skill su ognuno (manuale, baseline pre-fix)
# Per ogni repo, run /code-coverage <path> nella sessione Claude
# Annota a parte: numero approval [Y/n] dati, transcript token count

bash tools/benchmark-skill.sh /tmp/bench-small baseline
bash tools/benchmark-skill.sh /tmp/bench-medium baseline
bash tools/benchmark-skill.sh /tmp/bench-large baseline
```

Output atteso in `baseline-metrics.json`: 3 entry con `run_label: "baseline"` per ognuno dei 3 repo, ognuna con metriche popolate.

### Step 5 — Documenta token count manuale

Aggiungi al JSON, dopo l'esecuzione, il campo `transcript_tokens` per ogni entry baseline (estratto manualmente dalla telemetry Claude API o stima da `wc -c` del transcript se non disponibile).

Edit ogni entry baseline aggiungendo:
```json
"transcript_tokens": <numero>
```

### Step 6 — Commit

```bash
git checkout -b feat/code-coverage-opt-baseline
git add tools/benchmark-skill.sh docs/plans/2026-05-09-code-coverage-optimization/baseline-metrics.json
git commit -m "feat(code-coverage): add benchmark-skill.sh + collect baseline metrics on 3 repos

Baseline raccolta su SMALL/MEDIUM/LARGE per validare policy go/no-go
del piano docs/plans/2026-05-09-code-coverage-optimization/.

Co-Authored-By: SIAE DevForge"
```

PR title: `feat(code-coverage): baseline metrics + benchmark script`

---

## Acceptance criteria

- [ ] `tools/benchmark-skill.sh` esiste, eseguibile (`chmod +x`), passa smoke test
- [ ] `baseline-metrics.json` contiene 3 entry con `run_label: "baseline"`
- [ ] Ogni entry ha tutti gli 8 campi metrica popolati (anche `0` è valido se non applicabile)
- [ ] `transcript_tokens` popolato manualmente per ogni entry
- [ ] PR aperta con descrizione che cita il design doc §5.2
- [ ] Spec-reviewer PASS

## Note operative

- Lo script è bash + Python3 stdlib only (rispetta vincolo "no nuove dipendenze")
- Il baseline NON deve modificare la skill — sono solo misure
- `transcript_tokens` è approssimativo; baseline esatta richiede telemetry Claude API che potrebbe non essere disponibile localmente — accetta `null` con nota se non misurabile
- Lo script verrà ri-eseguito post-PR1, post-PR4, post-PR8 con label diverso (es. `post-pr1`, `post-pr4`, `final`) per misurare il delta
