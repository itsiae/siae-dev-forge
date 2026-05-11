# Design — siae-qa v2.1.0 Residual Fixes

> **REQUIRED SUB-SKILL:** `siae-writing-plans` (handoff post-approvazione)
>
> **Iterazione design:** 4 (post spec-review WARN iter 3)

## Contesto

La simulazione end-to-end della skill `siae-qa v2.0.0` su 3 golden fixture ha prodotto 3/3 PASS su validator e 4 criteria functional eval. La skill è funzionalmente Gold (43/50 scorecard), ma il **diff strutturale vs expected** ha esposto 5 ambiguità.

### I 5 Gap Effettivi (mappati su simulation report)

| ID | Gap | Sintomo osservato | Fixture |
|----|-----|-------------------|---------|
| **G1** | Over-explosion SIM da composite rules + EDGE su optional null + EDGE trim/NFC max-length non documentati | 39 rows SIM vs 25 EXP (delta +14: `DURATION=0`, `ORDER=null`, `GENRE=null`, `ISWC=null`, `TITLE 255 char`, `TITLE trim/NFC`, B-001/B-002 composite happy/worst) | `enumerative_spec` |
| **G2** | Over-explosion SIM su mandatory NEG decomposti per campo singolo (vs happy path unificato in EXP) — non ambiguità "missing EDGE frontiera bassa" come erroneamente diagnosticato in iter 1 | 15 rows SIM vs 8 EXP (EXP **contiene già** `A-003 EDGE importo=0.01`) | `functional_be` |
| **G3** | Convenzione `entity` non normativa: SIM produce `opere` (lowercase plurale endpoint), EXP usa `Opera` (PascalCase singolare logico) | `entity` mismatch 9/9 ma struttura match | `role_based` |
| **G4** | Multi-step side-effect verification per azioni mutating non prescritto in Phase 4b | SIM TC POST con 1-2 step monolitici; EXP TC con read-back/count/audit | tutti (variabile) |
| **G5** | Inferenza type-aware del valore "frontiera bassa" (decimal vs integer vs date) non specificata — riga 547 SKILL.md dice "frontiera bassa appena valida" senza definire come dedurre il tipo | Ambiguità: `> 0` su `importo` → `0.01` (decimal) o `1` (integer)? | `functional_be` (potenziale) |

## Obiettivo

Clarification patch v2.1.0 (non-breaking): edit a `SKILL.md` + `XRAY-TEMPLATES.md`, extension al validator, update sincronizzato golden fixture.

## Approccio Scelto

**Approccio A (patch puntuale).** Approccio B (DSL formale) è over-engineering; approccio C (defer) lascia debito.

## Decisioni Architetturali (ADR)

### ADR-001 — Type-aware "frontiera bassa appena valida" (G5)

La regola "frontiera bassa" di `SKILL.md` riga 547 (Phase 4b condition multi-valore) viene **estesa a Matrix Agent A** come regola di esplosione e resa **type-aware**:

| Tipo campo (dedotto da serializzazione Phase 1.5) | `> 0` produce | `>= 0` produce | `> 1000` produce |
|---|---|---|---|
| `decimal/float` | `0.01` | `0` | `1000.01` |
| `integer/long` | `1` | `0` | `1001` |
| `date` (`> 2020-01-01`) | `2020-01-02` | `2020-01-01` | — |
| `timestamp` (`> ts`) | `ts + 1s` | `ts` | — |

Il tipo viene dedotto **obbligatoriamente** dalla serializzazione Phase 1.5 (blocco `ENTITA E CAMPI: ... dominio: decimal/integer/date`). Se la spec non specifica il tipo: WARNING al developer + default `integer` (più conservativo).

### ADR-002 — Frontiera bassa POS auto-generata SOLO se vincolo è in classe "NEG-only" (G2 + risoluzione conflitto)

**Regola di priorità (risolve conflitto ADR-001 v1 / ADR-002 v1 segnalato dallo spec-reviewer):**

