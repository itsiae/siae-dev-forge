---
name: siae-qa
description: >
  Use when implementation is complete and formal test documentation for Xray is needed.
  Trigger: completamento brainstorming (Fase 2), completamento ciclo TDD (Fase 5), /forge-qa.
---

# SIAE QA — Orchestrazione Xray

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨 DevForge · AI Competence Center                  ║
║         "Il codice si forgia. Il developer cresce."              ║
╚══════════════════════════════════════════════════════════════════╝
```

## LA LEGGE DI FERRO

```
NESSUN RILASCIO SENZA CASI DI TEST VERIFICATI E DOCUMENTATI IN XRAY
```

> **Tipo:** Rigid | **Fase SDLC:** 5. Testing / QA

---

> 📊 **Dai repo itsiae:** Il 38% dei bug escapati in produzione non aveva scenario di test nel piano QA. I team con matrice scenari hanno 55% meno escape.
> Fonte: analisi su 816 repository GitHub itsiae (60 Java, 44 HCL, 23 Python, 22 TypeScript).

## QUANDO SI APPLICA

Questa skill si attiva in due momenti del ciclo SDLC:

- **Fine Fase 2 (brainstorming):** design approvato → generare bozza Test Plan con i Test Case corrispondenti agli AC
- **Fine Fase 5 (TDD):** test automatizzati scritti → creare/sincronizzare i Test Case Xray con lo stato di automazione corretto
- **Su `/forge-qa`:** invocazione manuale per export, riesecuzione o aggiornamento

---

## HARD-GATE — Nessun Test Case senza AC

```
Prima di generare Test Case, gli Acceptance Criteria devono essere disponibili.
```

Se Jira e' configurato ma il campo AC e' vuoto, **non fermarti**: procedi cosi':

1. Leggi la **descrizione** della Story (campo `description`) e cerca sezioni strutturate
   (Given/When/Then, "Come utente...", bullet list di requisiti)
2. Se la descrizione non e' sufficiente, leggi i **commenti** della Story e i link a pagine
   Confluence collegate
3. Se ancora insufficiente, poni **domande mirate al developer UNA ALLA VOLTA** finche' hai
   abbastanza contesto per scrivere Test Case concreti

Non generare Test Case vaghi o generici: ogni test deve essere tracciabile a un comportamento
specifico, anche se inferito dalla conversazione.

---

## LIVELLI DI INTEGRAZIONE (graceful degradation)

Prima di iniziare, verifica quale tier e' disponibile e annuncialo nella pre-flight card.

| Tier | Condizione | Comportamento |
|------|------------|---------------|
| **Tier 1 — MCP Atlassian** | MCP `atlassian` disponibile | Legge AC da Jira, legge Confluence, crea TC e Test Plan in Xray via MCP, raccoglie chiavi Jira assegnate |
| **Tier 3 — CSV export** | MCP non disponibile | Genera CSV semicolon-separated in formato Xray-importabile, import manuale, mappatura chiavi richiesta post-import |

Ogni operazione deve esplicitare il tier usato nella pre-flight card di apertura.

---

## PRE-FLIGHT CARD DI APERTURA

Prima di iniziare il workflow, mostra questa card con il tier rilevato:

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-qa |
|:---|
| 📡 Tier attivo: Tier 1 MCP / Tier 3 CSV |
| 🎫 Story Jira: `PROJ-XXX` |
| ✅ AC disponibili: Si / No |
| 📚 Confluence: Spazio QA trovato / Non configurato |
| 💡 Perche': Il tier determina come vengono sincronizzati i TC |
| 🚫 Se NO: Se Tier 3: esporto CSV importabile manualmente in Xray |

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

- **Se HIGH:** mostra la card e procedi con le domande del tree (0c).
  L'utente può correggere il tipo prima che il tree parta rispondendo con il tipo corretto
  (es. "in realtà è Auth"). In assenza di correzione, il tree parte immediatamente.
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

## WORKFLOW A 5 FASI

### Fase 1 — Lettura AC da Jira [HARD-GATE]

Non procedere alla Fase 2 senza AC o contesto sufficiente.

**Tier 1 (MCP):**
1. Usa `searchJiraIssuesUsingJql` con JQL: `key = {STORY_ID}` per recuperare la Story
2. Tenta di leggere il campo `Acceptance Criteria` (campo custom Xray/Jira)
3. Se il campo AC e' presente e popolato → usa direttamente, vai alla Fase 2
4. Se il campo AC e' assente o vuoto:
   - Leggi il campo `description` della Story — cerca strutture Given/When/Then, bullet list, "Come utente..."
   - Se description non e' sufficiente → leggi i `comments` della Story
   - Se ancora non basta → segui i link a pagine Confluence collegate alla Story
   - Se ancora insufficiente → chiedi al developer con domande mirate UNA ALLA VOLTA

**Tier 3 (no Jira):**
- Chiedi la Story ID (es. `PROJ-123`) e il titolo della User Story
- Poi chiedi gli AC con domande mirate, una alla volta, finche' il contesto e' completo
- Esempio prima domanda: "Descrivi il comportamento principale che questa Story deve implementare."

**Output atteso Fase 1:** lista strutturata di AC, ognuno identificabile come comportamento testabile.

---

### Fase 2 — Lettura Test Strategy da Confluence

**Tier 1 (MCP):**
- Cerca con CQL: `space = "QA" AND title ~ "Test Strategy {PROJECT_KEY}"`
- Naming convention attesa: `Test Strategy - {JIRA_PROJECT_KEY} - {Sprint/Release}`
- Leggi le sezioni: `Scope`, `Approach`, `Test Types`
- Se non trovata: registra WARNING e procedi senza questa sezione

**Tier 3 (no Confluence):**
- Segnala: `⚠️ WARNING: Test Strategy Confluence non cercabile — nessuna integrazione MCP`
- Procedi alla Fase 3 senza informazioni di scope

**Output atteso Fase 2:** sezioni Scope/Approach/Test Types lette, oppure WARNING registrato.

---

### Fase 3 — Generazione Test Plan

Struttura del Test Plan da creare o mostrare:

```
Test Plan: {Story summary}
  Versione:       {versione sprint/release}
  Sprint:         {sprint corrente}
  Link Story:     {URL Jira PROJ-XXX}
  Scope:          {da Confluence, o "da definire" se Tier 3}
  Test Cases:     [lista TC generati nella Fase 4]
