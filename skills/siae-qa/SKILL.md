---
name: siae-qa
version: 2.3.0
last_modified: 2026-05-22
description: >
  Genera documentazione test formale per Xray a completamento implementazione.
  Trigger: completamento brainstorming (Phase 2), completamento ciclo TDD (Phase 5),
  "genera test plan Xray", "export Test Case Xray".
changelog: |
  2.3.0 (2026-05-22): Guardrail TC Negativi (R1-R5) — fix RTD-108 (54% NEG non eseguibili).
    - ADR-013: classificazione `executability_class` (manual/automated-only/eliminated)
      su righe NEG/EDGE in Matrix A e Matrix B (Phase 1.5).
    - Phase 4b: routing pre-generazione — manual genera TC, automated-only produce
      entry `automated_only_note`, eliminated viene rimossa.
    - Phase 4c Gate #2: J6 NegativeExecutability Check (parallelo a J3+J4) — bloccante
      al 100% per TC NEG/EDGE manuali; bypass solo con consenso esplicito developer.
    - Nuova sezione "Guardrail TC Negativi (R1-R5)" prima di Phase 4b: rules R1
      (no system mutation), R2 (no DB direct action), R3 (no fault injection),
      R4 (no mirror negativo), R5 (checklist precondizione).
    - Schema m_final esteso con executability_class/rule_violated/automation_suggestion/eliminated_reason.
    - Schema tc_draft esteso con discriminator `kind` (test_case | automated_only_note).
    - Vincolo non negoziabile #20 (executability) e #21 (CSV pulito).
    - Phase 5 produce 2 file separati: `RTD-XXX_TC.csv` (solo TC eseguibili,
      importabile Xray senza errori) e `automated_only_notes.md` (note developer,
      raggruppate per regola R1/R2/R3). Le righe `eliminated` finiscono solo in
      `coverage_certificate.json.eliminated_rows[]`. Nessuna riga commento `#` nel CSV.
    - Schema coverage_certificate esteso con `j6`, `eliminated_rows[]`, `automated_only_count`.
    - Description = solo descrizione semantica (40-400 char). VIETATO `matrix_row_id`,
      `entity:`, `field:` nel testo. Tracciabilita' via campi schema separati. J3 legge
      `tc.matrix_row_id` come campo, non fa parsing testo. J4 aggiunge check
      "description_non_semantica" e "description_con_metadata".
    - Vincolo non negoziabile #1 aggiornato di conseguenza.
  2.2.0 (2026-05-11): Full closure 25 gap residui post 5-case simulation.
    - ADR-008: cross-temporal/cross-event composite (Matrix B temporal sequences).
    - ADR-009: ETL stateful pipeline rules (idempotency MERGE, threshold composito, async side-effect, pipeline ordering, DLQ schema, timezone).
    - ADR-010: multi-session TC pattern ([SESSION A]/[SESSION B] observer steps).
    - ADR-011: conflict resolution + 9 categorie aggiuntive (UI state, REST pagination empty, security boundary, type duration, performance NFR, cache header, doc artifact, policy-dependent, measurement-bound).
    - ADR-012: schema matrix_row_id regex extended con suffix tematico opzionale.
    - Scorecard 48→50/50 (Gold tier consolidato).
  2.1.0 (2026-05-11): Residual fixes post-simulazione end-to-end.
    - ADR-001: type-aware "frontiera bassa" in Matrix A (decimal/integer/date).
    - ADR-002: strict-bound (>, <) genera EDGE auto; non-strict (>=, <=) no EDGE.
    - ADR-003: string trim/NFC/max-length opt-in (keyword trigger esplicito).
    - ADR-004: entity naming gerarchia (SCREAMING_SNAKE_CASE per tabelle/section; PascalCase singolare altrove).
    - ADR-005: Phase 4b multi-step mutating obbligatorio (no response-code-only per 2xx).
    - ADR-006: validator WARN channel (exit 0 con [WARN] su stderr).
    - ADR-007: POS lookup unification + NEG per-field collapse + B-001/B-002 condizionale.
    - Vincoli #15 e #16 aggiunti.
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

