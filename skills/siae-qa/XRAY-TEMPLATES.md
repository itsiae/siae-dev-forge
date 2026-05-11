# SIAE QA — Template Xray e Esempi Test Case

## Table of Contents

- [Tabella Segnali Req Typing](#tabella-segnali-req-typing)
- [Template Req Profile Card](#template-req-profile-card)
- [Formato Test Case Step-Based](#formato-test-case-step-based)
- [Prefissi di Categoria (obbligatori)](#prefissi-di-categoria-obbligatori)
- [Regola Multi-Step](#regola-multi-step)
- [Riepilogo Copertura](#riepilogo-copertura)
- [Template M_FINAL (output Phase 1.5)](#template-m_final-output-phase-15)
- [Convenzione naming entity (ADR-004)](#convenzione-naming-entity-adr-004)
- [Domande di Elicitazione](#domande-di-elicitazione)
- [Mappatura ID Sequenziali e Chiavi Jira Xray](#mappatura-id-sequenziali-e-chiavi-jira-xray)
- [Tier 3 CSV Export](#tier-3-csv-export)
- [Checklist di Verifica](#checklist-di-verifica)

---

## Tabella Segnali Req Typing

| Tipo | Segnali (summary, AC, description, label, stack) |
|------|--------------------------------------------------|
| **Frontend (FE)** | "componente", "pagina", "form", "UI", "Vue", "Angular", "React", "click", "visualizza", "render", "responsive" |
| **Backend Microservice (BE)** | "API", "endpoint", "service", "REST", "controller", "Spring", "Lambda", "validazione", "business rule" |
| **ETL / Data Pipeline** | "Glue", "PySpark", "pipeline", "trasformazione", "bronze", "silver", "gold", "job", "ETL", "medallion" |
| **Database** | "migration", "schema", "query", "tabella", "indice", "DDL", "flyway", "liquibase" |
| **Auth / Security** | "login", "logout", "ruolo", "permesso", "token", "autenticazione", "RBAC", "JWT" |
| **Integration / External** | "webhook", "chiamata esterna", "API terza parte", "evento", "Kafka", "SQS", "notifica" |

**Confidence (formula deterministica):**

```
confidence = min(100, 30 * signal_count_strong + 15 * signal_count_weak)
```

- Un segnale e' "strong" se appare nel summary o nello stack del progetto (alta visibilita').
- Un segnale e' "weak" se appare solo in description/commenti/AC.

| Band | Range | Esempio |
|------|-------|---------|
| **HIGH** | confidence >= 90 | 3+ strong, o 2 strong + 2 weak |
| **MEDIUM** | 60 <= confidence < 90 | 2 strong, o 1 strong + 2 weak |
| **LOW** | confidence < 60 | 0 strong, 1-2 weak, o ambiguo |

---

## Template Req Profile Card

```
REQ PROFILE:
  Tipo:       [Frontend / BE / ETL / Database / Auth / Integration]
  Confidence: [HIGH / MEDIUM / LOW]
  Segnali:    [elenco segnali usati dall'inferenza]
  Stack:      [tecnologie rilevate]
```

Dopo le domande del tree (0c), aggiorna la card:

```
REQ PROFILE (aggiornato):
  Tipo:       [tipo]
  Scenari L1: [lista scenari flusso principale]
  Scenari L2: [lista edge case contestuali]
  Scenari L3: [lista scenari integrazione/dipendenze]
```

---

## Formato Test Case Step-Based

Per ogni scenario della matrice (4a), genera 1+ Test Case con questo formato:

| Campo | Contenuto |
|-------|-----------|
| ID | Numero sequenziale (1, 2, 3...) |
| Test Type | `Manual` |
| Team Competenza | `QA` |
| ID JIRA Story | `{PROJ-XXX}` — **obbligatorio** |
| User Story Description | Summary della Story Jira |
| Scenario (descrizione) | Titolo del Test Case — prefisso obbligatorio: `[POS]`, `[NEG]`, `[EDGE]`, `[ROLE]` — derivato dal `test_type` della riga M_FINAL |
| Step scenario | Numero step (1, 2, 3...) |
| Action | Cosa fa l'utente/sistema in questo step |
| Expected Result | Risultato atteso per questo step — **nel CSV il nome colonna e' `Expceted Result`** (typo storico del template importatore Xray SIAE) |
| Data | Dati di test specifici (vuoto se non necessario) |
| Automazione | `Y` se esiste test automatizzato per questo TC, `N` altrimenti |
| NRT | `Y` (default — il TC e' un Non-Regression Test) |

---

## Prefissi di Categoria (obbligatori)

Ogni TC ha prefisso esplicito derivato da `test_type` della riga M_FINAL:

- `[POS]` = scenario positivo (happy path, dato valido, valore in lookup)
- `[NEG]` = scenario negativo (input non valido, dipendenza assente, dato fuori lookup)
- `[EDGE]` = edge case (limite di range, vuoto, null accettato, formato boundary)
- `[ROLE]` = scenario di ruolo/permesso (utente con visibilita' o azione distinta)

**Non sono ammessi TC senza prefisso.** Un TC senza prefisso fallisce J3/J4.

---

## Regola Multi-Step

Stesso ID = stesso Test Case con step multipli. I metadati (tipo, team, Jira, descrizione scenario) si ripetono **solo nella prima riga**. Le righe successive dello stesso TC hanno solo: ID, step numero, Action, Expected Result.

---

## Riepilogo Copertura

**Mostrato in Phase 4a (input M_FINAL) e replicato pre-export (Phase 5).**

```
Riepilogo copertura (da M_FINAL):
  POS:        N TC
  NEG:        N TC
  EDGE:       N TC
  ROLE:       N TC
  TOTALE:     N TC

Entita' coperte: [lista entita' presenti in M_FINAL]
Lookup tables coperte: [lista lookup con # valori]
```

I valori N sono `count` dei `matrix_row_id` di M_FINAL con `test_type` corrispondente.
Il developer puo' modificare i campi `Automazione` e `NRT` dei singoli TC (default: `Automazione=N`, `NRT=Y`) — mai modificare la distribuzione M_FINAL pre-export senza ripassare Gate #1.

---

## Template M_FINAL (output Phase 1.5)

**M_FINAL e' la Coverage Matrix consolidata da Phase 1.5 (Matrix A+B+C dopo Gate #1).**
Ogni riga = 1 TC atteso in Phase 4b.

Schema esatto (colonne fisse, nomi case-sensitive):

| Colonna | Tipo | Esempio | Note |
|---------|------|---------|------|
| `matrix_row_id` | string univoco | `A-001`, `B-014`, `C-003`, `J5-gap-G01` | Prefisso: A=Matrix A, B=Matrix B, C=Matrix C, J5-gap=aggiunto post-J5 |
| `entity` | string | `GENERAL_DATA` | Entita' della spec (CSV section, classe, tabella) |
| `field` | string | `CATEGORY` | Campo o regola composita (`field_a + field_b` per regole) |
| `condition` | string | `"F" → feature` | Condizione concreta con valore (no placeholder) |
| `test_type` | enum | `POS` \| `NEG` \| `EDGE` \| `ROLE` | Determina il prefisso titolo del TC |
| `source_ref` | string | `AC-03`, `developer input`, `J5-gap`, `pairwise_ipog` | Tracciabilita' all'origine della riga |

**Persistenza:** `docs/qa/{STORY_ID}/MFINAL.md` (markdown table) + schema JSON in `reference/schemas/m_final.schema.json`.

**Regole di esplosione**: vedi `SKILL.md` Phase 1.5 sezione "Regole di esplosione (da campo a righe di matrice)".

### Convenzione naming `entity` (ADR-004)

Il campo `entity` segue una gerarchia di scelta deterministica:

1. **Se la spec ha tabelle DB o CSV section name** (es. `GENERAL_DATA`, `TITLES`, `CONTRIBUTORS`, `RIPARTIZIONI_RAW`): usa il nome **as-is** in SCREAMING_SNAKE_CASE. Mantenere il nome originale della spec.

2. **Altrimenti** (REST resource, business entity senza section name): usa il **nome logico singolare in PascalCase**. Esempi validi: `Opera`, `Ripartizione`, `Utente`, `Contratto`.

3. **Mai usare** come `entity`:
   - Nome endpoint: `POST /opere`, `POST_/opere`
   - Nome metodo: `createOpera`, `deleteOpera`
   - Plurale di resource: `opere`, `utenti`, `contratti`
   - Lowercase: `opera`, `ripartizione`

**Eccezioni esplicite (non sono violazioni):**
- `GENERAL_DATA` (CSV section): caso 1, mantenuto in SCREAMING_SNAKE_CASE.
- `EVERGREEN+EXPIRY` (composite field name): non e' un valore di `entity`, e' un valore della colonna `field`. La regola entity non si applica.

**Test sintattico:**

```python
# entity valida:
re.match(r'^[A-Z][A-Z0-9_]*[A-Z0-9]$', entity)  # SCREAMING_SNAKE_CASE
# OPPURE
re.match(r'^[A-Z][a-zA-Z0-9]*$', entity)  # PascalCase

# entity INVALIDA:
entity.startswith(('POST', 'GET', 'PUT', 'DELETE'))  # nome endpoint
entity.endswith(('s', 'i'))  # plurale (heuristic; vedi eccezioni esplicite)
entity == entity.lower()  # tutto lowercase
```

---

## Domande di Elicitazione

Le domande di elicitazione sono gestite esclusivamente da `reference/question-trees.md` durante Phase 0c (Smart Req Typing).
**Non duplicare alberi di domande in questo file.**

Eccezione: in Phase 4a, l'unica domanda permessa al developer e':
> "La matrice M_FINAL ha {N} righe, stimati {N} TC. Ci sono scenari specifici dal dominio (business knowledge) non derivabili dalla struttura del documento?"

---

## Mappatura ID Sequenziali e Chiavi Jira Xray

**Passo post-export — Mappatura ID sequenziali → chiavi Jira Xray [OBBLIGATORIO se si usa siae-automation]**

Dopo l'import del CSV (o la creazione MCP), Xray assegna a ogni TC una chiave Jira propria (`PROJ-XXX`).
Questa chiave e' diversa dall'ID sequenziale usato nel CSV (`1`, `2`, `3`).

Se prevedi di usare `siae-automation` per generare test Cypress o Appium, **devi raccogliere questa mappatura** prima di chiudere la skill:

```
Mappatura TC — {STORY_ID}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ID CSV  →  Chiave Xray   Scenario
  1       →  PROJ-456      [POS] Verifica login credenziali valide
  2       →  PROJ-457      [EDGE] Login con campo vuoto
  3       →  PROJ-458      [NEG] Login con password errata
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Tier 1 (MCP):** la chiave viene restituita dalla risposta del tool di creazione — raccoglila automaticamente.
**Tier 3 (CSV):** chiedi al developer di aprire Xray dopo l'import e comunicare le chiavi assegnate. Non procedere con siae-automation finche' non hai questa mappatura.

Salva la mappatura come file persistente: `docs/qa/{STORY_ID}/xray_id_mapping.json` (schema in `reference/schemas/xray_id_mapping.schema.json`). Senza questo file, siae-automation non puo' procedere.

---

## Tier 3 CSV Export

- Genera il file CSV con separatore `;` (semicolon) — **mai virgola**
- Formato esatto: vedi `reference/xray-csv-template.md`
- Header obbligatorio in prima riga
- Mostra il CSV all'utente e spiega come importarlo: Xray → Test → Import CSV

---

## Checklist di Verifica

Prima di dichiarare la skill completata, tutte le caselle devono essere spuntate.

### Phase 0 — Smart Req Typing
- [ ] Tipo requisito inferito con formula confidence (`min(100, 30*strong + 15*weak)`)
- [ ] Req Profile Card mostrata; band HIGH/MEDIUM/LOW dichiarata
- [ ] Confidence HIGH → tree lanciato senza conferma; MEDIUM/LOW → conferma esplicita ricevuta
- [ ] Domande del tree (`reference/question-trees.md`) lanciate UNA alla volta; skippate quelle gia' rispondibili dagli AC

### Phase 1 — Lettura AC [HARD-GATE]
- [ ] Tier dichiarato esplicitamente nella pre-flight card (T1 Jira / T2 doc / T3 chat)
- [ ] AC letti da Jira (Tier 1) o validati esplicitamente dall'utente (Tier 2) o raccolti via Q&A (Tier 3)
- [ ] Story ID e titolo presenti

### Phase 1.5 — Coverage Matrix [HARD-GATE]
- [ ] Blocco serializzazione (ENTITA/LOOKUP/REGOLE/VINCOLI) mostrato e confermato
- [ ] Matrix A/B/C lanciati in parallelo con Agent tool (3 tool_use visibili)
- [ ] J1_MATRIX eseguito con Agent tool (1 tool_use visibile), risultato PASS (100% entita' coperte)
- [ ] J2_MATRIX eseguito con Agent tool (1 tool_use visibile); duplicati rimossi
- [ ] `docs/qa/{STORY_ID}/MFINAL.md` scritto su filesystem (Write tool)
- [ ] M_FINAL conforme allo schema JSON `reference/schemas/m_final.schema.json`

### Phase 2 — Test Strategy
- [ ] Confluence cercata (Tier 1) o WARNING registrato (Tier 2/3)

### Phase 3 — Test Plan
- [ ] Struttura Test Plan creata (MCP Tier 1) o presentata testualmente (Tier 2/3)

### Phase 4 — Test Case
- [ ] Phase 4a: M_FINAL mostrata; distribuzione `N POS / N NEG / N EDGE / N ROLE`
- [ ] Phase 4b: 1 TC step-based per ogni riga M_FINAL; prefisso titolo `[POS]/[NEG]/[EDGE]/[ROLE]`
- [ ] Phase 4b: `matrix_row_id` presente nel campo `Description` di ogni TC
- [ ] `docs/qa/{STORY_ID}/TC_DRAFT.md` scritto su filesystem (Write tool)
- [ ] Phase 4c Gate #2: J3 bijection PASS (100% bijection); J4 specificity PASS (>= 75%)
- [ ] Phase 4d J5 eseguito (run-once); coverage_score calcolato
- [ ] Se TC aggiunti post-J5: Gate #2 RILANCIATO sui TC aggiornati

### Phase 5 — Export
- [ ] `docs/qa/{STORY_ID}/coverage_certificate.json` scritto (schema `reference/schemas/coverage_certificate.schema.json`)
- [ ] Stato Certificate dichiarato: `FULL_PASS` / `CONDITIONAL_PASS` / `FAIL`
- [ ] Export effettuato: MCP Xray (Tier 1) OR CSV semicolon (Tier 2/3, header esatto da `reference/xray-csv-template.md`)
- [ ] `docs/qa/{STORY_ID}/xray_id_mapping.json` scritto (input per siae-automation)
- [ ] Campi `Automazione` (default `N`) e `NRT` (default `Y`) verificati con il developer; eventuali override registrati nel certificate

**Non riesci a spuntare tutte le caselle? Il workflow non e' completo. Ricomincia dalla phase bloccata.**
