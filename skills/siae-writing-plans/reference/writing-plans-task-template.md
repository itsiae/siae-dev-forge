# siae-writing-plans — Template Task Bite-Sized

> Reference linked da `../SKILL.md`. Pattern dettagliato per ogni `task-NN-*.md` e per la struttura `overview.md`.

## LA LEGGE DI FERRO

```
OGNI STEP DEL PIANO E' UNA SINGOLA AZIONE DA 2-5 MINUTI,
CON PATH ESATTI, CODICE COMPLETO E COMANDO ATTESO
```

"Aggiungi la validazione" non e' uno step. Non e' un piano. E' un'aspirazione.

---

## Anatomia del piano (directory)

Il piano viene scritto come directory:

```
docs/plans/<topic>/
  overview.md          # header + indice task con stato
  task-01-<nome>.md    # task completo
  task-02-<nome>.md
  ...
  task-NN-<nome>.md
```

### `overview.md` — template

```markdown
# [Nome Feature] — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** [Una frase]
**Architettura:** [2-3 frasi]
**Stack:** [Tecnologie]
**SP:** [Stima]
**Design doc:** [path al design doc]

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | [Nome task 1] | `task-01-<nome>.md` | [PENDING] |
| 2 | [Nome task 2] | `task-02-<nome>.md` | [PENDING] |
| N | [Nome task N] | `task-NN-<nome>.md` | [PENDING] |

## Dipendenze

- Task 2 dipende da Task 1
- Task 3-4 sono indipendenti
```

### Stato task

Ogni task nasce con `[PENDING]`. Lo stato viene aggiornato durante l'esecuzione
da `siae-executing-plans` o `siae-subagent-development`. NON scrivere task senza
marker — un task senza marker e' un bug nel piano.

**Formato stato task:** usa `[PENDING]`/`[DONE]`/`[BLOCKED]` come formato
primario. Se il piano contiene checkbox markdown (`- [ ]`), mantienili
sincronizzati.

Tre stati possibili:
- `[PENDING]` — non ancora iniziato (default)
- `[DONE]` — completato e verificato
- `[BLOCKED]` — non completabile (con motivo obbligatorio)

**Regola:** un piano e' "completo" se e solo se **tutti** i task sono `[DONE]`.

---

## Anatomia di un singolo `task-NN-<nome>.md`

Ogni task contiene:

1. **Goal** — una frase, l'output verificabile
2. **File coinvolti** — path esatti (creazione/modifica)
3. **Step TDD bite-sized** — 5 step canonici:
   - Step 1: Scrivi il test fallente (con codice completo)
   - Step 2: Esegui e verifica che fallisce (con comando + output atteso)
   - Step 3: Implementa il codice minimo (con codice completo)
   - Step 4: Esegui e verifica che passa (con comando + output atteso)
   - Step 5: Commit (con messaggio commit suggerito)
4. **Comandi** — sempre con output atteso
5. **Criteri di accettazione** — checklist concreta

**Regola di dimensione:** se un task richiede piu' di 30 minuti, spezzalo.

---

## Regole di qualita' (esempi)

### Path esatti — sempre

```
# SBAGLIATO
Modifica il service di autenticazione

# GIUSTO
Modifica: `src/main/java/it/siae/auth/AuthService.java` (righe 112-134)
```

### Codice completo — sempre

```
# SBAGLIATO
Aggiungi la validazione dell'ISRC

# GIUSTO
if (!isrc.matches("^[A-Z]{2}-[A-Z0-9]{3}-[0-9]{2}-[0-9]{5}$")) {
    throw new ValidationException("ISRC non valido: " + isrc);
}
```

### Comandi con output atteso — sempre

```
# SBAGLIATO
Esegui i test

# GIUSTO
Run: `pytest tests/test_isrc_validator.py::test_invalid_format -v`
Output atteso: FAILED — ValidationException: ISRC non valido
```

### Step atomici — un'azione per step

```
# SBAGLIATO (troppo grande)
Implementa il validator ISRC con test e aggiornamento config

# GIUSTO (atomico)
Step 1: Scrivi il test per formato ISRC non valido
Step 2: Esegui e verifica che fallisce
Step 3: Implementa il regex di validazione
Step 4: Esegui e verifica che passa
Step 5: Commit
```

---

## Anti-pattern (rifiuto immediato)

| Pensiero | Realta' |
|----------|---------|
| "Il piano e' nella mia testa, basta implementare" | I piani non scritti sono assunzioni. Scrivili. |
| "I task sono ovvi, non serve dettagliare" | Ovvio per te. Opaco per un subagent con contesto fresco. |
| "Il codice nel piano puo' essere uno sketch" | Il codice incompleto nel piano diventa codice incompleto nell'implementazione. |
| "I path li ricorda il subagent" | Il subagent ha contesto fresco. Zero. Dai i path esatti. |
| "Questo task e' troppo grande ma lo scrivo uguale" | Spezzalo. Un task grande e' un task che fallira' a meta'. |
| "Aggiungo i comandi di test dopo" | Senza comandi nel piano, il subagent li inventa. Spesso sbagliati. |
| "E' solo un aggiornamento di config, non serve piano" | Le config rotte vanno in produzione. Testa e pianifica. |

---

## Limiti operativi (per ogni task)

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Tentativi fix per errore | 2 | Fermati. Diagnosi diversa necessaria. |
| File modificati per singolo step | 5 | Se devi toccare piu' file, decomponi in sub-task. |
| Output max per raccomandazione | 200 righe | Prioritizza. Top 5 issue, non lista esaustiva. |

---

## Retrocompatibilita'

I piani esistenti in formato file unico (`docs/plans/*-plan.md`) restano validi.
Le skill di esecuzione (`siae-subagent-development`, `siae-executing-plans`)
detectano automaticamente il formato:

- **Directory** (`docs/plans/<topic>/overview.md` esiste) → formato split
- **File** (`docs/plans/*-plan.md`) → formato legacy monolitico

Nessun piano esistente richiede migrazione.
