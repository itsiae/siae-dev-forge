# Task 03 — Strip Leakage `siae-microservices-map`

**Goal:** Rimuovere riferimento "mappa SPORT" dalla description. Skill diventa project-agnostic.

**File coinvolti:**
- `skills/siae-microservices-map/SKILL.md` (frontmatter linea ~6)

## Step 1 — Verifica match attuale

```bash
grep -nE 'SPORT|sport-' skills/siae-microservices-map/SKILL.md | head -5
```

Output atteso: match su "mappa SPORT" o simili nel frontmatter.

## Step 2 — Leggi frontmatter

```bash
sed -n '1,15p' skills/siae-microservices-map/SKILL.md
```

Identifica la stringa esatta da sostituire.

## Step 3 — Edit description

Pattern tipico (verifica esatta stringa nel file):

```
"mappa SPORT", "sistema a microservizi"
```

Sostituisci con:

```
"mappa sistema", "sistema a microservizi", "topologia distribuita"
```

Usa Edit tool con `old_string` e `new_string` esatti.

## Step 4 — Verifica zero leakage

```bash
grep -nE '\bSPORT\b' skills/siae-microservices-map/SKILL.md | grep -i description | head -3
```

Output atteso: 0 match nel frontmatter description.

NB: SPORT può apparire negli esempi del corpo skill (lecito), purché non nel trigger description.

## Step 5 — Commit atomico

```bash
git add skills/siae-microservices-map/SKILL.md
git commit -m "chore(skills): strip 'SPORT' from siae-microservices-map description trigger

Skill project-agnostic. Trigger generico (\"sistema\", \"microservizi\",
\"topologia distribuita\") consente attivazione su qualsiasi sistema multi-repo,
non solo SPORT. Esempi nel body possono mantenere riferimenti SIAE."
```

## Criteri accettazione

- 0 match `SPORT` nel frontmatter `description` (ok nel body come esempio)
- Description preserva intent (mappare sistemi distribuiti multi-repo)
- Commit atomico

## NO-REGRESSION

Verifica manuale: skill deve attivarsi su "mappa il sistema X" o "topologia microservizi" senza richiedere keyword "SPORT". Esempi in body con SPORT sono OK come illustrazione.
