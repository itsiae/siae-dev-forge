# Task 03 — Cardinalità minima matrice scenari [PENDING]

**File:** `skills/siae-qa/SKILL.md`
**Sezione:** "Fase 4 — Generazione Test Case step-based" → "4a — Elicitazione scenari"
**Cluster:** A — Determinismo

---

## Obiettivo

Aggiungere una tabella di cardinalità minima per tipo nella Fase 4a di SKILL.md.
Un developer che dichiara N/A su una categoria con minimo > 0 deve fornire
giustificazione esplicita registrata nel piano.

---

## Step 1 — Leggi la sezione corrente

Leggi `skills/siae-qa/SKILL.md` dalla sezione `#### 4a — Elicitazione scenari`.
Individua il testo "Per ogni categoria ancora scoperta dopo aver assorbito il Req Profile".

---

## Step 2 — Aggiungi tabella di cardinalità minima

Dopo il blocco `**Non puoi procedere alla generazione con categorie non valutate.**`
e prima della sezione `#### 4b`, inserisci:

```markdown
#### Cardinalità minima per tipo [OBBLIGATORIA]

Prima di procedere alla generazione, verifica che la matrice rispetti i minimi:

| Tipo | Positivi | Edge | Negativi | Profilazioni |
|------|----------|------|----------|--------------|
| Frontend (FE) | 1 per AC | 2 | 2 | 0 (obbligatorio solo se Auth presente) |
| Backend Microservice (BE) | 1 per AC | 2 | 3 | 0 (obbligatorio solo se Auth presente) |
| ETL / Data Pipeline | 1 | 3 | 2 | 0 |
| Database | 1 | 2 | 1 | 0 |
| Auth / Security | 1 | 2 | 2 | 2 (minimo assoluto) |
| Integration REST / Sync | 1 | 2 | 2 | 0 |
| Integration Event / Async | 1 | 3 | 2 | 0 |
| Notification / Messaging | 1 | 2 | 2 | 0 |
| Batch / Scheduler | 1 | 3 | 2 | 0 |
| Report / Export | 1 | 2 | 1 | 0 |
| Feature Flag / Configuration | 1 | 2 | 1 | 0 |
| File Processing / Async Upload | 1 | 2 | 2 | 0 |

**Regola N/A:**
Se il developer dichiara "N/A" su una categoria con minimo > 0, la skill deve:
1. Chiedere giustificazione esplicita: "Perché questa categoria non è applicabile?"
2. Registrare nel Test Plan: `⚠️ RISCHIO ACCETTATO: [categoria] — N/A dichiarato dal developer. Motivo: [motivo]`
3. Non procedere senza questa giustificazione.

**Non puoi procedere alla generazione se:**
- Una categoria con minimo > 0 ha 0 scenari E nessuna giustificazione N/A
- La matrice non ha il campo `Fonte` (AC / Code Scan / Developer) per ogni scenario
```

---

## Step 3 — Aggiorna il template Matrice Scenari in XRAY-TEMPLATES.md

Leggi `skills/siae-qa/XRAY-TEMPLATES.md` sezione "Template Matrice Scenari".

Sostituisci il template con la versione estesa che include il campo Fonte:

```markdown
## Template Matrice Scenari

Output atteso della fase 4a — matrice scenari compilata prima della generazione:

```
Categoria              | Scenari identificati                          | Fonte      | Count
-----------------------|-----------------------------------------------|------------|------
Positivi (happy path)  | [lista da AC + varianti]                      | AC         | N
Edge case              | [lista da domande o da AC]                    | AC/Dev/Scan| N
Alternativi/negativi   | [lista da domande o da AC]                    | AC/Dev/Scan| N
Profilazioni/ruoli     | [lista da domande, o "N/A - confermato + motivo"] | Dev     | N
```

Legenda Fonte:
- `AC` — derivato dagli Acceptance Criteria
- `Dev` — emerso dalle domande al developer
- `Scan` — derivato dalla Phase 0-bis Code Scan (se eseguita)

Se per una categoria il developer conferma N/A su categoria con minimo > 0:
→ Registra `⚠️ RISCHIO ACCETTATO: [categoria] N/A — Motivo: [motivo dichiarato]`
→ Il motivo è obbligatorio. Non accettare "N/A" senza motivazione.
```

---

## Step 4 — Commit

```bash
git add skills/siae-qa/SKILL.md skills/siae-qa/XRAY-TEMPLATES.md
git commit -m "feat(siae-qa): enforce minimum scenario cardinality per type in matrix 4a"
```
