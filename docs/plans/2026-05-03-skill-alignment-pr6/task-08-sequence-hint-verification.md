# Task 08 — Sequence Hint Advisory `siae-verification`

**Goal:** Aggiungere "Best after: ..." hint nel description di siae-verification (advisory, non blocca).

**File coinvolti:**
- `skills/siae-verification/SKILL.md` (frontmatter description)

## Step 1 — Leggi description attuale (post-PR-4 + PR-5)

```bash
sed -n '1,20p' skills/siae-verification/SKILL.md
```

## Step 2 — Aggiungi sequence hint

Pattern target (esempio):

```yaml
---
name: siae-verification
description: >
  Use when verifying that a fix or change is complete BEFORE declaring it done.
  Forces evidence-based verification (run tests, check output, confirm behaviour)
  prima di commit, PR, task complete declarations. **Best after**: siae-debugging
  completed (Phase 4 fix applied) OR siae-tdd cycle done (Red-Green-Refactor).
  Examples: "il fix funziona", "test passano", "ho finito", "tutto ok",
  "completato", "implementato".
---
```

NB: aggiungi solo "**Best after**: ..." come riga aggiuntiva. NON rimuovere altro.

## Step 3 — Edit + verifica YAML

## Step 4 — Smoke test

Prompt:
- "il fix funziona" → siae-verification (still attivata)
- "test passano" → siae-verification

NB: hint advisory; non altera attivazione.

## Step 5 — Commit

```bash
git add skills/siae-verification/SKILL.md
git commit -m "refactor(skills): siae-verification sequence hint 'Best after: debugging/tdd'

Advisory only — non altera attivazione. Comunica a Claude la sequenza canonica.
Enforcement reale via hook PostToolUse skill-advisory (PR-5 task 10)."
```

## Criteri accettazione

- "Best after:" presente nel description
- 2 smoke prompt OK

## NO-REGRESSION

Aggiunta puramente advisory, no rimozione di trigger.
