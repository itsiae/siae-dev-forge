# Task 09 — Ordinamento per flusso utente (Fase 4c) [PENDING]

**File:** `skills/siae-qa/SKILL.md` + `skills/siae-qa/reference/question-trees.md` + `skills/siae-qa/XRAY-TEMPLATES.md`
**Cluster:** C — Output enterprise

---

## Obiettivo

Aggiungere la Fase 4c "Riordinamento per flusso utente" in SKILL.md, con:
- 3 domande L0 trasversali per identificare le tappe del flusso
- Algoritmo di riordinamento con regole deterministiche
- Formato output con header di sezione per tappa
- Condizione di attivazione: solo se ≥ 2 tappe identificabili

---

## Step 1 — Aggiungi domande L0 trasversali in question-trees.md

Leggi `skills/siae-qa/reference/question-trees.md`. Inserisci PRIMA di `## Frontend (FE)`:

```markdown
## L0 — Flusso (trasversale a tutti i tipi)

> Queste domande identificano le tappe del flusso utente per l'ordinamento in Fase 4c.
> Si pongono PRIMA delle domande specifiche del tipo, ma SOLO se la struttura
> sequenziale non è già ricavabile dagli AC (Given/When/Then multipli, elenco numerato).
> Se il flusso è già esplicito negli AC, salta le domande L0 e procedi con L1.

**L0.1 — Tappe del flusso (universale)**
"Questa Story fa parte di un flusso utente più ampio?
Se sì, quali sono le tappe che un utente deve completare in sequenza per raggiungere l'obiettivo?
(es. registrazione → login → azione principale → conferma → notifica)"

> SKIP SE: gli AC contengono almeno 2 step Given/When/Then in sequenza, oppure
> un elenco numerato di passi, oppure frasi con "prima ... poi ...", "dopo aver ...",
> "una volta che ...", "a seguito di ..."

**L0.2 — Entry point del flusso (universale)**
"Da quale stato parte l'utente/sistema prima di eseguire l'azione principale?
(es. utente non autenticato, utente loggato con carrello vuoto, record in stato BOZZA,
job in attesa di trigger, file non ancora caricato)"

> SKIP SE: lo stato iniziale è esplicitamente descritto negli AC o nel Given della story

**L0.3 — Exit condition del flusso (universale)**
"Come sa l'utente/sistema che il flusso è completato con successo?
Cosa cambia nello stato del sistema alla fine del flusso?
(es. record in stato PUBBLICATO, email inviata, file in stato PROCESSED)"

> SKIP SE: la condizione finale è esplicitamente descritta negli AC o nel Then della story

---
```

---

## Step 2 — Aggiungi Fase 4c in SKILL.md

Leggi `skills/siae-qa/SKILL.md`. Individua la sezione `### Fase 5 — Export / Sincronizzazione`.

Inserisci PRIMA di Fase 5:

