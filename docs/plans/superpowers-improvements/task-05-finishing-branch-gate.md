# Task 5 — Patch finishing-branch per blind-review gate

**Stato:** [PENDING]
**Dipendenze:** Task 4 (siae-blind-review deve esistere)
**File coinvolti:**
- `skills/siae-finishing-branch/SKILL.md`

---

## Step 1 — Inserisci Blind Review Gate

Apri `skills/siae-finishing-branch/SKILL.md`.
Trova `### Step 4b — Plan Completion Gate (pre-PR)` (riga ~218).

Inserisci **dopo** Step 4b e **prima di** `### Step 5 — Apri la Pull Request`:

```markdown
### Step 4c — Blind Review Gate (pre-PR)

🟡 MEDIO

```
REQUIRED SUB-SKILL: siae-blind-review
```

Esegui una blind review prima di aprire la PR. Il reviewer parte SOLO dal design doc
e trova il codice autonomamente.

**Se il design doc esiste in `docs/plans/`:**
Invoca `siae-blind-review`. Attendi il verdetto.

- **Verdetto PASS:** procedi con Step 5
- **Verdetto FAIL:** riporta i finding. NON aprire la PR finche' non sono risolti
  o l'utente autorizza esplicitamente: `"procedi senza blind review — motivo: ..."`

**Se non esiste un design doc:**
La blind review non puo' procedere. Segnala e procedi con Step 5.
Questo e' un gap nel processo — il lavoro e' stato fatto senza spec scritta.
```

## Step 2 — Aggiorna conteggio step

Nella sezione HARD-GATE (riga ~40), aggiorna:

Da: `Hai completato TUTTI e 5 gli step di questa skill?`
A: `Hai completato TUTTI e 6 gli step di questa skill? (incluso Blind Review Gate)`

Nella sezione `## Processo in 5 Step` (riga ~77), aggiorna:

Da: `## Processo in 5 Step`
A: `## Processo in 6 Step`

## Step 3 — Verifica

```bash
grep -c "siae-blind-review" skills/siae-finishing-branch/SKILL.md
grep "Processo in 6 Step" skills/siae-finishing-branch/SKILL.md
```
Output atteso: almeno 2 occorrenze di `siae-blind-review`, e la riga `Processo in 6 Step`.

## Step 4 — Commit

```bash
git add skills/siae-finishing-branch/SKILL.md
git commit -m "feat(skills): add blind review gate to finishing-branch (#865)"
```
