# siae-qa Smart Typing — Design Doc

**Data:** 2026-03-12
**Autore:** mazzacuv
**Status:** APPROVATO

---

## Contesto

La skill `siae-qa` attualmente chiede domande al developer **solo quando gli AC sono assenti o incompleti**. L'elicitazione degli scenari (Phase 4a) usa 4 categorie generiche (positivi, edge, negativi, profilazioni) senza tenere conto del tipo di requisito (Frontend, Backend, ETL, Database, Auth, Integration).

Questo produce piani di test incompleti perché le domande giuste per una pipeline ETL sono radicalmente diverse da quelle per un componente Vue.js.

---

## Goal

Aggiungere alla skill `siae-qa` una **Phase 0: Smart Req Typing** che:

1. **Inferisce il tipo di requisito** leggendo la story/AC (mai chiedendo se può dedurlo)
2. **Mostra la typing card** con confidence level — chiede conferma solo se MEDIUM/LOW
3. **Lancia domande contestuali** specifiche per il tipo inferito (UNA alla volta, solo quelle non già rispondibili dagli AC)
4. Produce una **Req Profile Card** che alimenta tutte le fasi successive

Le domande contestuali del tree **integrano** (non sostituiscono) la matrice 4 categorie in Phase 4a: producono scenari che vengono classificati nelle categorie esistenti.

---

## Architettura

### Nuovi file

```
skills/siae-qa/
├── SKILL.md                          ← modifica: aggiunge Phase 0
└── reference/
    └── question-trees.md             ← NUOVO: alberi domande per tipo
```

### Tipi di requisito rilevabili

| Tipo | Segnali di inferenza (da summary, AC, description, label, stack) |
|------|------------------------------------------------------------------|
| **Frontend (FE)** | "componente", "pagina", "form", "UI", "Vue", "Angular", "React", "click", "visualizza", "render", "responsive" |
| **Backend Microservice (BE)** | "API", "endpoint", "service", "REST", "controller", "Spring", "Lambda", "validazione", "business rule" |
| **ETL / Data Pipeline** | "Glue", "PySpark", "pipeline", "trasformazione", "bronze", "silver", "gold", "job", "ETL", "medallion" |
| **Database** | "migration", "schema", "query", "tabella", "indice", "DDL", "flyway", "liquibase" |
| **Auth / Security** | "login", "logout", "ruolo", "permesso", "token", "autenticazione", "RBAC", "JWT", "SSO" |
| **Integration / External** | "webhook", "chiamata esterna", "API terza parte", "evento", "Kafka", "SQS", "SNS", "notifica" |

### Confidence levels

- **HIGH (≥ 90%):** 2+ segnali forti convergenti → mostra tipo + chiede conferma in blocco con la pre-flight card di apertura
- **MEDIUM (60-89%):** 1 segnale forte o 2+ deboli → chiede conferma esplicita prima di procedere
- **LOW (< 60%):** segnali ambigui o assenti → chiede direttamente "Che tipo di requisito è?" con scelta multipla

### Struttura domande per tree (L1 → L2 → L3)

Ogni tree ha 3 livelli:
- **L1 — Flusso principale:** "Cosa fa esattamente questa feature?" — verifica/completa la comprensione del happy path
- **L2 — Edge case specifici del tipo:** domande che dipendono dal tipo (es. FE: stati vuoti/loading/responsive; ETL: nulls/volumi/idempotency)
- **L3 — Integrazioni / dipendenze:** chi chiama questa feature? cosa chiama? dipendenze esterne?

Claude fa UNA domanda per volta. Salta le domande già rispondibili dagli AC esistenti.

---

## Modifiche a SKILL.md

### Phase 0 da aggiungere PRIMA di "WORKFLOW A 5 FASI"

```
## Phase 0 — Smart Req Typing [SEMPRE OBBLIGATORIA]

1. Leggi summary, AC, description, label Jira, stack del progetto
2. Inferisci il tipo con confidence level (HIGH/MEDIUM/LOW)
3. Mostra la Req Typing Card
4. Se HIGH → procedi con il tree del tipo inferito
   Se MEDIUM/LOW → chiedi conferma con scelta multipla
5. Lancia il tree di domande contestuali (reference/question-trees.md)
   Solo domande NON già rispondibili dagli AC
6. Produce la Req Profile Card → input per tutte le fasi successive
```

### Req Typing Card (output Phase 0)

```
REQ PROFILE:
  Tipo:      Frontend (FE) / BE / ETL / DB / Auth / Integration
  Confidence: HIGH / MEDIUM / LOW
  Segnali:   [lista segnali usati per l'inferenza]
  Stack:     [tecnologie rilevate]
  Domande tree risposto: [N/M domande]
```

### Aggiornamento Phase 4a

La matrice 4 categorie rimane invariata. Si aggiunge un riferimento al Req Profile:

