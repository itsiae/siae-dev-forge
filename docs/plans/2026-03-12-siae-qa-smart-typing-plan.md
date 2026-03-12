# siae-qa Smart Typing — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Aggiungere alla skill `siae-qa` una Phase 0 di Smart Req Typing che inferisce il tipo di requisito dalla story/AC e lancia domande contestuali mirate tramite alberi per tipo (FE / BE / ETL / DB / Auth / Integration).
**Architettura:** Nuova Phase 0 in SKILL.md + file `reference/question-trees.md` con 6 alberi di domande L1/L2/L3. Phase 4a aggiornata per consumare il Req Profile prodotto dalla Phase 0.
**Stack:** Markdown (skill DevForge), no codice sorgente.
**SP:** 3

---

### Task 1: Crea `skills/siae-qa/reference/question-trees.md` [DONE]

**File coinvolti:**
- Crea: `skills/siae-qa/reference/question-trees.md`

**Contesto:** File di reference con 6 alberi di domande contestuali (FE, BE, ETL, DB, Auth, Integration). Ogni albero ha domande su 3 livelli: L1 (flusso principale), L2 (edge case specifici del tipo), L3 (integrazioni/dipendenze). Le domande vengono usate dalla Phase 0 di SKILL.md.

**Step 1: Verifica che il file non esista ancora (RED)**

```bash
ls skills/siae-qa/reference/question-trees.md 2>&1
```
Output atteso: `No such file or directory`

**Step 2: Crea la directory reference se non esiste**

```bash
ls skills/siae-qa/reference/ 2>&1
```
Output atteso: directory esistente o `No such file or directory`

**Step 3: Scrivi `skills/siae-qa/reference/question-trees.md`**

Contenuto esatto del file:

