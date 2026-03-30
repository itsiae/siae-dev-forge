# Task 02 — Template TC Audit Gate in XRAY-TEMPLATES.md

**Stato:** [PENDING]
**File:** `skills/siae-qa/XRAY-TEMPLATES.md`
**Dipendenze:** Task 01 completato (coerenza contenuti)

---

## Obiettivo

1. Aggiungere la sezione `## TC Audit Gate Template` in `XRAY-TEMPLATES.md`
   (prima di `## Checklist di Verifica`)
2. Aggiungere voce nella Checklist di Verifica per Fase 4c

---

## Step 1 — Verifica che il template non esista già

Cerca in `skills/siae-qa/XRAY-TEMPLATES.md`:
```
TC Audit Gate
```

Se trovato → il task è già applicato. Marca `[DONE]` e fermati.
Se non trovato → procedi a Step 2.

---

## Step 2 — Individua il punto di inserimento per la sezione template

Cerca il testo esatto:
```
## Checklist di Verifica
```

La nuova sezione `## TC Audit Gate Template` va inserita **immediatamente prima** di questa riga,
con una riga vuota di separazione.

---

## Step 3 — Inserisci la sezione template

Usa Edit per sostituire:
```
## Checklist di Verifica
```

con:
```
## TC Audit Gate Template

Output atteso della Fase 4c — da compilare per ogni Story prima di procedere a Fase 5:

```
TC AUDIT GATE — {STORY_ID}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [1] Tracciabilità AC→TC
      AC1: "{testo AC}" → TC #{id} ✅ / ❌ MANCANTE
      AC2: "{testo AC}" → TC #{id} ✅ / ❌ MANCANTE

  [2] Categorie matrice 4a
      Positivi:     N TC ✅ / ❌ 0 TC (N/A mai confermato)
      Edge case:    N TC ✅ / N/A confermato ✅ / ❌ 0 TC
      Negativi:     N TC ✅ / N/A confermato ✅ / ❌ 0 TC
      Profilazioni: N TC ✅ / N/A confermato ✅ / ❌ 0 TC

  [3] Decision Table
      Gate 4a-bis: SI → TC [DT] presenti: ✅ N TC / ❌ 0 TC
      Gate 4a-bis: NO → N/A ✅

  [4] Domande contestuali (Phase 0)
      Tipo: {tipo} — L1 poste: ✅ / ❌ SALTATE
      L2/L3 applicabili: ✅ / N/A

  [5] Coverage Score: {XX}/100 — {OTTIMA/BUONA/PARZIALE/INSUFFICIENTE}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERDETTO: ✅ AUDIT PASS / ⛔ AUDIT FAIL
  Gap: [lista gap con riferimento alla fase da cui riprendere]
```

---

## Checklist di Verifica
```

---

## Step 4 — Inserisci voce nella Checklist

Individua il testo esatto:
```
- [ ] Coverage Score calcolato e giudizio mostrato al developer (se < 50: export bloccato)
```

Aggiungi **immediatamente dopo**:
```
- [ ] TC Audit Gate (Fase 4c) eseguito: AUDIT PASS ottenuto prima di Fase 5
```

---

## Step 5 — Output atteso

```
Run: grep -c "TC Audit Gate\|AUDIT PASS" skills/siae-qa/XRAY-TEMPLATES.md
Output atteso: >= 3
```

Se il count è >= 3 → task completato.
Aggiorna lo stato a `[DONE]` in `overview.md`.

---

## Step 6 — Placeholder Scan finale

Esegui il Placeholder Scan obbligatorio su tutti i file modificati dal piano:

```
Run: grep -n "TBD\|TODO\|da definire\|da decidere\|\.\.\." \
  skills/siae-qa/SKILL.md \
  skills/siae-qa/XRAY-TEMPLATES.md
Output atteso: 0 righe con placeholder nei blocchi aggiunti da questo piano
```

Se 0 match nei contenuti aggiunti → piano completato.
Emetti checkpoint finale:

```
[WRITING-PLANS:PLACEHOLDER-SCAN] Scan completato
  File scansionati: 2
  Pattern trovati: 0 = PASS
  Iterazioni: 1
```
