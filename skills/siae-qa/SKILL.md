---
name: siae-qa
description: >
  Genera documentazione test formale per Xray a completamento implementazione.
  Trigger: completamento brainstorming (Fase 2), completamento ciclo TDD (Fase 5),
  /forge-qa.
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

<EXTREMELY-IMPORTANT>
Stai per dichiarare l'implementazione completa senza Test Case in Xray?
FERMATI. Nessun rilascio senza TC verificati e documentati.

Stai per generare TC senza aver completato Phase 0 (Smart Req Typing)?
FERMATI. Il tipo di requisito determina le domande contestuali — senza Phase 0 i TC
coprono solo cio' che e' scritto negli AC, non cio' che puo' rompersi.

Stai per scrivere TC senza aver compilato la matrice scenari (4a)?
FERMATI. Tutti e 4 le categorie (positivi, edge, negativi, profilazioni) devono essere
valutate PRIMA di generare qualsiasi TC.
</EXTREMELY-IMPORTANT>

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
| **Tier 1 — Story Jira** | MCP `atlassian` disponibile | Legge AC da Jira, legge Confluence, crea TC e Test Plan in Xray via MCP, raccoglie chiavi Jira assegnate |
| **Tier 2 — Documento utente** | Utente fornisce documento (spec, PDF, markdown, testo con requisiti grezzi) | Deriva AC dai requisiti, chiede validazione esplicita al developer, genera CSV o crea TC via MCP se disponibile |
| **Tier 3 — Conversazione** | Nessuna fonte strutturata disponibile | Raccoglie AC via domande guidate una alla volta, genera CSV semicolon-separated importabile in Xray |

Il tier viene scelto esplicitamente dall'utente nell'Opening Dialog. Ogni operazione esplicita il tier attivo nella pre-flight card.

---

## OPENING DIALOG [OBBLIGATORIO — prima di tutto]

All'avvio mostra sempre questo dialog. **Non procedere senza risposta esplicita dell'utente.**

Smart pre-selection (suggerisci, non eseguire autonomamente):
- MCP Atlassian disponibile → suggerisci `[1]`
- Testo o documento già presente in chat → suggerisci `[2]`
- Nessuna fonte rilevata → suggerisci `[3]`

```
──────────────────────────────────────────────
Cosa vuoi fare?

[1] Story Jira       — ho un ticket PROJ-XXX da cui leggere i requisiti
[2] Documento        — ho una specifica/doc da allegare o incollare
[3] Conversazione    — descrivo i requisiti direttamente in chat

> Suggerito: [X] — motivo: {es. MCP disponibile / documento rilevato in chat}
──────────────────────────────────────────────
```

Attendi risposta prima di procedere.
Non avviare la PRE-FLIGHT CARD finché l'utente non ha scelto il tier.

---

## PRE-FLIGHT CARD DI APERTURA

Prima di iniziare il workflow, mostra questa card con il tier rilevato:

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-qa |
|:---|
| 📡 Tier attivo: `Tier 1 Jira / Tier 2 Documento / Tier 3 Conversazione` · 🎫 Story/Fonte: `PROJ-XXX / [nome doc] / [topic]` |
| ✅ AC: `Disponibili (Tier 1) / Da validare (Tier 2) / Da raccogliere (Tier 3)` · 📚 Confluence: `Spazio QA trovato / Non configurato` |
| **▼ Azione** |
| 1. 📋 Avvio workflow QA con tier scelto nell'Opening Dialog |
| 💡 Perche': Il tier determina come vengono letti i requisiti e sincronizzati i TC |
| 🚫 Se NO: Tier 2/3 → genero CSV importabile manualmente in Xray |

---

## Phase 0 — Smart Req Typing [SEMPRE OBBLIGATORIA — prima di tutto]

Prima di leggere AC o interrogare Jira, inferisci il tipo di requisito.
**Non chiedere ciò che la story dice già.** Leggi prima, chiedi solo il delta.

### 0a — Inferisci il tipo

Leggi in ordine: summary della story, AC/description, commenti, label Jira, stack del progetto.
Cerca i segnali nella tabella req typing. Vedi [XRAY-TEMPLATES.md](XRAY-TEMPLATES.md) sezione "Tabella Segnali Req Typing" per la tabella completa con segnali e livelli di confidence.