```markdown
# Question Trees — siae-qa Smart Req Typing

Ogni albero è strutturato su 3 livelli:
- **L1 — Flusso principale:** verifica/completa la comprensione del happy path
- **L2 — Edge case specifici del tipo:** scenari limite propri di quel dominio
- **L3 — Integrazioni / dipendenze:** chi chiama? cosa chiama? dipendenze esterne?

Claude fa UNA domanda alla volta.
**Salta ogni domanda già rispondibile dagli AC/description/commenti esistenti.**

---

## Frontend (FE)

**Segnali di inferenza:** "componente", "pagina", "form", "UI", "Vue", "Angular",
"React", "click", "visualizza", "render", "responsive", "upload", "drag"

### L1 — Flusso principale
1. "Il form/componente ha stati di caricamento (loading/skeleton)?
   Cosa mostra all'utente mentre aspetta i dati dall'API?"
2. "Quali campi sono obbligatori? Ci sono campi con formato specifico
   (email, IBAN, data, codice fiscale) che richiedono validazione?"

### L2 — Edge case specifici FE
3. "Cosa mostra la pagina se la lista di dati è vuota?
   C'è un empty state dedicato o si nasconde il componente?"
4. "La feature deve funzionare su mobile? Ci sono breakpoint critici
   (es. < 768px) dove il layout cambia significativamente?"
5. "Cosa succede se l'utente naviga via durante un'operazione in corso
   (upload in corso, form non salvato)? C'è una guardia di navigazione?"

### L3 — Integrazioni / dipendenze
6. "Da quale API recupera i dati? Cosa mostra se l'API risponde
   con errore 500 o timeout? C'è un messaggio di errore dedicato?"

---

## Backend Microservice (BE)

**Segnali di inferenza:** "API", "endpoint", "service", "REST", "controller",
"Spring", "Lambda", "validazione", "business rule", "handler", "mapper"

### L1 — Flusso principale
1. "Quali metodi HTTP espone questo endpoint? Quali status code restituisce
   per il caso di successo e per ogni caso di errore previsto?"
2. "Quali campi del payload sono obbligatori?
   Ci sono vincoli di formato o range (es. importo > 0, ISRC pattern)?"

### L2 — Edge case specifici BE
3. "L'operazione è idempotente? Cosa succede se viene chiamata due volte
   con lo stesso payload (es. doppio click, retry automatico del client)?"
4. "Ci sono regole business che bloccano l'operazione?
   (es. stato record incompatibile, quota superata, record già esistente)"
5. "Come gestisce una dipendenza esterna assente o lenta?
   C'è circuit breaker, timeout configurato o retry con backoff?"

### L3 — Integrazioni / dipendenze
6. "Chi chiama questo endpoint (client FE, altro microservizio, scheduler)?
   Il contratto API è già definito in un file OpenAPI/Swagger?"

---

## ETL / Data Pipeline

**Segnali di inferenza:** "Glue", "PySpark", "pipeline", "trasformazione",
"bronze", "silver", "gold", "job", "ETL", "medallion", "crawler", "Athena"

### L1 — Flusso principale
1. "Qual è la trasformazione principale?
   Da quale layer (bronze/silver/gold) parte e quale layer produce?"
2. "Qual è la chiave di deduplicazione dei record?
   Come vengono gestiti i duplicati (drop, keep-first, keep-last, merge)?"

### L2 — Edge case specifici ETL
3. "Cosa succede con record nulli o malformati nella sorgente?
   Vengono scartati (drop), messi in quarantena (dead-letter) o il job fallisce?"
4. "Il job è idempotente? Se viene rieseguito sullo stesso intervallo temporale,
   sovrascrive i dati o li duplica?"
5. "C'è un volume soglia (es. 0 record letti, > N record anomali)
   oltre il quale il job deve fallire o generare un alert?"

### L3 — Integrazioni / dipendenze
6. "Il job dipende da job o layer upstream? Come si comporta se upstream
   non ha prodotto dati per questa finestra temporale?"

---

## Database

**Segnali di inferenza:** "migration", "schema", "query", "tabella", "indice",
"DDL", "flyway", "liquibase", "ALTER TABLE", "stored procedure", "view"

### L1 — Flusso principale
1. "La migration è reversibile? Esiste (o va creato) uno script di rollback
   testato che riporta allo stato precedente?"
2. "La migration modifica dati esistenti (UPDATE/DELETE su righe)
   o solo struttura (DDL puro senza toccare dati)?"

### L2 — Edge case specifici DB
3. "Ci sono vincoli di integrità referenziale (FK) da verificare
   prima o dopo la migration? Quali tabelle correlate potrebbero rompersi?"
4. "La migration è safe su tabelle con milioni di righe?
   Usa LOCK TABLE? Ha un impatto stimato sul tempo di downtime?"

### L3 — Integrazioni / dipendenze
5. "I servizi applicativi che leggono/scrivono su questa tabella
   sono compatibili con il nuovo schema PRIMA del deploy applicativo?"

---

## Auth / Security

**Segnali di inferenza:** "login", "logout", "ruolo", "permesso", "token",
"autenticazione", "RBAC", "JWT", "SSO", "autorizzazione", "profilo utente"

### L1 — Flusso principale
1. "Quali ruoli/profili possono eseguire questa operazione?
   Chi NON deve poterla eseguire? Il blocco è silenzioso (403) o con messaggio?"
2. "Il token di autenticazione ha un TTL?
   Cosa succede se scade durante una sessione attiva?"

### L2 — Edge case specifici Auth
3. "Un utente può agire su risorse di un altro utente?
   C'è isolamento per tenant, organizzazione o codice autore?"
4. "L'endpoint è soggetto a rate limiting?
   Cosa restituisce il sistema quando la soglia viene superata?"

### L3 — Integrazioni / dipendenze
5. "Le azioni di questo tipo vengono registrate in un log di audit?
   Chi ha fatto cosa, quando, da quale IP?"

---

## Integration / External

**Segnali di inferenza:** "webhook", "chiamata esterna", "API terza parte",
"evento", "Kafka", "SQS", "SNS", "notifica", "callback", "polling"

### L1 — Flusso principale
1. "Cosa fa il sistema se l'API/servizio esterno non risponde entro il timeout?
   C'è retry automatico con backoff? Quanti tentativi?"
2. "Come si gestisce un payload inatteso o un codice di errore sconosciuto
   proveniente dall'esterno? Il sistema ignora, logga o fallisce?"

### L2 — Edge case specifici Integration
3. "Il sistema è resiliente a risposte parziali
   (es. solo alcuni record restituiti, paginazione incompleta)?"
4. "L'evento/messaggio può arrivare out-of-order o duplicato?
   Il consumer è idempotente?"

### L3 — Integrazioni / dipendenze
5. "Esiste un ambiente di staging o sandbox dell'esterno per i test?
   O si usa un mock/stub/WireMock in locale?"
```

