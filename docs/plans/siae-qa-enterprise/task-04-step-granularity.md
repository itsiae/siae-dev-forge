# Task 04 — Regole granularità step [PENDING]

**File:** `skills/siae-qa/SKILL.md` + `skills/siae-qa/XRAY-TEMPLATES.md`
**Sezione:** "Fase 4b — Generazione Test Case" e "Formato Test Case Step-Based"
**Cluster:** A — Determinismo

---

## Obiettivo

Definire 3 regole obbligatorie di granularità degli step per rendere i TC
comparabili tra sprint e valutabili in modo univoco pass/fail.

---

## Step 1 — Aggiungi regole granularità in SKILL.md

Leggi `skills/siae-qa/SKILL.md`. Individua la sezione `#### 4b — Generazione Test Case`.

Dopo la prima frase "Per ogni scenario della matrice (4a), genera 1+ Test Case step-based.",
aggiungi:

```markdown
**Regole di granularità step [OBBLIGATORIE]:**

**Regola A — 1 step = 1 interazione atomica**
Un step non può descrivere più di un'azione dell'utente o del sistema.
"Compilare il form e premere Invio" → 2 step separati.
"Aprire la pagina, inserire i dati e verificare il risultato" → 3+ step separati.

**Regola B — Ogni navigazione è step distinto**
"Aprire la pagina X" è sempre step 1 di qualsiasi TC. Non può essere fuso con step 2.
Esempi di step di navigazione: "Navigare a /pagina", "Cliccare su tab X",
"Aprire il form di Y", "Espandere la sezione Z".

**Regola C — Expected Result verificabile senza ambiguità**
L'Expected Result deve permettere a qualsiasi QA di rispondere "pass/fail" guardando lo schermo
senza interpretazione soggettiva.
❌ Non valido: "il sistema funziona correttamente", "la pagina si carica", "tutto ok"
✅ Valido: "Il sistema mostra il messaggio 'Operazione completata con successo'"
✅ Valido: "L'endpoint restituisce HTTP 201 con body `{id: <uuid>, status: 'CREATED'}`"
✅ Valido: "Il campo 'amount' mostra il messaggio di errore 'Il valore deve essere maggiore di 0'"
✅ Valido: "Il job completa con exit code 0 e scrive N record nella tabella silver.operazioni"

**Regola D — Step con precondizioni implicite**
Se uno step richiede che un'azione precedente abbia prodotto un risultato specifico
(es. "il record deve esistere nel DB"), questo va dichiarato come precondizione nel campo `Data`,
non come step 1. I dati di test specifici appartengono al campo `Data`, non all'`Action`.
```

---

## Step 2 — Aggiorna la sezione "Formato Test Case Step-Based" in XRAY-TEMPLATES.md

Leggi `skills/siae-qa/XRAY-TEMPLATES.md` sezione "Formato Test Case Step-Based".

Aggiungi dopo la tabella dei campi, prima della sezione "Prefissi di Categoria":

```markdown
**Regole di granularità step (vedi SKILL.md) — riepilogo rapido:**

| Regola | Applicazione |
|--------|-------------|
| A | 1 step = 1 azione atomica. Mai combinare due azioni in un step. |
| B | Navigazione = sempre step separato e primo della sequenza. |
| C | Expected Result deve essere pass/fail senza interpretazione. Mai "funziona" o "ok". |
| D | Precondizioni dati → campo `Data`, non step 1. |

**Esempi di Expected Result validi:**

| Tipo | Expected Result valido |
|------|----------------------|
| FE | "La pagina mostra la lista con N elementi visibili. Il campo totale mostra '€ X.XX'." |
| BE | "HTTP 201. Body: `{id: '<uuid>', createdAt: '<ISO8601>'}`. Header `Location: /api/v1/resource/<id>`." |
| ETL | "Job termina con status SUCCESS. Tabella silver.X contiene N record. 0 record in dead-letter." |
| DB | "Migration applicata. `SELECT COUNT(*) FROM flyway_schema_history WHERE success = true` restituisce N." |
| Auth | "HTTP 403. Body: `{error: 'Forbidden', message: 'Accesso negato: ruolo insufficiente'}`." |
| Integration | "Il sistema ritorna HTTP 200 dopo max 500ms. Il body contiene il campo `correlationId`." |
```

---

## Step 3 — Commit

```bash
git add skills/siae-qa/SKILL.md skills/siae-qa/XRAY-TEMPLATES.md
git commit -m "feat(siae-qa): add mandatory step granularity rules (A/B/C/D)"
```
