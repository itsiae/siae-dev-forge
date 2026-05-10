# Task 05 — Smoke Test Runner End-to-End

**Goal:** Validare l'intero stack runner+evaluator con 3 prompt prima di runnare baseline 30-prompt.

**File coinvolti:**
- Read-only: `tests/skill-activation/run.sh`, `evaluator.py`, `cases.yml`
- Output: `tests/skill-activation/report-YYYY-MM-DD-smoke.md`

## Step 1 — Setup env

```bash
export AWS_REGION=eu-west-1
export CLAUDE_CODE_USE_BEDROCK=1
# Verifica token presente
[ -n "${AWS_BEARER_TOKEN_BEDROCK:-}" ] || { echo "Token missing"; exit 1; }
```

## Step 2 — Run smoke con Haiku (cost-tight)

```bash
cd tests/skill-activation
TEST_MODEL=haiku ./run.sh --smoke
```

Output atteso:
- File `.cache/run-YYYYMMDD-HHMMSS.jsonl` con 3 entry
- Cost: ~$0.001 (tre chiamate Haiku)

## Step 3 — Run evaluator

```bash
LOG=$(ls -t .cache/run-*.jsonl | head -1)
python3 evaluator.py "$LOG" --label smoke
ls report-*-smoke.md
```

Output atteso:
- File `report-YYYY-MM-DD-smoke.md` con tabella 3 case
- Accuracy stampata in stdout

## Step 4 — Validazione output

Verifica:
- 3 case nel report (numero corretto)
- Almeno 1 case PASS (sanity check: il LLM router funziona basicamente)
- Nessun errore Python in stderr

Se 0/3 PASS → debug:
- Verifica skill descriptions presenti nel context (`cat .cache/skill-context.txt`)
- Verifica response Bedrock contiene JSON parseable
- Verifica nomi skill corrispondono (es. `name:` field nel SKILL.md frontmatter)

## Step 5 — Cleanup smoke artifacts

```bash
rm -f tests/skill-activation/report-*-smoke.md tests/skill-activation/.cache/*.jsonl
```

## Step 6 — Commit log smoke success (se OK)

Solo conferma che lo smoke funziona; non committiamo report smoke (sarebbe rumore).

```bash
echo "Smoke OK: $(date) - 3/3 calls successful, evaluator parses correctly" >> tests/skill-activation/.smoke-history
git add tests/skill-activation/.smoke-history 2>/dev/null || true
```

## Criteri accettazione

- Smoke completa senza errori
- Report markdown smoke generato (contenuto sensato)
- Cleanup finito

## NO-REGRESSION

Pure infrastrutturale.

## Decisione gate

Se smoke fallisce → NON procedere a Task 06 (baseline). Debug runner/evaluator.
