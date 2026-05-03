# Task 11 — Description Rewrite `siae-verification`

**Goal:** Riscrivere description in pattern "Use when X". Skill già <200 righe (179), no PD. Tone-down body è OOS (PR-5 Task 13).

**File coinvolti:**
- `skills/siae-verification/SKILL.md` (frontmatter)

## Step 1 — Leggi attuale

```bash
sed -n '1,15p' skills/siae-verification/SKILL.md
```

## Step 2 — Pattern target

```yaml
---
name: siae-verification
description: >
  Use when verifying that a fix or change is complete BEFORE declaring it done.
  Forces evidence-based verification (run tests, check output, confirm behaviour)
  prima di commit, PR, task complete declarations. Examples: "il fix funziona",
  "test passano", "ho finito", "tutto ok", "completato", "implementato".
---
```

## Step 3 — Edit

Sostituisci frontmatter description preservando struttura.

## Step 4 — Verifica YAML

```bash
python3 -c "import yaml; yaml.safe_load(open('skills/siae-verification/SKILL.md').read().split('---')[1])"
```

## Step 5 — Smoke test no-regression

Prompt:
- "il fix funziona" → skill attivata
- "test passano" → skill attivata
- "ho finito" → skill attivata
- "completato" → skill attivata

## Step 6 — Commit

```bash
git add skills/siae-verification/SKILL.md
git commit -m "refactor(skills): siae-verification description in 'Use when X' pattern

Tone-down del body OOS (PR-5 task 13). Solo description rewrite. Trigger
keyword preservati: 'fix funziona/test passano/ho finito/completato'.
NO-REGRESSION 4 smoke prompt OK."
```

## Criteri accettazione

- Description "Use when X" pattern
- Trigger preservati
- 4 smoke prompt attivano skill

## NO-REGRESSION

Skill verification è critica per gate pre-commit. Tutti prompt completion-claim devono attivarla.