### 0b — Mostra Req Typing Card

Mostra la Req Profile Card. Vedi [XRAY-TEMPLATES.md](XRAY-TEMPLATES.md) sezione "Template Req Profile Card" per il formato.

- **Se HIGH:** mostra la card e procedi con le domande del tree (0c). L'utente puo' correggere il tipo.
- **Se MEDIUM/LOW:** chiedi conferma con scelta multipla.

### 0c — Lancia le domande del tree contestuale

Usa le domande in `reference/question-trees.md` per il tipo confermato.

> Il file `reference/question-trees.md` si trova nella directory `reference/` di questa skill.

**Regola fondamentale:** salta ogni domanda già rispondibile dagli AC/description esistenti.
Fai UNA domanda alla volta. Aspetta la risposta prima di procedere alla successiva.

Al termine delle domande, aggiorna la Req Profile Card con gli scenari raccolti (formato aggiornato in [XRAY-TEMPLATES.md](XRAY-TEMPLATES.md)).
Questa card e' l'input aggiuntivo per Phase 4a (matrice scenari).

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

**Tier 2 (Documento):**

Il documento contiene **requisiti grezzi** — non AC strutturati. Formato libero,
potenzialmente molti requisiti, nessun template garantito.

1. Se il documento non è ancora presente in chat: chiedi all'utente di incollare il testo,
   allegare il file o indicare il contenuto (qualunque formato: prosa, lista, tabelle,
   normativa, capitolato, specifica tecnica)
2. Leggi l'intero documento e **deriva** gli AC candidati dai requisiti
   (step interpretativo: un requisito → 1+ AC testabili, espressi come comportamenti verificabili)
3. Presenta la lista AC derivati in forma numerata al developer per revisione
4. **[HARD-GATE]** Attendi validazione/correzione esplicita dall'utente:
   l'utente conferma, modifica o integra gli AC prima che il workflow proceda.
   Non procedere alla Fase 2 senza questa conferma.
5. Se Story ID o titolo feature sono assenti dal documento: chiedi esplicitamente
   (necessario per collegare i TC a Xray)
6. Gli AC confermati diventano l'input equivalente degli AC Jira per tutte le fasi successive

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

**Tier 2 (Documento):**
- Verifica se il documento fornito dall'utente contiene già una sezione
  Test Strategy, Approccio di Test, o Strategia di Verifica
- Se sì: usa quella sezione come input per Scope/Approach/Test Types
- Se no: segnala `⚠️ WARNING: Test Strategy non presente nel documento` e procedi
  senza — identico al comportamento Tier 3

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

Se per una categoria il developer conferma che non ci sono scenari aggiuntivi, registra "N/A -- confermato dal developer" e procedi.
**Non puoi procedere alla generazione con categorie non valutate.**

Vedi [XRAY-TEMPLATES.md](XRAY-TEMPLATES.md) per template Matrice Scenari e formato output.

---

#### 4b — Generazione Test Case

Per ogni scenario della matrice (4a), genera 1+ Test Case step-based.
Vedi [XRAY-TEMPLATES.md](XRAY-TEMPLATES.md) sezioni "Formato Test Case Step-Based", "Prefissi di Categoria", "Regola Multi-Step" e "Riepilogo Copertura" per formato completo, prefissi e template riepilogo.

**Riepilogo prima dell'export:** mostra la tabella completa al developer con la distribuzione per categoria. Il developer puo' modificare i valori di `Automazione` e `NRT` prima di procedere all'export.

---

---

### Fase 4c — 5-Judge Coverage Gate [OBBLIGATORIO — prima dell'export]

Dopo la generazione dei TC (Fase 4b), **prima dell'export**, lancia 5 agenti AI
in parallelo. Ognuno valuta una dimensione diversa della copertura.
Il gate è bloccante: non si procede a Fase 5 senza aver soddisfatto le soglie.

#### Struttura dei 5 Giudici