Stai per generare un TC `[NEG]` la cui precondizione richiede di modificare template,
config, SMTP, DB direct INSERT/UPDATE, fault injection (servizio down, race, retry)?
FERMATI. Quel TC NON e' eseguibile da QA manuale — vedi sezione "Guardrail TC Negativi (R1-R5)".
La precondizione corretta classifica la riga come `automated-only` (nota commento, no TC)
o `eliminated` (mirror di un POS gia' coperto). Una TL piena di TC non eseguibili e'
un fallimento di workflow, non un compromise accettabile.
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
- **Invocazione manuale via trigger sentence** (es. "genera test plan Xray"): per export, riesecuzione o aggiornamento

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
| **Strict-bound numerico** (`>`, `<`, `> X AND < Y`) | POS(valore tipico) + NEG(violazione) + EDGE(frontiera bassa type-aware) | `importo > 0` decimal → `0.01` EDGE; `quantita > 0` integer → `1` EDGE |
| **Non-strict-bound numerico** (`>=`, `<=`, BETWEEN inclusivo) | POS(valore tipico) + NEG(violazione). **NO EDGE auto** (frontiera già in POS) | `DURATION >= 0` mandatory → 2 righe (POS valido + NEG assente) |
| **String con vincolo length/encoding** (opt-in) | POS + NEG(>max length) + EDGE(trim/NFC) **solo se** spec menziona `trim`, `whitespace`, `NFC`, `max length`, `255 char` | `TITLE max 255 char` → POS + NEG(>255). Senza menzione esplicita: solo POS |
| **Valore fisso business** | POS(= costante) + NEG(≠ costante) | UNIQUEREF2 = "074" |
| **Regola composita** (N campi interdipendenti) | Prodotto cartesiano filtrato per esiti distinti + pairwise IPOG se > 16 | account × IPI → 4 combinazioni; 5 boolean → 32 combinazioni → 16 selezionate via pairwise IPOG |
| **Cross-sezione** (chiave condivisa tra CSV/entità) | NEG per ogni sezione dipendente (chiave assente) | UNIQUEREF1 assente in TITLES |
| **Cross-temporal / cross-event composite** | POS(first execution canonica) + EDGE(race/replay stesso input) + EDGE(out-of-order eventi B prima di A) + NEG(stato finale inconsistente) | idempotency `event.id`: POS first + EDGE duplicate + EDGE OOO |
| **Stateful pipeline idempotency** (MERGE/UPSERT per chiave) | POS(first run produce expected count) + EDGE(rerun same key → no-op, count invariato) + NEG(rerun different value → conflict resolved/upsert update) | MERGE INTO silver.ripartizioni USING bronze... ON id_ripartizione |
| **Volume threshold composito** (count + ratio + drift) | 1 POS within + 1 NEG per ogni threshold superato (count, ratio, drift) + 1 EDGE per boundary value di ogni threshold | drop_ratio > 30% triggers alarm |
| **Async side-effect** (CloudWatch alarm, SNS, audit log entry) | POS(side-effect fired entro window) + NEG(side-effect NOT fired when expected) + EDGE(side-effect duplicato/idempotency) | RIPARTIZIONI_QUALITY_DEGRADED alarm |
| **Pipeline ordering cross-AC** (filter → dedup → null → lookup → FK) | POS(canonical order respected) + NEG(stage skipped) + NEG(stage reordered modifica esito) | bronze→silver con stage order |

#### Priorità Regole su Conflitto (ADR-011)

Quando due categorie di esplosione si applicano allo stesso campo, applica priorità deterministica:

1. **Boolean + valore fisso business** → priorità valore fisso. Esplosione: POS(true) + NEG(false) + NEG(non-parseable). **NON duplicare** POS(false) come da regola booleano standard.
2. **String length/encoding + valore fisso** → priorità valore fisso (length/encoding implicito nel valore). POS(=valore) + NEG(≠valore) + NEG(>max length).
3. **Strict-bound numerico + valore fisso** → priorità valore fisso. POS(=valore) + NEG(≠valore).

#### Categorie aggiuntive di esplosione (v2.2.0)

| Categoria | Esplosione | Esempio |
|-----------|------------|---------|
| **UI state** (loading/empty/error/disabled) | 1 POS per stato osservabile + 1 NEG per transizione errata | form button: enabled(valid)+disabled(invalid)+loading(submit)+error(API 5xx) |
| **REST pagination/empty-set** | 200 con `content: []` (NON 404). POS empty + POS first-page + POS last-page + EDGE page-overflow | GET /api/opere?titolo=NOMATCH → 200 + empty content |
| **Security boundary** (SQL inj, XSS, path traversal) | 1 NEG per vettore noto, status 400 o sanitized 200 | `'; DROP TABLE`, `<script>`, `../etc/passwd` |
| **Type duration/interval** (ADR-001 extension) | EDGE `valore + granularità minima` (es. `> 5min` decimal → EDGE `5min 1s`) | signature timestamp validity |
| **Performance NFR** (latency, throughput, P95) | source_ref=`nfr_perf` — annotazione per test suite separata (k6/JMeter), NO TC funzionale | P95 < 500ms |
| **Cache header** (Cache-Control, ETag) | POS header presente + NEG header mancante quando expected | max-age=60 con filtri assenti |
| **Documentation artifact** (runbook, ADR, README) | source_ref=`doc_artifact` + TC step "verifica presenza file X" | recovery runbook esiste |
| **Policy-dependent constraint** | source_ref=`policy_dependent` + nota "verify policy in place" — non NEG ambiguo | DROP COLUMN dopo write |
| **Measurement-bound** (tempo, RAM misurati) | EDGE con tolerance range invece di valore fisso | duration < 35 min ± 10% |

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
  - Lookup enumerato (test sintattico per esplosione completa):
    * SE la spec contiene mapping esplicito campo→valore→esito (tabella con header `| Campo | Lookup | Mapping |` o sezione "Mapping CSV → Target"):
      → 1 POS per ogni valore + 1 NEG "fuori lookup" (esplosione completa, default migration)
    * ALTRIMENTI (lookup senza esiti distinti documentati):
      → 1 POS rappresentativa (primo valore in ordine sintattico) `source_ref="lookup_repr"` + 1 POS per ogni valore con comportamento downstream distinto documentato + 1 NEG "fuori lookup"
  - Mandatory non-numerico → POS(valido) + NEG(assente/null)
    * NEG per-field collapse: se piu' campi mandatory dello stesso entity hanno errore simmetrico (stesso status_code + stesso pattern errore lessicale modulo nome campo), genera 1 NEG rappresentativa `source_ref="mandatory_collapsed"` con `condition="<primo campo mandatory>=null"`. Se errori asimmetrici (es. `autore_id → 404`, `opera_id → 400`), 1 NEG per classe-errore distinta.
  - Optional → POS(valido) + EDGE(null = accettato)
  - Formato data/regex → POS(corretto) + NEG(errato) + EDGE(null se optional)
  - Strict-bound numerico (`>`, `<`) — EDGE type-aware:
    * Inferire tipo dalla serializzazione Phase 1.5 (`ENTITA E CAMPI ... dominio: decimal/integer/date`)
    * `> 0` decimal → EDGE `0.01`; `> 0` integer → EDGE `1`; `> '2020-01-01'` date → EDGE `2020-01-02`
    * Se tipo non specificato in spec: default `integer`, segnala WARNING `source_ref="type_inferred_default_integer"`
  - Valore fisso business → POS(= costante) + NEG(≠ costante)

**Classificazione executability per righe NEG/EDGE (OBBLIGATORIA, ADR-013):**
Per ogni riga NEG/EDGE che produci, assegna `executability_class` con uno dei 3 valori,
applicando l'albero decisionale R1-R4 dalla sezione "Guardrail TC Negativi" della SKILL.md:

  - `manual` → la precondizione e' producibile dal QA via browser/email-client/Postman/curl,
    senza modificare codice/template/config/DB. Esempi: URL manipolato, header mancante,
    form con campo vuoto, payload con valore fuori lookup, token scaduto via attesa, replay
    del link gia' consumato.
  - `automated-only` → la precondizione richiede system mutation (template/SMTP/CDN/sender),
    DB direct INSERT/UPDATE come azione, fault injection (DB down, SMTP timeout, race,
    rollback parziale), o comunque uno stub/mock non disponibile al QA. La riga NON
    generera' un TC manuale: in Phase 4b produrra' solo una nota `[AUTOMATED-ONLY]` con motivo.
  - `eliminated` → la riga e' un "mirror negativo" di un campo statico di configurazione
    gia' coperto dal POS corrispondente (es. NEG "subject template errato" mentre POS verifica
    "subject template corretto" — stesso campo, nessun input path autonomo). La riga viene
    rimossa da M_FINAL prima del salvataggio; conserva la motivazione nel campo
    `eliminated_reason` (es. "mirror di A-001: copertura garantita dal POS, no input path autonomo").

