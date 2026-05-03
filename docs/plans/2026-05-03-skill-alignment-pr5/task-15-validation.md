# Task 15 — Final Validation PR-5

**Goal:** Verificare tutti criteri accettazione PR-5 prima di aprire la PR.

**File coinvolti:**
- Read-only: skills/, hooks/hooks.json, hooks/, tests/skill-activation/, docs/measurements/

## Step 1 — Checklist criteri

Esegui ogni check, registra PASS/FAIL:

```bash
echo "## PR-5 Final Validation"

# 1. 39/39 description "Use when X"
TOTAL=$(ls skills/ | wc -l | tr -d ' ')
COMPLIANT=$(for f in skills/*/SKILL.md; do grep -l 'Use when' "$f"; done | wc -l | tr -d ' ')
echo "1. Description compliance: $COMPLIANT/$TOTAL — $([ "$COMPLIANT" = "$TOTAL" ] && echo PASS || echo FAIL)"

# 2. Hook registrati in hooks/hooks.json
HOOK_REG=$(python3 -c "
import json
s = json.load(open('hooks/hooks.json'))
hooks = s.get('hooks', {}).get('PostToolUse', [])
found = any('skill-advisory' in str(h) or 'state-writer' in str(h) for h in hooks)
print('PASS' if found else 'FAIL')
")
echo "2. Hook PostToolUse registrati: $HOOK_REG"

# 3. Hook eseguibili (no .sh extension per pattern repo)
[ -x hooks/skill-advisory ] && [ -x hooks/state-writer ] && \
  echo "3. Hook eseguibili: PASS" || echo "3. Hook eseguibili: FAIL"

# 4. Baseline + post-PR report committati
[ -f tests/skill-activation/baseline-2026-05-03.md ] && \
  [ -f tests/skill-activation/report-2026-05-03-post-pr5.md ] && \
  echo "4. Report commit: PASS" || echo "4. Report commit: FAIL"

# 5. Diff no-regression
DIFF_FILE="docs/measurements/skill-alignment-pr5-diff-2026-05-03.md"
if [ -f "$DIFF_FILE" ]; then
  REGR=$(grep -c "^- " <(awk '/## Regressions/,/## Improvements/' "$DIFF_FILE") || echo 0)
  REGR=$((REGR > 0 ? REGR - 1 : 0))  # subtract header
  echo "5. Regressions: $REGR — $([ "$REGR" -eq 0 ] && echo PASS || echo FAIL)"
fi

# 6. Verification tone-down
COUNT=$(grep -cE '\b(SEMPRE|MAI|NEVER|ALWAYS|MANDATORY)\b' skills/siae-verification/SKILL.md)
echo "6. Verification tone-down: $COUNT (≤3 PASS): $([ "$COUNT" -le 3 ] && echo PASS || echo FAIL)"

# 7. Cost effettivo Bedrock
echo "7. Cost effettivo (manual check AWS console): __ USD"
```

## Step 2 — KPI report

In `docs/measurements/skill-alignment-pr5-summary-2026-05-03.md`:

```markdown
# PR-5 Skill Alignment Summary

## Acceptance criteria

| # | Check | Status |
|---|---|---|
| 1 | 39/39 description "Use when X" | [da Step 1] |
| 2 | Hook PostToolUse registrati | [da Step 1] |
| 3 | Hook eseguibili | [da Step 1] |
| 4 | Baseline + post-PR committati | [da Step 1] |
| 5 | 0 regressioni | [da Step 1] |
| 6 | Verification tone ≤3 keyword | [da Step 1] |
| 7 | Cost <$5 | __ |

## KPI

- activation_accuracy baseline: __%
- activation_accuracy post-PR-5: __%
- delta: +__pp
- chain_completeness baseline: __%
- chain_completeness post-PR-5: __%
- forbidden_rate post-PR-5: __%

## Note operative

- [ ] Tool R6: matcher PostToolUse "Skill" funziona vs fallback ".*"
- [ ] Eventuale rollback granulare effettuato per skill X (vedi commits)
```

## Step 3 — Commit summary

```bash
git add docs/measurements/skill-alignment-pr5-summary-2026-05-03.md
git commit -m "docs(measurements): PR-5 final validation summary"
```

## Step 4 — Pre-flight PR

A questo punto invoca skill `siae-finishing-branch` per pre-flight checklist e PR open.

## Criteri accettazione

- 7/7 check Step 1 PASS
- KPI report completo
- Pre-flight pronto per PR

## NO-REGRESSION

Verifica finale: tutti i 30 case baseline ancora PASS o migliorati. 0 regressioni assolute.
