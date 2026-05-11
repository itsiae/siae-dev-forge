# Task 12 — Final Validation PR-6

**Goal:** Verifica tutti criteri accettazione PR-6 + KPI globali tutte 3 PR.

**File coinvolti:**
- Read-only: skills/, agents/, tests/skill-activation/, docs/measurements/

## Step 1 — Checklist PR-6

```bash
echo "## PR-6 Final Validation"

# 1. tdd trigger ≤8
COUNT=$(python3 -c "
import yaml
data = yaml.safe_load(open('skills/siae-tdd/SKILL.md').read().split('---')[1])
desc = data.get('description', '')
# Count keyword in 'Examples:' or 'Trigger:' part
import re
m = re.search(r'Trigger[s]?:.*', desc, re.IGNORECASE)
if m:
    keywords = [k.strip() for k in m.group(0).split(',') if k.strip()]
else:
    keywords = re.findall(r'\"([^\"]+)\"', desc)
print(len(keywords))
")
echo "1. tdd trigger keyword count: $COUNT — $([ "$COUNT" -le 8 ] && echo PASS || echo FAIL)"

# 2. CHANGELOG entry presente
grep -q '## \[Unreleased\]' CHANGELOG.md && grep -q 'siae-tdd' CHANGELOG.md \
  && echo "2. CHANGELOG entry: PASS" || echo "2. CHANGELOG entry: FAIL"

# 3. service-logic-map 2 modalità
grep -q "Mode A" skills/siae-service-logic-map/SKILL.md && \
  grep -q "Mode B" skills/siae-service-logic-map/SKILL.md && \
  echo "3. service-logic-map disambiguazione: PASS" || \
  echo "3. service-logic-map disambiguazione: FAIL"

# 4. 5 agent tool whitelist
COUNT_AGENT=0
for a in code-reviewer spec-reviewer mcp-impact-analyst qa-investigator doc-generator; do
  if python3 -c "import yaml; t=yaml.safe_load(open('agents/$a.md').read().split('---')[1]).get('tools'); exit(0 if t else 1)" 2>/dev/null; then
    COUNT_AGENT=$((COUNT_AGENT+1))
  fi
done
echo "4. Agent tool whitelist: $COUNT_AGENT/5 — $([ "$COUNT_AGENT" = "5" ] && echo PASS || echo FAIL)"

# 5. Sequence hint in 3+ skill
HINT_COUNT=0
for s in siae-verification siae-architecture siae-finishing-branch; do
  grep -q "Best after" skills/$s/SKILL.md && HINT_COUNT=$((HINT_COUNT+1))
done
echo "5. Sequence hint: $HINT_COUNT/3 — $([ "$HINT_COUNT" = "3" ] && echo PASS || echo FAIL)"

# 6. TDD regression smoke OK
TDD_REPORT=tests/skill-activation/report-2026-05-03-tdd-regression.md
[ -f "$TDD_REPORT" ] && echo "6. TDD regression report: PASS" || echo "6. TDD regression report: FAIL"

# 7. Cumulative no-regression
echo "7. Cumulative no-regression — manual check report file"
```

## Step 2 — KPI globali (consolidato 3 PR)

In `docs/measurements/skill-alignment-final-2026-05-03.md`:

```markdown
# Skill Alignment Final Report (PR-4 + PR-5 + PR-6)

## KPI globali

| KPI | Baseline | Post-PR-4 | Post-PR-5 | Post-PR-6 | Target | Status |
|---|---|---|---|---|---|---|
| activation_accuracy | __% | __% | __% | __% | +15pp | ___ |
| chain_completeness | __% | n/a | __% | __% | +10pp | ___ |
| backbone_skills_under_200_lines | 3/8 | 8/8 | 8/8 | 8/8 | 8/8 | ___ |
| description_pattern_compliance | ~5/39 | 8/39 | 39/39 | 39/39 | ≥33/39 | ___ |
| agent_tool_whitelist_coverage | 0/5 | 0/5 | 0/5 | 5/5 | 5/5 | ___ |
| backbone_leakage_grep_match | 3 file | 0 file | 0 file | 0 file | 0 | ___ |
| verification_dogmatic_keyword | 7+ | 7+ | ≤3 | ≤3 | ≤3 | ___ |
| nudge_signal_to_noise | n/a | n/a | __ | __ | ≥0.7 | ___ |

## Cost effettivo Bedrock

- Smoke test (Haiku): __ USD
- Baseline (Sonnet): __ USD
- Post-PR-5 (Sonnet): __ USD
- Post-PR-6 (Sonnet): __ USD
- Cumulative: __ USD (target <$5)

## Note

- [ ] Eventuali rollback parziali effettuati: list commits
- [ ] Risk R6 risolto: matcher PostToolUse "Skill" funziona / fallback ".*"
- [ ] CHANGELOG completo: PR-4, PR-5, PR-6 entries
```

## Step 3 — Commit

```bash
git add docs/measurements/skill-alignment-final-2026-05-03.md
git commit -m "docs(measurements): final report skill alignment (PR-4 + PR-5 + PR-6)

KPI consolidati. Cost cumulativo Bedrock <\$5. NO-REGRESSION cumulativa OK."
```

## Step 4 — Pre-flight PR-6

Invoca `siae-finishing-branch` per checklist e PR open.

## Criteri accettazione

- 6/7 check PR-6 PASS (cost effettivo manuale)
- KPI report completo
- Final report committato
- Pre-flight PR-6 pronto

## NO-REGRESSION FINAL

Verifica cumulative: tutti criteri PR-4, PR-5, PR-6 mantenuti. Nessuna regressione su skill esistenti. Solo aggiunte di copertura e ottimizzazioni descritte nel design doc.