**Step 4: Verifica struttura (GREEN)**

```bash
grep -c "^## " skills/siae-qa/reference/question-trees.md
```
Output atteso: `6` (6 sezioni per tipo)

```bash
grep -c "^### L" skills/siae-qa/reference/question-trees.md
```
Output atteso: `17` (L1+L2+L3 per ogni tipo, DB ne ha solo 2)

**Step 5: Commit**

```bash
git add skills/siae-qa/reference/question-trees.md
git commit -m "feat(siae-qa): add contextual question trees for smart req typing"
```

---

### Task 2: Aggiungi Phase 0 a `skills/siae-qa/SKILL.md` [PENDING]

**Dipende da:** Task 1 (question-trees.md deve esistere prima)

**File coinvolti:**
- Modifica: `skills/siae-qa/SKILL.md`

**Contesto:** Inserire la nuova sezione "Phase 0 — Smart Req Typing" PRIMA di "WORKFLOW A 5 FASI". La Phase 0 è sempre obbligatoria: inferisce il tipo dalla story, mostra la Req Typing Card, chiede conferma solo se MEDIUM/LOW, poi lancia le domande del tree pertinente.

**Step 1: Verifica stato attuale (RED)**

```bash
grep -n "Phase 0" skills/siae-qa/SKILL.md
```
Output atteso: nessun output (Phase 0 non esiste ancora)

```bash
wc -l skills/siae-qa/SKILL.md
```
Output atteso: `~377` righe

**Step 2: Inserisci Phase 0 in `skills/siae-qa/SKILL.md`**

Inserire PRIMA della riga `## WORKFLOW A 5 FASI` il seguente blocco:

