# Task 3 — Checkbox Sync in 3 skill

**Stato:** [PENDING]
**Dipendenze:** nessuna
**File coinvolti:**
- `skills/siae-executing-plans/SKILL.md`
- `skills/siae-subagent-development/SKILL.md`
- `skills/siae-writing-plans/SKILL.md`

---

## Step 1 — Patch siae-executing-plans

Apri `skills/siae-executing-plans/SKILL.md`.
Trova il punto 5 nella sezione Step 2 (riga ~138):

```
5. Aggiorna il marker nel piano: `[PENDING]` → `[DONE]`
6. Se bloccato: `[PENDING]` → `[BLOCKED]` — motivo
```

Sostituisci con:

```markdown
5. Aggiorna il marker nel piano — **dual format:**
   - Formato marker: `[PENDING]` → `[DONE]` (o `[BLOCKED]`)
   - Formato checkbox: `- [ ] Task description` → `- [x] Task description`
   - Rileva quale formato usa il piano e aggiorna di conseguenza
   - Se il piano usa entrambi i formati, aggiorna entrambi
6. Se bloccato: `[PENDING]` → `[BLOCKED]` — motivo (e `- [ ]` resta invariato)
```

## Step 2 — Patch siae-subagent-development

Apri `skills/siae-subagent-development/SKILL.md`.
Trova la sezione post-reviewer (riga ~212-214):

```
1. Apri `docs/plans/<filename>.md`
2. Aggiorna il marker del task: `[PENDING]` → `[DONE]`
```

Sostituisci il punto 2 con:

```markdown
2. Aggiorna il marker del task — **dual format:**
   - Formato marker: `[PENDING]` → `[DONE]` (o `[BLOCKED]`)
   - Formato checkbox: `- [ ] Task description` → `- [x] Task description`
   - Rileva quale formato usa il piano e aggiorna di conseguenza
```

## Step 3 — Patch siae-writing-plans

Apri `skills/siae-writing-plans/SKILL.md`.
Trova la sezione sullo stato task nel template overview.md. Dopo la riga:

```
NON scrivere task senza marker — un task senza marker e' un bug nel piano.
```

Aggiungi:

```markdown
**Formato stato task:** usa `[PENDING]`/`[DONE]`/`[BLOCKED]` come formato primario.
Se il piano contiene checkbox markdown (`- [ ]`), mantienili sincronizzati.
```

## Step 4 — Verifica

```bash
grep -l "dual format" skills/siae-executing-plans/SKILL.md skills/siae-subagent-development/SKILL.md
grep -l "checkbox" skills/siae-writing-plans/SKILL.md
```
Output atteso: tutti e 3 i file elencati.

## Step 5 — Commit

```bash
git add skills/siae-executing-plans/SKILL.md skills/siae-subagent-development/SKILL.md skills/siae-writing-plans/SKILL.md
git commit -m "feat(skills): add checkbox sync dual-format to plan execution skills (#874)"
```