| Judge | Focus | Soglia | Bloccante |
|-------|-------|--------|-----------|
| **J1** | Copertura Requisiti → TC: ogni requisito fornito ha ≥1 TC tracciabile | **100%** | SI |
| **J2** | Copertura AC → Test: ogni Acceptance Criterion ha ≥1 test tracciabile | **100%** | SI |
| **J3** | Copertura casi negativi: flussi di errore, input non validi, stati alternativi | **≥75%** | SI |
| **J4** | Copertura casi positivi: happy path completi per ogni AC | **≥75%** | SI |
| **J5** | Correttezza tecnica + gap analysis + boundary conditions | Best effort | NO |

#### Prompt dei Giudici (da lanciare in parallelo con Agent tool)

**J1 — Copertura Requisiti:**

Prompt da iniettare nel subagent:
```
Sei un QA Judge specializzato in copertura requisiti.
Input: [lista requisiti originali] + [lista TC generati].
Verifica che ogni requisito abbia almeno 1 TC che lo copre esplicitamente.
Calcola: TC coperti / totale requisiti = XX%.
Elenca i requisiti senza copertura. Soglia: 100%.
Output: percentuale + lista gap.
```

**J2 — Copertura AC:**

Prompt da iniettare nel subagent:
```
Sei un QA Judge specializzato in copertura Acceptance Criteria.
Input: [lista AC validati] + [lista TC generati].
Verifica che ogni AC abbia almeno 1 test che lo verifica esplicitamente.
Calcola: AC coperti / totale AC = XX%.
Elenca gli AC senza test. Soglia: 100%.
Output: percentuale + lista gap.
```

**J3 — Casi Negativi:**

Prompt da iniettare nel subagent:
```
Sei un QA Judge specializzato in test negativi e flussi di errore.
Input: [lista AC] + [lista TC generati].
Verifica la presenza di TC per: input non validi, errori di sistema,
permessi mancanti, stati incompatibili, dipendenze assenti.
Stima la percentuale di scenari negativi coperti sul totale identificabile.
Elenca i gap. Soglia minima: 75%.
Output: percentuale + lista gap.
```

**J4 — Casi Positivi:**

Prompt da iniettare nel subagent:
```
Sei un QA Judge specializzato in happy path e scenari positivi.
Input: [lista AC] + [lista TC generati].
Verifica che ogni AC abbia almeno 1 TC positivo che copra il flusso principale.
Stima la percentuale di happy path coperti sul totale identificabile.
Elenca i gap. Soglia minima: 75%.
Output: percentuale + lista gap.
```

**J5 — Gap Analysis & Correttezza Tecnica:**

Prompt da iniettare nel subagent:
```
Sei un QA Judge specializzato in correttezza tecnica e boundary conditions.
Input: [lista requisiti/AC] + [lista TC generati].
Analizza: valori limite, condizioni di gara, idempotenza, edge case tecnici,
coerenza tra step Action e Expected Result, precisione delle precondizioni.
Non hai soglia bloccante. Produci un report gap prioritizzato (ALTA/MEDIA/BASSA).
Output: lista gap con priorità.
```

#### Comportamento del Gate

```
1. Lancia J1, J2, J3, J4, J5 in parallelo (Agent tool — 5 subagent simultanei)
   Input comune a tutti: lista requisiti/AC + lista TC generati in Fase 4b

2. Valuta le soglie sui risultati ricevuti:
   - J1 < 100% → BLOCCANTE
   - J2 < 100% → BLOCCANTE
   - J3 < 75%  → BLOCCANTE
   - J4 < 75%  → BLOCCANTE
   - J5        → NON bloccante (report informativo)

3. Se almeno 1 giudice bloccante fallisce:
   a. Mostra il COVERAGE GATE REPORT (formato sotto)
   b. Genera i TC mancanti per i gap specifici identificati (torna a Fase 4b mirata)
   c. Rilancia l'intero gate dall'inizio
   d. Ripeti fino a quando tutte le soglie bloccanti sono soddisfatte

4. Se tutti i giudici bloccanti sono soddisfatti (J1-J4 OK):
   a. Mostra il COVERAGE GATE REPORT completo
   b. J5: presenta il report gap — il developer può accettare o integrare
   c. Procedi a Fase 5 (export)
```

#### Formato COVERAGE GATE REPORT

