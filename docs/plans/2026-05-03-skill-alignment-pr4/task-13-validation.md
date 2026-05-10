# Task 13 — Final Validation PR-4

**Goal:** Validare tutti i criteri accettazione PR-4 + diff vs baseline (Task 01) per principio no-regression.

**File coinvolti:**
- Output: `docs/measurements/skill-alignment-post-pr4-2026-05-03.md` (nuovo)
- Read-only: tutte 8 skill backbone, baseline da Task 01

## Step 1 — Genera report post-PR

```bash
#!/usr/bin/env bash
set -euo pipefail
OUT="docs/measurements/skill-alignment-post-pr4-2026-05-03.md"
BACKBONE=(siae-brainstorming siae-tdd siae-debugging siae-verification siae-writing-plans siae-executing-plans siae-finishing-branch using-devforge)

{
  echo "# Skill Alignment Post-PR-4 Validation 2026-05-03"
  echo
  echo "Branch: $(git rev-parse --abbrev-ref HEAD)"
  echo "Commit: $(git rev-parse HEAD)"
  echo
  echo "## Line counts (target <200)"
  echo
  echo "| Skill | Lines | Status |"
  echo "|---|---|---|"
  for s in "${BACKBONE[@]}"; do
    f="skills/$s/SKILL.md"
    if [ -f "$f" ]; then
      L=$(wc -l < "$f")
      [ "$L" -lt 200 ] && S="PASS" || S="FAIL"
      echo "| $s | $L | $S |"
    fi
  done
  echo
  echo "## Leakage grep (target 0)"
  echo
  echo '```'
  TOTAL=0
  for s in "${BACKBONE[@]}"; do
    f="skills/$s/SKILL.md"
    [ -f "$f" ] || continue
    M=$(grep -cE 'sport-\*|pop-\*|pae-\*|PRODUZIONE|CERTIFICAZIONE' "$f" || true)
    [ -z "$M" ] && M=0
    TOTAL=$((TOTAL + M))
    [ "$M" -gt 0 ] && echo "$s: $M match"
  done
  echo "TOTAL leakage match: $TOTAL"
  echo '```'
  echo
  echo "## Description pattern compliance ('Use when')"
  echo
  echo "| Skill | Compliant |"
  echo "|---|---|"
  for s in "${BACKBONE[@]}"; do
    f="skills/$s/SKILL.md"
    [ -f "$f" ] || continue
    if grep -q 'Use when' "$f"; then
      echo "| $s | YES |"
    else
      echo "| $s | NO |"
    fi
  done
  echo
  echo "## Reference files exist"
  echo
  for s in siae-debugging siae-finishing-branch siae-writing-plans siae-executing-plans siae-brainstorming; do
    if [ -d "skills/$s/reference" ]; then
      COUNT=$(ls "skills/$s/reference/" | wc -l | tr -d ' ')
      echo "- $s/reference/: $COUNT file"
    fi
  done
  echo
  echo "## Cross-reference integrity"
  echo
  echo '```'
  grep -rE 'REQUIRED SUB-SKILL: siae-[a-z-]+' skills/siae-{brainstorming,tdd,debugging,verification,writing-plans,executing-plans,finishing-branch}/SKILL.md skills/using-devforge/SKILL.md 2>/dev/null | while read line; do
    ref=$(echo "$line" | grep -oE 'siae-[a-z-]+' | tail -1)
    if [ -d "skills/$ref" ]; then
      echo "OK $line"
    else
      echo "MISSING $line"
    fi
  done | grep MISSING || echo "All cross-refs OK"
  echo '```'
} > "$OUT"

cat "$OUT"
```

## Step 2 — Diff vs baseline

```bash
diff -u docs/measurements/skill-alignment-baseline-2026-05-03.md docs/measurements/skill-alignment-post-pr4-2026-05-03.md | head -80
```

Verifica esistenza miglioramenti attesi:
- Tutti line count <200
- 0 leakage match
- 8/8 description "Use when" YES

## Step 3 — Smoke test attivazione consolidato

Prompt list (da eseguire MANUALMENTE in session test, baseline pre vs post):

| Prompt | Pre-PR-4 | Post-PR-4 |
|---|---|---|
| "ho un bug NPE su /endpoint" | siae-debugging | siae-debugging |
| "design feature nuova" | siae-brainstorming | siae-brainstorming |
| "implementa metodo X" | siae-tdd | siae-tdd |
| "il fix funziona" | siae-verification | siae-verification |
| "scrivi piano implementativo" | siae-writing-plans | siae-writing-plans |
| "esegui piano in nuova sessione" | siae-executing-plans | siae-executing-plans |
| "pronto per PR" | siae-finishing-branch | siae-finishing-branch |
| "inizio sessione" | using-devforge | using-devforge |

Tutte le 8 skill backbone devono attivarsi come prima (NO-REGRESSION).

Se ≥1 fallisce → rollback granulare quella skill, fix, rerun.

## Step 4 — Commit report

```bash
git add docs/measurements/skill-alignment-post-pr4-2026-05-03.md
git commit -m "docs(measurements): post-PR-4 validation report (no-regression OK)

8/8 backbone skill <200 righe. 0 leakage. 8/8 description 'Use when X'.
Smoke test: 8/8 backbone skill ancora attive sui prompt baseline."
```

## Step 5 — PR open prep

A questo punto PR-4 è pronta per `siae-finishing-branch` (vedi skill).

## Criteri accettazione

- Report post-PR-4 generato e committato
- Diff vs baseline mostra solo miglioramenti (no regressioni)
- Smoke test 8/8 PASS

## NO-REGRESSION FINAL CHECK

Se anche UNA skill backbone fallisce smoke test, NON aprire PR. Rollback granulare la skill problematica, indaga, fix mirato, rerun validation.
