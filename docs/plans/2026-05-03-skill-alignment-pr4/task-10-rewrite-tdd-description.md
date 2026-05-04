# Task 10 — Description Rewrite `siae-tdd`

**Goal:** Riscrivere description di `siae-tdd` in pattern Anthropic "Use when X". Skill già <200 righe (179), no progressive disclosure necessaria.

**File coinvolti:**
- `skills/siae-tdd/SKILL.md` (frontmatter)

## Step 1 — Leggi description attuale

```bash
sed -n '1,15p' skills/siae-tdd/SKILL.md
```

Identifica trigger keyword attuali (>20 secondo review).

NB: la riduzione del numero di trigger keyword da 20+ a 5-8 è in PR-6 (Task 01). In questo task ci limitiamo a riformulare in pattern "Use when X" preservando i keyword esistenti per ora — la riduzione viene dopo per minimizzare rischio.

## Step 2 — Pattern target

Description nuova:

```yaml
---
name: siae-tdd
description: >
  Use when implementing production code (feature, bug fix, refactor). Enforces
  Red-Green-Refactor cycle: failing test BEFORE implementation, every time.
  Trigger: implementazione feature, bug fix, refactoring, qualsiasi scrittura
  di codice, aggiungi metodo, crea classe, modifica logica, nuovo endpoint,
  scrivi funzione, implementa, codifica, sviluppa.
---
```

NB: trigger keyword originali preservati (riduzione PR-6).

## Step 3 — Edit con tool Edit

Sostituisci frontmatter description preservando struttura YAML del file.

## Step 4 — Verifica YAML valido

```bash
python3 -c "import yaml,sys; data=yaml.safe_load(open('skills/siae-tdd/SKILL.md').read().split('---')[1]); print(data.get('description','MISSING')[:100])"
```

Output atteso: prime 100 char della description nuova, no errore parse.

## Step 5 — Smoke test no-regression

Prompt:
- "implementa la funzione X" → skill attivata
- "scrivo i test prima del codice" → skill attivata
- "TDD per feature nuova" → skill attivata
- "Red-Green-Refactor" → skill attivata

## Step 6 — Commit

```bash
git add skills/siae-tdd/SKILL.md
git commit -m "refactor(skills): siae-tdd description in 'Use when X' Anthropic pattern

Trigger keyword preservati (riduzione in PR-6 task 01). Pattern allineato:
'Use when implementing production code. Enforces Red-Green-Refactor cycle.'
NO-REGRESSION verificata su 4 smoke prompt."
```

## Criteri accettazione

- Description inizia con "Use when"
- Trigger keyword ORIGINALI preservati (riduzione in PR-6)
- YAML valido
- 4 smoke prompt attivano skill

## NO-REGRESSION

Tutti i prompt che pre-task attivavano `siae-tdd` devono continuare a farlo. Trigger reduction è OOS (PR-6).