```

**Tier 1 (MCP):** crea il Test Plan in Xray via MCP tool
**Tier 3:** mostra la struttura testuale, da importare manualmente

---

### Fase 4 — Generazione Test Case step-based

#### 4a — Elicitazione scenari [OBBLIGATORIA prima di scrivere qualsiasi TC]

**Input:** Req Profile Card (Phase 0) + AC (Phase 1).
Gli scenari raccolti nella Phase 0 (L1/L2/L3) vanno classificati nelle 4 categorie qui sotto
PRIMA di generare i TC. Non ripetere domande gia' poste in Phase 0.

Per ogni categoria ancora scoperta dopo aver assorbito il Req Profile e gli AC,
fai domande esplicite al developer. UNA alla volta.
Non procedere alla generazione finche' tutte e 4 le categorie non sono valutate.

**Categoria 1 — Scenari positivi (happy path)**
Hai gia' questo dagli AC. Verifica solo che siano completi.
Domanda tipo: "L'AC descrive il caso principale. C'e' qualche variante del flusso positivo che vuoi coprire esplicitamente?"

**Categoria 2 — Edge case**
Valori limite, stati vuoti, volumi estremi, timing. Se non emergono dagli AC, chiedi:
- "Cosa succede con input al limite del range valido? (es. importo = 0, lista vuota, data = oggi)"
- "Ci sono condizioni di gara o sequenze di eventi inattesi da coprire?"
- "Il sistema e' idempotente? Cosa succede se l'operazione viene eseguita due volte?"

**Categoria 3 — Scenari alternativi / negativi**
Flussi di errore, input non validi, permessi mancanti. Se non emergono dagli AC, chiedi:
- "Quali input non validi deve rifiutare il sistema? Con quale messaggio/comportamento?"
- "Cosa succede se una dipendenza esterna e' assente o risponde con errore?"
- "Ci sono stati del sistema che impediscono l'operazione? (es. record gia' esistente, stato non compatibile)"

**Categoria 4 — Profilazioni / ruoli**
Utenti diversi con permessi o dati diversi. Se la Story tocca autorizzazioni o ruoli, chiedi:
- "Quale tipo di utente esegue questa operazione? Ci sono altri ruoli che possono o non possono farlo?"
- "Il comportamento cambia in base al profilo? (es. autore vs editore, admin vs operatore)"
- "Ci sono dati sensibili che solo alcuni ruoli possono vedere?"

**Output atteso 4a:** matrice scenari compilata prima della generazione:

```
Categoria              | Scenari identificati
-----------------------|-----------------------------------------------
Positivi (happy path)  | [lista da AC + eventuali varianti]
Edge case              | [lista da domande o da AC]
Alternativi/negativi   | [lista da domande o da AC]
Profilazioni/ruoli     | [lista da domande, o "N/A - nessun controllo ruolo"]
```

Se per una categoria il developer conferma che non ci sono scenari aggiuntivi, registra "N/A — confermato dal developer" e procedi.
**Non puoi procedere alla generazione con categorie non valutate.**

---

#### 4b — Generazione Test Case

Per ogni scenario della matrice (4a), genera 1+ Test Case con questo formato:

| Campo | Contenuto |
|-------|-----------|
| ID | Numero sequenziale (1, 2, 3...) |
| Test Type | `Manual` |
| Team Competenza | `QA` |
| ID JIRA Story | `{PROJ-XXX}` — **obbligatorio** |
| User Story Description | Summary della Story Jira |
| Scenario (descrizione) | Titolo del Test Case — includi la categoria: es. `[EDGE] ...`, `[NEG] ...`, `[PROFILO] ...` |
| Step scenario | Numero step (1, 2, 3...) |
| Action | Cosa fa l'utente/sistema in questo step |
| Expected Result | Risultato atteso per questo step — **nel CSV il nome colonna e' `Expceted Result`** (typo storico del template importatore Xray SIAE) |
| Data | Dati di test specifici (vuoto se non necessario) |
| Automazione | `Y` se esiste test automatizzato per questo TC, `N` altrimenti |
| NRT | `Y` (default — il TC e' un Non-Regression Test) |

**Prefissi di categoria nel titolo Scenario:**
- Nessun prefisso = scenario positivo (happy path)
- `[EDGE]` = edge case (limite, vuoto, volume estremo)
- `[NEG]` = scenario negativo / alternativo (errore, input non valido, dipendenza assente)
- `[PROFILO]` = scenario specifico di ruolo / profilazione

**Regola multi-step:** stesso ID = stesso Test Case con step multipli. I metadati (tipo, team, Jira, descrizione scenario) si ripetono **solo nella prima riga**. Le righe successive dello stesso TC hanno solo: ID, step numero, Action, Expected Result.

**Riepilogo prima dell'export:** mostra la tabella completa al developer con la distribuzione per categoria. Il developer puo' modificare i valori di `Automazione` e `NRT` prima di procedere all'export.

```
Riepilogo copertura:
  Positivi:    N TC
  Edge case:   N TC
  Negativi:    N TC
  Profilazioni: N TC
  TOTALE:      N TC
