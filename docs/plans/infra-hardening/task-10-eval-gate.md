# Task 10: Eval Gate con Soglie (D10)

**Deliverable:** D10
**Dipendenze:** nessuna (indipendente)
**File coinvolti:** `evals/trigger-evals/*.json` (29 file), `tests/run-trigger-eval.py`, `tests/run-trigger-regression.sh`

---

## Step 1 — Aggiungi campo `threshold` agli eval file

Per ciascuno dei 29 file in `evals/trigger-evals/*.json`, aggiungi il campo `threshold`:

```json
{
  "skill": "siae-brainstorming",
  "threshold": { "precision": 0.8, "recall": 0.8 },
  "queries": ["query 1", "query 2"]
}
```

**Soglie iniziali (conservative):**
- Skill core (brainstorming, tdd, debugging, verification, git-workflow): `precision: 0.8, recall: 0.8`
- Skill di dominio (iac, frontend, data-engineering, flutter): `precision: 0.7, recall: 0.7`
- Skill rare (autoresearch, writing-skills, finops): `precision: 0.6, recall: 0.6`

Lista completa:

| Skill | Precision | Recall |
|-------|-----------|--------|
| siae-brainstorming | 0.8 | 0.8 |
| siae-tdd | 0.8 | 0.8 |
| siae-debugging | 0.8 | 0.8 |
| siae-verification | 0.8 | 0.8 |
| siae-git-workflow | 0.8 | 0.8 |
| siae-finishing-branch | 0.7 | 0.7 |
| siae-code-standards | 0.7 | 0.7 |
| siae-architecture | 0.7 | 0.7 |
| siae-iac | 0.7 | 0.7 |
| siae-frontend | 0.7 | 0.7 |
| siae-data-engineering | 0.7 | 0.7 |
| siae-security | 0.7 | 0.7 |
| siae-automation | 0.7 | 0.7 |
| siae-qa | 0.7 | 0.7 |
| Tutte le altre | 0.6 | 0.6 |

## Step 2 — Aggiorna `run-trigger-eval.py` per leggere/validare threshold

Dopo il parsing degli argomenti, leggere il threshold dall'eval file:

```python
# Read threshold from eval file
with open(args.eval_file) as f:
    eval_data = json.load(f)
threshold = eval_data.get('threshold', {'precision': 0.0, 'recall': 0.0})
```

A fine esecuzione, confrontare i risultati con la soglia e produrre un campo `threshold_pass` nell'output:

```python
results['threshold'] = threshold
results['threshold_pass'] = (
    results.get('precision', 0) >= threshold['precision'] and
    results.get('recall', 0) >= threshold['recall']
)
```

## Step 3 — Aggiorna `run-trigger-regression.sh` per gate con exit code

Dopo che tutti gli eval sono completati, controlla i risultati:

```bash
# Check thresholds
THRESHOLD_FAILURES=0
for result_file in "${RESULTS_DIR}"/*-latest.json; do
  [ ! -f "$result_file" ] && continue
  pass=$(python3 -c "
import json, sys
r = json.load(open('$result_file'))
print('pass' if r.get('threshold_pass', True) else 'fail')
" 2>/dev/null || echo "pass")
  if [ "$pass" = "fail" ]; then
    skill_name=$(basename "$result_file" -latest.json)
    echo "  FAIL  ${skill_name}: sotto soglia threshold"
    THRESHOLD_FAILURES=$((THRESHOLD_FAILURES + 1))
  fi
done

if [ "$THRESHOLD_FAILURES" -gt 0 ]; then
  echo ""
  echo "THRESHOLD GATE: ${THRESHOLD_FAILURES} skill sotto soglia"
  exit 1
fi
```

## Step 4 — Aggiungi salvataggio baseline storica

In `run-trigger-eval.py`, dopo aver scritto i risultati:

```python
# Save timestamped baseline
from datetime import datetime
baseline_path = os.path.join(
    args.results_dir,
    f"{args.skill}-{datetime.now().strftime('%Y%m%d')}.json"
)
with open(baseline_path, 'w') as f:
    json.dump(results, f, indent=2)
```

## Step 5 — Aggiungi summary report

In `run-trigger-regression.sh`, a fine esecuzione:

```bash
# Generate regression summary
python3 -c "
import json, glob, os
results = []
for f in sorted(glob.glob('${RESULTS_DIR}/*-latest.json')):
    with open(f) as fh:
        r = json.load(fh)
        results.append({
            'skill': r.get('skill', os.path.basename(f)),
            'precision': r.get('precision', 0),
            'recall': r.get('recall', 0),
            'threshold_pass': r.get('threshold_pass', True)
        })
with open('${RESULTS_DIR}/regression-summary.json', 'w') as fh:
    json.dump({'results': results, 'total': len(results),
               'pass': sum(1 for r in results if r['threshold_pass']),
               'fail': sum(1 for r in results if not r['threshold_pass'])}, fh, indent=2)
print('Summary:', '${RESULTS_DIR}/regression-summary.json')
" 2>/dev/null || true
```

## Step 6 — Verifica

```bash
# Verifica che tutti i 29 eval file hanno threshold
for f in evals/trigger-evals/*.json; do
  has_threshold=$(python3 -c "import json; d=json.load(open('$f')); print('yes' if 'threshold' in d else 'no')")
  if [ "$has_threshold" != "yes" ]; then
    echo "MISSING threshold: $f"
  fi
done
```
Output atteso: nessun output (tutti hanno threshold).

## Step 7 — Commit

```bash
git add evals/trigger-evals/*.json tests/run-trigger-eval.py tests/run-trigger-regression.sh
git commit -m "feat(eval): add precision/recall thresholds to trigger eval gate

- Each eval file now has a threshold field (precision + recall)
- run-trigger-regression.sh exits 1 if any skill is below threshold
- Timestamped baselines saved in evals/results/ for trend tracking
- Summary report generated in evals/results/regression-summary.json

Co-Authored-By: SIAE DevForge"
```