```
COVERAGE GATE REPORT
────────────────────
J1 Req → TC:     XX/YY requisiti coperti (XX%)   [PASS ✅ / FAIL ❌]
J2 AC  → Test:   XX/YY AC coperti       (XX%)   [PASS ✅ / FAIL ❌]
J3 Negativi:     XX% scenari negativi coperti   [PASS ✅ / FAIL ❌]
J4 Positivi:     XX% happy path coperti         [PASS ✅ / FAIL ❌]
J5 Gap analysis: N gap trovati                  [REPORT 📋]

Gap bloccanti da colmare:
  J1: [lista requisiti senza TC]
  J2: [lista AC senza test]
  J3: [lista scenari negativi scoperti]
  J4: [lista happy path mancanti]

Gap non bloccanti (J5 — accetta o integra):
  ALTA:   [gap con impatto alto]
  MEDIA:  [gap con impatto medio]
  BASSA:  [suggerimenti opzionali]
────────────────────
```

---

### Fase 5 — Export / Sincronizzazione

**Tier 1 (MCP):**
1. Crea ogni Test Case in Xray via MCP
2. Ogni TC creato ottiene automaticamente una chiave Jira (es. `PROJ-456`) — registrala nella mappatura (vedi Passo post-export)
3. Dopo l'esecuzione dei test, aggiorna il Test Execution con i risultati

**Tier 2 (Documento):**
- Usa la stessa pipeline export di Tier 3: CSV semicolon-separated in formato Xray-importabile
- Se MCP Atlassian è disponibile: puoi usare il flusso Tier 1 (crea TC via MCP)
  dopo aver validato gli AC nel workflow Tier 2
- Vedi [XRAY-TEMPLATES.md](XRAY-TEMPLATES.md) sezione "Tier 3 CSV Export" per formato e istruzioni

**Tier 3 (CSV):**
Vedi [XRAY-TEMPLATES.md](XRAY-TEMPLATES.md) sezione "Tier 3 CSV Export" per formato e istruzioni import.

**Passo post-export — Mappatura ID sequenziali -> chiavi Jira Xray [OBBLIGATORIO se si usa siae-automation]**
Vedi [XRAY-TEMPLATES.md](XRAY-TEMPLATES.md) sezione "Mappatura ID Sequenziali e Chiavi Jira Xray" per procedura e template mappatura.
Salva la mappatura come output della skill: sara' l'input di Fase 1 di siae-automation.

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
| "Il documento ha i requisiti, non serve derivare gli AC" | I requisiti descrivono cosa fare, gli AC descrivono come verificarlo. Derivare gli AC è lo step interpretativo chiave — senza di esso i TC testano il documento, non il comportamento. |
| "Ho già letto il documento, so quali AC ci sono" | La derivazione degli AC deve essere esplicita e validata dall'utente. Un'inferenza non validata è un'assunzione. |
| "Il Coverage Gate rallenta il workflow" | Un TC che non copre un requisito è un buco nel collaudo. 5 giudici in parallelo impiegano secondi. Un bug in produzione da AC non coperto costa ore. |
| "J1 e J2 al 100% è irraggiungibile con molti requisiti" | È raggiungibile: ogni requisito deve avere almeno 1 TC. Non deve coprire tutti gli aspetti — deve esistere. 1 TC per requisito è il minimo, non il massimo. |
| "Salto il Coverage Gate per la Fase 5, tanto i TC sono completi" | Il Coverage Gate non si salta. È la prova formale che la copertura è sufficiente, non una stima soggettiva. |
| "Ho scelto il tier sbagliato nell'Opening Dialog, è un problema" | Puoi cambiare tier prima che il workflow inizi: rilancia la skill e scegli di nuovo. Il dialog è il momento giusto per decidere, non dopo. |

---

## CHECKLIST DI VERIFICA

Vedi [XRAY-TEMPLATES.md](XRAY-TEMPLATES.md) sezione "Checklist di Verifica" per la checklist completa.
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
9. **Il 5-Judge Coverage Gate è obbligatorio prima di Fase 5** — nessun export senza aver soddisfatto le soglie J1/J2 (100%) e J3/J4 (≥75%)

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
