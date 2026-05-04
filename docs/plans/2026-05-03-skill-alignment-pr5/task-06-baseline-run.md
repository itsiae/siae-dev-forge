# Task 06 — Run Baseline Completa (30 prompt)

**Goal:** Run completa 30 prompt PRE description audit (Task 07-09) per immutable baseline. Critico per principio no-regression.

**File coinvolti:**
- Read-only: `run.sh`, `evaluator.py`, `cases.yml`
- Output: `tests/skill-activation/baseline-2026-05-03.md` (immutabile, committato)

## Step 1 — Setup

```bash
export AWS_REGION=eu-west-1
export CLAUDE_CODE_USE_BEDROCK=1
[ -n "${AWS_BEARER_TOKEN_BEDROCK:-}" ] || exit 1
cd tests/skill-activation
```

## Step 2 — Run baseline Sonnet 4.6

```bash
TEST_MODEL=sonnet ./run.sh
```

Cost: ~$0.04. Run NON parziale, deve completare tutti 30.

## Step 3 — Genera report baseline

```bash
LOG=$(ls -t .cache/run-*.jsonl | head -1)
python3 evaluator.py "$LOG" --label baseline-pre-pr5
mv report-$(date +%F)-baseline-pre-pr5.md baseline-2026-05-03.md
```

## Step 4 — Verifica report completo

```bash
grep -c '^| ' baseline-2026-05-03.md  # ~30+ righe tabella
grep '^- \*\*activation_accuracy\*\*' baseline-2026-05-03.md
```

Output atteso:
- ≥30 righe tabella (header + 30 case)
- KPI activation_accuracy presente

## Step 5 — Documenta cost effettivo

Aggiungi a `baseline-2026-05-03.md` in fondo:

```markdown
## Run metadata

- Date: 2026-05-03
- Model: eu.anthropic.claude-sonnet-4-6-20250929-v1:0
- Region: eu-west-1
- Cost effettivo: $X.XX (verifica AWS console)
```

## Step 6 — Commit IMMUTABILE

```bash
git add tests/skill-activation/baseline-2026-05-03.md
git commit -m "test(skill-activation): baseline pre-PR-5 (30 prompt, Sonnet 4.6)

Misura activation accuracy + chain_completeness + forbidden_rate PRIMA delle
modifiche description (Task 07-09). Riferimento immutabile per no-regression.
Tutti task successivi NON devono ridurre accuracy per skill toccata."
```

## Criteri accettazione

- File `baseline-2026-05-03.md` esiste, committato
- Tabella 30 case completa
- KPI numerici chiari
- Cost effettivo documentato in metadata

## NO-REGRESSION reference

Questo file è il riferimento per Task 14. **Mai modificare dopo il commit.**

Se accuracy baseline è bassa (<60%) — questo è già un finding: significa che molte skill non vengono attivate correttamente nemmeno PRIMA delle modifiche. Salva l'output ma flagga l'incognita per Task 07-09 (description rewrite mira a migliorare).
