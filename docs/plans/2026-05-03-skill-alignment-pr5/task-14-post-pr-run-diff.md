# Task 14 — Run Post-PR-5 + Diff vs Baseline

**Goal:** Rieseguire suite Bedrock dopo description audit (Task 07-09) + tone-down (Task 13) + hook attivi (Task 10-12). Diff vs baseline (Task 06) per verificare no-regression.

**File coinvolti:**
- Read-only: `tests/skill-activation/cases.yml`, `baseline-2026-05-03.md`, runner, evaluator
- Output: `tests/skill-activation/report-2026-05-03-post-pr5.md`
- Output: `docs/measurements/skill-alignment-pr5-diff-2026-05-03.md`

## Step 1 — Setup

```bash
export AWS_REGION=eu-west-1
export CLAUDE_CODE_USE_BEDROCK=1
[ -n "${AWS_BEARER_TOKEN_BEDROCK:-}" ] || exit 1
cd tests/skill-activation
```

## Step 2 — Run post-PR

```bash
TEST_MODEL=sonnet ./run.sh
LOG=$(ls -t .cache/run-*.jsonl | head -1)
python3 evaluator.py "$LOG" --label post-pr5
ls report-*-post-pr5.md
```

Cost: ~$0.04.

## Step 3 — Genera diff report

In `docs/measurements/skill-alignment-pr5-diff-2026-05-03.md`:

```bash
python3 <<'PYEOF'
import re, sys
from pathlib import Path

base = Path("tests/skill-activation/baseline-2026-05-03.md").read_text()
post = Path(f"tests/skill-activation/report-{__import__('datetime').date.today().isoformat()}-post-pr5.md").read_text()

def parse_table(md):
    rows = {}
    for line in md.splitlines():
        if line.startswith("|") and "siae-" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 5:
                rows[parts[1]] = parts[2]  # id -> status
    return rows

def parse_kpi(md):
    m = re.search(r'activation_accuracy.*?(\d+\.\d+)%', md)
    return float(m.group(1)) if m else None

base_rows = parse_table(base)
post_rows = parse_table(post)
base_acc = parse_kpi(base)
post_acc = parse_kpi(post)

regressions = []
improvements = []
for case_id in base_rows:
    b = base_rows.get(case_id)
    p = post_rows.get(case_id)
    if b == "PASS" and p != "PASS":
        regressions.append(case_id)
    elif b != "PASS" and p == "PASS":
        improvements.append(case_id)

out = Path("docs/measurements/skill-alignment-pr5-diff-2026-05-03.md")
out.parent.mkdir(parents=True, exist_ok=True)
with out.open("w") as f:
    f.write(f"# Skill Alignment PR-5 Diff vs Baseline\n\n")
    f.write(f"- Baseline accuracy: {base_acc}%\n")
    f.write(f"- Post-PR-5 accuracy: {post_acc}%\n")
    f.write(f"- Delta: {(post_acc or 0) - (base_acc or 0):+.1f}pp\n\n")
    f.write(f"## Regressions ({len(regressions)})\n\n")
    for r in regressions:
        f.write(f"- {r}\n")
    f.write(f"\n## Improvements ({len(improvements)})\n\n")
    for i in improvements:
        f.write(f"- {i}\n")

print(f"Regressions: {len(regressions)}, Improvements: {len(improvements)}")
print(f"Delta accuracy: {(post_acc or 0) - (base_acc or 0):+.1f}pp")
PYEOF
```

## Step 4 — Decisione gate no-regression

Leggi `docs/measurements/skill-alignment-pr5-diff-2026-05-03.md`.

**Regola no-regression**:
- Se `Regressions == 0` → OK, procedi
- Se `Regressions ≥ 1` → identifica per skill, rollback granulare descripion di QUELLA skill, retry
- Se `Delta accuracy < 0` → BLOCK, indaga prima di committare

**Target ottimale**:
- Delta ≥ +15pp accuracy
- 0 regressioni

## Step 5 — Commit (solo se no-regression)

```bash
git add tests/skill-activation/report-2026-05-03-post-pr5.md docs/measurements/skill-alignment-pr5-diff-2026-05-03.md
git commit -m "test(skill-activation): post-PR-5 diff vs baseline (no-regression OK)

Activation accuracy: baseline X% → post Y% (delta +Zpp)
Regressions: 0/30. Improvements: N. Hook advisory + description audit
hanno migliorato discovery come previsto."
```

## Step 6 — Se regressioni: rollback granulare

Per ogni `regressing_case_id`:
1. Identifica skill `expected_primary` di quel case (consulta cases.yml)
2. `git diff main..HEAD -- skills/<skill>/SKILL.md`
3. Identifica modifica problematica nel description
4. Rollback parziale (es. ripristina trigger keyword chiave) preservando "Use when X" pattern
5. Run task 14 di nuovo

## Criteri accettazione

- Report post-PR + diff committati
- Delta accuracy ≥0 (no-regression assoluto)
- Idealmente +15pp

## NO-REGRESSION (CRITICAL GATE)

Questo task è il gate no-regression principale di PR-5. Se fallisce, non procedere a Task 15 / non aprire PR. Rollback iterativo finché Regressions == 0.
