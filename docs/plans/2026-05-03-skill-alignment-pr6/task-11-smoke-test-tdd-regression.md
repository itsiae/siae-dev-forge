# Task 11 — Smoke Test Pre-Merge: TDD Regression

**Goal:** Eseguire suite Bedrock 30 prompt + 10 prompt extra TDD-specific per validare:
1. PR-6 non degrada accuracy globale (no-regression vs PR-5)
2. tdd trigger reduction (Task 01) ha effetto atteso: 6/10 ancora attivano siae-tdd, 4/10 deviati a brainstorming

**File coinvolti:**
- Read-only: `tests/skill-activation/`
- Output: `tests/skill-activation/report-2026-05-03-post-pr6.md`
- Output: `tests/skill-activation/cases-tdd-regression.yml` (nuovo, 10 prompt extra)
- Output: `docs/measurements/skill-alignment-pr6-summary-2026-05-03.md`

## Step 1 — Aggiungi 10 prompt TDD-regression

In `tests/skill-activation/cases-tdd-regression.yml`:

```yaml
# 10 prompt che usavano vecchie keyword tdd, ora dovrebbero deviare a brainstorming
# (4) o restare su tdd (6)

- id: tdd-keep-1
  prompt: "TDD per nuova feature pagamento"
  expected_primary: siae-tdd

- id: tdd-keep-2
  prompt: "ciclo Red-Green-Refactor sulla funzione X"
  expected_primary: siae-tdd

- id: tdd-keep-3
  prompt: "scrivo test prima del codice per validateISRC"
  expected_primary: siae-tdd

- id: tdd-keep-4
  prompt: "test-driven development sul modulo auth"
  expected_primary: siae-tdd

- id: tdd-keep-5
  prompt: "refactoring del modulo X con test"
  expected_primary: siae-tdd

- id: tdd-keep-6
  prompt: "pytest scrittura test isrc validator"
  expected_primary: siae-tdd

- id: tdd-deviate-1
  prompt: "implementa la funzione validateISRC"
  expected_primary: siae-brainstorming  # design first

- id: tdd-deviate-2
  prompt: "scrivo nuovo metodo X"
  expected_primary: siae-brainstorming

- id: tdd-deviate-3
  prompt: "modifico la logica di calcolo"
  expected_primary: siae-brainstorming

- id: tdd-deviate-4
  prompt: "creo classe MyService"
  expected_primary: siae-brainstorming
```

## Step 2 — Run suite principale (30 case)

```bash
cd tests/skill-activation
TEST_MODEL=sonnet ./run.sh
LOG=$(ls -t .cache/run-*.jsonl | head -1)
python3 evaluator.py "$LOG" --label post-pr6
```

## Step 3 — Run TDD regression (10 case extra)

`run.sh` supporta già `CASES_FILE` env var (PR-5 Task 03 — `: "${CASES_FILE:=cases.yml}"`).

```bash
TEST_MODEL=sonnet CASES_FILE=cases-tdd-regression.yml ./run.sh

LOG2=$(ls -t .cache/run-*.jsonl | head -1)
python3 evaluator.py "$LOG2" --label tdd-regression --cases cases-tdd-regression.yml
```

## Step 4 — Diff vs post-PR-5

```bash
python3 -c "
from pathlib import Path
import re

p5 = Path('tests/skill-activation/report-2026-05-03-post-pr5.md').read_text()
p6 = Path('tests/skill-activation/report-2026-05-03-post-pr6.md').read_text()

def acc(md):
    m = re.search(r'activation_accuracy.*?(\d+\.\d+)%', md)
    return float(m.group(1)) if m else 0

print(f'PR-5: {acc(p5)}%, PR-6: {acc(p6)}%, delta: {acc(p6)-acc(p5):+.1f}pp')
"
```

## Step 5 — Validazione TDD regression

Verifica nel `report-2026-05-03-tdd-regression.md`:
- 6/6 prompt `tdd-keep-*` PASS (siae-tdd attivata)
- 4/4 prompt `tdd-deviate-*` PASS (siae-brainstorming attivata)

Se 1+ `tdd-keep-*` FAIL → riduzione trigger troppo aggressiva, rollback parziale (riaggiungi 1-2 keyword più importanti).
Se 1+ `tdd-deviate-*` FAIL → trigger ancora attiva tdd su prompt generici, ulteriore restringimento o rivedi brainstorming description.

## Step 6 — Genera summary

In `docs/measurements/skill-alignment-pr6-summary-2026-05-03.md`:

```markdown
# PR-6 Skill Alignment Summary

## Suite Bedrock 30 prompt

- Post-PR-5 accuracy: __%
- Post-PR-6 accuracy: __%
- Delta: __pp

## TDD regression suite (10 prompt extra)

- tdd-keep PASS: __/6  (target 6/6, hard pass)
- tdd-deviate PASS: __/4  (target 4/4, soft pass: 3/4 acceptable per stochasticity R8)
- Verdetto: PASS se tdd-keep == 6/6 AND tdd-deviate ≥ 3/4

## Cumulative no-regression

- Baseline (pre-PR-5): __%
- Post-PR-6: __%
- Cumulative delta: +__pp
```

## Step 7 — Commit

```bash
git add tests/skill-activation/cases-tdd-regression.yml tests/skill-activation/report-2026-05-03-post-pr6.md tests/skill-activation/report-2026-05-03-tdd-regression.md docs/measurements/skill-alignment-pr6-summary-2026-05-03.md
git commit -m "test(skill-activation): post-PR-6 + TDD regression suite

Suite 30 prompt + 10 prompt extra TDD regression.
- Accuracy globale: post-PR-5 X% → post-PR-6 Y% (delta +Zpp)
- TDD-keep: 6/6 PASS (trigger TDD-specific preservati)
- TDD-deviate: 4/4 PASS (prompt generici deviati a brainstorming)
- NO-REGRESSION cumulativa OK"
```

## Criteri accettazione

- 30 case suite + 10 case TDD eseguiti
- TDD-keep == 6/6 PASS (hard requirement, no-regression strict)
- TDD-deviate ≥3/4 PASS (soft, 3/4 acceptable per Risk R8 model stochasticity; 4/4 ideale)
- Accuracy globale ≥ post-PR-5

## NO-REGRESSION (CRITICAL)

Se TDD-keep fallisce (≥1 prompt TDD-specific perde attivazione siae-tdd):
1. Rollback parziale Task 01 — riaggiungi keyword più discriminanti
2. Re-run suite
3. Iterativo finché ≥6/6