```

---

### Fase 5 — Export / Sincronizzazione

**Tier 1 (MCP):**
1. Crea ogni Test Case in Xray via MCP
2. Ogni TC creato ottiene automaticamente una chiave Jira (es. `PROJ-456`) — registrala nella mappatura (vedi Passo post-export)
3. Dopo l'esecuzione dei test, aggiorna il Test Execution con i risultati

**Tier 3 (CSV):**
- Genera il file CSV con separatore `;` (semicolon) — **mai virgola**
- Formato esatto: vedi `reference/xray-csv-template.md`
- Header obbligatorio in prima riga
- Mostra il CSV all'utente e spiega come importarlo: Xray → Test → Import CSV

**Passo post-export — Mappatura ID sequenziali → chiavi Jira Xray [OBBLIGATORIO se si usa siae-automation]**

Dopo l'import del CSV (o la creazione MCP), Xray assegna a ogni TC una chiave Jira propria (`PROJ-XXX`).
Questa chiave è diversa dall'ID sequenziale usato nel CSV (`1`, `2`, `3`).

Se prevedi di usare `siae-automation` per generare test Cypress o Appium, **devi raccogliere questa mappatura** prima di chiudere la skill:

```
Mappatura TC — {STORY_ID}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ID CSV  →  Chiave Xray   Scenario
  1       →  PROJ-456      Verifica login credenziali valide
  2       →  PROJ-457      [EDGE] Login con campo vuoto
  3       →  PROJ-458      [NEG] Login con password errata
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Tier 1 (MCP):** la chiave viene restituita dalla risposta del tool di creazione — raccoglila automaticamente.
**Tier 3 (CSV):** chiedi al developer di aprire Xray dopo l'import e comunicare le chiavi assegnate. Non procedere con siae-automation finché non hai questa mappatura.

Salva la mappatura come output della skill: sarà l'input di Fase 1 di siae-automation.

---