Un vincolo numerico genera EDGE auto **se e solo se** è **strict bound** (esclusivo): `>`, `<`, `> X AND < Y`, `IN (a,b,c)`, `NOT IN (...)`. NON genera EDGE auto se è **non-strict bound** (inclusivo): `>= X`, `<= X`, `BETWEEN X AND Y` (inclusivo per definizione SQL).

| Vincolo | Mandatory? | EDGE auto? |
|---|---|---|
| `importo > 0` (strict) | sì o no | **SÌ** → EDGE `importo=0.01` (frontiera bassa) |
| `importo >= 0` (non-strict) | sì o no | NO (0 è già nel dominio POS) |
| `DURATION >= 0` | mandatory | NO (vincolo non-strict, `0` è valido POS) |
| `account IN (A,B,C)` (strict) | — | **SÌ** → 3 POS + 1 NEG (regola lookup esistente, non cambia) |

Questa regola **risolve il caso ambiguo** `importo > 0 mandatory`: è strict → EDGE auto, ortogonalmente al mandatory flag.

### ADR-003 — Boundary EDGE per stringhe (trim/NFC/max-length) opt-in (G1 parziale)

Aggiungere riga di esplosione **opt-in**: stringhe con vincoli di length/encoding generano EDGE **solo se** la spec menziona esplicitamente uno dei termini chiave: `lunghezza max`, `max length`, `255 char`, `trim`, `whitespace`, `NFC`, `Unicode normalization`. Senza menzione esplicita: NO EDGE trim/length.

Questo chiude G1 parzialmente: i 3 EDGE `TITLE 255 char`, `TITLE trim/NFC` di `enumerative_spec` SIM erano over-explosion (spec non menziona "trim" o "255 char" — Matrix A li ha inventati). Con ADR-003 questi non vengono più generati.

### ADR-004 — Entity naming convention con eccezioni esplicite (G3)

In M_FINAL, il campo `entity` segue questa **gerarchia di scelta**:

1. **Se la spec ha tabelle DB / CSV section name** (es. `GENERAL_DATA`, `TITLES`, `CONTRIBUTORS`): usa il nome **as-is** (mantenuto in SCREAMING_SNAKE_CASE). Esempi validi: `GENERAL_DATA`, `RIPARTIZIONI_RAW`.
2. **Altrimenti** (REST resource, business entity): usa il **nome logico singolare in PascalCase**. Esempi: `Opera`, `Ripartizione`, `Utente`.
3. **Mai usare**: nome endpoint (`POST /opere`, `opere`), nome metodo (`createOpera`), plurale di resource (`opere`, `utenti`).

Eccezioni esplicite (no fixture update necessario):
- `GENERAL_DATA` (CSV section) resta — caso 1 della gerarchia.
- `EVERGREEN+EXPIRY` (composite field name): NON è entity, è `field` composito. La regola entity non si applica.

### ADR-005 — Multi-step per azioni mutating (G4) — riformulato post iter 2

In Phase 4b, ogni TC che testa un'azione mutating (HTTP `POST`/`PUT`/`PATCH`/`DELETE`, SQL `INSERT`/`UPDATE`/`DELETE`, CSV write) deve avere **minimo 2 step**:

- **Step 1 — Action:** eseguire l'operazione mutating con dati concreti.
- **Step 2 — Side-effect verification:** read-back (`GET /resource/{id}` o `SELECT ... WHERE id = ...`) o count (`SELECT COUNT(*)`) o audit log query. **Response code da solo NON è sufficiente** come step 2 per le azioni mutating, salvo che il response code 2xx includa esplicitamente il body con i campi creati (in tal caso lo step 2 può essere "assert body fields == expected").

**Per status 4xx/5xx (error mutating):** serve step esplicito di **side-effect NON occurred**: `SELECT COUNT(*) → invariato`, `GET /resource/{id} → 404`, audit log assente.

**Verifica empirica dei golden v2.0.0 (iter 2 spec-review):**

