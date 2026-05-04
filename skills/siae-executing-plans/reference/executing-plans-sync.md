# siae-executing-plans — Sync Stato Task

> Reference linked da `../SKILL.md`. Aggiornamento marker
> `[PENDING]`/`[DONE]`/`[BLOCKED]` e checkbox dopo ogni task del batch.

## Marker stato

Per ogni task completato durante un batch, aggiorna il marker nel piano.
Il formato dipende dalla struttura del piano:

| Formato piano | Posizione marker | Update |
|---------------|------------------|--------|
| Split (`docs/plans/<topic>/overview.md` + `task-NN-*.md`) | Tabella indice in `overview.md` | colonna `Stato`: `[PENDING]` → `[DONE]` |
| Legacy (`docs/plans/*-plan.md` monolitico) | Inline nel file unico | sezione task: `[PENDING]` → `[DONE]` |

**Stati ammessi:**
- `[PENDING]` — task non ancora iniziato
- `[DONE]` — task completato e verificato
- `[BLOCKED]` — task bloccato, motivo nel commit

**Transizioni valide:**
- `[PENDING]` → `[DONE]` (success path)
- `[PENDING]` → `[BLOCKED]` — motivo

NON committare un task come `[DONE]` se la verifica e' fallita.

---

## Checkbox sync (formato legacy)

Alcuni piani legacy usano checkbox markdown invece (o oltre) ai marker:

```markdown
- [ ] Task description
```

In questo caso aggiorna anche il checkbox a completamento:

- `- [ ] Task description` → `- [x] Task description`

**Dual format:** se il piano usa entrambi (marker + checkbox), aggiorna
entrambi nello stesso commit.

**Stato BLOCKED:** marker diventa `[BLOCKED]`, checkbox `- [ ]` rimane
invariato (il task non e' completato, e' bloccato).

---

## Commit stato

Dopo ogni task completato, commit il piano aggiornato in commit separato
dal codice:

```bash
git add docs/plans/<filename>.md
git commit -m "docs(plans): mark task N as DONE in <piano>"
```

Per task BLOCKED:

```bash
git commit -m "docs(plans): mark task N as BLOCKED in <piano> — <motivo breve>"
```

Il commit separato per il piano facilita il review (file diff piccolo) e
mantiene la storia degli stati pulita.

---

## Plan Completion Gate (Step 4b)

Prima di dichiarare il piano completato, verifica:

```bash
grep -c "\[PENDING\]" docs/plans/<filename>.md
grep -c "\[BLOCKED\]" docs/plans/<filename>.md
grep -c "\[DONE\]" docs/plans/<filename>.md
```

**Nota formato split:** i marker `[PENDING]`/`[DONE]`/`[BLOCKED]` si trovano
nella tabella indice di `overview.md`, non nei file task singoli.

**Se PENDING > 0 o BLOCKED > 0:** STOP. Il piano non e' completo.

```
🔴 PIANO INCOMPLETO — non puoi procedere con siae-verification.

Piano: docs/plans/<filename>.md
Stato: X [DONE] / Y [PENDING] / Z [BLOCKED]

Opzioni:
1. Completa i task [PENDING]
2. Chiedi all'utente se i [BLOCKED] vanno risolti o rimossi dal piano
3. Solo quando tutti sono [DONE] → procedi con Step 5
```

**Se tutti [DONE]:** procedi con Step 5 (Completamento) della SKILL principale.
