# Task 02 — Vincolo non negoziabile DT in SKILL.md

**Stato:** [PENDING]
**File:** `skills/siae-qa/SKILL.md`
**Dipendenze:** Task 01 completato

---

## Obiettivo

Aggiungere il vincolo non negoziabile relativo alla Decision Table nella sezione
`## VINCOLI NON NEGOZIABILI` di `SKILL.md`, come punto numerato aggiuntivo.

---

## Step 1 — Individua la sezione

Leggi `skills/siae-qa/SKILL.md` e cerca il testo esatto:
```
## VINCOLI NON NEGOZIABILI
```

---

## Step 2 — Individua l'ultimo vincolo numerato

Nella sezione `VINCOLI NON NEGOZIABILI`, cerca l'ultimo punto numerato.
Attualmente l'ultimo dovrebbe essere:
```
8. **Nel CSV, il nome colonna e' `Expceted Result`**
```

Annota il numero dell'ultimo vincolo (8 o diverso se aggiornato).

---

## Step 3 — Verifica che il vincolo DT non esista già

Cerca in `SKILL.md`:
```
Decision Table deve essere mostrata
```

Se trovato → il task è già applicato. Marca `[DONE]` e fermati.
Se non trovato → procedi a Step 4.

---

## Step 4 — Aggiungi il vincolo

Usa Edit per aggiungere il seguente punto **dopo l'ultimo vincolo numerato** (es. dopo il punto 8):

```
9. **La Decision Table (gate 4a-bis) deve essere mostrata e approvata dal developer
   prima di generare i TC da essa derivati** — non generare TC con prefisso `[DT]`
   senza conferma esplicita della tabella
```

---

## Step 5 — Output atteso

```
Run: grep -n "Decision Table deve essere mostrata" skills/siae-qa/SKILL.md
Output atteso: una riga con il testo del vincolo
```

Se il grep trova il testo → task completato.
Aggiorna lo stato a `[DONE]` in `overview.md`.
