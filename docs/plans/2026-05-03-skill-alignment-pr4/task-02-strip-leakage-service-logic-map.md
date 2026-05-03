# Task 02 — Strip Leakage `siae-service-logic-map`

**Goal:** Rimuovere riferimenti SIAE-specific (`sport-*/pop-*/pae-*`) dalla description di `siae-service-logic-map`. Skill diventa project-agnostic.

**File coinvolti:**
- `skills/siae-service-logic-map/SKILL.md` (frontmatter linea ~10)

## Step 1 — Verifica match attuale

```bash
grep -nE 'sport-\*|pop-\*|pae-\*' skills/siae-service-logic-map/SKILL.md
```

Output atteso: 1+ match su frontmatter description.

## Step 2 — Edit frontmatter

Trova la stringa esatta nel file (può variare leggermente). Pattern atteso:

```
"modifica su sport-*/pop-*/pae-*"
```

Sostituisci con:

```
"modifica su servizio business-critical o microservizio"
```

Comando concreto (verifica esatta stringa con grep prima):

```bash
# Prima leggi:
sed -n '1,20p' skills/siae-service-logic-map/SKILL.md
# Poi edit con Edit tool (NON sed in-place — preserva safety)
```

Usa Edit tool con `old_string` e `new_string` ESATTI dal file.

## Step 3 — Verifica zero match SIAE-specific

```bash
grep -nE 'sport-\*|pop-\*|pae-\*' skills/siae-service-logic-map/SKILL.md && echo "FAIL" || echo "PASS"
```

Output atteso: `PASS`.

## Step 4 — Verifica trigger keyword non rotti

```bash
# La skill dovrebbe ancora menzionare i trigger principali:
grep -E 'mappa|microservi|impact|cluster|catalogo' skills/siae-service-logic-map/SKILL.md | head -3
```

Output atteso: 1+ match (la skill conserva trigger generici).

## Step 5 — Commit atomico

```bash
git add skills/siae-service-logic-map/SKILL.md
git commit -m "chore(skills): strip SIAE-specific leakage from siae-service-logic-map description

Project-agnostic backbone principle: skill core non devono contenere prefissi
servizi specifici (sport-*/pop-*/pae-*). Trigger mantiene language generico
(\"servizio business-critical\")."
```

## Criteri accettazione

- 0 match grep `sport-\*\|pop-\*\|pae-\*` in `skills/siae-service-logic-map/SKILL.md`
- Description preserva intent (skill ancora invocabile per impact analysis e build catalog)
- Commit atomico isolato (no altri file modificati)

## NO-REGRESSION

Skill `siae-service-logic-map` deve continuare ad attivarsi su prompt come "mappa il sistema X" o "impact su servizio Y". Verifica manuale post-task: leggi description nuova e conferma trigger generici sono presenti.