```
Input Phase 4a: Req Profile Card (Phase 0) + AC (Phase 1)
Le domande del tree hanno già elicitato scenari contestuali.
Classifica quei scenari nelle 4 categorie prima di generare i TC.
```

---

## Contenuto reference/question-trees.md

Per ogni tipo, 4-6 domande strutturate su 3 livelli:

### Frontend (FE)
- L1: "La feature ha stati di caricamento (loading/skeleton)? Cosa mostra mentre aspetta i dati?"
- L1: "Il form ha validazione client-side? Quali campi sono obbligatori? Quali hanno formato specifico?"
- L2: "Cosa mostra la pagina se la lista di dati è vuota? C'è un empty state dedicato?"
- L2: "La feature deve funzionare su mobile? Ci sono breakpoint critici da coprire?"
- L2: "Cosa succede se l'utente naviga via durante un'operazione in corso (upload, salvataggio)?"
- L3: "Da quale API recupera i dati? Cosa mostra se l'API risponde con errore 500 o timeout?"

### Backend Microservice (BE)
- L1: "Quali metodi HTTP espone questo endpoint? Quali status code restituisce per ogni caso?"
- L1: "Quali campi del payload sono obbligatori? Quali vincoli di formato/range?"
- L2: "L'operazione è idempotente? Cosa succede se viene chiamata due volte con lo stesso payload?"
- L2: "Ci sono regole business che bloccano l'operazione? (es. stato incompatibile, record duplicato)"
- L2: "Come gestisce una dipendenza esterna assente o lenta? C'è circuit breaker o retry?"
- L3: "Chi chiama questo endpoint? Il contratto API è già definito (OpenAPI)?"

### ETL / Data Pipeline
- L1: "Qual è la trasformazione principale? Da quale layer (bronze/silver/gold) a quale?"
- L1: "Qual è la chiave di deduplicazione? Come si gestiscono i duplicati?"
- L2: "Cosa succede con record nulli o malformati nella sorgente? Drop, quarantena o errore?"
- L2: "Il job è idempotente? Si può rieseguire senza effetti collaterali sui dati?"
- L2: "C'è un volume soglia oltre il quale il job deve fallire o segnalare un'anomalia?"
- L3: "Il job dipende da job upstream? Come si gestisce se upstream non ha prodotto dati?"

### Database
- L1: "La migration è reversibile? Esiste uno script di rollback?"
- L1: "La migration modifica dati esistenti (UPDATE/DELETE) o solo struttura (DDL)?"
- L2: "Ci sono vincoli di integrità referenziale da verificare prima/dopo la migration?"
- L2: "La migration è safe su tabelle con milioni di righe? Si usa LOCK TABLE?"
- L3: "I servizi che usano questa tabella sono compatibili con il nuovo schema prima del deploy?"

### Auth / Security
- L1: "Quali ruoli possono eseguire questa operazione? Chi non deve poterla eseguire?"
- L1: "Il token di autenticazione ha un TTL? Cosa succede alla scadenza?"
- L2: "Un utente può agire su risorse di un altro utente? C'è isolamento per tenant/organizzazione?"
- L2: "L'endpoint è protetto da rate limiting? Cosa succede oltre la soglia?"
- L3: "Il log di audit registra chi ha eseguito l'operazione e quando?"

### Integration / External
- L1: "Cosa fa il sistema se l'API esterna non risponde entro il timeout? C'è retry con backoff?"
- L1: "Come si gestisce un payload inatteso o un codice di errore sconosciuto dall'esterno?"
- L2: "Il sistema è resiliente a risposte parziali (es. solo alcuni record restituiti)?"
- L2: "L'evento/webhook può arrivare out-of-order o duplicato? Come si gestisce?"
- L3: "Esiste un ambiente di staging dell'esterno per i test? O si usa un mock/stub?"

---

## Criteri di Accettazione

- [ ] Phase 0 è SEMPRE la prima fase eseguita, prima della lettura AC
- [ ] L'inferenza usa i segnali definiti nella tabella tipi — mai inventati
- [ ] Confidence HIGH → nessuna domanda di conferma tipo (solo mostra la card)
- [ ] Confidence MEDIUM/LOW → una domanda di conferma con scelta multipla
- [ ] Le domande del tree si saltano se la risposta è già negli AC
- [ ] La Req Profile Card è sempre presente come output di Phase 0
- [ ] Phase 4a usa la Req Profile Card come input aggiuntivo
- [ ] question-trees.md creato con tutti e 6 i tipi documentati
- [ ] Il comportamento è identico in Tier 1 (MCP) e Tier 3 (CSV)

---

## Stima Story Points

**3 SP** — 1-2 giorni

- Modifica SKILL.md: 1 SP (aggiunge ~60-80 righe a 377 esistenti → rimane < 500)
- Creazione reference/question-trees.md: 1 SP
- Aggiornamento Phase 4a con riferimento al Req Profile: 0.5 SP
- Aggiornamento checklist + anti-razionalizzazione: 0.5 SP
