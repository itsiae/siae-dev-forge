# Task 09 — Checklist di Verifica (+2 voci) in XRAY-TEMPLATES.md

**Stato:** [PENDING]
**File:** `skills/siae-qa/XRAY-TEMPLATES.md`
**Dipendenze:** Task 08 completato (stesso file)

---

## Obiettivo

Aggiungere 2 nuove voci alla `## Checklist di Verifica` in `XRAY-TEMPLATES.md`:
una per il gate 4a-bis (Decision Table check) e una per il Coverage Score.

---

## Step 1 — Verifica che le voci non esistano già

Cerca in `skills/siae-qa/XRAY-TEMPLATES.md`:
```
4a-bis eseguito
```

Se trovato → il task è già applicato. Marca `[DONE]` e fermati.
Se non trovato → procedi a Step 2.

---

## Step 2 — Individua il punto di inserimento

Nella sezione `## Checklist di Verifica`, cerca la voce:
```
- [ ] Matrice scenari compilata (4 categorie valutate: positivi, edge, negativi, profilazioni)
```

La voce sul gate 4a-bis va inserita **immediatamente dopo** questa riga.

La voce sul Coverage Score va inserita **dopo** la voce:
```
- [ ] Riepilogo copertura per categoria mostrato al developer prima dell'export
```

---

## Step 3 — Aggiungi la voce per il gate 4a-bis

Usa Edit per inserire la seguente voce dopo la riga della matrice scenari:

```
- [ ] Gate 4a-bis eseguito: Decision Table applicata (se 2+ condizioni booleane) o scartata con SE NO esplicito
```

---

## Step 4 — Aggiungi la voce per il Coverage Score

Usa Edit per inserire la seguente voce dopo la riga del riepilogo copertura:

```
- [ ] Coverage Score calcolato e giudizio mostrato al developer (se < 50: export bloccato)
```

---

## Step 5 — Output atteso

```
Run: grep -c "4a-bis eseguito\|Coverage Score calcolato" skills/siae-qa/XRAY-TEMPLATES.md
Output atteso: 2
```

Se il count è 2 → task completato.
Aggiorna lo stato a `[DONE]` in `overview.md`.

---

## Step 6 — Placeholder Scan finale sull'intero piano

Esegui il Placeholder Scan obbligatorio su tutti i file modificati:

```
Run: grep -rn "TBD\|TODO\|da definire\|da decidere\|\.\.\." \
  skills/siae-qa/SKILL.md \
  skills/siae-qa/XRAY-TEMPLATES.md \
  skills/siae-qa/reference/question-trees.md
Output atteso: 0 righe con placeholder nei blocchi aggiunti da questo piano
```

Se 0 match nei contenuti aggiunti → piano completato.
Emetti checkpoint finale:

```
[WRITING-PLANS:PLACEHOLDER-SCAN] Scan completato
  File scansionati: 3
  Pattern trovati: 0 = PASS
  Iterazioni: 1
```
