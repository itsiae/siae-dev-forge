---
name: siae-qa
version: 2.0.0
last_modified: 2026-05-11
description: >
  Genera documentazione test formale per Xray a completamento implementazione.
  Trigger: completamento brainstorming (Phase 2), completamento ciclo TDD (Phase 5),
  /forge-qa.
changelog: |
  2.0.0 (2026-05-11): Refactor Coverage Matrix M_FINAL come single source of truth.
    - Phase 1.5 introduce M_FINAL (Matrix A/B/C + Gate #1).
    - Phase 4 riorganizzata in 4a (verifica) / 4b (genera) / 4c (Gate #2) / 4d (J5).
    - Prefissi TC uniformati: [POS]/[NEG]/[EDGE]/[ROLE] (ex [PROFILO] eliminato).
    - coverage_certificate.json e xray_id_mapping.json persistiti su docs/qa/{STORY_ID}/.
    - Schemi JSON formali in reference/schemas/.
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

Stai per scrivere TC senza aver costruito la Coverage Matrix (Phase 1.5)?
FERMATI. M_FINAL deve esistere PRIMA di generare qualsiasi TC.
Ogni TC deve essere tracciabile a una riga di M_FINAL — nessun TC orfano, nessuna riga orfana.
</EXTREMELY-IMPORTANT>

> **Tipo:** Rigid | **Fase SDLC:** 5. Testing / QA

## Indice

- [La Legge di Ferro](#la-legge-di-ferro)
- [Quando si applica](#quando-si-applica)
- [Hard-Gate — Nessun Test Case senza AC](#hard-gate--nessun-test-case-senza-ac)
- [Livelli di Integrazione (graceful degradation)](#livelli-di-integrazione-graceful-degradation)
- [Opening Dialog](#opening-dialog-obbligatorio--prima-di-tutto)
- [Pre-Flight Card di Apertura](#pre-flight-card-di-apertura)
- [Phase 0 — Smart Req Typing](#phase-0--smart-req-typing-sempre-obbligatoria--prima-di-tutto)
- [Workflow a 5 Phase](#workflow-a-5-phase)
  - [Phase 1 — Lettura AC](#phase-1--lettura-ac-da-jira-hard-gate)
  - [Phase 1.5 — Coverage Matrix](#phase-15--coverage-matrix-builder-obbligatoria--prima-di-generare-qualsiasi-tc)
  - [Phase 2 — Test Strategy](#phase-2--lettura-test-strategy-da-confluence)
  - [Phase 3 — Test Plan](#phase-3--generazione-test-plan)
  - [Phase 4a/b/c/d — Test Case Generation](#phase-4--generazione-test-case-step-based)
  - [Phase 5 — Export](#phase-5--export--sincronizzazione)
- [Limiti Operativi](#limiti-operativi)
- [Required Sub-Skill](#required-sub-skill-siae-verification)
- [Vincoli Non Negoziabili](#vincoli-non-negoziabili)
- [Permission Denied Handling](#permission-denied-handling)
- [Quando sei bloccato](#quando-sei-bloccato)

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

```
──────────────────────────────────────────────
Cosa vuoi fare?

[1] Story Jira       — ho un ticket PROJ-XXX da cui leggere i requisiti
[2] Documento        — ho una specifica/doc da allegare o incollare
[3] Conversazione    — descrivo i requisiti direttamente in chat
──────────────────────────────────────────────
```

Attendi risposta prima di procedere.
Non avviare la PRE-FLIGHT CARD finché l'utente non ha scelto il tier.
**Non fare inferenze, non suggerire, non pre-selezionare. Solo chiedere.**

Anti-razionalizzazione inline:
- "So già il tier dal contesto, salto il dialog" → Non inferire. Chiedi sempre.
- "L'utente ha già detto Tier 2, è confermato" → Il dialog non è opzionale. Mostralo e aspetta.

### Definizione di "conferma valida" (vincolante per tutta la skill)

```
Conferma valida = risposta esplicita affermativa, una delle seguenti stringhe (case-insensitive)
seguita da newline, punto, o EOF (no trailing junk):
  - "si" / "si'" / "sì"
  - "ok" / "OK"
  - "confermo" / "confermato"
  - "procedi" / "vai"

Risposte INVALIDE (richiedi nuovamente):
  - silenzio / risposta vuota
  - risposte ambigue: "forse", "boh", "non lo so", "vediamo"
  - "ok ma..." / "si pero'..." (presenza di disjunction = non conferma)
```

Questa definizione vale per: Opening Dialog (tier), Phase 1.5 (checkpoint serializzazione), Phase 1 Tier 2 (validazione AC), Phase 4d (accept gap o aggiungi TC).

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

**Prima di lanciare le domande:** usa Read tool per leggere `reference/question-trees.md`.
Se il file non è trovato: segnala `⚠️ question-trees.md non trovato — uso domande generiche` e usa le seguenti domande di fallback:
1. "Ci sono valori di lookup enumerati non elencati negli AC?"
2. "Ci sono campi obbligatori la cui assenza deve produrre un errore esplicito?"
3. "Ci sono regole condizionali dipendenti da più campi contemporaneamente?"
4. "Ci sono ruoli utente con comportamenti distinti per questa funzionalità?"

Usa le domande in `reference/question-trees.md` per il tipo confermato.

> Il file `reference/question-trees.md` si trova nella directory `reference/` di questa skill.

**Regola fondamentale:** salta ogni domanda già rispondibile dagli AC/description esistenti.
Fai UNA domanda alla volta. Aspetta la risposta prima di procedere alla successiva.

Al termine delle domande, aggiorna la Req Profile Card con gli scenari raccolti (formato aggiornato in [XRAY-TEMPLATES.md](XRAY-TEMPLATES.md)).
Questa card e' input per Phase 1.5: campo "info ruolo/permesso" alimenta Matrix C, campo "stack tecnologico" guida la scelta degli esempi in Matrix A e M_FINAL.

---

## Workflow a 5 Phase

### Phase 1 — Lettura AC da Jira [HARD-GATE]

Non procedere alla Phase 2 senza AC o contesto sufficiente.

**Tier 1 (MCP):**
1. Usa `searchJiraIssuesUsingJql` con JQL: `key = {STORY_ID}` per recuperare la Story
2. Tenta di leggere il campo `Acceptance Criteria` (campo custom Xray/Jira)
3. Se il campo AC e' presente e popolato → usa direttamente, vai alla Phase 2
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
   Granularita': per requisiti funzionali standard, deriva massimo 3 AC nell'ordine deterministico:
   - (a) happy path principale (il comportamento positivo descritto per primo)
   - (b) primo errore di validazione esplicitato nel testo
   - (c) primo edge case esplicitato nel testo
   Se sono > 3 i candidati pertinenti: NON scartare gli altri — sposta la granularita' a Phase 1.5 (la matrice copre i casi extra come righe esplicite). Per specifiche **enumerative** (mapping CSV, lookup tables, campi con valori fissi, specifiche di migrazione dati): ogni valore/campo atomico e' un AC distinto — il cap non si applica. Se il documento ha tabelle campo→valore o lookup esplicite, ogni riga della tabella e' un AC separato.
3. Presenta la lista AC derivati in forma numerata al developer per revisione
4. **[HARD-GATE]** Attendi validazione/correzione esplicita dall'utente:
   l'utente conferma, modifica o integra gli AC prima che il workflow proceda.
   Non procedere alla Phase 2 senza questa conferma.
   Se l'utente non risponde o risponde in modo ambiguo: **blocca e chiedi di nuovo esplicitamente** — "Confermato il testo: 'AC confermati' prima di procedere."
   Un silenzio o un "ok" generico non è una conferma valida.
5. Se Story ID o titolo feature sono assenti dal documento: chiedi esplicitamente
   (necessario per collegare i TC a Xray)
6. Gli AC confermati diventano l'input equivalente degli AC Jira per tutte le fasi successive

**Tier 3 (no Jira):**
- Chiedi la Story ID (es. `PROJ-123`) e il titolo della User Story
- Poi chiedi gli AC con domande mirate, una alla volta, finche' il contesto e' completo
- Esempio prima domanda: "Descrivi il comportamento principale che questa Story deve implementare."

**Output atteso Phase 1:** lista strutturata di AC, ognuno identificabile come comportamento testabile.

---

### Phase 1.5 — Coverage Matrix Builder [OBBLIGATORIA — prima di generare qualsiasi TC]

Dopo la lettura degli AC/requisiti (Phase 1), prima di qualsiasi generazione TC,
costruisci la **Coverage Matrix (M_FINAL)** tramite 3 agenti in parallelo.
**M_FINAL è l'unico driver della generazione TC in Phase 4b.**

<EXTREMELY-IMPORTANT>
Non avviare Phase 4b senza M_FINAL completata e approvata da Gate #1 (J1_MATRIX + J2_MATRIX).
Generare TC dagli AC grezzi senza passare per la matrice produce TC generici.
La matrice forza la sistematicità: ogni campo, ogni lookup, ogni combinazione di regola di business
diventa una riga esplicita PRIMA che esista un TC.

Stai per saltare questa fase perché i requisiti "sembrano semplici"?
FERMATI. Ogni spec con lookup tables, campi obbligatori/opzionali o regole condizionali
richiede la matrice. Senza di essa la generazione è narrativa, non sistematica.
</EXTREMELY-IMPORTANT>

#### Formato Coverage Matrix (schema M_FINAL)

Ogni riga della matrice corrisponde esattamente a **1 TC da generare**:

| matrix_row_id | entity | field | condition | test_type | source_ref |
|---------------|--------|-------|-----------|-----------|------------|
| ID univoco | entità (es. GENERAL_DATA) | campo (es. CATEGORY) | condizione concreta (es. `"F"→feature`) | POS/NEG/EDGE/ROLE | AC o paragrafo |

#### Regole di esplosione (da campo a righe di matrice)

| Tipo campo | Righe generate | Esempio |
|-----------|----------------|---------|
| **Lookup enumerato** (N valori) | N righe POS (1 per valore) + 1 riga NEG ("fuori lookup") | CATEGORY F/S/null → 3 POS + 1 NEG |
| **Booleano/flag** | POS(true) + POS(false) + NEG(non parseable) | EVERGREEN data→true, null→false |
| **Obbligatorio (mandatory)** | POS(valido) + NEG(assente/null) | DURATION mancante → errore |
| **Opzionale (optional)** | POS(valido) + EDGE(null accettato) | ORDER null → ok |
| **Formato (data/regex/ISO)** | POS(corretto) + NEG(formato errato) + EDGE(null se optional) | RELEASED ISO8601 |
| **Valore fisso business** | POS(= costante) + NEG(≠ costante) | UNIQUEREF2 = "074" |
| **Regola composita** (N campi interdipendenti) | Prodotto cartesiano filtrato per esiti distinti + pairwise IPOG se > 16 | account × IPI → 4 combinazioni; 5 boolean → 32 combinazioni → 16 selezionate via pairwise IPOG |
| **Cross-sezione** (chiave condivisa tra CSV/entità) | NEG per ogni sezione dipendente (chiave assente) | UNIQUEREF1 assente in TITLES |

#### Serializzazione input per gli agenti (OBBLIGATORIA prima del lancio)

Prima di invocare i 3 agenti, serializza i dati estratti dalla Phase 1:

```
ENTITÀ E CAMPI:
[entità 1]:
  - campo: TYPE | mandatory/optional | dominio: lookup CueType
  - campo: CATEGORY | optional | lookup: F/S/null
  ...
[entità 2]:
  ...

LOOKUP TABLES:
CATEGORY: F, S, null (Documentary)
PRODUCTNAMETYPE: OT, SE, EP, AT, ET
...

REGOLE DI BUSINESS COMPOSTE:
1. ACCOUNTNUMBER assente AND IPINAMENUMBER assente → genera nuovo IR
2. PERFORMING SHARE NUM/DEN → re-proporzionamento in %
...

VINCOLI REFERENZIALI:
UNIQUEREF1 è chiave condivisa tra: GENERAL_DATA, TITLES, NUMBERS, CONTRIBUTORS, WORK
...
```

**Formato riga output atteso (schema uniforme obbligatorio per tutti e 3 gli agenti):**

| matrix_row_id | entity | field | condition | test_type | source_ref |
|---|---|---|---|---|---|
| A-001 | GENERAL_DATA | CATEGORY | `"F"` → tipo feature | POS | AC-03 |
| A-002 | GENERAL_DATA | CATEGORY | `"S"` → tipo serie | POS | AC-03 |
| A-003 | GENERAL_DATA | CATEGORY | valore fuori lookup (es. `"X"`) | NEG | AC-03 |

Ogni agente DEVE usare esattamente questi nomi di colonna. Variazioni nei nomi colonna rendono il merge M_A+M_B+M_C non valido.

**[CHECKPOINT SERIALIZZAZIONE — OBBLIGATORIO prima del lancio]**

Mostra al developer il blocco serializzato e chiedi:
> "La serializzazione è completa? Entità, lookup tables, regole business e vincoli referenziali corrispondono alla specifica? Posso procedere con il lancio dei 3 agenti Matrix?"

Non lanciare Matrix A/B/C senza risposta esplicita conforme alla "Definizione di conferma valida" (vedi sezione Opening Dialog). La spec e' gia' stata validata in Phase 1: questo e' un sanity check sulla serializzazione.

#### Lancio 3 agenti in parallelo (Agent tool — stesso turno)

**Matrix Agent A — Field/Value Decomposer:**
```
Sei un QA Matrix Agent specializzato in decomposizione campo-valore.
Input: {ENTITÀ E CAMPI serializzati} + {LOOKUP TABLES serializzate}
Per ogni campo di ogni entità, applica le regole di esplosione:
  - Lookup enumerato → 1 riga POS per ogni valore + 1 riga NEG "fuori lookup"
  - Mandatory → POS(valido) + NEG(assente/null)
  - Optional → POS(valido) + EDGE(null = accettato)
  - Formato data/regex → POS(corretto) + NEG(errato) + EDGE(null se optional)
  - Valore fisso business → POS(= costante) + NEG(≠ costante)
Produci: tabella M_A con colonne matrix_row_id, entity, field, condition, test_type, source_ref
```

**Matrix Agent B — Rule Composer:**
```
Sei un QA Matrix Agent specializzato in regole di business composte e vincoli referenziali.
Input: {REGOLE DI BUSINESS COMPOSTE serializzate} + {VINCOLI REFERENZIALI} + {LOOKUP TABLES serializzate}
Per ogni regola composita: costruisci prodotto cartesiano ridotto
  - Esito DISTINTO = differenza nello status_code di ritorno OR classe del messaggio di errore (validation_error vs authorization_error vs business_rule_violation). Stesso status + stessa classe = stesso esito → tieni 1 combinazione rappresentativa.
  - Aggiungi 1 happy path (tutti i campi nominali validi) come riga POS marcata `source_ref="composite_happy"`
  - Aggiungi 1 worst case (tutti i campi edge contemporaneamente) come riga EDGE marcata `source_ref="composite_worst"`
  - Limite: max 16 combinazioni per regola. Se lo spazio delle combinazioni eccede 16: applica **pairwise covering (IPOG)** — selezione che copre ogni coppia di valori almeno una volta. Marca le righe con `source_ref="pairwise_ipog"`. Ordine deterministico: ordina i fattori per nome campo asc, poi seleziona le combinazioni nell'ordine prodotto da IPOG canonico.
Per ogni vincolo referenziale: 1 riga NEG per ogni sezione dipendente (chiave assente)
Produci: tabella M_B con colonne matrix_row_id, entity, field, condition, test_type, source_ref
  (colonne aggiuntive: combo_fields[], combo_values[] per regole composite)
```

**Matrix Agent C — Role/Permission Mapper:**
```
Sei un QA Matrix Agent specializzato in copertura ruoli e permessi.
Input: {ENTITÀ E CAMPI con info ruolo/permesso}
Se il documento specifica ruoli diversi con comportamenti distinti:
  → 1 riga ROLE per ogni coppia (ruolo, azione) semanticamente distinta
  → Non duplicare se due ruoli hanno identici permessi
Se non ci sono ruoli distinti → produci M_C vuota con nota "N/A — nessun ruolo distinto"
Produci: tabella M_C con colonne matrix_row_id, entity, field, condition, test_type, source_ref
```

#### Gate #1 — J1_MATRIX + J2_MATRIX (bloccante, opera su M_A+M_B+M_C)

<EXTREMELY-IMPORTANT>
FERMATI. Stai per procedere a Phase 4b? Esegui prima Gate #1 con Agent tool.

J1 e J2 operano QUI sulle matrici — NON sui TC (che non esistono ancora).
Invoca J1 e J2 in parallelo con Agent tool dopo aver ricevuto M_A, M_B, M_C.
NON procedere a Phase 4b senza PASS da entrambi.
Un'autovalutazione interna di Claude NON è Gate #1 — è un'assunzione.

**Criterio verificabile:** l'esecuzione di Gate #1 deve produrre 2 tool call result di Agent tool visibili nella conversazione. Se non puoi mostrare questi tool call result, Gate #1 non è stato eseguito — è stato simulato.
</EXTREMELY-IMPORTANT>

**J1_MATRIX — Coverage Completeness:**
```
Sei un QA Judge per completezza della coverage matrix.
Input: M_A + M_B + M_C + {ENTITÀ E CAMPI serializzati}
Verifica:
  1. Ogni entità ha almeno 1 riga POS + 1 riga NEG in M_A o M_B
  2. Ogni lookup enumerato ha 1 riga per ogni valore (non collassate)
  3. Ogni vincolo referenziale ha almeno 1 riga NEG cross-sezione in M_B
Elenca entità/campi senza copertura. Soglia: 100% delle entità.
Output: GIUDICE J1_MATRIX | PERCENTUALE: XX% | PASS/FAIL | GAP: [lista]
```

**J2_MATRIX — Deduplication:**
```
Sei un QA Judge per deduplicazione della coverage matrix.
Input: M_A + M_B + M_C
Identifica righe semanticamente identiche (stessa entità, campo, condizione, esito
anche se formulate diversamente tra agenti diversi). Elencale.
Output: GIUDICE J2_MATRIX | DUPLICATI: N | LISTA_DUPLICATI: [lista da rimuovere]
```

Dopo J1_MATRIX PASS e J2_MATRIX dedup applicato: merge M_A + M_B + M_C (senza duplicati) = **M_FINAL**.
Assegna matrix_row_id univoco a ogni riga. M_FINAL è l'input esclusivo di Phase 4b.

**[CHECKPOINT OBBLIGATORIO — salva M_FINAL su file prima di procedere]**

Usa Write tool per salvare M_FINAL su `docs/qa/{STORY_ID}/MFINAL.md` (crea la directory se non esiste). Schema JSON formale in `reference/schemas/m_final.schema.json` — valida prima di salvare se Bash disponibile. Se Story ID assente: degrada a `docs/qa/UNTRACKED-{timestamp}/MFINAL.md` e segnala WARNING. Se MFINAL.md esiste gia': suffix `.bak.{timestamp}` sul vecchio file (no overwrite silente).
Dopo il salvataggio: **M_A, M_B, M_C non sono più necessarie** — non referenziarle nelle phase successive.
Tutte le phase successive (4b, J3, J4, J5) leggono M_FINAL da `docs/qa/{STORY_ID}/MFINAL.md` tramite Read tool.
Questo protegge M_FINAL dalla compattazione automatica del context.

**Partial failure handling:**

- **Se un agente Matrix (A/B/C) restituisce errore o output vuoto:** rilancia quell'agente singolo una volta. Se il retry fallisce: segnala `⚠️ Matrix [A/B/C] non disponibile` e procedi con la matrice parziale — annota il gap in `docs/qa/{STORY_ID}/MFINAL.md`.
- **Se M_C è vuota (nessun ruolo distinto):** comportamento atteso — J1_MATRIX opera solo su M_A+M_B. Procedi normalmente.
- **Se J1_MATRIX FAIL:** rilancia solo l'agente mancante (A o B) per le entità/campi scoperti. Poi ripeti J1_MATRIX. Max 2 iterazioni, poi escalation all'utente.
- **Se J2_MATRIX identifica duplicati:** rimuovili da M_FINAL prima del salvataggio su file.

**Output atteso Phase 1.5:** `docs/qa/{STORY_ID}/MFINAL.md` su filesystem — tabella con N righe, ognuna = 1 TC atteso.

---

### Phase 2 — Lettura Test Strategy da Confluence

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
- Procedi alla Phase 3 senza informazioni di scope

**Output atteso Phase 2:** sezioni Scope/Approach/Test Types lette, oppure WARNING registrato.

---

### Phase 3 — Generazione Test Plan

Struttura del Test Plan da creare o mostrare:

```
Test Plan: {Story summary}
  Versione:       {versione sprint/release}
  Sprint:         {sprint corrente}
  Link Story:     {URL Jira PROJ-XXX}
  Scope:          {da Confluence, o "da definire" se Tier 3}
  Test Cases:     [lista TC generati nella Phase 4]
```

**Tier 1 (MCP):** crea il Test Plan in Xray via MCP tool
**Tier 2 (Documento):** mostra la struttura testuale del Test Plan; usa `[nome documento]` come fonte al posto del link Jira; il Test Plan verra' esportato come CSV in Phase 5
**Tier 3 (Conversazione):** mostra la struttura testuale, da importare manualmente

---

### Phase 4 — Generazione Test Case step-based

#### 4a — Verifica e completamento M_FINAL [input: Phase 1.5]

**Input:** M_FINAL prodotta da Phase 1.5 (Gate #1 già PASS).

Non è più una fase di elicitazione scenari astratti. La matrice guida la generazione.

1. **Mostra M_FINAL** al developer in forma tabellare compatta:
   - Totale righe (= TC attesi)
   - Distribuzione: N POS / N NEG / N EDGE / N ROLE
   - Entità coperte

2. **Chiedi una sola domanda:** "La matrice ha {N} righe, stimati {N} TC. Ci sono scenari specifici che conosci dal dominio ma non derivabili dalla struttura del documento? (es. comportamenti impliciti, business knowledge non scritta)"

3. Il developer può aggiungere righe manualmente. Registra aggiunte con `source_ref = "developer input"`.

4. Se nessuna aggiunta: procedi immediatamente a Phase 4b.

**M_FINAL aggiornata è l'input esclusivo per Phase 4b.**

---

#### 4b — Generazione Test Case da M_FINAL

**Prima di iniziare:**
1. Usa Read tool per ricaricare `docs/qa/{STORY_ID}/MFINAL.md` dal filesystem (protegge dalla compattazione)
2. Usa Read tool per leggere `XRAY-TEMPLATES.md` — sezioni "Formato Test Case Step-Based", "Prefissi di Categoria", "Regola Multi-Step"
   Se `XRAY-TEMPLATES.md` non è trovato: segnala `⚠️ XRAY-TEMPLATES.md non trovato — uso formato inline` e usa il template minimo:
   ```
   Titolo: [test_type] descrizione
   Description: matrix_row_id: {id} | entity: {entity} | field: {field}
   Precondizioni: {condizione concreta dalla colonna condition}
   Step 1 - Action: {azione concreta}
   Step 1 - Expected Result: {risultato verificabile e non generico}
   ```

Per ogni riga di M_FINAL genera **esattamente 1 TC** step-based.

**Vincolo di specificità (obbligatorio):** ogni TC deve contenere nei passi/precondizioni i valori concreti dalla colonna `condition` della riga matrice:
- ❌ "Inserire una categoria valida"
- ✅ "Impostare CATEGORY = `'F'` nel CSV GENERAL_DATA"
- ❌ "Fornire una data non valida"
- ✅ "Impostare RELEASED = `'01/01/2024'` (formato DD/MM/YYYY, non ISO 8601)"

**Tracciabilità obbligatoria:** ogni TC deve riportare il `matrix_row_id` corrispondente nel campo `Description` (non nel titolo).

Esempio di struttura TC corretta:
```
Titolo:        [POS] CATEGORY = "F" → migrazione come feature
Description:   matrix_row_id: A-001 | entity: GENERAL_DATA | field: CATEGORY
Precondizioni: CSV GENERAL_DATA contiene riga con CATEGORY = "F"
Step 1 Action: Esegui la migrazione del record
Step 1 Expected Result: Il record viene creato come tipo "feature" nel nuovo sistema
```

**Condizioni multi-valore nella colonna `condition`:** se la condizione contiene `AND`/`OR` tra piu' valori (es. `"importo > 1000 AND valuta IN (EUR, USD)"`), genera **1 TC** scegliendo i valori in modo **deterministico**:
- Per condizioni numeriche di range (`> X`, `>= X`, `< X`, `<= X`, `BETWEEN X AND Y`): usa la **frontiera bassa appena valida** (es. `> 1000` → `1001`; `>= 1000` → `1000`; `BETWEEN 100 AND 200` → `100`).
- Per condizioni `IN (a, b, c)`: usa il **primo valore** dell'elenco nell'ordine sintattico (es. `IN (EUR, USD)` → `EUR`).
- Per `OR` tra valori esclusivi: usa il **primo termine** dell'OR.
Non espandere in TC multipli — l'esplosione combinatoria e' gia' avvenuta in Phase 1.5 tramite le regole di Agent B.

Esempio: `importo > 1000 AND valuta IN (EUR, USD)` → TC con `importo=1001, valuta=EUR`.

**Prefisso titolo:** usa il `test_type` della riga (`[POS]`, `[NEG]`, `[EDGE]`, `[ROLE]`).

**[CHECKPOINT OBBLIGATORIO — salva TC su file prima di Gate #2]**

Usa Write tool per salvare i TC generati su `docs/qa/{STORY_ID}/TC_DRAFT.md`. Schema JSON formale in `reference/schemas/tc_draft.schema.json`. Stessa policy di backup di MFINAL.md.
Gate #2 (J3+J4) leggera' da `docs/qa/{STORY_ID}/TC_DRAFT.md` — garantisce dati integri anche dopo compattazione.

**Default deterministico per ogni TC generato (Phase 4b):**
- `Automazione = N` (no test automatizzato esistente — il developer aggiorna a `Y` solo se conferma esistenza di test JUnit/vitest/pytest che coprono esattamente questo TC)
- `NRT = Y` (default Non-Regression Test)

**Riepilogo prima del gate:** mostra la tabella compatta al developer (TC-ID, titolo, matrix_row_id, test_type, Automazione, NRT). Il developer puo' sovrascrivere `Automazione` e `NRT` **solo dopo Gate #2 PASS**, pre-export. Ogni override viene registrato nel campo `developer_overrides` del `coverage_certificate.json` (lista di `{tc_id, field, old_value, new_value}`).

---

### Phase 4c — Gate #2: TC vs Matrix Verification [bloccante — post-generazione]

Dopo la generazione (Phase 4b), lancia **J3 e J4 in parallelo** con Agent tool.
Verificano la bijection TC↔M_FINAL e la specificità dei TC.

<EXTREMELY-IMPORTANT>
FERMATI. Stai per procedere a Phase 4d senza Gate #2?

J3 e J4 operano QUI sui TC prodotti — verificano che ogni riga di M_FINAL sia diventata
un TC concreto e che ogni TC abbia dati di test specifici (non generici).
Invoca J3 e J4 con Agent tool nello STESSO turno. Non sequenzialmente.
Un'autovalutazione interna di Claude NON è Gate #2.

**Criterio verificabile:** l'esecuzione di Gate #2 deve produrre 2 tool call result di Agent tool visibili nella conversazione. Se non puoi mostrare questi tool call result, Gate #2 non è stato eseguito — è stato simulato.

**Input per J3 e J4:** leggi M_FINAL da `docs/qa/{STORY_ID}/MFINAL.md` e i TC da `docs/qa/{STORY_ID}/TC_DRAFT.md` tramite Read tool — non usare il context direttamente, i file garantiscono dati integri dopo eventuale compattazione.
</EXTREMELY-IMPORTANT>

#### Serializzazione input (OBBLIGATORIA prima del lancio)

```
M_FINAL (da Phase 1.5, letto da docs/qa/{STORY_ID}/MFINAL.md):
matrix_row_id | entity | field | condition | test_type
{row_id_1} | {entity} | {field} | {condition} | {POS|NEG|EDGE|ROLE}
...

TC GENERATI (da Phase 4b, letto da docs/qa/{STORY_ID}/TC_DRAFT.md):
TC-ID | Titolo (con prefisso [POS|NEG|EDGE|ROLE]) | matrix_row_id | test_type
TC-01 | [POS] {titolo} | {matrix_row_id} | POS
...
```

#### J3 — Bijection Check

```
Sei un QA Judge specializzato in tracciabilità TC↔matrice.
Input: M_FINAL + TC GENERATI (serializzati sopra)
Verifica:
  1. Ogni riga di M_FINAL ha esattamente 1 TC con matrix_row_id corrispondente
     (righe orfane = righe senza TC)
  2. Ogni TC ha un matrix_row_id valido che esiste in M_FINAL
     (TC orfani = TC senza riga matrice)
Elenca righe orfane e TC orfani. Soglia: 100% bijection.
Output: GIUDICE J3 | PASS/FAIL | RIGHE_ORFANE: [lista] | TC_ORFANI: [lista]
```

#### J4 — Specificity Check

```
Sei un QA Judge specializzato in qualità e specificità dei TC.
Input: M_FINAL + TC GENERATI (serializzati sopra)
Per ogni TC, recupera la riga M_FINAL corrispondente e verifica:
  1. Passi/precondizioni contengono i valori concreti dalla colonna "condition"
     (es. se condition = "'F'→feature" il TC deve menzionare il valore "F")
  2. Expected result è verificabile e non generico (non "dovrebbe funzionare")
  3. Precondizioni sono sufficienti per eseguire il test senza ambiguità
Elenca TC con specificità insufficiente. Soglia: 75%.
Output: GIUDICE J4 | PERCENTUALE: XX% | PASS/FAIL | TC_GENERICI: [lista con motivazione]
```

#### Comportamento Gate #2

```
1. Lancia J3 e J4 in parallelo (Agent tool, stesso turno)
2. Valuta:
   - J3 FAIL → rigenerazione selettiva solo per righe orfane (Phase 4b parziale)
   - J4 < 75% → riformulazione selettiva dei TC generici identificati
3. Rilancia SOLO i judge falliti con:
   "Nel run precedente hai trovato questi problemi: [lista].
   Valuta i TC aggiornati: [lista TC nuovi]."
4. Max 2 iterazioni per gate, poi escalation all'utente

Escalation asimmetrica: se un solo judge (J3 o J4) supera il max di iterazioni mentre
l'altro è già PASS, l'escalation riguarda solo il judge fallito. Mostra il GATE #2
REPORT parziale e chiedi: "J3/J4 non converge dopo 2 iterazioni — vuoi procedere
con questo gap o rifai la generazione da zero per le righe coinvolte?"

Se J3 PASS e J4 PASS: procedi a Phase 4d (J5 Final Audit)
```

#### Formato GATE #2 REPORT

```
GATE #2 REPORT
──────────────
J3 Bijection:   N/N righe coperte (100%) | N TC orfani   [PASS ✅ / FAIL ❌]
J4 Specificità: XX% TC con dati concreti                  [PASS ✅ / FAIL ❌]

Righe orfane (senza TC): [lista]
TC orfani (senza riga matrice): [lista]
TC generici da riformulare: [lista con motivazione]
──────────────────────────────────────────────────
```

---

### Phase 4d — Final Audit (J5) [non bloccante — run-once]

Dopo Gate #2 PASS, lancia J5 con Agent tool come auditor finale con vista completa.

```
Sei un QA Judge specializzato in correttezza tecnica e audit finale.
Input: M_FINAL (da `docs/qa/{STORY_ID}/MFINAL.md`) + TC GENERATI (da `docs/qa/{STORY_ID}/TC_DRAFT.md`) + REPORT J1_MATRIX + J2_MATRIX + GATE#2
       + {TIPI E RANGE CAMPI: tipi dato, range validi, formati attesi dei campi dalla serializzazione Phase 1.5}
Analizza:
  1. Boundary conditions non catturate dalla matrice (valori al limite del range,
     overflow numerico, timezone, caratteri speciali, encoding)
  2. Edge case tecnici: idempotenza, race conditions, ordine di elaborazione CSV
  3. Coerenza tra step Action e Expected Result per ogni TC
  4. Gap residui rispetto alla specifica (comportamenti impliciti non documentati)
Produci:
  - coverage_score: percentuale calcolata come `count(matrix_row_id PRESENTI in TC_DRAFT con J3_PASS=true AND J4_PASS=true) / count(M_FINAL.rows) * 100` (intero arrotondato)
  - lista gap prioritizzata (HIGH / MEDIUM / LOW)
  - coverage_certificate: { timestamp, score, total_tc, matrix_rows }
Output: GIUDICE J5 | SCORE: XX% | CERTIFICATE: {dati} | GAP: [lista con priorità]
```

**J5 è run-once.** Non viene mai rilanciato. Il developer può accettare i gap o aggiungere TC.

#### Comportamento post-J5

```
SE il developer sceglie di aggiungere TC per i gap J5:

1. Aggiungi i nuovi TC alla lista (con matrix_row_id = "J5-gap-Gxx")
2. PRIMA di esportare: RILANCIA Gate #2 (J3 + J4) in parallelo
   sui TC AGGIORNATI (vecchi + nuovi)
   Input aggiornato:
     M_FINAL + nuove righe J5 (aggiunte come righe sintetiche)
     TC aggiornati (vecchi + nuovi)
3. Se Gate #2 PASS → procedi a Phase 5 (export)
4. Se Gate #2 FAIL → fixa solo i TC falliti, ripeti Gate #2 (max 1 iterazione aggiuntiva)

SE il developer sceglie di NON aggiungere TC (accetta i gap):
→ Procedi direttamente a Phase 5 (export) con il certificate "CONDITIONAL_PASS"

NON esportare mai dopo aver aggiunto TC senza aver ripassato Gate #2.
"Ho appena aggiunto i TC, sicuramente passano" → non è Gate #2. Il gate va eseguito.
```

<EXTREMELY-IMPORTANT>
Hai aggiunto TC per i gap J5 e stai per esportare senza rilanciare Gate #2?
FERMATI. I nuovi TC non sono stati verificati da J3 (bijection) né da J4 (specificità).
Gate #2 va rilanciato sui TC aggiornati prima di qualsiasi export.
</EXTREMELY-IMPORTANT>

#### Formato COVERAGE CERTIFICATE

```
COVERAGE CERTIFICATE
────────────────────
Stato:                FULL_PASS | CONDITIONAL_PASS | FAIL
Story ID:             {PROJ-XXX}
Timestamp (ISO8601):  {YYYY-MM-DDTHH:MM:SSZ}
M_FINAL righe:        N (+K righe J5-gap se aggiunte)
TC generati:          N (+K nuovi se aggiunte)
coverage_score:       XX%
Gate #1 (matrix):     PASS ✅
Gate #2 (TC):         PASS ✅  [ri-eseguito post-J5 se TC aggiunti]
J5 Gap HIGH risolti:  K/N
J5 Gap MEDIUM aperti: N (sprint successivo)
J5 Gap LOW aperti:    N (opzionali)
developer_overrides:  N (vedi xray_id_mapping.json campo overrides)

Gap aperti accettati:
  MEDIUM: [gap con impatto medio]
  LOW:    [suggerimenti opzionali]
────────────────────
```

**Regole automatiche per il campo `Stato`:**
- `FULL_PASS` se: Gate #1 PASS AND Gate #2 PASS AND coverage_score >= 90 AND nessun gap HIGH aperto
- `CONDITIONAL_PASS` se: Gate #1 PASS AND Gate #2 PASS AND (coverage_score < 90 OR gap MEDIUM/LOW aperti accettati dal developer)
- `FAIL` se: Gate #1 FAIL OR Gate #2 FAIL (non si dovrebbe mai arrivare al certificato in questo stato)

**Persistenza obbligatoria:**

Prima di procedere a Phase 5, usa Write tool per salvare il certificate come JSON in `docs/qa/{STORY_ID}/coverage_certificate.json`. Schema formale: `reference/schemas/coverage_certificate.schema.json`. Il file JSON e' parsabile programmaticamente e usato dal collaudo.

Procedi a Phase 5 (export) con il certificate allegato.

---

### Phase 5 — Export / Sincronizzazione

**Pre-export step:** verifica che `docs/qa/{STORY_ID}/coverage_certificate.json` sia stato scritto in Phase 4d. Senza certificate, non procedere all'export.

**Tier 1 (MCP):**
1. Crea ogni Test Case in Xray via MCP
2. Ogni TC creato ottiene automaticamente una chiave Jira (es. `PROJ-456`) — registrala nella mappatura (vedi Passo post-export)
3. Dopo l'esecuzione dei test, aggiorna il Test Execution con i risultati

**Tier 2 (Documento):**
- Output sempre CSV semicolon-separated in formato Xray-importabile — indipendentemente dalla disponibilità MCP
- Vedi [XRAY-TEMPLATES.md](XRAY-TEMPLATES.md) sezione "Tier 3 CSV Export" per formato e istruzioni

**Tier 3 (Conversazione):**
Vedi [XRAY-TEMPLATES.md](XRAY-TEMPLATES.md) sezione "Tier 3 CSV Export" per formato e istruzioni import.

**Passo post-export — Mappatura ID sequenziali -> chiavi Jira Xray [OBBLIGATORIO se si usa siae-automation]**
Vedi [XRAY-TEMPLATES.md](XRAY-TEMPLATES.md) sezione "Mappatura ID Sequenziali e Chiavi Jira Xray" per procedura e template mappatura.
Salva la mappatura come file JSON in `docs/qa/{STORY_ID}/xray_id_mapping.json`. Schema formale: `reference/schemas/xray_id_mapping.schema.json`. Senza questo file, siae-automation non puo' iniziare. Tier 3 (CSV): la mappatura viene popolata dopo che il developer comunica le chiavi Xray; il file viene scritto solo quando le chiavi sono complete.

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
| "Ho letto gli AC, so gia' il tipo — salto Phase 0" | Phase 0 non e' solo typing: e' la raccolta degli scenari contestuali che gli AC non esplicitano. Senza queste domande, i TC coprono solo cio' che e' scritto, non cio' che puo' rompersi. |
| "Il documento ha i requisiti, non serve derivare gli AC" | I requisiti descrivono cosa fare, gli AC descrivono come verificarlo. Derivare gli AC è lo step interpretativo chiave — senza di esso i TC testano il documento, non il comportamento. |
| "Ho già letto il documento, so quali AC ci sono" | La derivazione degli AC deve essere esplicita e validata dall'utente. Un'inferenza non validata è un'assunzione. |
| "So gia' il tier dal contesto, salto l'Opening Dialog" | Il dialog non e' opzionale. Mostralo e aspetta risposta conforme alla "Definizione di conferma valida". Inferire il tier produce CSV invece di MCP (o viceversa) e silenzia errori a valle. |
| "Salto la Coverage Matrix, tanto genero i TC dagli AC" | TC generati dagli AC grezzi sono narrativi: coprono i casi che vengono in mente, non tutti i casi. La matrice è sistematica: copre ogni campo, ogni lookup, ogni combinazione. |
| "Il documento è semplice, non serve la Coverage Matrix" | Semplice per chi lo ha scritto. Ogni campo obbligatorio ha 2 TC (POS+NEG), ogni lookup ha N+1 TC. La matrice lo scopre in automatico; l'approccio narrativo lo dimentica. |
| "Matrix Agent B rallenta per regole composte semplici" | Se la spec ha 0 regole composite, M_B è vuota in pochi secondi. Il costo è zero. Se le regole ci sono e non costruisci la matrice, mancano quei TC nel collaudo. |
| "Il Coverage Gate rallenta il workflow" | Un TC che non copre un requisito è un buco nel collaudo. I judge in parallelo impiegano secondi. Un bug in produzione da AC non coperto costa ore. |
| "J1_MATRIX al 100% è irraggiungibile con molti campi" | È raggiungibile: ogni entità/campo deve avere almeno 1 riga POS + 1 NEG in M_FINAL. Non tutte le combinazioni — solo quelle con esito distinto. |
| "I TC sono OK con formulazioni generiche tipo 'inserire valore valido'" | Il vincolo di specificita' richiede i valori concreti della colonna `condition`. Senza prefisso `[POS]/[NEG]/[EDGE]/[ROLE]` e senza valori concreti, J3/J4 falliscono. |
| "Salto Phase 4c Gate #2, i TC li ho appena generati da M_FINAL" | La generazione produce TC tracciabili ma non garantisce specificità. Gate #2 verifica che i valori concreti della colonna 'condition' siano nei passi — non è ridondante. |
| "J5 non blocca, non serve" | J5 produce il coverage_certificate e identifica boundary conditions che M_FINAL non cattura. Saltarlo significa non avere il certificate per il collaudo. |
| "Ho appena aggiunto i TC per J5, Gate #2 è superfluo" | I TC aggiunti per J5 non sono stati verificati da J3 (bijection) né da J4 (specificità). Gate #2 va rilanciato. Un TC aggiunto senza matrix_row_id o con passi generici passa la generazione ma fallisce il gate. |
| "Esporto subito dopo J5, poi se serve riciclo" | Non si esporta con TC non verificati. Gate #2 post-J5 costa secondi. Riciclare dopo l'export significa aggiornare il file CSV già distribuito al team — costo molto più alto. |
| "coverage_certificate.json e' un nice-to-have, esporto e basta" | Senza certificate il collaudo non puo' validare la chiusura del ciclo QA e siae-automation non ha l'input previsto. L'export non parte senza certificate (FULL_PASS o CONDITIONAL_PASS). |

---

## CHECKLIST DI VERIFICA

Vedi [XRAY-TEMPLATES.md](XRAY-TEMPLATES.md) sezione "Checklist di Verifica" per la checklist completa.
**Non riesci a spuntare tutte le caselle? Il workflow non e' completo. Ricomincia dalla fase bloccata.**

---

## VINCOLI NON NEGOZIABILI

0. **Phase 0 e' sempre la prima phase** — nessun AC viene letto senza aver prima inferito il tipo e lanciato le domande del tree contestuale; la Req Profile Card deve essere prodotta prima di Phase 1
1. **Nessun Test Case senza riga M_FINAL corrispondente** — ogni TC è tracciabile a una riga della Coverage Matrix (matrix_row_id obbligatorio nel campo Description)
2. **M_FINAL deve esistere PRIMA di generare qualsiasi TC** — Phase 1.5 e Gate #1 sono bloccanti; non si genera senza M_FINAL approvata da J1_MATRIX + J2_MATRIX
3. **La generazione TC è 1:1 con M_FINAL** — ogni riga di M_FINAL produce esattamente 1 TC; nessun TC senza riga, nessuna riga senza TC
4. **I TC devono contenere i valori concreti dalla colonna "condition" di M_FINAL** — nessuna formulazione generica ("inserire un valore valido")
5. **Il campo `ID JIRA Story` e' obbligatorio** — senza di esso il TC non ha senso in Xray
6. **Ogni step ha `Action` e `Expected Result`** — step senza Expected Result = step non valido
7. **Il CSV usa separatore `;` (semicolon)** — non virgola, non tab
8. **Righe con stesso ID = stesso Test Case** — i metadati solo nella prima riga, step multipli nelle righe successive
9. **Nel CSV, il nome colonna e' `Expceted Result`** — typo storico del template importatore Xray SIAE. Usarlo esattamente per compatibilita' import.
10. **Gate #1 (J1_MATRIX+J2_MATRIX) è obbligatorio prima di Phase 4b** — nessuna generazione senza M_FINAL validata
11. **Gate #2 (J3+J4) è obbligatorio dopo Phase 4b** — nessun export senza bijection PASS e specificità ≥75%
12. **J5 Final Audit è obbligatorio prima dell'export** — il coverage_certificate è il documento di chiusura del ciclo QA
13. **coverage_certificate.json deve esistere prima di Phase 5** — l'export non parte senza certificate (FULL_PASS o CONDITIONAL_PASS).
14. **Tutti i TC hanno prefisso esplicito** — `[POS]/[NEG]/[EDGE]/[ROLE]`. Nessun TC senza prefisso (fallirebbe J3/J4).

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

**Se Agent tool viene negato (Matrix A/B/C o J1-J5):**

<EXTREMELY-IMPORTANT>
NON simulare il judge o l'agente Matrix internamente.
Simulare un giudice senza Agent tool invalida l'intero meccanismo di verifica indipendente.
</EXTREMELY-IMPORTANT>

1. FERMATI. Il gate/phase non può essere eseguito senza Agent tool.
2. Comunica esplicitamente: "Agent tool è necessario per [phase X] — senza invocazione reale il gate non è eseguito. Vuoi continuare con un piano QA non verificato da judge indipendente? Confermalo esplicitamente."
3. **Se l'utente conferma consapevolmente:** procedi ma aggiungi nel Coverage Certificate: `⚠️ ATTENZIONE: [Gate X] non eseguito con Agent tool — validazione manuale richiesta prima del collaudo`
4. **Se l'utente non conferma:** blocca. Attendi che Agent tool sia abilitato.

**Phase completabili senza permessi:** Phase 1 (conversazionale — lettura AC/requisiti, elicitazione scenari)
**Phase che richiedono Agent tool:** Phase 1.5 (Matrix A/B/C, J1_MATRIX/J2_MATRIX), Phase 4c (J3/J4), Phase 4d (J5)
**Phase che richiedono Write tool:** Phase 1.5 (`docs/qa/{STORY_ID}/MFINAL.md`), Phase 4b (`docs/qa/{STORY_ID}/TC_DRAFT.md`), Phase 4d (`docs/qa/{STORY_ID}/coverage_certificate.json`), Phase 5 (`docs/qa/{STORY_ID}/xray_id_mapping.json`).
**Phase che richiedono MCP:** Phase 5 (Xray — solo Tier 1)

Se i permessi sono negati:
1. Completa tutte le phase conversazionali (1-4)
2. Presenta CSV/TC come output testuale
3. NON entrare in loop di retry su tool negato
4. NON dichiarare completamento per phase non eseguite

---

## QUANDO SEI BLOCCATO

| Problema | Soluzione |
|----------|-----------|
| Campo AC vuoto in Jira | Leggi description → commenti → Confluence → chiedi al developer |
| MCP non risponde | Degrada a Tier 3 CSV, segnala il problema all'utente |
| Story non trovata in Jira | Chiedi l'ID corretto, verifica permessi MCP |
| TC troppo astratti | Torna agli AC, fai domande piu' specifiche al developer |
| Developer non sa quali campi Automazione/NRT usare | Default: Automazione=N, NRT=Y. Correggi insieme revisando i test automatizzati esistenti |
