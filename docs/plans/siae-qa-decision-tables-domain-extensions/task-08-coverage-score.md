# Task 08 — Coverage Score nel Riepilogo Copertura in XRAY-TEMPLATES.md

**Stato:** [PENDING]
**File:** `skills/siae-qa/XRAY-TEMPLATES.md`
**Dipendenze:** Task 07 completato (stesso file)

---

## Obiettivo

Sostituire il template `## Riepilogo Copertura` esistente in `XRAY-TEMPLATES.md`
con il template esteso che include il Coverage Score (formula + soglie).

---

## Step 1 — Verifica che il Coverage Score non esista già

Cerca in `skills/siae-qa/XRAY-TEMPLATES.md`:
```
Coverage Score
```

Se trovato → il task è già applicato. Marca `[DONE]` e fermati.
Se non trovato → procedi a Step 2.

---

## Step 2 — Individua il template attuale da sostituire

Il template attuale è:
```
## Riepilogo Copertura

**Riepilogo prima dell'export:** mostra la tabella completa al developer con la distribuzione per categoria. Il developer puo' modificare i valori di `Automazione` e `NRT` prima di procedere all'export.

```
Riepilogo copertura:
  Positivi:    N TC
  Edge case:   N TC
  Negativi:    N TC
  Profilazioni: N TC
  TOTALE:      N TC
```
```

---

## Step 3 — Sostituisci con il template esteso

Usa Edit (replace_all: false) per sostituire il blocco del template attuale
con il seguente template esteso:

```markdown
## Riepilogo Copertura

**Riepilogo prima dell'export:** mostra la tabella completa al developer con la distribuzione per categoria. Il developer puo' modificare i valori di `Automazione` e `NRT` prima di procedere all'export.

```
Riepilogo copertura:
  Positivi:     N TC
  Edge case:    N TC
  Negativi:     N TC
  Profilazioni: N TC
  [DT]:         N TC   (ometti la riga se il gate 4a-bis ha risposto NO)
  TOTALE:       N TC

  ─────────────────────────────────────
  Coverage Score: XX/100
    Breadth:   XX/40  (N/4 categorie con almeno 1 TC — 10 pt ciascuna)
    Depth:     XX/20  (negativi ≥ positivi: SI/NO +10 | 1 TC per ogni AC: SI/NO +10)
    Technique: XX/20  (DT applicata: SI +20 | DT non applicabile: +20 auto | DT mancante: +0)
    Domain:    XX/20  (L1 domande poste: SI/NO +10 | L2/L3 → ≥1 TC extra: SI/NO +10)

  Giudizio: OTTIMA (90-100) / BUONA (70-89) / PARZIALE (50-69) / INSUFFICIENTE (<50)
  ─────────────────────────────────────
```

**Soglie e azioni:**

| Score | Giudizio | Azione |
|-------|----------|--------|
| 90–100 | OTTIMA | Procedi all'export |
| 70–89 | BUONA | Accettabile — aggiungi note sui gap minori come commento nel TC |
| 50–69 | PARZIALE | Suggerisci integrazione su categorie deboli, ma non blocca |
| < 50 | **INSUFFICIENTE** | **EXPORT BLOCCATO** — torna a 4a; indica categoria con score più basso |

Se il giudizio è INSUFFICIENTE, mostra:
```
⛔ EXPORT BLOCCATO — Coverage Score: XX/100
   Categoria debole: {Breadth/Depth/Technique/Domain} ({XX}/{max} pt)
   Azione richiesta: {descrizione specifica — es. "aggiungere almeno 1 TC negativo"}
```
```

---

## Step 4 — Output atteso

```
Run: grep -n "Coverage Score" skills/siae-qa/XRAY-TEMPLATES.md
Output atteso: almeno 2 righe (nel template e nella formula)
```

Se il grep trova almeno 2 occorrenze → task completato.
Aggiorna lo stato a `[DONE]` in `overview.md`.
