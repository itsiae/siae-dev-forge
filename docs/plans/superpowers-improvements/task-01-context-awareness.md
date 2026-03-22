# Task 1 — Context-First Rule in 4 skill

**Stato:** [PENDING]
**Dipendenze:** nessuna
**File coinvolti:**
- `skills/siae-brainstorming/SKILL.md`
- `skills/siae-tdd/SKILL.md`
- `skills/siae-verification/SKILL.md`
- `skills/siae-debugging/SKILL.md`

---

## Testo da inserire (identico per tutte)

```markdown
### Context-First Rule

Prima di leggere file, eseguire comandi, o fare domande all'utente,
verifica se l'informazione e' gia' presente nella conversazione corrente
(messaggi precedenti, output di tool, skill gia' invocate).
Non chiedere cio' che e' gia' stato detto. Non rileggere cio' che e' gia' stato letto.
```

---

## Step 1 — Inserisci in siae-brainstorming

Apri `skills/siae-brainstorming/SKILL.md`.
Trova la sezione `### 1. Smart Intake — Inferisci il contesto dal codebase`.
Inserisci il blocco Context-First Rule **subito dopo** la riga:
```
**NON chiedere cio' che il codice sa gia'.** Leggi prima, chiedi dopo.
```
e **prima di**:
```
**Fonti da leggere (in ordine):**
```

## Step 2 — Inserisci in siae-tdd

Apri `skills/siae-tdd/SKILL.md`.
Trova la sezione `## Rilevamento Tipo Codice` (riga ~105).
Inserisci il blocco Context-First Rule **subito prima** della riga:
```
**Prima del ciclo RED-GREEN-REFACTOR**, identifica il tipo di codice.
```

## Step 3 — Inserisci in siae-verification

Apri `skills/siae-verification/SKILL.md`.
Trova la sezione `### Step 1 — IDENTIFICA` (riga ~114).
Inserisci il blocco Context-First Rule **subito prima** della riga:
```
Determina il modo corretto per verificare il lavoro svolto.
```

## Step 4 — Inserisci in siae-debugging

Apri `skills/siae-debugging/SKILL.md`.
Trova `### Fase 1: Root Cause Investigation (HARD-GATE)` (riga ~100).
Inserisci il blocco Context-First Rule **subito prima** della riga:
```
**PRIMA di tentare QUALSIASI fix:**
```

## Step 5 — Verifica

Per ciascuna delle 4 skill, cerca `Context-First Rule`:
```bash
grep -l "Context-First Rule" skills/siae-brainstorming/SKILL.md skills/siae-tdd/SKILL.md skills/siae-verification/SKILL.md skills/siae-debugging/SKILL.md
```
Output atteso: tutte e 4 le skill elencate.

## Step 6 — Commit

```bash
git add skills/siae-brainstorming/SKILL.md skills/siae-tdd/SKILL.md skills/siae-verification/SKILL.md skills/siae-debugging/SKILL.md
git commit -m "feat(skills): add Context-First Rule to discovery-phase skills (#877)"
```