```markdown
### Fase 4c — Riordinamento per flusso utente [CONDIZIONALE]

> **Condizione di attivazione:** esegui questa fase solo se sono identificabili ≥ 2 tappe
> distinte nel flusso utente (dagli AC o dalle risposte L0 del question tree).
> Se la Story ha un singolo AC con un singolo comportamento → il riordinamento produce
> output identico a quello per categoria: salta questa fase.

#### Algoritmo di estrazione tappe

**Passo 1 — Cerca pattern sequenziali negli AC:**
- Given/When/Then multipli in sequenza → ogni blocco When/Then = una tappa
- Elenco numerato negli AC → l'ordine numerico = ordine delle tappe
- Frasi con "prima ... poi ...", "dopo aver ...", "una volta che ..." → sequenza esplicita
- Verbi di azione che cambiano lo stato del sistema → potenziale tappa

**Passo 2 — Se i pattern non sono trovati:**
Usa le risposte a L0.1/L0.2/L0.3 del question tree per costruire le tappe.

**Passo 3 — Default CRUD skeleton (se ancora nessuna tappa identificabile):**
1. Tappa 1: Precondizione / Setup (autenticazione, navigazione, stato iniziale)
2. Tappa 2: Azione principale (la funzionalità core della Story)
3. Tappa 3: Conferma / Feedback (messaggio di successo, redirect, aggiornamento)
4. Tappa 4: Post-condizione / Side effect (notifiche, audit, dati aggiornati)

#### Varianti per tipo

| Tipo | Modello di tappa |
|------|-----------------|
| FE | Pagine/schermate → loading → interazione → feedback → redirect |
| BE | Auth → Request → Response → Side effect (evento, DB write) |
| ETL | Bronze layer → Silver layer → Gold layer → Verifica downstream |
| DB | Pre-migration state → DDL/DML apply → Integrity check → Rollback test |
| Auth | AuthN (chi sei?) → AuthZ (puoi farlo?) → Operazione → Audit |
| Integration REST | Setup/Auth → Request → Response → State verification |
| Integration Event | Event production → Consumer processing → Ack/callback → State final |

#### Algoritmo di associazione scenario → tappa

Per ogni scenario della matrice 4a:
1. Cerca overlap tra parole chiave del titolo scenario e parole chiave di ogni tappa
2. Assegna alla tappa con score massimo
3. Se score = 0 per tutte le tappe → assegna a sezione "E2E / Cross-Tappa"

#### Ordinamento interno a ogni tappa

Dentro ogni tappa, ordina in questo ordine fisso:
1. Scenari positivi (happy path) — nessun prefisso
2. Scenari `[EDGE]` — valori limite della tappa
3. Scenari `[NEG]` — errori specifici della tappa
4. Scenari `[PROFILO]` — solo se rilevanti per questa tappa specifica

#### Formato output Fase 4c

```
═══════════════════════════════════════════════════════
TEST PLAN — {STORY_ID}: {Story summary}
═══════════════════════════════════════════════════════
Flusso: {N} tappe + E2E
Totale: {X} positivi | {Y} EDGE | {Z} NEG | {W} PROFILO
═══════════════════════════════════════════════════════

── TAPPA {N}: {Nome tappa} [{X} TC: {distribuzione}]
─────────────────────────────────────────────────────
TC-{NN}  {Titolo scenario positivo}
         Automazione: {Y/N} | NRT: {Y/N} | Priority: {P1-P4}
TC-{NN}  [EDGE] {Titolo edge case}
         Automazione: {Y/N} | NRT: {Y/N} | Priority: {P1-P4}
TC-{NN}  [NEG] {Titolo scenario negativo}
         Automazione: {Y/N} | NRT: {Y/N} | Priority: {P1-P4}

[... ripeti per ogni tappa ...]

── PROFILAZIONI [{X} TC]
─────────────────────────────────────────────────────
[TC di profilazione non associabili a una tappa specifica]

── E2E / CROSS-TAPPA [{X} TC]
─────────────────────────────────────────────────────
[TC che coprono 2+ tappe del flusso completo]

═══════════════════════════════════════════════════════
RIEPILOGO
  Tappa 1 ({Nome}):   {N} TC
  [...]
  Profilazioni:       {N} TC
  E2E:                {N} TC
  TOTALE:             {N} TC
═══════════════════════════════════════════════════════
```

#### Colonna Flow_Step nel CSV

Aggiungere colonna facoltativa `Flow_Step` in coda al CSV (non importata da Xray,
usata per reference interna e filtering in Excel pre-import):

```
ID;Test Type;...;NRT;Flow_Step
1;Manual;...;Y;Tappa 1 - {Nome}
2;Manual;...;Y;Tappa 1 - {Nome}
3;Manual;...;Y;Tappa 2 - {Nome}
```
```

---

## Step 3 — Aggiorna checklist in XRAY-TEMPLATES.md

Aggiungere alla checklist di verifica:
```markdown
- [ ] Fase 4c eseguita se ≥ 2 tappe identificabili, oppure skip documentato (story a singola tappa)
- [ ] Se Fase 4c eseguita: output presentato con header di sezione per tappa
- [ ] Se Fase 4c eseguita: riepilogo per tappa mostrato accanto al riepilogo per categoria
```

---

## Step 4 — Commit

```bash
git add skills/siae-qa/SKILL.md skills/siae-qa/reference/question-trees.md skills/siae-qa/XRAY-TEMPLATES.md
git commit -m "feat(siae-qa): add Phase 4c user-flow ordering with L0 questions and CRUD skeleton"
```