| Fixture | TC mutating 2xx con read-back/SELECT? | TC mutating 4xx con side-effect-not-occurred? |
|---|---|---|
| `enumerative_spec` (CSV migration) | sì, 25/25 TC hanno step 2 con verifica row in target o DLQ | DLQ NEG già conformi |
| `functional_be` | sì, 5/5 POS mutating con SELECT/GET | 1/4 NEG mutating con SELECT COUNT (`importo=0`); 3 NEG mancano step "record non inserito" |
| `role_based` | sì, 6/6 POS mutating con read-back | 2/3 NEG mutating con verifica side-effect-not (`editor DELETE 403`, `viewer POST 403`); 1 mancante (`viewer DELETE 403`) |

**Scope concreto ADR-005 (recalibrato):** espandere **4 TC error mutating mancanti** (3 in `functional_be` + 1 in `role_based`). `enumerative_spec` già conforme. Stima precedente (~12 TC) era sovradimensionata 3x.

**Backward compat:** ADR-005 NON degrada il livello dei golden esistenti (response code da solo non basta). I golden 2xx attuali già fanno read-back/SELECT e restano canonici.

### ADR-007 — Unificazione POS lookup + collapse NEG per-field (G2 effettivo)

**Diagnosi corretta (post spec-review iter 2):** l'over-explosion `functional_be` (15 vs 8) e parzialmente `enumerative_spec` deriva da:
- **POS lookup decomposed** in SIM: ogni valore lookup → 1 POS separata; in EXP: 1 POS "happy path" rappresentativa (con campi nominali) + 1 POS extra solo se il valore distinto genera flusso semanticamente diverso.
- **NEG per-field decomposed** in SIM: 1 NEG per ogni campo mandatory mancante; in EXP: 1 NEG rappresentativa "body malformato" o "campo obbligatorio mancante" che copre tutti i campi.
- **B-001/B-002 composite happy/worst** sempre presenti in SIM (regola attuale `SKILL.md:370-372`); in EXP solo se la spec ha effettivamente regole composite multi-campo non-banali.

**Regole nuove Matrix A (operazionalizzazione):**

1. **POS lookup unification:** per campo lookup enumerato con N valori, generare:
   - 1 POS rappresentativa (primo valore in ordine sintattico, usato in tutti i TC come "happy path") con `source_ref="lookup_repr"`.
   - 1 POS extra per ogni valore che genera **comportamento downstream distinto** documentato nella spec (es. CATEGORY `F`→`feature`, `S`→`serie`: comportamenti distinti → 2 POS).
   - 1 NEG "fuori lookup".
   - Esempio: `CATEGORY F/S/null (Documentary)` → SIM v2.0.0 produce 3 POS+1 NEG; v2.1.0 produce 2 POS (`F`, `S`) + 1 POS `null→Documentary` se documentato + 1 NEG. Se solo `F/S` sono "documentati con esiti distinti": 2 POS+1 NEG (delta -1).
   - **Trigger di esplosione completa (test sintattico operazionale):** se la spec contiene un **mapping esplicito campo→valore→esito** (es. tabella con colonne `Lookup enumerato: X, Y, Z` + colonna `Esito downstream:` o testo "il valore X mappa a entità Y nel sistema di destinazione"), allora ogni valore = 1 POS distinta (esplosione completa è il default per spec di migrazione/lookup table). Indicatori sintattici: tabella markdown con header `| Campo | Lookup | Mapping |`, oppure sezione "Mapping CSV → Target" con elenco riga-per-riga.

2. **NEG per-field collapse:** per campi mandatory dello stesso entity, se la spec dichiara il comportamento errore in modo **simmetrico** (stesso status code + stesso pattern errore: `field X is required`), generare **1 sola NEG rappresentativa** con `condition="<primo campo mandatory>=null"` e `source_ref="mandatory_collapsed"`. Se la spec dichiara errori asimmetrici (es. `autore_id` → `404 author not found`, `opera_id` → `400 invalid format`), generare 1 NEG per ogni classe-errore distinta.
   - Esempio: SIM `functional_be` v2.0.0 produce NEG per `autore_id`, `opera_id`, `importo`, `stato_iniziale`, `body malformato`; v2.1.0 collassa `autore_id missing/opera_id missing` in `mandatory_collapsed` (stessa 400 validazione), mantiene `autore_id 404` (errore semantico diverso), `importo<0` (regola business), `body malformato`. Delta: -2 NEG.