Le righe POS e ROLE hanno `executability_class = "manual"` per default (non si applicano R1-R4).
```

**Matrix Agent B — Rule Composer:**
```
Sei un QA Matrix Agent specializzato in regole di business composte e vincoli referenziali.
Input: {REGOLE DI BUSINESS COMPOSTE serializzate} + {VINCOLI REFERENZIALI} + {LOOKUP TABLES serializzate}
Per ogni regola composita: costruisci prodotto cartesiano ridotto
  - Esito DISTINTO = differenza nello status_code di ritorno OR classe del messaggio di errore (validation_error vs authorization_error vs business_rule_violation). Stesso status + stessa classe = stesso esito → tieni 1 combinazione rappresentativa.
  - B-001 (composite_happy) e B-002 (composite_worst) SOLO se la spec contiene almeno 1 regola composita cross-field (vincolo che lega 2+ campi con AND/OR di condizioni interdipendenti).
    * SE spec ha composite rules → genera B-001 (POS, tutti campi nominali validi, `source_ref="composite_happy"`) + B-002 (EDGE, tutti campi edge contemporaneamente, `source_ref="composite_worst"`).
    * SE spec NO composite rules → NON generare B-001/B-002 (M_B può essere vuoto).
  - Limite: max 16 combinazioni per regola. Se lo spazio delle combinazioni eccede 16: applica **pairwise covering (IPOG)** — selezione che copre ogni coppia di valori almeno una volta. Marca le righe con `source_ref="pairwise_ipog"`. Ordine deterministico: ordina i fattori per nome campo asc, poi seleziona le combinazioni nell'ordine prodotto da IPOG canonico.
Per ogni vincolo referenziale: 1 riga NEG per ogni sezione dipendente (chiave assente)
Produci: tabella M_B con colonne matrix_row_id, entity, field, condition, test_type, source_ref
  (colonne aggiuntive: combo_fields[], combo_values[] per regole composite)

**Temporal/cross-event composite (ADR-008):**
Trigger sintattici: `ANTE/POST`, `prima/dopo`, `out-of-order`, `replay`, `event.id`, `processed_at`, `last_*_at`, `idempotency-key`, `version A→version B`, `rollback dopo write`, `MERGE INTO`.
Per ogni sequenza identificata:
  - 1 POS per outcome canonico (first execution successful)
  - 1 EDGE per race/replay (stesso input 2 volte → outcome idempotente)
  - 1 EDGE per out-of-order (eventi B applicato prima di A nella catena)
  - 1 NEG per stato finale inconsistente (es. rollback dopo write con dati persistenti)
Marca le righe con `source_ref="temporal_composite"`.

**Classificazione executability per righe NEG/EDGE (OBBLIGATORIA, ADR-013):**
Applica lo stesso albero decisionale R1-R4 documentato per Matrix Agent A. Attenzione
particolare per Matrix B:
  - Cross-temporal "rollback dopo write" / "fail a meta' transazione" → `automated-only`
    (richiede stub applicativo, non producibile dal QA).
  - "Replay event id duplicato" su sistema reale con idempotency-key passato dal client →
    `manual` (basta riinviare lo stesso payload via Postman).
  - "Replay" che richiede INSERT DB duplicato di chiave primaria → `automated-only`.
  - "Out-of-order eventi" via Kafka/SQS con accesso al broker da parte del QA → `manual`;
    senza accesso al broker → `automated-only`.
  - Pipeline "DB offline / SMTP down" → `automated-only` (fault injection).
  - Volume threshold drift su ambiente condiviso → `automated-only` (non controllabile in QA).
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

#### Guardrail TC Negativi (R1-R5) [BLOCCANTE — applicato in Phase 4b, verificato in Gate #2]