## Limiti Operativi

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Tentativi max per step | 2 | Fermati. Chiedi all'utente prima di riprovare. |
| Step totali del processo QA | 5 | Se ne servono di piu', il perimetro di test e' troppo ampio. Decomponi. |
| Output max per analisi | 300 righe | Sintetizza. L'utente non legge wall-of-text. |

---

## REQUIRED SUB-SKILL: siae-verification

Invoca `siae-verification` prima di dichiarare il piano QA completato.

---

## Tabella Anti-Razionalizzazione

**Stai per razionalizzare? Leggi questa tabella. Poi torna al workflow.**

| Pensiero | Realta' |
|----------|---------|
| "Gli AC li so gia', non serve leggere Jira" | I Test Case derivano dagli AC formali, non dalla memoria. Se non li leggi, testi quello che pensi, non quello che serve. |
| "Il campo AC in Jira e' vuoto, non posso procedere" | Leggi la description, i commenti, i link Confluence. Se ancora non basta, chiedi al developer. Non fermarti mai solo perche' un campo e' vuoto. |
| "Xray non e' configurato, salto" | Genera il CSV. Il formato e' lo stesso. L'import manuale richiede 30 secondi. |
| "La Test Strategy in Confluence non c'e'" | Segnala WARNING e procedi, ma non fingere che non manchi. |
| "I test automatizzati coprono tutto, non servono i Test Case manuali" | I Test Case Xray non sono solo per test manuali. Sono la traccia formale QA collegata agli AC. |
| "Creo i Test Case dopo il deploy" | Dopo il deploy non si creano mai. I Test Case vanno in Xray prima del collaudo. |
| "Ho solo 2 AC, non serve uno step-by-step" | Ogni AC deve avere almeno 1 Test Case step-based. Il formato Xray e' standard: non si semplifica. |
| "Il developer sa gia' cosa testare" | Il developer sa cosa ha implementato. I Test Case tracciano cosa era richiesto. Sono cose diverse. |
| "Il happy path copre tutto" | Il happy path copre il caso ideale. I bug vivono negli edge case, nei negativi e nelle profilazioni. Non rilasciare senza averli elicitati esplicitamente. |
| "Gli edge case sono ovvi, non servono domande" | Gli edge case ovvi per il developer non lo sono per il QA — e viceversa. Chiedi sempre. Hai il permesso di sembrare pedante. |
| "Non ci sono ruoli diversi in questa Story" | Hai chiesto? Se non hai fatto la domanda, non puoi saperlo. Chiedi e poi registra "N/A — confermato". |
| "Genero i TC negativi dopo, ora faccio quelli positivi" | I TC negativi vengono dimenticati. La matrice 4a si compila PRIMA di scrivere qualsiasi TC. |
| "Ho troppi scenari, semplificoo" | La semplificazione e' un rischio QA, non un'efficienza. Se gli scenari sono troppi, discutili col developer e prioritizza — ma non eliminare senza discussione. |
| "Ho letto gli AC, so gia' il tipo — salto Phase 0" | Phase 0 non e' solo typing: e' la raccolta degli scenari contestuali che gli AC non esplicitano. Senza queste domande, i TC coprono solo cio' che e' scritto, non cio' che puo' rompersi. |
| "Le domande del tree rallentano il workflow" | 4-6 domande mirate producono 2-3x piu' scenari edge rispetto alla matrice generica. Il piano di test finale e' piu' completo in meno iterazioni. |
| "Il tipo e' ovvio, non serve inferire" | Ovvio per te. La Req Profile Card documenta il tipo e i segnali: e' evidenza, non burocrazia. Se sbagli il tipo, i TC coprono il dominio sbagliato. |

---

## CHECKLIST DI VERIFICA

Prima di dichiarare la skill completata:

