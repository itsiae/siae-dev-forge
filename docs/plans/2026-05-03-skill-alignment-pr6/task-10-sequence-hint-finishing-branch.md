# Task 10 — Sequence Hint Advisory `siae-finishing-branch`

**Goal:** Aggiungere "Best after: siae-verification" hint nel description.

**File coinvolti:**
- `skills/siae-finishing-branch/SKILL.md` (frontmatter)

## Step 1 — Leggi description (post-PR-4 progressive disclosure + PR-5 audit)

## Step 2 — Aggiungi hint

```yaml
description: >
  Use when preparing a feature/fix branch for PR. Pre-flight checklist completo
  (test, coverage, CHANGELOG, version bump, branch hygiene) prima di pushare e
  aprire la PR. **Best after**: siae-verification passed (evidence-based verify
  prima del finishing). Examples: "pronto per PR", "apro la PR", "ready to merge".
---
```

NB: in PR-4 task 06 il hint era già stato aggiunto (refactor finishing-branch). Verifica se è ancora presente; se sì, questo task è verify-only.

## Step 3 — Edit (se necessario) + YAML check

## Step 4 — Smoke test

- "pronto per PR" → siae-finishing-branch

## Step 5 — Commit (se modificato)

```bash
git add skills/siae-finishing-branch/SKILL.md
git commit -m "refactor(skills): siae-finishing-branch sequence hint 'Best after: siae-verification'

Verify only (eventually noop se già fatto in PR-4)."
```

## Criteri accettazione

- "Best after:" presente
- Smoke OK

## NO-REGRESSION

Verify-only o additivo.
