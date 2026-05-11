# Task 12 — Description Rewrite `using-devforge`

**Goal:** Riscrivere description in pattern "Use when X". Skill già 90 righe.

**File coinvolti:**
- `skills/using-devforge/SKILL.md` (frontmatter)

## Step 1 — Leggi attuale

```bash
sed -n '1,15p' skills/using-devforge/SKILL.md
```

## Step 2 — Pattern target

```yaml
---
name: using-devforge
description: >
  Use at session start or new project context to establish the DevForge backbone
  (brainstorm → plan → tdd → verification) and discover available skills. Acts
  as the discovery entry point for the marketplace. Examples: "inizio sessione",
  "apertura nuovo progetto", "prima interazione", session-start hook trigger.
---
```

## Step 3 — Edit

## Step 4 — Verifica YAML

```bash
python3 -c "import yaml; yaml.safe_load(open('skills/using-devforge/SKILL.md').read().split('---')[1])"
```

## Step 5 — Smoke test

Prompt:
- "inizio sessione" → skill attivata
- "apertura nuovo progetto" → skill attivata

NB: questa skill è anche evocata da hook session-start automatico — verifica che cross-reference hook continui a funzionare (no rinomina del campo `name:`).

## Step 6 — Commit

```bash
git add skills/using-devforge/SKILL.md
git commit -m "refactor(skills): using-devforge description in 'Use when X' pattern

Skill name preservato (cross-reference hook session-start). Pattern aligned to
Anthropic discovery best practice. NO-REGRESSION 2 smoke + hook session-start OK."
```

## Criteri accettazione

- Description "Use when X" pattern
- `name: using-devforge` PRESERVATO esattamente (no rename)
- Hook session-start continua a funzionare

## NO-REGRESSION

Questa skill è invocata da hook automatici (session-start). Rinominare `name:` rompe l'integrazione. Verifica con: `grep -r "using-devforge" .claude/ skills/ hooks/`.
