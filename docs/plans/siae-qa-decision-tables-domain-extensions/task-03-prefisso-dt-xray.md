# Task 03 — Prefisso [DT] in XRAY-TEMPLATES.md

**Stato:** [PENDING]
**File:** `skills/siae-qa/XRAY-TEMPLATES.md`
**Dipendenze:** nessuna

---

## Obiettivo

Aggiungere il prefisso `[DT]` nella sezione `## Prefissi di Categoria` di `XRAY-TEMPLATES.md`.

---

## Step 1 — Individua la sezione

Leggi `skills/siae-qa/XRAY-TEMPLATES.md` e cerca il testo esatto:
```
## Prefissi di Categoria
```

---

## Step 2 — Verifica che [DT] non esista già

Cerca in `XRAY-TEMPLATES.md`:
```
`[DT]`
```

Se trovato → il task è già applicato. Marca `[DONE]` e fermati.
Se non trovato → procedi a Step 3.

---

## Step 3 — Individua l'ultimo prefisso

La sezione attuale contiene:
```
- Nessun prefisso = scenario positivo (happy path)
- `[EDGE]` = edge case (limite, vuoto, volume estremo)
- `[NEG]` = scenario negativo / alternativo (errore, input non valido, dipendenza assente)
- `[PROFILO]` = scenario specifico di ruolo / profilazione
```

---

## Step 4 — Aggiungi il prefisso [DT]

Usa Edit per aggiungere la riga `[DT]` **dopo** la riga `[PROFILO]`:

```
- `[DT]` = test case derivato da Decision Table (combinazione di 2+ condizioni indipendenti)
```

Il risultato atteso della sezione dopo l'edit:
```
- Nessun prefisso = scenario positivo (happy path)
- `[EDGE]` = edge case (limite, vuoto, volume estremo)
- `[NEG]` = scenario negativo / alternativo (errore, input non valido, dipendenza assente)
- `[PROFILO]` = scenario specifico di ruolo / profilazione
- `[DT]` = test case derivato da Decision Table (combinazione di 2+ condizioni indipendenti)
```

---

## Step 5 — Output atteso

```
Run: grep -n "\[DT\]" skills/siae-qa/XRAY-TEMPLATES.md
Output atteso: almeno 1 riga contenente [DT]
```

Se il grep trova il testo → task completato.
Aggiorna lo stato a `[DONE]` in `overview.md`.