```markdown
---

## Phase 0 — Smart Req Typing [SEMPRE OBBLIGATORIA — prima di tutto]

Prima di leggere AC o interrogare Jira, inferisci il tipo di requisito.
**Non chiedere ciò che la story dice già.** Leggi prima, chiedi solo il delta.

### 0a — Inferisci il tipo

Leggi in ordine: summary della story, AC/description, commenti, label Jira, stack del progetto.
Cerca i segnali della tabella seguente:

| Tipo | Segnali (summary, AC, description, label, stack) |
|------|--------------------------------------------------|
| **Frontend (FE)** | "componente", "pagina", "form", "UI", "Vue", "Angular", "React", "click", "visualizza", "render", "responsive" |
| **Backend Microservice (BE)** | "API", "endpoint", "service", "REST", "controller", "Spring", "Lambda", "validazione", "business rule" |
| **ETL / Data Pipeline** | "Glue", "PySpark", "pipeline", "trasformazione", "bronze", "silver", "gold", "job", "ETL", "medallion" |
| **Database** | "migration", "schema", "query", "tabella", "indice", "DDL", "flyway", "liquibase" |
| **Auth / Security** | "login", "logout", "ruolo", "permesso", "token", "autenticazione", "RBAC", "JWT" |
| **Integration / External** | "webhook", "chiamata esterna", "API terza parte", "evento", "Kafka", "SQS", "notifica" |

**Confidence:**
- **HIGH (≥ 90%):** 2+ segnali forti convergenti
- **MEDIUM (60-89%):** 1 segnale forte o 2+ deboli
- **LOW (< 60%):** segnali ambigui o assenti

### 0b — Mostra Req Typing Card

Mostra sempre la card con il tipo inferito:

```
REQ PROFILE:
  Tipo:       [Frontend / BE / ETL / Database / Auth / Integration]
  Confidence: [HIGH / MEDIUM / LOW]
  Segnali:    [elenco segnali usati dall'inferenza]
  Stack:      [tecnologie rilevate]
```

- **Se HIGH:** procedi direttamente con le domande del tree (0c)
- **Se MEDIUM/LOW:** chiedi conferma con scelta multipla:
  "Il requisito mi sembra [tipo inferito]. Confermi? (si / altro tipo: FE / BE / ETL / DB / Auth / Integration)"

### 0c — Lancia le domande del tree contestuale

Usa le domande in `reference/question-trees.md` per il tipo confermato.

**Regola fondamentale:** salta ogni domanda già rispondibile dagli AC/description esistenti.
Fai UNA domanda alla volta. Aspetta la risposta prima di procedere alla successiva.

Al termine delle domande, aggiorna la Req Profile Card con gli scenari raccolti:

```
REQ PROFILE (aggiornato):
  Tipo:       [tipo]
  Scenari L1: [lista scenari flusso principale]
  Scenari L2: [lista edge case contestuali]
  Scenari L3: [lista scenari integrazione/dipendenze]
```

Questa card è l'input aggiuntivo per Phase 4a (matrice scenari).

---
```

**Step 3: Verifica inserimento (GREEN)**

```bash
grep -n "Phase 0" skills/siae-qa/SKILL.md
```
Output atteso: almeno 2 righe con "Phase 0"

```bash
grep -n "Req Typing Card\|REQ PROFILE\|question-trees" skills/siae-qa/SKILL.md
```
Output atteso: almeno 3 righe matchate

```bash
wc -l skills/siae-qa/SKILL.md
```
Output atteso: `~430-440` righe (< 500 — sotto soglia)

**Step 4: Commit**

```bash
git add skills/siae-qa/SKILL.md
git commit -m "feat(siae-qa): add Phase 0 Smart Req Typing with inference and contextual question trees"
```

---

### Task 3: Aggiorna Phase 4a in `skills/siae-qa/SKILL.md` [PENDING]

**Dipende da:** Task 2

**File coinvolti:**
- Modifica: `skills/siae-qa/SKILL.md` (sezione Phase 4a)

**Contesto:** Phase 4a deve consumare la Req Profile Card prodotta da Phase 0. Aggiungere un paragrafo di apertura che integra gli scenari del Req Profile nella matrice 4 categorie esistente (positivi/edge/negativi/profilazioni).

**Step 1: Verifica stato attuale (RED)**

```bash
grep -n "Req Profile" skills/siae-qa/SKILL.md
```
Output atteso: solo le righe in Phase 0 (nessuna in Phase 4a ancora)

**Step 2: Aggiorna apertura Phase 4a in `skills/siae-qa/SKILL.md`**

Sostituire la riga di apertura di `#### 4a — Elicitazione scenari [OBBLIGATORIA prima di scrivere qualsiasi TC]`:

Da:
```markdown
Prima di generare i Test Case, devi coprire tutte e quattro le categorie di scenario.
Per ogni categoria dove il contesto non e' gia' chiaro dagli AC, fai domande esplicite al developer.
Fai UNA domanda alla volta. Non procedere alla generazione finche' non hai risposta su ogni categoria.
```

A:
```markdown
**Input:** Req Profile Card (Phase 0) + AC (Phase 1).
Gli scenari raccolti nella Phase 0 (L1/L2/L3) vanno classificati nelle 4 categorie qui sotto
PRIMA di generare i TC. Non ripetere domande già poste in Phase 0.

Per ogni categoria ancora scoperta dopo aver assorbito il Req Profile e gli AC,
fai domande esplicite al developer. UNA alla volta.
Non procedere alla generazione finché tutte e 4 le categorie non sono valutate.
```

**Step 3: Verifica (GREEN)**

```bash
grep -n "Req Profile Card (Phase 0)" skills/siae-qa/SKILL.md
```
Output atteso: 1 riga in Phase 4a

**Step 4: Commit**

```bash
git add skills/siae-qa/SKILL.md
git commit -m "feat(siae-qa): update Phase 4a to consume Req Profile from Phase 0"
```

---

### Task 4: Aggiorna checklist, anti-razionalizzazione e vincoli in `skills/siae-qa/SKILL.md` [PENDING]

**Dipende da:** Task 3

**File coinvolti:**
- Modifica: `skills/siae-qa/SKILL.md` (sezioni CHECKLIST, anti-razionalizzazione, VINCOLI)

**Contesto:** Aggiungere voci relative alla Phase 0 in tutte e tre le sezioni di governance della skill.

**Step 1: Verifica stato attuale (RED)**

```bash
grep -n "Smart Typing\|Req Profile\|question-trees\|Phase 0" skills/siae-qa/SKILL.md | grep -v "^.*Phase 0 —"
```
Output atteso: solo le righe già inserite nei task precedenti (nessuna in checklist/anti-raz/vincoli)

**Step 2: Aggiungi voci in CHECKLIST DI VERIFICA**

Aggiungere come PRIME voci della checklist (prima di "AC letti da Jira..."):

```markdown
- [ ] Phase 0 eseguita: tipo requisito inferito e Req Profile Card mostrata
- [ ] Confidence HIGH → tree lanciato senza conferma tipo | MEDIUM/LOW → conferma ricevuta
- [ ] Domande del tree skippate se risposta già presente in AC/description
- [ ] Req Profile Card aggiornata con scenari L1/L2/L3 prima di procedere a Phase 4a
```

**Step 3: Aggiungi voci in Tabella Anti-Razionalizzazione**

Aggiungere in fondo alla tabella:

```markdown
| "Ho letto gli AC, so già il tipo — salto Phase 0" | Phase 0 non è solo typing: è la raccolta degli scenari contestuali che gli AC non esplicitano. Senza queste domande, i TC coprono solo ciò che è scritto, non ciò che può rompersi. |
| "Le domande del tree rallentano il workflow" | 4-6 domande mirate producono 2-3x più scenari edge rispetto alla matrice generica. Il piano di test finale è più completo in meno iterazioni. |
| "Il tipo è ovvio, non serve inferire" | Ovvio per te. La Req Profile Card documenta il tipo e i segnali: è evidenza, non burocrazia. Se sbagli il tipo, i TC coprono il dominio sbagliato. |
```

**Step 4: Aggiungi vincolo in VINCOLI NON NEGOZIABILI**

Aggiungere come primo vincolo (prima dell'attuale vincolo 1):

```markdown
0. **Phase 0 è sempre la prima fase** — nessun AC viene letto senza aver prima inferito il tipo e lanciato le domande del tree contestuale; la Req Profile Card deve essere prodotta prima di Phase 1
```

Rinumerare i vincoli esistenti (1→2, 2→3, ecc.) oppure usare numerazione 0 + mantenere 1-8 invariati.

**Step 5: Verifica finale (GREEN)**

```bash
grep -n "Phase 0 eseguita\|Phase 0 è sempre\|rallentano il workflow" skills/siae-qa/SKILL.md
```
Output atteso: 3 righe, una per ciascuna voce aggiunta

```bash
wc -l skills/siae-qa/SKILL.md
```
Output atteso: ≤ 500 righe

**Step 6: Commit**

```bash
git add skills/siae-qa/SKILL.md
git commit -m "feat(siae-qa): update checklist, anti-rationalization and constraints for Phase 0"
```
