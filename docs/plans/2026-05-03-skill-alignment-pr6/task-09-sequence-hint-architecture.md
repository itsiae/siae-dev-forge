# Task 09 — Sequence Hint Advisory `siae-architecture`

**Goal:** Aggiungere "Best after: siae-brainstorming Step 4" hint nel description.

**File coinvolti:**
- `skills/siae-architecture/SKILL.md` (frontmatter description)

## Step 1 — Leggi description attuale (post PR-5 audit)

## Step 2 — Aggiungi sequence hint

```yaml
description: >
  Use when evaluating, choosing, or analyzing architectural patterns for an
  existing or new system. Covers C4 model, HLD, bounded context, CQRS,
  event-driven, microservizi vs monolite, resilienza, coupling. **Best after**:
  siae-brainstorming Step 4 (options proposed) — questa skill è specialistica
  per deepen architectural choice già scoperto. Examples: "valutiamo CQRS",
  "microservizi o monolite?", "crea il C4", "definisci bounded context".
---
```

## Step 3 — Edit + YAML check

## Step 4 — Smoke test

- "valutiamo CQRS" → siae-architecture (still attivata)
- "crea il C4" → siae-architecture

## Step 5 — Commit

```bash
git add skills/siae-architecture/SKILL.md
git commit -m "refactor(skills): siae-architecture sequence hint 'Best after: brainstorming Step 4'

Advisory only. Comunica posizionamento canonico (architecture deepen dopo
opzioni proposte). Enforcement via hook advisory PR-5."
```

## Criteri accettazione

- "Best after:" hint presente
- 2 smoke OK

## NO-REGRESSION

Pure advisory addition.