3. **B-001/B-002 composite suppression:** generare `composite_happy` e `composite_worst` (Matrix Agent B) **solo se** la spec ha ≥1 regola composita esplicitamente definita (cross-field constraint, non semplice combinazione di vincoli indipendenti). Spec con solo regole single-field → nessuna B-001/B-002.

**Effetto stimato sui delta:**

| Fixture | EXP | SIM v2.0.0 | SIM v2.1.0 atteso (ADR-002/003/004/007) | Delta v2.1.0 |
|---|---:|---:|---:|---:|
| enumerative_spec | 25 | 39 | 24-26 (rimosso EDGE trim/length/DURATION=0 da ADR-003 [-3]; **B-001/B-002 NON generate perché spec senza composite rules cross-field — coerente con ADR-007 rule #3 [-2]**; lookup non collassati perché spec contiene mapping esplicito campo→valore→esito) | 0..+1 |
| functional_be | 8 | 15 | 9-10 (NEG decomposed → 1 NEG `mandatory_collapsed` [-2]; POS extra rimossi [-2]; B-001/B-002 NON generate perché spec senza composite cross-field [-2]) | +1..+2 |
| role_based | 9 | 9 | 9 (ADR-007 non si applica: tutti ROLE, no lookup, no NEG per-field) | 0 |

### ADR-006 — Validator warning channel formalizzato

`validate_outputs.py` riceve nuovo livello di output `WARN` (oltre `PASS`/`FAIL`):

- Stampa: `[WARN] <check_name>: <details>` su stderr.
- Exit code: 0 se solo WARN (no FAIL). Exit code 1 solo se almeno 1 FAIL.
- Nuovo check (v2.1.0, livello WARN): `check_neg_numeric_has_edge_low(m_final)` — se esiste row con `test_type=NEG` e `condition` matcha pattern `(>|<) [0-9]+`, cerca row con `test_type=EDGE` su stesso `(entity, field)` con valore alla frontiera. Mancante → WARN (non FAIL).

## Componenti Toccati (corretto post-review)

| File | Righe target | Tipo modifica | Effort |
|------|--------------|---------------|--------|
| `skills/siae-qa/SKILL.md` | 297-306 (tabella esplosione), 547 (frontiera bassa), **790-810** (Anti-Razionalizzazione — verificato post iter 2), **821-838** (Vincoli — verificato post iter 2) | 5 edit tabella + 2 ADR text + 2 anti-razionalizzazione + 1 vincolo + version bump 2.0.0→2.1.0 + changelog | M |
| `skills/siae-qa/XRAY-TEMPLATES.md` | sezione "Template M_FINAL" | Inserire ADR-004 entity naming gerarchia | S |
| `skills/siae-qa/reference/scripts/validate_outputs.py` | `_report()` + main | Nuovo livello WARN; nuovo check `check_neg_numeric_has_edge_low()` | S |
| `evals/eval-sets/siae-qa/golden/role_based/expected_*.json` | tutti | `entity: "opere" → "Opera"` cascading nei TC `description` e `condition` text | S |
| `evals/eval-sets/siae-qa/golden/{functional_be,role_based}/expected_tc_draft.json` | TC mutating error | Aggiungere step "verify side-effect not occurred" ai **4 TC totali**: 3 in `functional_be` (autore_id 404, opera_id 400, body malformato 400) + 1 in `role_based` (viewer DELETE 403). `enumerative_spec` già conforme. | S |
| `evals/eval-sets/siae-qa/golden/enumerative_spec/expected_mfinal.json` | nessuna | Verifica già conforme ADR-002/003 (no over-explosion) → no change | XS |
| `evals/eval-sets/siae-qa/golden/functional_be/expected_mfinal.json` | nessuna | EXP contiene già `A-003 EDGE importo=0.01` → no change | XS |
| `reference/question-trees.md` | sezione Backend | Aggiungere domanda type-aware ("Il vincolo numerico è strict `>`/`<` o non-strict `>=`/`<=`?") | XS |

## Flusso Dati (regole di esplosione aggiornate)

```
spec → Phase 1.5 Matrix A
       │
       ├── lookup → POS×N + NEG×1                                  [unchanged]
       ├── booleano → POS(true) + POS(false) + NEG(non-parseable)  [unchanged]
       ├── mandatory non-numerico → POS + NEG(assente)              [unchanged]
       ├── optional → POS + EDGE(null)                              [unchanged]
       ├── formato data/regex/ISO → POS + NEG + EDGE(null se opt)   [unchanged]
       ├── valore fisso business → POS + NEG                        [unchanged]
       ├── strict-bound numerico (`>`, `<`)                         [ADR-002 NEW]
       │   → POS(valore tipico) + NEG(violazione) + EDGE(frontiera bassa type-aware)
       ├── non-strict-bound numerico (`>=`, `<=`, BETWEEN)          [ADR-002 NEW]
       │   → POS + NEG(violazione). NO EDGE auto.
       ├── string con vincolo length/encoding ESPLICITO             [ADR-003 NEW]
       │   → POS + NEG(>max) + EDGE(trim/NFC) solo se spec menziona
       ├── regola composita → IPOG pairwise se > 16                 [unchanged]
       └── cross-sezione → NEG per sezione dipendente               [unchanged]

Naming:
  entity = se spec ha tabella/section name → mantieni as-is         [ADR-004 NEW]
           altrimenti PascalCase singolare logico (no plurale/endpoint)

Phase 4b TC generation:
  TC mutating (POST/PUT/PATCH/DELETE/INSERT/UPDATE)                 [ADR-005 NEW]
    status 2xx → 2 step: action + verify response (response code = evidence)
    status 4xx/5xx → 3 step: action + verify error response + verify side-effect NOT occurred
```

## Status Gap Audit Originale (chiusi vs aperti)

**Mapping finding audit → edit v2.0.0 (corretto post iter 2):**

| Hotspot audit | Stato post-v2.1.0 | Edit canonico (audit IDs) |
|---|---|---|
| H-07 / F-HIGH-04 (set rappresentativo per condition multi-valore) | **CHIUSO** già in v2.0.0 | R-007 applicato (frontiera bassa SKILL.md:547) |
| H-08 / F-MED-08 (max 3 AC senza criterio) | **CHIUSO** già in v2.0.0 | R-008 applicato (criterio happy/validation/edge) |
| H-09 (max 16 senza pairwise IPOG) | **CHIUSO** già in v2.0.0 | R-009 applicato (pairwise SKILL.md:376) |
| H-10 ("esiti distinti" non operazionalizzato) | **CHIUSO** già in v2.0.0 | R-009 stesso edit (status_code OR error class) |
| H-11 / F-MED-02 (confidence formula) | **CHIUSO** già in v2.0.0 | R-019 applicato (XRAY-TEMPLATES.md:33) |
| NEW G5 (type-aware frontiera bassa) | **CHIUSO** in v2.1.0 | ADR-001 (questo design) |
| NEW G2/parziale (strict vs non-strict) | **CHIUSO** in v2.1.0 | ADR-002 (questo design) |
| NEW G2/parziale (POS unification + NEG collapse) | **CHIUSO** in v2.1.0 | ADR-007 (questo design) |
| NEW G1 (trim/NFC/max-length opt-in) | **CHIUSO** in v2.1.0 | ADR-003 (questo design) |
| NEW G3 (entity naming) | **CHIUSO** in v2.1.0 | ADR-004 (questo design) |
| NEW G4 (multi-step mutating + error side-effect-not) | **CHIUSO** in v2.1.0 | ADR-005 riformulato (questo design) |
| NEW: validator warning channel | **CHIUSO** in v2.1.0 | ADR-006 (questo design) |

## Error Handling / Backward Compat

- **Golden `enumerative_spec`:** già 25 rows, già conforme ADR-002 (no EDGE su mandatory numerici non-strict) e ADR-003 (no EDGE trim/NFC). **No update richiesto a `expected_mfinal.json`**. Solo TC mutating error → step 2 esplicito side-effect verification.
- **Golden `functional_be`:** EXP `A-003 EDGE importo=0.01` **già presente** (strict bound `> 0` decimal → ADR-001+002 produrrebbero esattamente questa row). **No update richiesto a `expected_mfinal.json`**. Solo TC mutating error → step 2.
- **Golden `role_based`:** entity cascade `opere → Opera` su 9 rows + correlated TC descriptions. **Update richiesto su tutti i 3 expected JSON**.
- **Validator extension**: cambiamento exit code semantics (WARN = 0, FAIL = 1). Compatibile con uso esistente (chi controlla solo `exit_code != 0` non vede regressione).
- **No breaking change** sulle skill consumer (`siae-automation`): l'`xray_id_mapping.json` schema invariato.

## Testing

- Re-run simulazione 3 fixture con SKILL.md v2.1.0 → atteso:
  - `enumerative_spec`: 25 rows ± 1 (no over-explosion da ADR-003 trim/length non documentati; B-001/B-002 composite mantenuti se applicabili)
  - `functional_be`: 8 rows ± 1 (no over-explosion da decomposed mandatory NEG)
  - `role_based`: 9 rows entity=`Opera`
- Validator: 0 FAIL, ≤ 2 WARN su 3 fixture (WARN tollerati per casi marginali documentati).

## Criteri di Accettazione (verificabili)

1. `SKILL.md` riga **297-306** (tabella esplosione) contiene **3 nuove righe**: `strict-bound numerico`, `non-strict-bound numerico`, `string length/encoding opt-in`. Verifica: `grep -c "strict-bound\|non-strict-bound\|string length" SKILL.md` ≥ 3.
2. `SKILL.md` Phase 4b prescrive minimo 2 step per mutating + 3 step per error mutating. Verifica: grep `step.*mutating` in sezione 4b.
3. `XRAY-TEMPLATES.md` sezione "Template M_FINAL" contiene gerarchia entity naming (3 livelli). Verifica: grep `SCREAMING_SNAKE_CASE\|PascalCase singolare`.
4. `validate_outputs.py` ha funzione `check_neg_numeric_has_edge_low()` E supporta livello WARN (exit 0 con `[WARN]` su stderr). Verifica: `python validate_outputs.py --help` mostra WARN; unit test su input synthetic.
5. 3 golden fixture aggiornate per ADR-005 (TC error mutating con step 2 explicit) e ADR-004 (role_based entity=Opera). Validator PASS su tutte (0 FAIL).
6. SKILL.md frontmatter `version: 2.0.0 → 2.1.0` + changelog inline cita ADR-001..006.
7. **Diff strutturale operazionalizzato (rivisto post iter 2):** re-run simulazione produce, per ciascuna fixture:
   - `|count(SIM rows) - count(EXP rows)| ≤ 3` per fixture con EXP ≤ 10 rows (`functional_be`, `role_based`)
   - `|count(SIM rows) - count(EXP rows)| ≤ max(EXP_count × 0.15, 4)` per fixture con EXP > 10 rows (`enumerative_spec`: tolleranza ≤ 4)
   - `set(SIM entity) == set(EXP entity)` (match esatto post-ADR-004 entity naming)
   - Distribuzione (POS/NEG/EDGE/ROLE): delta ≤ 2 per categoria per fixture > 10 rows; ≤ 1 per fixture ≤ 10
   - Tutti i `matrix_row_id` SIM hanno mapping semantico (entity, field, condition) verso ≥1 row EXP (no row "fantasma")

## Stima SP (rivista post-review)

| Subtask | Umano | Augmented |
|---------|------:|----------:|
| 6 edit SKILL.md (esplosione + ADR-007 POS/NEG rules + Phase 4b + Anti-Raz + Vincoli + version) | 2.5 | 1 |
| 1 edit XRAY-TEMPLATES.md (entity gerarchia) | 0.5 | 0.5 |
| 1 edit question-trees.md (strict vs non-strict) | 0.5 | 0 |
| Validator extension (WARN level + new check `check_neg_numeric_has_edge_low`) | 1.5 | 0.5 |
| Update golden role_based (cascade entity `opere→Opera` su 9 rows + TC) | 1 | 0.5 |
| Update 4 TC error mutating step "side-effect not occurred" (3 in `functional_be` + 1 in `role_based`) | 0.5 | 0 |
| Re-run sim + verifica diff strutturale (Criterio #7 rivisto) | 1 | 0.5 |
| **Totale** | **9.5** | **3** |

## Out of Scope

- Refactor a DSL formale (Approach B) — backlog v3.0.0.
- Promozione validator WARN → FAIL su check `check_neg_numeric_has_edge_low` — richiede 1 sprint di osservazione su run reali. Pianificato per v2.2.0.
- Aggiornamento trigger eval — invariati.
- Approvazione cross-team del cambio entity naming convention — assumiamo OK (è documentazione interna).

---

**Branch target:** `feat/siae-qa-v21-residual`

**Next step (post-approvazione):** invocazione `siae-writing-plans` per generare `docs/plans/2026-05-11-siae-qa-v21-residual/` con overview + 7 task-NN files bite-sized.

## Changelog Design Doc

- **iter 4 (2026-05-11):** correzioni post spec-review WARN iter 3 (no CRITICAL/ALTO residui). Risolti: (a) NEW-1 MEDIO — riallineata tabella delta atteso linea 123: `enumerative_spec` 24-26 (delta 0..+1), B-001/B-002 NON generate coerentemente con ADR-007 rule #3; (b) NEW-2 BASSO — corretto componenti toccati linea 143: 4 TC totali (3 functional_be + 1 role_based), 0 enumerative_spec; (c) NEW-3 BASSO informativo — aggiunto test sintattico operazionale per "spec di tipo enumerative" in ADR-007 rule #1 (tabella markdown con header lookup esplicito o sezione mapping CSV→Target).
- **iter 3 (2026-05-11):** correzioni post spec-review BLOCK iter 2. Risolti: (a) ADR-007 NUOVO introdotto per chiudere G2 effettivamente (POS lookup unification + NEG per-field collapse + B-001/B-002 composite suppression condizionale); (b) ADR-005 riformulato — response code NON è step 2 valido per mutating; verifica empirica golden riportata (~5 TC reali da espandere, non 12); (c) riferimenti riga corretti: 790-810 Anti-Raz, 821-838 Vincoli (refactor SKILL.md intercorso); (d) Criterio #7 rivisto con soglie differenziate per fixture size (`≤3 per EXP≤10`, `≤max(15%,4) per EXP>10`); (e) finding IDs audit mappati canonicamente (F-HIGH-04/F-MED-02/F-MED-08); (f) SP rivisto 8 → 9.5 (Umano) con +1.5 SP per ADR-007; (g) tabella delta atteso post-v2.1.0 mostra rientro nei nuovi bound del Criterio #7 per tutte le 3 fixture.
- **iter 2 (2026-05-11):** correzioni post spec-review BLOCK iter 1. Risolti: (1) riferimento riga 297-306 corretto, (2) conflitto ADR-001/002 risolto con regola strict/non-strict, (3) diagnosi G2 corretta (over-explosion SIM, no missing EXP), (4) 5 gap esplicitati in tabella, (5) eccezioni ADR-004 documentate (`GENERAL_DATA` resta), (6) ADR-005 backward compat chiarito (response code = evidence per 2xx), (7) ADR-006 validator WARN channel formalizzato, (8) criterio #7 diff strutturale operazionalizzato, (9) SP rivisto a 8/3, (10) ADR-001 type-aware (decimal/integer/date), (11) status H-07..H-11 audit documentato.