- [ ] Phase 0 eseguita: tipo requisito inferito e Req Profile Card mostrata
- [ ] Confidence HIGH → tree lanciato senza conferma tipo | MEDIUM/LOW → conferma ricevuta
- [ ] Domande del tree skippate se risposta gia' presente in AC/description
- [ ] Req Profile Card aggiornata con scenari L1/L2/L3 prima di procedere a Phase 4a
- [ ] AC letti da Jira (o forniti esplicitamente dal developer)
- [ ] Test Strategy Confluence cercata (trovata o WARNING registrato)
- [ ] Test Plan generato/creato con campi obbligatori
- [ ] Matrice scenari compilata (4 categorie valutate: positivi, edge, negativi, profilazioni)
- [ ] Ogni categoria ha scenari identificati o "N/A — confermato dal developer"
- [ ] Ogni AC ha almeno 1 Test Case step-based
- [ ] Presenti TC per scenari positivi, edge case, negativi e profilazioni (se applicabili)
- [ ] I titoli Scenario usano i prefissi `[EDGE]`, `[NEG]`, `[PROFILO]` dove appropriato
- [ ] Ogni step ha sia `Action` che `Expected Result` (nel CSV usa la colonna `Expceted Result` — typo template)
- [ ] Il campo `ID JIRA Story` e' presente in tutti i Test Case
- [ ] Riepilogo copertura per categoria mostrato al developer prima dell'export
- [ ] Campi `Automazione` e `NRT` verificati con il developer
- [ ] Export effettuato (MCP / CSV) o spiegato come farlo
- [ ] Mappatura ID sequenziali → chiavi Jira Xray raccolta (se si prevede di usare siae-automation)
- [ ] Tier usato annunciato nella pre-flight card di apertura

**Non riesci a spuntare tutte le caselle? Il workflow non e' completo. Ricomincia dalla fase bloccata.**

---

## VINCOLI NON NEGOZIABILI

0. **Phase 0 e' sempre la prima fase** — nessun AC viene letto senza aver prima inferito il tipo e lanciato le domande del tree contestuale; la Req Profile Card deve essere prodotta prima di Phase 1
1. **Nessun Test Case senza AC corrispondente** — ogni TC e' tracciabile a un comportamento specifico
2. **La matrice 4a va compilata prima di scrivere qualsiasi TC** — non si genera senza aver valutato tutte e 4 le categorie
3. **Le domande su edge case, negativi e profilazioni sono obbligatorie** — se non emergono dagli AC, si chiedono; non si assumono
4. **Il campo `ID JIRA Story` e' obbligatorio** — senza di esso il TC non ha senso in Xray
5. **Ogni step ha `Action` e `Expected Result`** — step senza Expected Result = step non valido
6. **Il CSV usa separatore `;` (semicolon)** — non virgola, non tab
7. **Righe con stesso ID = stesso Test Case** — i metadati solo nella prima riga, step multipli nelle righe successive
8. **Nel CSV, il nome colonna e' `Expceted Result`** — typo storico del template importatore Xray SIAE. Usarlo esattamente per compatibilita' import. Ovunque altrove (documentazione, checklist, commenti) usare `Expected Result` (corretto).

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Analisi Acceptance Criteria | 🟢 Sicuro | No |
| Scrittura test cases | 🟢 Sicuro | No |
| Creazione test plan | 🟢 Sicuro | No |
| Export test su Xray/JIRA | 🟡 Medio | Si |
| Esecuzione test su ambiente di collaudo | 🟡 Medio | Si |
| Apertura bug su JIRA | 🟡 Medio | Si |
| Approvazione go/no-go al rilascio | 🔴 Alto | Si |

---

## Permission Denied Handling

**Se Write viene negato (export CSV — Tier 3):**
1. Presenta il contenuto CSV completo come output testuale in chat (blocco code fenced)
2. Indica il path suggerito per il file CSV
3. L'utente puo' copiare il contenuto e salvarlo manualmente
4. Le istruzioni di import Xray rimangono invariate

**Se MCP non disponibile (gia' gestito dal Tier system):**
- Il Tier 3 (CSV) e' gia' il fallback — non richiede MCP

**Fasi completabili senza permessi:** Fase 1-4 (conversazionali — lettura AC, elicitazione scenari, generazione TC)
**Fasi che richiedono permessi:** Fase 5 (Write per CSV, MCP per Xray)

Se i permessi sono negati:
1. Completa tutte le fasi conversazionali (1-4)
2. Presenta CSV/TC come output testuale
3. NON entrare in loop di retry su tool negato
4. NON dichiarare completamento per fasi non eseguite

---

## QUANDO SEI BLOCCATO

| Problema | Soluzione |
|----------|-----------|
| Campo AC vuoto in Jira | Leggi description → commenti → Confluence → chiedi al developer |
| MCP non risponde | Degrada a Tier 3 CSV, segnala il problema all'utente |
| Story non trovata in Jira | Chiedi l'ID corretto, verifica permessi MCP |
| TC troppo astratti | Torna agli AC, fai domande piu' specifiche al developer |
| Developer non sa quali campi Automazione/NRT usare | Default: Automazione=N, NRT=Y. Correggi insieme revisando i test automatizzati esistenti |
