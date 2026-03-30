# Task 01 — Fase 4c TC Audit Gate in SKILL.md

**Stato:** [PENDING]
**File:** `skills/siae-qa/SKILL.md`
**Dipendenze:** nessuna

---

## Obiettivo

Inserire la sezione `#### 4c — TC Audit Gate` in `SKILL.md`
tra la fine di Fase 4b (riga 270, separatore `---`) e l'inizio di `### Fase 5`.

---

## Step 1 — Verifica che Fase 4c non esista già

Cerca in `skills/siae-qa/SKILL.md`:
```
4c
```

Se trovato → il task è già applicato. Marca `[DONE]` e fermati.
Se non trovato → procedi a Step 2.

---

## Step 2 — Individua il punto di inserimento

Il testo esatto da trovare (riga 270-272):
```
---

### Fase 5 — Export / Sincronizzazione
```

La nuova sezione va inserita **prima** di `### Fase 5`, subito dopo il `---` che chiude Fase 4b.

---

## Step 3 — Inserisci Fase 4c

Usa Edit per sostituire il blocco `---\n\n### Fase 5` con il seguente contenuto:

```
---

#### 4c — TC Audit Gate [OBBLIGATORIO — esegui prima di Fase 5]

Prima di procedere all'export, esegui un audit strutturato del TC set generato.
Approccio distrust: parti dall'assunzione che ci siano lacune — non fidarti del Coverage Score da solo.

Esegui i 5 check in sequenza:

**[1] Tracciabilità AC→TC**
Per ogni AC letto in Fase 1, verifica che esista almeno 1 TC esplicitamente tracciabile.
```
TC AUDIT GATE — {STORY_ID}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [1] Tracciabilità AC→TC
      AC1: "{testo AC}" → TC #{id} ✅ / ❌ MANCANTE
      AC2: "{testo AC}" → TC #{id} ✅ / ❌ MANCANTE
```
Se almeno 1 AC è senza TC → AUDIT FAIL, torna a Fase 4b e genera il TC mancante.

**[2] Categorie matrice 4a**
Verifica che nessuna categoria abbia 0 TC senza N/A esplicito confermato dal developer.
```
  [2] Categorie matrice 4a
      Positivi:     N TC ✅ / ❌ 0 TC (N/A mai confermato)
      Edge case:    N TC ✅ / N/A confermato ✅ / ❌ 0 TC
      Negativi:     N TC ✅ / ...
      Profilazioni: N TC ✅ / ...
```
Se almeno 1 categoria ha 0 TC e nessun N/A confermato → AUDIT FAIL, torna a Fase 4a.

**[3] Decision Table**
Se gate 4a-bis ha risposto SI → verifica che ci siano TC con prefisso `[DT]`.
```
  [3] Decision Table
      Gate 4a-bis: SI → TC [DT] presenti: ✅ N TC / ❌ 0 TC
      Gate 4a-bis: NO → N/A ✅
```
Se gate 4a-bis=SI e nessun TC [DT] → AUDIT FAIL, torna a fase 4a-bis.

**[4] Domande contestuali (Phase 0)**
Verifica che le domande L1 del tree contestuale siano state poste per il req type rilevato.
```
  [4] Domande contestuali (Phase 0)
      Tipo: {tipo} — L1 poste: ✅ / ❌ SALTATE
      L2/L3 applicabili: ✅ / N/A
```
Se L1 saltate senza motivo documentato → AUDIT FAIL, torna a Phase 0c e rilancia le domande L1.

**[5] Coverage Score**
```
  [5] Coverage Score: {XX}/100 — {OTTIMA/BUONA/PARZIALE/INSUFFICIENTE}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
Se score < 50 → AUDIT FAIL (già bloccato da Riepilogo Copertura — riconferma).

**Verdetto finale:**
- Tutti i check OK → `✅ AUDIT PASS — procedi a Fase 5`
- Almeno 1 check KO → mostra:

```
⛔ AUDIT FAIL
   Check fallito: [numero e descrizione del check]
   Gap: [descrizione specifica]
   Azione: torna a [fase] e [azione richiesta]
```

Vedi [XRAY-TEMPLATES.md](XRAY-TEMPLATES.md) sezione "TC Audit Gate Template" per il formato completo dell'output.

---

### Fase 5 — Export / Sincronizzazione
```

---

## Step 4 — Output atteso

```
Run: grep -c "4c\|AUDIT PASS\|AUDIT FAIL" skills/siae-qa/SKILL.md
Output atteso: >= 3
```

Se il count è >= 3 → task completato.
Aggiorna lo stato a `[DONE]` in `overview.md`.