<EXTREMELY-IMPORTANT>
Un TC negativo che il QA manuale non puo' eseguire NON e' un test: e' uno script di sabotaggio.
Tutti i TC con prefisso `[NEG]` (e `[EDGE]` quando la precondizione e' avversa) DEVONO
soddisfare le 5 regole R1-R5. Senza questi guardrail la skill produce TL non eseguibili
in QA manuale standard — bug analizzato su RTD-108 (54% dei NEG non eseguibili).
</EXTREMELY-IMPORTANT>

##### Razionale

Un QA manuale standard ha accesso a: browser, client email, Postman/curl, applicazioni
client del sistema. NON ha accesso a: codice sorgente, template engine, SMTP/CDN config,
DB con privilegi di scrittura, mock/stub framework, broker Kafka/SQS interni, switch di
fault injection. Generare TC che presuppongono questi accessi produce TL eseguibili solo
da chi sta scrivendo il codice — cioe' nessuno, perche' il QA non puo' fare il lavoro e
lo sviluppatore non rileggera' la TL.

##### Le 5 regole

```
[R1 — NO SYSTEM MUTATION]
Non generare TC negativi la cui PRECONDIZIONE richiede di modificare:
  - template email / template engine (subject, body, CTA, sender, locale)
  - configurazione SMTP, CDN, sender, SES, deploy, feature flag
  - record nel DB con INSERT/UPDATE diretto come setup
  - configurazione applicativa, properties, environment variables
  - implementazione errata (es. "differenzia messaggi di errore")
Routing: executability_class = "automated-only" — nessun TC manuale, nessuna riga nel CSV Xray.
Output destinato a `docs/qa/{STORY_ID}/automated_only_notes.md` (file di reportistica
per lo sviluppatore, NON importato in Xray): blocco con `matrix_row_id`, `rule_violated`,
`reason`, `automation_suggestion` (snapshot test, unit test, contract test, golden file).

[R2 — NO DB DIRECT ACTION]
Le ACTION di un TC manuale devono essere eseguibili tramite:
  - browser (navigazione, click, form input)
  - client email (apertura, ispezione header)
  - tool HTTP (Postman, curl) per chiamate API
  - shell client del prodotto (CLI utente-facing)
Query SQL (SELECT/INSERT/UPDATE/DELETE) NON sono Action valide per QA manuale.
Routing:
  - SELECT diagnostica come EXPECTED RESULT → spostarla nella verifica, marcata
    "verifica su tool monitoring/log" — il TC resta manuale.
  - SELECT/INSERT/UPDATE come ACTION o PRECONDIZIONE di setup-dati → executability_class
    = "automated-only" (richiede DBA, fuori scope QA standard).
  - Eccezione: se l'ambiente QA documenta esplicitamente un tool SQL nel kit standard
    del tester (es. read-only DBeaver con utenza ro), allora SELECT in expected_result
    e' manuale; INSERT/UPDATE restano automated-only.

[R3 — NO FAULT INJECTION]
Scenari non generabili dall'esterno tramite input legittimo:
  - servizi down (DB, SMTP, queue, broker)
  - retry simulati / mock stub applicativi
  - race condition / timing arbitrariamente preciso
  - rollback parziale di transazione DB
  - fallimento orchestrato di N-esimo tentativo
Routing: executability_class = "automated-only" — label aggiuntivo `chaos-test` o
`integration-test` nel suggerimento di copertura.

[R4 — NO MIRROR NEGATIVO]
Un TC NEG e' "mirror" quando soddisfa TUTTE queste condizioni:
  (a) il campo testato e' un campo statico di configurazione/template (NON un input utente)
  (b) il POS corrispondente verifica lo stesso campo con il valore corretto
  (c) l'unico modo per produrre il NEG e' alterare il sistema corretto
Routing: executability_class = "eliminated" — riga rimossa da M_FINAL. La nota di
eliminazione in coverage_certificate.json: "mirror di {POS_matrix_row_id}: copertura
del valore corretto garantita dal POS; nessun input path autonomo per produrre il
negativo sul sistema corretto".

[R5 — CHECKLIST PRECONDIZIONE]
Prima di emettere un [NEG] TC manuale, rispondi SI a tutte e 3:
  1. Il QA puo' produrre lo scenario con browser / Postman / email client?
  2. La precondizione e' impostabile senza modificare il sistema (codice/template/config/DB)?
  3. L'Action e' un'operazione UI/API/email-client, non una query SQL diretta?
Se anche una sola risposta e' NO → il TC NON viene generato come manuale.
```

##### Decision matrix sintetica

| Sintomo del TC candidato                                    | Routing        | Output destinato a            |
|--------------------------------------------------------------|----------------|--------------------------------|
| Input producibile da browser/Postman (URL, form, header)     | manual         | CSV Xray (riga TC `[NEG]`)     |
| Token scaduto via attesa temporale                           | manual         | CSV Xray (riga TC `[NEG]`)     |
| Replay link gia' consumato                                   | manual         | CSV Xray (riga TC `[NEG]`)     |
| Modifica template/subject/sender                             | automated-only | `automated_only_notes.md` (R1) |
| INSERT/UPDATE DB come setup                                  | automated-only | `automated_only_notes.md` (R2) |
| SMTP/DB down, retry exhausted, race                          | automated-only | `automated_only_notes.md` (R3) |
| Mirror inverso di campo statico gia' verificato dal POS      | eliminated     | `coverage_certificate.json`    |

**IMPORTANTE — separazione output:** il CSV Xray contiene SOLO TC manuali eseguibili
(prefisso `[POS]/[NEG]/[EDGE]/[ROLE]`). Note `[AUTOMATED-ONLY]` ed `[ELIMINATED]` NON
vanno mai nel CSV (l'importer Xray non gestisce in modo affidabile righe commento e
puo' importarle come TC vuoti o errori). Vanno in file separati di reportistica.

##### Esempi di riscrittura (dal bug RTD-108)

```
INPUT (riga M_FINAL):
  matrix_row_id: A-002 | entity: EmailTemplate | field: subject
  condition: subject = "Benvenuto" (non conforme) | test_type: NEG

OUTPUT R1 (automated-only):
  Riga eliminata da TC_DRAFT.md. Aggiunta in coverage_certificate.json:
  {
    "matrix_row_id": "A-002",
    "decision": "automated-only",
    "rule": "R1",
    "reason": "Subject template modificato come precondizione = system mutation.
               Coprire con snapshot test del template engine."
  }
  Entry in `docs/qa/RTD-108/automated_only_notes.md` (NON nel CSV):
  ## A-002 — [AUTOMATED-ONLY] Subject non conforme
  - rule_violated: R1 (system mutation)
  - reason: precondizione richiede modifica template, fuori scope QA manuale
  - automation_suggestion: snapshot test del template engine + golden file
  - original_condition: subject = "Benvenuto" non conforme
```

```
INPUT (riga M_FINAL):
  matrix_row_id: A-022 | entity: MagicLinkToken | field: generated_at
  condition: generated_at = "2026-13-45T99:99:99" (malformato) | test_type: NEG

OUTPUT R2 (automated-only):
  Entry in `docs/qa/RTD-108/automated_only_notes.md` (NON nel CSV):
  ## A-022 — [AUTOMATED-ONLY] generated_at malformato in DB
  - rule_violated: R2 (DB direct action)
  - reason: richiede INSERT SQL diretto con dato corrotto come precondizione
  - automation_suggestion: unit test sul parser timestamp con input fuzzato (property-based)
  - original_condition: generated_at = "2026-13-45T99:99:99"
```

```
INPUT (riga M_FINAL):
  matrix_row_id: A-061 | entity: MagicLinkToken | field: expires_at
  condition: now > generated_at + 5min → expired | test_type: NEG

OUTPUT R5 PASS (manual):
  TC-XX | [NEG] Token scaduto dopo 5 minuti
  Precondizione: Token generato a T0 via POST /magic-link/request
  Step 1 Action: Attendere 5 minuti e 1 secondo dopo T0
  Step 1 Expected: Trascorso il TTL atteso
  Step 2 Action: Visitare URL del magic link nel browser
  Step 2 Expected: Pagina errore "link scaduto" (HTTP 410 o redirect con messaggio)
```

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

**Routing pre-generazione per executability_class (R1-R5):**

Prima di generare il TC, leggi `executability_class` dalla riga M_FINAL:

- `manual` → genera 1 TC step-based completo (flusso normale, vedi sotto), finira' nel
  CSV Xray in Phase 5.
- `automated-only` → **NON generare TC manuale e NON inserire nel CSV Xray**. Registra
  in `TC_DRAFT.md` una entry speciale con `kind="automated_only_note"`, `matrix_row_id`,
  `rule_violated` (R1/R2/R3), `reason`, `automation_suggestion`. Nessun campo step.
  In Phase 5 verra' esportata in `docs/qa/{STORY_ID}/automated_only_notes.md` (file
  separato per lo sviluppatore, NON nel CSV).
- `eliminated` → **NON generare nulla**. La riga e' gia' stata rimossa da M_FINAL in
  Phase 1.5; verifica solo che non sia rientrata per errore. Se presente: produci una
  nota in `coverage_certificate.json` con `decision="eliminated"`, `rule="R4"`,
  `reason=<motivazione mirror>`. Nessun output nel CSV.

Per ogni riga di M_FINAL **con `executability_class = "manual"`** genera **esattamente 1 TC** step-based.

**Sanity check R5 in-line (per ogni TC `[NEG]` o `[EDGE]` con condition avversa):**
Prima di scrivere il TC, applica la checklist R5 (3 domande). Se una risposta e' NO,
riclassifica la riga (aggiorna M_FINAL: `executability_class = "automated-only"` e
`rule_violated`) e produci la nota commento invece del TC. Questo cattura righe
mal-classificate da Matrix A/B.

**Vincolo di specificità (obbligatorio):** ogni TC deve contenere nei passi/precondizioni i valori concreti dalla colonna `condition` della riga matrice:
- ❌ "Inserire una categoria valida"
- ✅ "Impostare CATEGORY = `'F'` nel CSV GENERAL_DATA"
- ❌ "Fornire una data non valida"
- ✅ "Impostare RELEASED = `'01/01/2024'` (formato DD/MM/YYYY, non ISO 8601)"

**Multi-step per azioni mutating (ADR-005, obbligatorio):**

Identifica TC che testano azioni mutating: HTTP `POST`/`PUT`/`PATCH`/`DELETE`, SQL `INSERT`/`UPDATE`/`DELETE`, CSV write su target.

Per TC mutating con status atteso 2xx:
- **Minimo 2 step:** (1) Action mutating con dati concreti; (2) **Side-effect verification** = read-back (`GET /resource/{id}`, `SELECT WHERE id = ...`) OR count (`SELECT COUNT(*) FROM table WHERE ... → incremento atteso`) OR audit log query.
- Response code 2xx **NON e' sufficiente** da solo come step 2, salvo che il body 2xx includa esplicitamente i campi creati (allora step 2 = "assert body fields == expected values").

Per TC mutating con status atteso 4xx/5xx (error mutating):
- **Minimo 3 step:** (1) Action mutating; (2) Verify error response (status code + error message specifico); (3) **Side-effect NOT occurred** = `SELECT COUNT(*) → invariato`, `GET /resource/{id} → 404`, o audit log assente.

Per TC read-only (HTTP `GET`, SQL `SELECT`):
- Minimo 1 step (azione + assertion sullo stesso step).

**Esempi:**

```
[POS] POST /ripartizioni happy path (3 step):
  Step 1: POST /ripartizioni body {importo=100.50, autore_id=UUID} → 201
  Step 2: GET /ripartizioni/{id_returned} → body contiene importo=100.50
  Step 3: SELECT stato FROM ripartizioni WHERE id={id_returned} → "PENDING"

[NEG] POST /ripartizioni importo=0 (3 step):
  Step 1: POST /ripartizioni body {importo=0, autore_id=UUID} → 400 con error.code="IMPORTO_NON_VALIDO"
  Step 2: Verify body contiene error.code="IMPORTO_NON_VALIDO" AND error.message contiene "importo deve essere > 0"
  Step 3: SELECT COUNT(*) FROM ripartizioni WHERE autore_id=UUID → invariato (record NON inserito)
```

**Multi-session TC pattern (ADR-010, opzionale per lock-free / async verification):**

Per TC che richiedono osservazione concorrente (lock-free verification, async side-effect propagation, race detection):

- Step naming convention: `[SESSION A] action` / `[SESSION B] observe`
- Session B = monitor passivo, NON deve influenzare Session A (read-only queries, no write)
- Timing window esplicita: "entro X secondi dall'azione" / "dopo X secondi di stabilizzazione"
- Cleanup esplicito: ogni sessione chiude connessioni/timer alla fine del TC

Trigger: `pg_locks`, `sessione parallela`, `concurrent`, `lock-free`, `CONCURRENTLY`, `CloudWatch alarm propagation`, `monitor durante`, `osservazione asincrona`.

Marca i TC multi-session con `source_ref="multi_session"`.

**Tracciabilità obbligatoria:** ogni TC deve avere il `matrix_row_id` come **campo schema separato** dell'oggetto TC (in `TC_DRAFT.md`/`TC_DRAFT.json`), **non** dentro il testo della Description. J3 legge il campo schema, non fa parsing del testo.

**Description = SOLO testo semantico (40-400 char, 1-3 frasi parlanti).**
Una persona QA che apre il TC in Xray legge la Description per capire **cosa fa il test**, non per leggere metadata di tracciabilità. Vietato includere `matrix_row_id`, `entity:`, `field:`, ID di matrice, prefissi tipo "matrix_row_id: A-001" nel testo della Description.

La Description risponde a: "cosa verifica questo TC, in linguaggio comprensibile?".
Esempi validi:
- `"Verifica che il subject dell'email di accesso corrisponda alla stringa approvata dal copy SIAE."`
- `"Visitando un URL del magic link con token in formato non-UUID il sistema mostra la pagina di errore standard e non crea sessione."`
- `"Una seconda POST per lo stesso utente deve invalidare i token precedenti (rotation) e generare un nuovo token consumabile."`

Esempi invalidi:
- ❌ `"matrix_row_id: A-001 | entity: MAGIC_LINK_EMAIL | field: subject"` (solo metadata, non semantica)
- ❌ `"Test per A-001"` (no contesto)
- ❌ `"Verifica subject"` (troppo generico)

Esempio di struttura TC corretta:
```
Titolo:        [POS] CATEGORY = "F" → migrazione come feature
matrix_row_id: A-001                                      ← campo schema separato
entity:        GENERAL_DATA                               ← campo schema separato
field:         CATEGORY                                   ← campo schema separato
Description:   "Verifica che un record con CATEGORY 'F' venga migrato come tipo
                feature nel nuovo sistema, conservando i campi correlati."
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
Gate #2 (J3+J4+J6) leggera' da `docs/qa/{STORY_ID}/TC_DRAFT.md` — garantisce dati integri anche dopo compattazione.

**Default deterministico per ogni TC generato (Phase 4b):**
- `Automazione = N` (no test automatizzato esistente — il developer aggiorna a `Y` solo se conferma esistenza di test JUnit/vitest/pytest che coprono esattamente questo TC)
- `NRT = Y` (default Non-Regression Test)

**Riepilogo prima del gate:** mostra la tabella compatta al developer (TC-ID, titolo, matrix_row_id, test_type, Automazione, NRT). Il developer puo' sovrascrivere `Automazione` e `NRT` **solo dopo Gate #2 PASS**, pre-export. Ogni override viene registrato nel campo `developer_overrides` del `coverage_certificate.json` (lista di `{tc_id, field, old_value, new_value}`).

---

### Phase 4c — Gate #2: TC vs Matrix Verification [bloccante — post-generazione]

Dopo la generazione (Phase 4b), lancia **J3 + J4 + J6 in parallelo** con Agent tool.
Verificano la bijection TC↔M_FINAL, la specificità dei TC e l'**executability dei TC negativi**.

<EXTREMELY-IMPORTANT>
FERMATI. Stai per procedere a Phase 4d senza Gate #2?

J3, J4 e J6 operano QUI sui TC prodotti:
  - J3 verifica che ogni riga `manual` di M_FINAL sia diventata un TC concreto
  - J4 verifica che ogni TC abbia dati di test specifici (non generici)
  - J6 verifica che ogni TC `[NEG]` (e `[EDGE]` avverso) sia eseguibile da QA manuale (R1-R5)
Invoca J3, J4 e J6 con Agent tool nello STESSO turno. Non sequenzialmente.
Un'autovalutazione interna di Claude NON è Gate #2.

**Criterio verificabile:** l'esecuzione di Gate #2 deve produrre 3 tool call result di Agent tool visibili nella conversazione. Se non puoi mostrare questi tool call result, Gate #2 non è stato eseguito — è stato simulato.

**Input per J3, J4 e J6:** leggi M_FINAL da `docs/qa/{STORY_ID}/MFINAL.md` e i TC da `docs/qa/{STORY_ID}/TC_DRAFT.md` tramite Read tool — non usare il context direttamente, i file garantiscono dati integri dopo eventuale compattazione.
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
Verifica leggendo i CAMPI SCHEMA dei TC (matrix_row_id, entity, field, test_type) — NON
fare parsing del testo della Description (Description e' testo semantico libero, non
metadata).
  1. Ogni riga di M_FINAL con executability_class='manual' ha esattamente 1 TC con
     tc.matrix_row_id corrispondente
     (righe orfane = righe manual senza TC)
  2. Ogni TC ha un tc.matrix_row_id valido che esiste in M_FINAL
     (TC orfani = TC senza riga matrice)
  3. Per ogni TC: tc.entity == M_FINAL[matrix_row_id].entity e
     tc.field == M_FINAL[matrix_row_id].field (consistenza campi schema)
Elenca righe orfane, TC orfani e inconsistenze entity/field. Soglia: 100% bijection.
Output: GIUDICE J3 | PASS/FAIL | RIGHE_ORFANE: [lista] | TC_ORFANI: [lista] | INCONSISTENZE: [lista]
```

#### J4 — Specificity Check

```
Sei un QA Judge specializzato in qualità e specificità dei TC.
Input: M_FINAL + TC GENERATI (serializzati sopra)
Per ogni TC, recupera la riga M_FINAL corrispondente (via tc.matrix_row_id) e verifica:
  1. Passi/precondizioni contengono i valori concreti dalla colonna "condition"
     (es. se condition = "'F'→feature" il TC deve menzionare il valore "F")
  2. Expected result è verificabile e non generico (non "dovrebbe funzionare")
  3. Precondizioni sono sufficienti per eseguire il test senza ambiguità
  4. **Description e' SEMANTICA E PARLANTE**: 40-400 char, 1-3 frasi che descrivono
     il comportamento testato in linguaggio comprensibile. FAIL se la Description:
       - contiene metadata di tracciabilita' (`matrix_row_id`, `entity:`, `field:`)
       - e' troppo generica ("verifica il campo", "test sul subject")
       - duplica il titolo senza aggiungere informazione
       - e' vuota o sotto 40 char
Elenca TC con specificità insufficiente o description non semantica. Soglia: 75%.
Output: GIUDICE J4 | PERCENTUALE: XX% | PASS/FAIL | TC_GENERICI: [lista con motivazione e categoria: "valori_assenti" | "expected_generico" | "description_non_semantica" | "description_con_metadata"]
```

#### J6 — Negative Executability Check (R1-R5)

```
Sei un QA Judge specializzato in executability dei TC negativi per QA manuale.
Input: M_FINAL + TC GENERATI (serializzati sopra) + sezione "Guardrail TC Negativi (R1-R5)" dalla SKILL.md
Atteggiamento: scettico — assumi che ogni [NEG] sia non-eseguibile finche' non passa R5.

Per ogni TC con prefisso `[NEG]` (e ogni `[EDGE]` con condition avversa che presuppone
input fuori dominio normale), applica le 5 regole R1-R5:

R1 (no system mutation): la PRECONDIZIONE include modifiche a:
   template / SMTP / CDN / sender / DB INSERT-UPDATE / config / feature flag /
   implementazione errata? Se SI → FAIL R1.

R2 (no DB direct action): le ACTION (non expected) contengono SELECT/INSERT/UPDATE/DELETE
   SQL? Se SI → FAIL R2. Eccezione: SELECT in expected_result e' permessa se l'ambiente
   QA documenta un tool SQL read-only (in dubbio = FAIL R2).

R3 (no fault injection): la precondizione richiede servizio down, mock/stub, race condition
   precisa, rollback transazione parziale, retry orchestrato? Se SI → FAIL R3.

R4 (no mirror negativo): il NEG e' "campo statico di configurazione gia' coperto dal
   POS, nessun input path autonomo"? Se SI → FAIL R4 con riferimento al POS matrix_row_id.

R5 (checklist precondizione): rispondi SI a tutte e 3:
   (a) producibile con browser/Postman/email-client?
   (b) precondizione impostabile senza modificare sistema?
   (c) action e' UI/API/email, non SQL diretto?
   Se anche una NO → FAIL R5.

Output per ciascun TC NEG/EDGE: verdict PASS / FAIL_R<n> con motivazione 1 riga.

Soglia: 100% dei TC manuali NEG/EDGE devono passare R1-R5.
Output: GIUDICE J6 | TC_VALUTATI: N | PASS: N | FAIL: N | LISTA_FAIL: [
  {tc_id, matrix_row_id, rule_violated, motivazione, routing_suggerito (automated-only|eliminated)}
]
```

#### Comportamento Gate #2

```
1. Lancia J3, J4 e J6 in parallelo (Agent tool, stesso turno — 3 tool_use visibili)
2. Valuta:
   - J3 FAIL → rigenerazione selettiva solo per righe `manual` orfane (Phase 4b parziale)
   - J4 < 75% → riformulazione selettiva dei TC generici identificati
   - J6 FAIL → per ogni TC fallito: applica il routing_suggerito da J6
     * automated-only → riclassifica la riga M_FINAL (executability_class = "automated-only",
       rule_violated = "Rn"), elimina il TC manuale da TC_DRAFT, aggiungi entry
       "automated_only_note" in TC_DRAFT.md
     * eliminated → rimuovi la riga da M_FINAL (con backup .bak), elimina il TC,
       registra eliminazione in coverage_certificate.json
3. Rilancia SOLO i judge falliti con:
   "Nel run precedente hai trovato questi problemi: [lista].
   Valuta i TC aggiornati: [lista TC nuovi]."
4. Max 2 iterazioni per gate, poi escalation all'utente.
   Per J6 specificamente: se dopo 2 iterazioni esistono ancora TC FAIL, NON si esporta —
   l'export di TL non eseguibili e' un fallimento di workflow, non un compromise.

Escalation asimmetrica: se un solo judge (J3, J4 o J6) supera il max di iterazioni mentre
gli altri sono già PASS, l'escalation riguarda solo il judge fallito. Mostra il GATE #2
REPORT parziale e chiedi: "J<n> non converge dopo 2 iterazioni — vuoi procedere
con questo gap o rifai la generazione da zero per le righe coinvolte?"
Per J6 (executability): il default e' BLOCK, non procedere — chiedi esplicita conferma
del developer che accetta TL con TC non eseguibili (registralo nel certificate come
`developer_overrides[].field = "j6_bypass"`).

Se J3 PASS, J4 PASS e J6 PASS: procedi a Phase 4d (J5 Final Audit)
```

#### Formato GATE #2 REPORT

```
GATE #2 REPORT
──────────────
J3 Bijection:      N/N righe `manual` coperte (100%) | N TC orfani   [PASS ✅ / FAIL ❌]
J4 Specificità:    XX% TC con dati concreti                          [PASS ✅ / FAIL ❌]
J6 Executability:  N/N TC [NEG]/[EDGE] eseguibili da QA manuale      [PASS ✅ / FAIL ❌]

Righe `manual` orfane (senza TC): [lista]
TC orfani (senza riga matrice): [lista]
TC generici da riformulare: [lista con motivazione]
TC non eseguibili (R1-R5 violati): [
  {tc_id, matrix_row_id, rule_violated, routing_suggerito}
]
Routing post-J6 applicato:
  - automated-only riclassificati: N
  - eliminated rimossi: N
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

**Artefatti prodotti in Phase 5:**

1. **`docs/qa/{STORY_ID}/RTD-XXX_TC.csv`** — CSV Xray pulito. Contiene SOLO TC manuali
   eseguibili (entry con `kind=test_case` in TC_DRAFT). Nessun commento, nessuna riga
   `[AUTOMATED-ONLY]`, nessuna riga `[ELIMINATED]`. Importabile direttamente in Xray
   senza errori di parsing.
2. **`docs/qa/{STORY_ID}/automated_only_notes.md`** — file di reportistica per lo
   sviluppatore. Contiene le entry `kind=automated_only_note` di TC_DRAFT, raggruppate
   per regola violata (R1/R2/R3) e per entita'. Ogni entry indica `matrix_row_id`,
   motivo, `automation_suggestion`, `original_condition`. Non importato in Xray.
3. **`docs/qa/{STORY_ID}/coverage_certificate.json`** — gia' scritto in Phase 4d.
   Include la sezione `eliminated_rows` con le righe R4 rimosse e la motivazione.

**Anti-pattern (BLOCCATO):** non concatenare le 3 sezioni in un unico CSV con righe
commento `#`. L'importer Xray non gestisce in modo affidabile le righe commento e
puo' importarle come TC vuoti, generando errori o TC malformati nel progetto Jira.

**Tier 1 (MCP):**
1. Crea ogni TC `kind=test_case` in Xray via MCP — le `automated_only_note` NON vengono
   create in Xray, restano solo nel file `.md`
2. Ogni TC creato ottiene automaticamente una chiave Jira (es. `PROJ-456`) — registrala nella mappatura (vedi Passo post-export)
3. Dopo l'esecuzione dei test, aggiorna il Test Execution con i risultati

**Tier 2 (Documento):**
- Output `RTD-XXX_TC.csv` semicolon-separated, solo TC eseguibili — indipendentemente dalla disponibilità MCP
- `automated_only_notes.md` come file separato per il developer
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
| "Lo step 2 'verify response code' basta per i POST" | No. Per mutating 2xx serve read-back (GET/SELECT) o assert body fields. Response code da solo conferma che la chiamata e' arrivata, non che il record esista nello stato atteso. |
| "I lookup li espando tutti, e' piu' rigoroso" | Esplosione completa solo per spec con mapping esplicito campo→valore→esito. Per lookup senza esiti distinti documentati, una POS rappresentativa basta — risparmia 2-5 righe per campo senza perdere copertura semantica. |
| "Il NEG e' il POS al contrario, basta cambiare il valore atteso" | Spesso il "contrario" del POS richiede di modificare il sistema (template/config/DB). Quel NEG NON e' eseguibile dal QA manuale — e' un mirror, e va eliminato o convertito in automated-only. Vedi R4 nei Guardrail TC Negativi. |
| "Per generare il NEG basta che il QA modifichi il template/config" | Il QA manuale NON ha accesso a template engine, SMTP config, deploy properties, feature flag. Modificare il sistema come precondizione = R1 violata. Routing corretto: automated-only con suggerimento snapshot/unit test. |
| "Il NEG sul DB lo faccio mettere un dato corrotto con SELECT/INSERT" | SELECT/INSERT/UPDATE come Action o Precondizione non sono passi eseguibili da QA manuale (R2). Spostare SELECT in expected (verifica su monitoring tool) o riclassificare automated-only se serve setup DB. |
| "Per testare il timeout SMTP gli faccio spegnere il servizio" | Fault injection (R3): servizi down, mock stub, race condition arbitraria non sono producibili dal QA manuale. Coprire con chaos-test o integration-test. |
| "J6 e' troppo rigoroso, esporto con qualche TC non eseguibile" | Una TL con TC non eseguibili e' la causa identificata dall'analisi RTD-108: 54% dei NEG non eseguibili dal QA. Esportare TL non eseguibili significa che il QA non puo' fare il lavoro e i bug passano in produzione. Default J6: BLOCK. Per bypass serve consenso esplicito del developer registrato come `j6_bypass` in `developer_overrides`. |
| "Faccio Matrix A/B senza executability_class, poi vediamo in Phase 4b" | Senza classificazione upfront, Phase 4b genera TC che J6 rigettera' — costo doppio (rigenerazione + cleanup). La classificazione in Matrix A/B costa pochi token e azzera il rework. |
| "Metto matrix_row_id in Description, cosi' J3 lo trova subito" | J3 legge il campo schema `tc.matrix_row_id`, non fa parsing del testo. La Description e' visibile al QA in Xray: deve essere semantica, non metadata. Metadata in Description = J4 FAIL "description_con_metadata". |
| "Description = 'matrix_row_id: A-001 \| entity: X \| field: y' basta per tracciabilita'" | No: il QA che apre il TC in Xray legge la Description per capire COSA testa. "matrix_row_id: A-001" gli dice nulla. La tracciabilita' vive nei campi schema separati; la Description e' linguaggio naturale 40-400 char. |

---

## CHECKLIST DI VERIFICA

Vedi [XRAY-TEMPLATES.md](XRAY-TEMPLATES.md) sezione "Checklist di Verifica" per la checklist completa.
**Non riesci a spuntare tutte le caselle? Il workflow non e' completo. Ricomincia dalla fase bloccata.**

---

## VINCOLI NON NEGOZIABILI

0. **Phase 0 e' sempre la prima phase** — nessun AC viene letto senza aver prima inferito il tipo e lanciato le domande del tree contestuale; la Req Profile Card deve essere prodotta prima di Phase 1
1. **Nessun Test Case senza riga M_FINAL corrispondente** — ogni TC è tracciabile a una riga della Coverage Matrix (matrix_row_id obbligatorio come **campo schema separato** dell'oggetto TC; **vietato** nel testo della Description, che e' riservata alla descrizione semantica del comportamento testato)
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
15. **Mutating TC con status 2xx ha minimo 2 step** — action + read-back/SELECT/audit. Response code da solo NON e' side-effect verification. Mutating 4xx/5xx ha minimo 3 step (terzo step = side-effect NOT occurred).
16. **B-001/B-002 composite generate SOLO se spec ha regole composite cross-field** — se la spec ha solo vincoli single-field, M_B non contiene composite_happy/composite_worst. Generare B-001/B-002 senza regole reali = falsi TC che non testano nulla.
17. **Cross-temporal/cross-event rules generano almeno 1 EDGE per replay E 1 EDGE per out-of-order** — se la spec menziona idempotency/sequenza, Matrix B deve esplodere su entrambi (no shortcut "tanto è idempotente").
18. **Multi-session TC usano tag espliciti `[SESSION A]/[SESSION B]`** — un TC concurrent senza tag e' un TC sequenziale travestito.
19. **Priorita' regole su conflitto e' deterministica** — boolean+valore_fisso → priorità valore_fisso, no doppio TC su POS(false)/NEG(false).
20. **Ogni TC `[NEG]` (e ogni `[EDGE]` con condition avversa) deve passare R1-R5** — no system mutation, no DB direct action, no fault injection, no mirror negativo, checklist precondizione PASS. Le righe M_FINAL che violano R1/R2/R3 hanno `executability_class="automated-only"` (nessun TC manuale, output in `automated_only_notes.md` SEPARATO dal CSV); R4 produce `executability_class="eliminated"` (riga rimossa, nota in `coverage_certificate.json`). J6 in Gate #2 e' bloccante: senza J6 PASS l'export non parte (TL non eseguibile e' un fallimento di workflow). Vedi sezione "Guardrail TC Negativi (R1-R5)" e ADR-013.
21. **Il CSV Xray contiene SOLO TC eseguibili** — nessuna riga commento `#`, nessuna entry `[AUTOMATED-ONLY]`, nessuna entry `[ELIMINATED]`. Le note tecniche vivono in `automated_only_notes.md` e `coverage_certificate.json`. L'importer Xray puo' creare TC malformati o errori se trova righe commento.

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
**Phase che richiedono Write tool:** Phase 1.5 (`docs/qa/{STORY_ID}/MFINAL.md`), Phase 4b (`docs/qa/{STORY_ID}/TC_DRAFT.md`), Phase 4d (`docs/qa/{STORY_ID}/coverage_certificate.json`), Phase 5 (`docs/qa/{STORY_ID}/RTD-XXX_TC.csv`, `docs/qa/{STORY_ID}/automated_only_notes.md`, `docs/qa/{STORY_ID}/xray_id_mapping.json`).
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
