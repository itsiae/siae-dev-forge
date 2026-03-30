# Task 01 — Gate 4a-bis Decision Table in SKILL.md

**Stato:** [PENDING]
**File:** `skills/siae-qa/SKILL.md`
**Dipendenze:** nessuna

---

## Obiettivo

Inserire il gate `4a-bis — Decision Table Check` tra la fine della sezione
"Fase 4 — Generazione Test Case step-based > 4a" e l'inizio di "4b — Generazione Test Case"
in `SKILL.md`.

---

## Step 1 — Individua il punto di inserimento

Leggi `skills/siae-qa/SKILL.md`.

Cerca il testo esatto:
```
#### 4b — Generazione Test Case
```

Il nuovo gate va inserito **immediatamente prima** di questa riga.

---

## Step 2 — Verifica che 4a-bis non esista già

Cerca in `SKILL.md`:
```
4a-bis
```

Se trovato → il task è già applicato. Marca `[DONE]` e fermati.
Se non trovato → procedi a Step 3.

---

## Step 3 — Inserisci il gate 4a-bis

Usa il tool Edit per inserire il blocco seguente **prima** di `#### 4b — Generazione Test Case`.

Il blocco da inserire (includi la riga vuota prima e dopo):

```markdown

---

#### 4a-bis — Decision Table Check [AUTOMATICO — esegui sempre dopo 4a]

Dopo aver compilato la matrice scenari, verifica:
**"Negli AC o nella Req Profile Card ci sono 2+ condizioni booleane/discrete
indipendenti la cui combinazione cambia il comportamento del sistema?"**

Segnali tipici:
- Frasi del tipo "se [A] e [B] allora [X], altrimenti [Y]"
- Campi con valori discreti multipli (es. stato = {bozza, pubblicato, archiviato})
- Combinazioni ruolo × stato → comportamento diverso
- Logica "solo se entrambe le condizioni sono vere"

**SE SÌ → costruisci una mini Decision Table prima di generare i TC:**
1. Colonne = condizioni (max 4 per mantenibilità)
2. Righe = combinazioni rilevanti — usa MC/DC (Modified Condition/Decision Coverage):
   non serve generare 2^N combinazioni, seleziona quelle che cambiano l'output
3. Output = azione attesa del sistema per ogni combinazione
4. **Mostra la tabella al developer e attendi conferma prima di procedere**
5. Ogni riga della DT approvata genera obbligatoriamente 1 TC con prefisso `[DT]`

**SE NO → procedi a 4b direttamente.**
Non forzare DT dove non ci sono condizioni combinatorie — peggiora la leggibilità
della test list senza aggiungere valore.

```

---

## Step 4 — Verifica visiva

Dopo l'edit, leggi le righe attorno al punto di inserimento in `SKILL.md`.

Verifica che la struttura sia:
```
[...fine di 4a...]

---

#### 4a-bis — Decision Table Check [AUTOMATICO — esegui sempre dopo 4a]
[...contenuto gate...]

#### 4b — Generazione Test Case
[...contenuto 4b...]
```

Se la struttura è corretta → procedi a Step 5.
Se la struttura è errata → ripristina usando un secondo Edit.

---

## Step 5 — Output atteso

```
Run: grep -n "4a-bis" skills/siae-qa/SKILL.md
Output atteso: una riga con "4a-bis — Decision Table Check"
```

Se il grep restituisce almeno 1 risultato → task completato.
Aggiorna lo stato a `[DONE]` in `overview.md`.
