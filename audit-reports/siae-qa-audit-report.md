# SIAE-QA Skill — Enterprise Audit Report

> **Auditor:** Senior Quality Engineer / Skill Architect
> **Date:** 2026-05-11
> **Branch under audit:** `feat/code-coverage-opt-batch-1` (last touched siae-qa commit: 13 apr 2026 — `skills/siae-qa/SKILL.md`)
> **Output path:** `audit-reports/siae-qa-audit-report.md` (target `/mnt/user-data/outputs/` non disponibile su filesystem locale — fallback su directory di audit del repo, già utilizzata per `code-coverage-audit-2026-05-07.md`).

---

## 0. Executive Summary

- **Verdict:** **Bronze** (production-usable ma non gold). La skill ha una spina dorsale di workflow forte (Phase 0 → 1 → 1.5 → 2 → 3 → 4a/b/c/d → 5) con due gate bloccanti basati su Agent tool, ma il **single source of truth è frammentato fra `SKILL.md` e `XRAY-TEMPLATES.md`** e quest'ultimo è **rimasto fermo al workflow pre-Coverage-Matrix**. Determinismo end-to-end compromesso da incoerenze terminologiche (`ROLE` vs `PROFILO`) e da artefatti dell'output (Riepilogo Copertura, Matrice Scenari, Checklist) che descrivono un processo che la SKILL.md non esegue più.
- **Score complessivo:** **24 / 50** sulla Enterprise Maturity Scorecard (Phase 6).
- **Top 3 rischi critici:**
  1. **Doppio schema di categorizzazione TC**: `[POS]/[NEG]/[EDGE]/[ROLE]` in `SKILL.md:495` vs `[EDGE]/[NEG]/[PROFILO]` (positivo = no prefisso) in `XRAY-TEMPLATES.md:70,82-85,204`. Stesso TC può uscire con prefisso diverso a seconda della sezione che Claude rilegge per ultima.
  2. **Documentazione `XRAY-TEMPLATES.md` parzialmente dead-code**: sezioni `Riepilogo Copertura` (`XRAY-TEMPLATES.md:95-106`), `Template Matrice Scenari` (`XRAY-TEMPLATES.md:110-124`), `Domande Elicitazione per Categoria` (`XRAY-TEMPLATES.md:128-150`) e `Checklist di Verifica` (`XRAY-TEMPLATES.md:189-213`) descrivono il processo a 4-categorie ELIMINATO dalla Phase 1.5 M_FINAL (`SKILL.md:217-392`). La checklist finale **non menziona M_FINAL, Gate #1, Gate #2, J1-J5, coverage_certificate**.
  3. **Zero test funzionali sul WORKFLOW output**: l'eval set (`evals/eval-sets/siae-qa/trigger.json`, `evals/trigger-evals/siae-qa.json`) copre solo il **trigger detection**; **nessun golden output**, nessun e2e su M_FINAL/TC_DRAFT, nessuna regressione su Gate #1/Gate #2. Tutto il workflow output è non-verificato programmaticamente.
- **Top 3 quick win:**
  1. Sostituire `XRAY-TEMPLATES.md` (interi blocchi obsoleti) con i template del nuovo workflow M_FINAL → POS/NEG/EDGE/ROLE — 1-2h di edit puro.
  2. Aggiungere lo schema JSON formale di `MFINAL.md` e `coverage_certificate` come allegati `reference/schemas/*.json` con validatore Python — sblocca tutti i test programmatici a costo lineare.
  3. Aggiungere a `evals/eval-sets/siae-qa/` 3 golden fixture (spec enumerativa, spec funzionale standard, spec con ruoli) + 1 test che valuta bijection TC↔M_FINAL su output reale — chiude il gap di test_determinism dimensione #10.

---

## 1. Scope & Methodology

- **Versione skill auditata:** ultimo commit che tocca `skills/siae-qa/SKILL.md` = `13 apr 2026 10:51` (mtime filesystem). Nessuna intestazione `version:` in `SKILL.md` (vedi Phase 6, dim. 5). Marketplace plugin a `version: 1.49.0` (`.claude-plugin/marketplace.json:13`) ma non c'è binding skill→version.
- **Files analizzati (4 file, ~1.296 righe totali):**
  ```
  skills/siae-qa/
  ├── SKILL.md                          834 righe
  ├── XRAY-TEMPLATES.md                 213 righe
  └── reference/
      ├── question-trees.md             153 righe
      └── xray-csv-template.md           96 righe
  evals/
  ├── eval-sets/siae-qa/trigger.json     (10 trigger+10 non-trigger)
  └── trigger-evals/siae-qa.json         (duplicato del precedente)
  ```
- **Limiti dell'audit:**
  - Nessuna esecuzione reale dei prompt agent (J1-J5, Matrix A/B/C). L'audit valuta lo **statico**: cosa è scritto, non cosa farebbe Claude in runtime.
  - Audit non considera `siae-automation` (consumer downstream della mappatura ID).
  - Audit non considera storia git oltre alla mtime del file (commits di refactor verso M_FINAL non analizzati).
  - File del worktree `(.claude/worktrees/agent-a74d44f1/skills/siae-qa)` non confrontati con la canonical version: assumiamo che la canonical sia `skills/siae-qa/`.

---

## 2. Skill Inventory & Workflow Map

### 2.1 File inventory

| Path | Righe | Ruolo | Note critiche |
|------|------:|-------|---------------|
| `skills/siae-qa/SKILL.md` | 834 | Workflow principale, 5 fasi + 4 sub-phase | 12 blocchi `<EXTREMELY-IMPORTANT>` (densità alta); 44 righe di "Tabella Anti-Razionalizzazione" — overlap con vincoli |
| `skills/siae-qa/XRAY-TEMPLATES.md` | 213 | Template e checklist | **Parzialmente dead-doc**: descrive il processo pre-M_FINAL |
| `skills/siae-qa/reference/question-trees.md` | 153 | 6 alberi tematici (FE/BE/ETL/DB/Auth/Integration) × L1/L2/L3 | Coerente. Unico file pulito |
| `skills/siae-qa/reference/xray-csv-template.md` | 96 | Spec CSV semicolon-separated | Coerente. `Test  Type` (2 spazi) e `Expceted Result` documentati come quirks del template Xray SIAE |
| `evals/eval-sets/siae-qa/trigger.json` | 23 | 10 should_trigger=true + 10 false | **Solo trigger detection, nessun workflow eval** |
| `evals/trigger-evals/siae-qa.json` | 23 | **Duplicato byte-identico** di `eval-sets/siae-qa/trigger.json` | Forma di duplicazione codice — manutenzione doppia |

### 2.2 Workflow diagram (as-coded)

```
                                ┌────────────────────────────┐
USER request ──▶  Opening Dialog (3 tier) ◀── HARD-GATE: tier scelto esplicitamente
                                └─────────────┬──────────────┘
                                              ▼
                              PRE-FLIGHT CARD (🟡 medio)
                                              │
                                              ▼
                ┌──────────────────────  Phase 0 — Smart Req Typing ────────────────────┐
                │ 0a infer tipo  ▶  0b mostra Req Profile Card  ▶  0c question tree     │
                │ Input: question-trees.md (6 tipi × L1/L2/L3)                          │
                │ Output: Req Profile Card aggiornata con scenari L1/L2/L3              │
                └────────────────────────────────┬──────────────────────────────────────┘
                                                 ▼
                ┌──────────────────────  Phase 1 — Lettura AC [HARD-GATE] ──────────────┐
                │ Tier 1: MCP Jira  /  Tier 2: doc + validation  /  Tier 3: chat        │
                │ Output: lista strutturata di AC                                        │
                └────────────────────────────────┬──────────────────────────────────────┘
                                                 ▼
                ┌──── Phase 1.5 — Coverage Matrix Builder [HARD-GATE — OBBLIGATORIA] ───┐
                │ 1. Serializza ENTITÀ/CAMPI + LOOKUP + REGOLE + VINCOLI                │
                │    [CHECKPOINT SERIALIZZAZIONE OBBLIGATORIO]                          │
                │ 2. Lancia 3 agent in parallelo:                                       │
                │    Matrix A (field/value) | Matrix B (rules) | Matrix C (roles)       │
                │ 3. Gate #1 (parallelo): J1_MATRIX coverage + J2_MATRIX dedup          │
                │ 4. Merge M_A+M_B+M_C → M_FINAL  →  Write MFINAL.md                   │
                │ Output: file MFINAL.md su filesystem                                  │
                └────────────────────────────────┬──────────────────────────────────────┘
                                                 ▼
                ┌────────────  Phase 2 — Test Strategy da Confluence ───────────────────┐
                │ Tier 1 CQL, Tier 2 doc, Tier 3 WARNING                                │
                │ Output: scope/approach/test_types OR warning                          │
                └────────────────────────────────┬──────────────────────────────────────┘
                                                 ▼
                ┌────────────────  Phase 3 — Generazione Test Plan ─────────────────────┐
                │ Output: struttura Test Plan (in MCP Tier 1 / testuale Tier 2-3)       │
                └────────────────────────────────┬──────────────────────────────────────┘
                                                 ▼
                ┌──────────────  Phase 4 — Generazione Test Case ───────────────────────┐
                │ 4a Verifica M_FINAL + domanda business knowledge (1 domanda max)      │
                │ 4b Read MFINAL.md → genera 1 TC step-based per riga → Write TC_DRAFT  │
                │ 4c Gate #2 (parallelo): J3 bijection + J4 specificity (soglia 75%)    │
                │ 4d J5 Final Audit (run-once, non-bloccante) → coverage_certificate    │
                │    Se developer aggiunge TC ⇒ RILANCIA Gate #2                        │
                │ Output: TC_DRAFT.md + GATE #2 REPORT + COVERAGE CERTIFICATE           │
                └────────────────────────────────┬──────────────────────────────────────┘
                                                 ▼
                ┌──────────────────  Phase 5 — Export/Sincronizzazione ─────────────────┐
                │ Tier 1 MCP createTestIssue × N (raccogli chiavi Jira)                 │
                │ Tier 2/3 CSV semicolon-separated importabile (Header in xray-csv-...) │
                │ Mappatura ID sequenziali → chiavi Jira (input per siae-automation)    │
                │ Output: TC creati in Xray + mappatura                                 │
                └─────────────────────────────────────────────────────────────────────-─┘
```

### 2.3 Output catalog (artifact prodotti dal workflow)

| # | Output | Tipo | Persistenza | Generato in | Consumer |
|---|--------|------|------------|-------------|----------|
| O-1 | Req Profile Card (iniziale) | testo in chat | conversation only | Phase 0b | UI/utente |
| O-2 | Req Profile Card (aggiornata con L1/L2/L3) | testo in chat | conversation only | Phase 0c (post-tree) | UI/utente; (anche dichiarato come "input aggiuntivo per Phase 4a", `SKILL.md:167` — **claim residuo pre-refactor**) |
| O-3 | Blocco di serializzazione (entità/lookup/regole/vincoli) | testo in chat | conversation only | Phase 1.5 (pre-agent) | Matrix A/B/C |
| O-4 | M_A, M_B, M_C (tabelle parziali) | tabelle markdown in chat | conversation only | Phase 1.5 (agent output) | J1_MATRIX, J2_MATRIX, merge |
| O-5 | J1_MATRIX report | testo in chat | conversation only | Phase 1.5 Gate #1 | logica di retry |
| O-6 | J2_MATRIX dedup list | testo in chat | conversation only | Phase 1.5 Gate #1 | merge M_FINAL |
| O-7 | **MFINAL.md** | file markdown | **filesystem (Write tool)** | Phase 1.5 final | Phase 4b, J3, J4, J5 |
| O-8 | **TC_DRAFT.md** | file markdown | **filesystem (Write tool)** | Phase 4b | J3, J4 |
| O-9 | J3 bijection report | testo in chat | conversation only | Phase 4c | gate decision |
| O-10 | J4 specificity report | testo in chat | conversation only | Phase 4c | gate decision |
| O-11 | GATE #2 REPORT | formato fisso (`SKILL.md:589-598`) | conversation only | Phase 4c | UI/utente |
| O-12 | J5 GAP list + coverage_score | testo in chat | conversation only | Phase 4d | utente/decisione export |
| O-13 | **COVERAGE CERTIFICATE** | formato fisso (`SKILL.md:654-671`) | conversation only — **NON salvato su file** | Phase 4d | collaudo |
| O-14 | TC Xray creati via MCP | issue Jira | persistente in Xray | Phase 5 Tier 1 | siae-automation |
| O-15 | CSV semicolon-separated (header + N righe) | file CSV / blocco testo | filesystem o chat | Phase 5 Tier 2-3 | import Xray manuale |
| O-16 | Mappatura ID sequenziali → chiavi Jira | testo formato fisso (`XRAY-TEMPLATES.md:163-171`) | conversation only — **NON salvata su file** | Phase 5 post-export | siae-automation Phase 1 |

**Gap evidente:** O-13 (Coverage Certificate) e O-16 (Mappatura ID) sono dichiarati output critici (collaudo + handoff a siae-automation) ma **NON c'è regola di persistence** → vivono solo nel context conversazione.

---

## 3. Output Specification Matrix

| Output ID | Tipo | Formato | Dichiarato in | Struttura attesa | Criteri qualità | DoD esplicita? |
|-----------|------|---------|---------------|------------------|-----------------|----------------|
| O-1 Req Profile Card iniziale | block testuale | template fisso `XRAY-TEMPLATES.md:39-45` | `SKILL.md:144-148` | 4 campi (Tipo/Confidence/Segnali/Stack) | Confidence band quantizzata `XRAY-TEMPLATES.md:30-33` | **No** — non c'è validatore; "scenari L1/L2/L3" introdotti dopo le domande non hanno schema |
| O-2 Req Profile Card aggiornata | block testuale | template `XRAY-TEMPLATES.md:49-55` | `SKILL.md:166-167` | 4 campi (Tipo/Scenari L1/L2/L3) | Min: 1 scenario per livello? non specificato | **No** |
| O-3 Blocco serializzazione | block testuale strutturato | template `SKILL.md:259-281` | `SKILL.md:255-298` | 4 sezioni fisse (ENTITÀ E CAMPI / LOOKUP / REGOLE / VINCOLI) | "completa = entità+lookup+regole+vincoli corrispondono alla specifica" | **No** — checkpoint chiede conferma ("sì"/"ok") senza criteri di accept |
| O-4 M_A/M_B/M_C | tabella markdown | 6 colonne fisse + 2 extra per M_B | `SKILL.md:283-291` | matrix_row_id, entity, field, condition, test_type, source_ref | "esattamente questi nomi colonna" + `test_type ∈ {POS,NEG,EDGE,ROLE}` | **Implicita** — J2_MATRIX verifica solo dedup, nessuna validazione schema |
| O-5 J1_MATRIX report | string formato fisso | `SKILL.md:362` "GIUDICE J1_MATRIX \| PERCENTUALE: XX% \| PASS/FAIL \| GAP: [lista]" | `SKILL.md:354-363` | 4 campi fissi | Soglia: 100% entità coperte (`SKILL.md:361`) | **Sì (soglia 100%)** |
| O-6 J2_MATRIX dedup | string formato fisso | `SKILL.md:371` "GIUDICE J2_MATRIX \| DUPLICATI: N \| LISTA_DUPLICATI: [lista]" | `SKILL.md:366-371` | 3 campi fissi | Nessuna soglia, è descrittivo | **Parziale** (no pass/fail) |
| O-7 MFINAL.md (file) | markdown / tabella | non c'è schema formale, solo "tabella con N righe, ognuna = 1 TC atteso" | `SKILL.md:391` | tabella con 6 colonne base | **Manca specifica formato file** (frontmatter? sezione header? metadati timestamp?) | **No** |
| O-8 TC_DRAFT.md (file) | markdown | template TC `SKILL.md:484-491` | `SKILL.md:497-500` | sequenza TC step-based con metadati | Specificità: J4 ≥75% (`SKILL.md:562`); Tracciabilità: matrix_row_id in Description (`SKILL.md:482`) | **Parziale** — soglia 75% definita, ma formato file (sezioni, frontmatter) **non specificato** |
| O-9 J3 bijection | string formato fisso | `SKILL.md:549` | `SKILL.md:540-549` | "PASS/FAIL \| RIGHE_ORFANE: [lista] \| TC_ORFANI: [lista]" | Soglia 100% bijection | **Sì** |
| O-10 J4 specificity | string formato fisso | `SKILL.md:563` | `SKILL.md:554-563` | "PERCENTUALE: XX% \| PASS/FAIL \| TC_GENERICI: [lista]" | Soglia 75% | **Sì** |
| O-11 GATE #2 REPORT | block formato fisso | `SKILL.md:589-598` | `SKILL.md:587-598` | 4 righe (J3, J4, righe orfane, TC generici) | Bound visivo a 50 char separator | **Sì** (formato testuale) ma **No** schema parsabile |
| O-12 J5 output | string formato fisso | `SKILL.md:620` | `SKILL.md:606-621` | "SCORE: XX% \| CERTIFICATE: {dati} \| GAP: [lista con priorità]" | **Nessuna soglia** (non bloccante) | **No** — `coverage_score` definito come "% righe con TC di qualità verificata" ma non c'è formula riproducibile |
| O-13 COVERAGE CERTIFICATE | block formato fisso | `SKILL.md:654-671` | `SKILL.md:652-673` | 10 campi fissi | Allegato a Phase 5 | **No** — non salvato su file, non c'è schema JSON parsabile, "CONDITIONAL PASS" attivato solo se gap accettati |
| O-14 TC Xray (MCP) | issue Jira | gestito da MCP atlassian | `SKILL.md:680-682` | dipende dal tool MCP | post-creazione: raccogliere chiave Jira | **No** — nessun fallback test se la creazione fallisce a metà |
| O-15 CSV semicolon | file CSV | `reference/xray-csv-template.md:53` header esatto + esempio righe 64-71 | `XRAY-TEMPLATES.md:180-186` | 12 colonne fisse (`Test  Type` con 2 spazi, `Expceted Result` typo voluto) | UTF-8 senza BOM, separatore `;` | **Sì** (schema CSV preciso, unico output con DoD enterprise-grade) |
| O-16 Mappatura ID | block formato fisso | `XRAY-TEMPLATES.md:163-171` | `XRAY-TEMPLATES.md:154-176` | tabella ID CSV → chiave Xray → scenario | "obbligatorio se si usa siae-automation" | **No** — non salvata su file; **bloccante per siae-automation** ma non per la skill |

**Riepilogo:** su 16 output, **3 hanno DoD esplicita** (O-5, O-9, O-15), **3 parziale** (O-6, O-8, O-10), **10 senza DoD**. Concentrazione di rigore sul lato gate (J-judges) e CSV import, lato output di handoff (Certificate, Mappatura) **sotto-specificato**.

---

## 4. Non-Determinism Hotspots

Identificati **17 hotspot**. Ordinati per impatto.

### H-01 — Doppio schema di prefisso TC (ALTO)

- **Evidence A:** `SKILL.md:495` — `**Prefisso titolo:** usa il `test_type` della riga (`[POS]`, `[NEG]`, `[EDGE]`, `[ROLE]`).`
- **Evidence B:** `XRAY-TEMPLATES.md:70` — `Titolo del Test Case — includi la categoria: es. `[EDGE] ...`, `[NEG] ...`, `[PROFILO] ...`` + `XRAY-TEMPLATES.md:82-85` — `Nessun prefisso = scenario positivo (happy path)`.
- **Evidence C:** `XRAY-TEMPLATES.md:204` — checklist `I titoli Scenario usano i prefissi `[EDGE]`, `[NEG]`, `[PROFILO]` dove appropriato`.
- **Two divergent outputs allowed by current rules:**
  - Output A (segue SKILL.md:495): `[POS] CATEGORY = "F" → migrazione come feature` (esempio `SKILL.md:486`)
  - Output B (segue XRAY-TEMPLATES.md:82): `CATEGORY = "F" → migrazione come feature` (senza prefisso) + un TC con ruolo `[PROFILO] Verifica accesso editor`
- **Impatto:** ALTO. Stesso input può produrre due tassonomie di prefisso incompatibili — Xray reports e dashboards filtrano su questi prefissi.

### H-02 — `XRAY-TEMPLATES.md` template "Matrice Scenari" è dead documentation (ALTO)

- **Evidence:** `XRAY-TEMPLATES.md:110-124` descrive l'output atteso "della fase 4a — matrice scenari compilata prima della generazione" come tabella `Positivi / Edge case / Alternativi-negativi / Profilazioni-ruoli`.
- **Conflict:** `SKILL.md:439-456` ridefinisce Phase 4a come **"Verifica e completamento M_FINAL"** che opera sulla Coverage Matrix di Phase 1.5 (POS/NEG/EDGE/ROLE).
- **Two divergent outputs:**
  - Output A (segue SKILL.md): Phase 4a mostra M_FINAL tabellare con 6 colonne + chiede 1 domanda sul business knowledge.
  - Output B (segue XRAY-TEMPLATES.md): Phase 4a costruisce una tabella a 4 categorie elicitando da domande.
- **Impatto:** ALTO. Forme di output e step interattivi completamente diversi.

### H-03 — `Riepilogo Copertura` template usa tassonomia obsoleta (ALTO)

- **Evidence:** `XRAY-TEMPLATES.md:99-106` — `Positivi: N TC / Edge case: N TC / Negativi: N TC / Profilazioni: N TC`.
- **Conflict:** `SKILL.md:447` — `Distribuzione: N POS / N NEG / N EDGE / N ROLE`.
- **Impatto:** ALTO. La Distribuzione mostrata in Phase 4a (M_FINAL) e il Riepilogo Copertura mostrato pre-export (`SKILL.md:502` rimanda implicitamente al template) usano nomi diversi. Aggregazione downstream rotta.

### H-04 — `Checklist di Verifica` non menziona M_FINAL / Gate / J1-J5 / certificate (ALTO)

- **Evidence:** `XRAY-TEMPLATES.md:189-213` (intera sezione). La checklist dice:
  - Riga 200: `Matrice scenari compilata (4 categorie valutate: positivi, edge, negativi, profilazioni)` — **referenzia il vecchio processo**.
  - Riga 203: `Presenti TC per scenari positivi, edge case, negativi e profilazioni`.
  - Riga 211: `Tier usato annunciato nella pre-flight card di apertura`.
  - **Nessun item** su: `MFINAL.md presente`, `J1_MATRIX PASS`, `J2_MATRIX dedup applicato`, `TC_DRAFT.md salvato`, `Gate #2 PASS`, `J5 eseguito`, `coverage_certificate prodotto`, `Mappatura ID raccolta`.
- **Conflict:** `SKILL.md:751-754` rinvia ESPLICITAMENTE a questa checklist (`Vedi [XRAY-TEMPLATES.md](XRAY-TEMPLATES.md) sezione "Checklist di Verifica" per la checklist completa.`).
- **Impatto:** ALTO. La skill auto-dichiara "completato" senza verificare i bloccanti reali. Anti-razionalizzazione `SKILL.md:746` ("Salto Fase 4c Gate #2") **non è prevenuta dalla checklist linkata**.

### H-05 — `SKILL.md:167` lascia un riferimento orfano alla "Phase 4a (matrice scenari)" (MEDIO)

- **Evidence:** `SKILL.md:167` — `Questa card e' l'input aggiuntivo per Phase 4a (matrice scenari).`
- **Conflict:** Phase 4a è ora "Verifica M_FINAL" (`SKILL.md:439`), non costruzione matrice. La Req Profile Card aggiornata viene di fatto usata implicitamente nella serializzazione di Phase 1.5 (campo "info ruolo/permesso" per Matrix C, `SKILL.md:332`) ma il rinvio non è esplicito.
- **Two outputs allowed:**
  - Output A: Claude considera la Req Profile Card come deliverable di Phase 0 e non la passa esplicitamente in Phase 1.5.
  - Output B: Claude tenta di "iniettare" gli scenari L1/L2/L3 della Req Profile Card come righe sintetiche di M_A/M_B/M_C.
- **Impatto:** MEDIO. L'inferenza di tipo (BE, FE, ETL, ...) influenza scelte di scope nei test ma il percorso di propagazione non è esplicito.

### H-06 — `Domande Elicitazione per Categoria` è obsoleta ma referenziata implicitamente (MEDIO)

- **Evidence:** `XRAY-TEMPLATES.md:128-150`. Descrive domande per le 4 categorie pre-M_FINAL.
- **Conflict:** Le domande del workflow attuale sono in `reference/question-trees.md` (driver Phase 0c).
- **Impatto:** MEDIO. Claude può rileggere `XRAY-TEMPLATES.md:128-150` e iniziare a porre domande Categoria-based in Phase 4a, generando elicitazione superflua post-M_FINAL.

### H-07 — `"set di valori rappresentativo"` per condition multi-valore non deterministico (MEDIO)

- **Evidence:** `SKILL.md:493` — `se la condizione contiene AND/OR tra più valori (es. "importo > 1000 AND valuta IN (EUR, USD)"), genera 1 TC con un set di valori rappresentativo (es. importo=1500, valuta=EUR).`
- **Two divergent outputs:**
  - Output A: `importo=1500, valuta=EUR` (esempio fornito)
  - Output B: `importo=99999.99, valuta=USD` (anche "rappresentativo")
- **Impatto:** MEDIO. La specificità J4 può accettare entrambi, ma due TC orientati allo stesso `matrix_row_id` divergono in dati di test.

### H-08 — `"massimo 3 AC per requisito"` senza criterio di selezione (MEDIO)

- **Evidence:** `SKILL.md:197` — `Granularità: per requisiti funzionali standard massimo 3 AC.`
- **Two divergent outputs:** dato un requisito che genera 7 AC candidati, Claude può sceglierne 3 in 35 modi diversi. Nessuna regola di prioritizzazione.
- **Impatto:** MEDIO. Coverage Matrix downstream perde righe a seconda di quali 3 AC sono scelti.

### H-09 — `max 16 combinazioni per regola; se superi, annota "ridotto per complessità"` (MEDIO)

- **Evidence:** `SKILL.md:323` (Matrix Agent B) — `Limite: max 16 combinazioni per regola; se superi, annota "ridotto per complessità"`.
- **Gap:** Manca **regola di selezione** delle 16 combinazioni quando lo spazio è > 16. Quali combinazioni si tengono? Tutte le frontiere? Sample casuale? Pairwise testing?
- **Impatto:** MEDIO. Due esecuzioni della Matrix B sulla stessa regola con 32 combinazioni possono tenere 16 sottoinsiemi disgiunti.

### H-10 — `"combinazioni con esiti DISTINTI"` non operazionalizzato (MEDIO)

- **Evidence:** `SKILL.md:321` — Matrix B: `Mantieni solo combinazioni con esiti DISTINTI`.
- **Gap:** "Esito distinto" non è definito. Code = 200 vs 201? Messaggio errore A vs errore B?
- **Impatto:** MEDIO. Ambiguità nella riduzione del prodotto cartesiano.

### H-11 — `confidence HIGH/MEDIUM/LOW` percentuali non riproducibili (BASSO)

- **Evidence:** `XRAY-TEMPLATES.md:30-33` — `HIGH (>= 90%): 2+ segnali forti convergenti / MEDIUM (60-89%): 1 segnale forte o 2+ deboli / LOW (< 60%): segnali ambigui o assenti`.
- **Gap:** Come si passa da "2+ segnali forti" a un numero ≥90%? Non c'è formula.
- **Impatto:** BASSO (l'output è una band, non un numero), ma il branch logico `SKILL.md:147-148` (`HIGH → procedi senza conferma | MEDIUM/LOW → chiedi conferma`) dipende dalla band.

### H-12 — `"se opportuno"` nei prefissi TC (BASSO)

- **Evidence:** `XRAY-TEMPLATES.md:204` — `I titoli Scenario usano i prefissi `[EDGE]`, `[NEG]`, `[PROFILO]` dove appropriato`.
- **Gap:** "dove appropriato" — non è esplicito.
- **Impatto:** BASSO (è una checklist), ma rafforza H-01.

### H-13 — `"directory del progetto corrente"` ambigua per MFINAL.md / TC_DRAFT.md (MEDIO)

- **Evidence A:** `SKILL.md:379` — `Usa Write tool per salvare M_FINAL su MFINAL.md nella directory del progetto corrente.`
- **Evidence B:** `SKILL.md:499` — `Usa Write tool per salvare tutti i TC generati su TC_DRAFT.md nella directory del progetto.`
- **Gap:** Non specifica se: (a) root del repo, (b) `docs/qa/`, (c) `tmp/`, (d) directory dello slash command. Inconsistenza minore tra "del progetto corrente" e "del progetto".
- **Impatto:** MEDIO. Su monorepo, esecuzioni concorrenti su due story collidono su `MFINAL.md`.

### H-14 — `coverage_score` di J5 senza formula esplicita (MEDIO)

- **Evidence:** `SKILL.md:617-618` — `coverage_score: % righe M_FINAL con TC di qualità verificata`.
- **Gap:** "qualità verificata" non è definita operazionalmente (riusa J3+J4? Aggiunge boundary check?). J4 ha già "specificità %" — sono la stessa metrica?
- **Impatto:** MEDIO. Il `coverage_certificate` riporta uno score non comparabile tra run.

### H-15 — `"CONDITIONAL PASS"` triggerato da regola implicita (MEDIO)

- **Evidence:** `SKILL.md:640` — `→ Procedi direttamente a Fase 5 (export) con il certificate "CONDITIONAL PASS"`.
- **Gap:** Il template del certificate `SKILL.md:654-671` non contiene il campo "CONDITIONAL PASS" — solo `Gate #1: PASS ✅ / Gate #2: PASS ✅`. Dove va segnato il "CONDITIONAL"?
- **Impatto:** MEDIO. Il certificato a valle può mancare la dichiarazione di stato condizionale.

### H-16 — `"un sì o un ok è sufficiente"` checkpoint serializzazione (BASSO)

- **Evidence:** `SKILL.md:298` — `Non lanciare Matrix A/B/C senza risposta esplicita. Un "sì" o "ok" è sufficiente`.
- **Tension:** `SKILL.md:202-203` invece dice che `Un silenzio o un "ok" generico non è una conferma valida` (per AC Tier 2). Due definizioni di "conferma valida" in punti diversi.
- **Impatto:** BASSO ma rumoroso: stesso utente, stesso "ok", esito diverso.

### H-17 — `Automazione` / `NRT` non sono parte di M_FINAL ma il riepilogo 4b ne permette la modifica (MEDIO)

- **Evidence:** `SKILL.md:502` — `Riepilogo prima del gate: mostra la tabella compatta al developer (TC-ID, titolo, matrix_row_id, test_type). Il developer puo' modificare Automazione e NRT prima di procedere.`
- **Gap:** Questi due campi non esistono in M_FINAL (`SKILL.md:238-241`) e non hanno default deterministico nella TC generation di 4b. Il default `Automazione=N, NRT=Y` è dichiarato solo a `SKILL.md:834` (sezione "QUANDO SEI BLOCCATO").
- **Impatto:** MEDIO. Generazione e modifica avvengono senza single source of truth — i TC possono uscire con valori indefiniti per Automazione/NRT.

---

## 5. Logical & Functional Ordering Assessment

| Dimensione | Score (1-5) | Motivazione + evidence |
|------------|:-----------:|------------------------|
| Ordine causale | 4 | Workflow lineare con dipendenze esplicite (M_FINAL ⟶ TC ⟶ J3/J4 ⟶ J5 ⟶ export). Hard-gate ben posizionati. Unica deviazione: Phase 2 (Test Strategy) è inserita **tra** Phase 1.5 e Phase 3 ma è un side-effect informativo che non blocca; potrebbe stare in Phase 0 o parallelo a Phase 1. Vedi `SKILL.md:395-415`. |
| Gerarchia output | 2 | Il flow finale mescola report parsabili (`GATE #2 REPORT`, `COVERAGE CERTIFICATE`) con elementi narrativi (Riepilogo Copertura, mappatura). Manca executive-summary unica esplicita. Il `coverage_certificate` è la cosa più simile a un "exec summary" ma non è salvata. Vedi `SKILL.md:654-671`. |
| Ridondanza | 2 | Tre fonti di "anti-razionalizzazione" che dicono la stessa cosa: (a) blocchi `<EXTREMELY-IMPORTANT>` (×12, `SKILL.md:30-41, 222-232, 342-351, 511-522, 646-650, 803-806`); (b) Tabella Anti-Razionalizzazione (`SKILL.md:715-747`, 32 righe); (c) Vincoli Non Negoziabili (`SKILL.md:758-772`, 12 punti). Stesse regole espresse 2-3 volte con wording diverso. |
| Flow narrativo (gen→spec) | 3 | Generale → specifico è rispettato (Tier → Phase → Sub-phase). Ma la lunghezza dei singoli step (Phase 1.5: 175 righe da `SKILL.md:217` a `SKILL.md:391`) sovrasta le fasi finali (Phase 5: 18 righe). Disequilibrio. |
| Naming consistente | 1 | **Inconsistenze critiche:** `ROLE` vs `PROFILO` (H-01), `Positivi/Edge/Negativi/Profilazioni` vs `POS/NEG/EDGE/ROLE` (H-03), `Phase` vs `Fase` (mix nello stesso doc), `M_FINAL` (`SKILL.md`) vs `MFINAL.md` (filename, no underscore), `MEDIO` vs `MEDIA` (priorità gap J5 = "ALTA/MEDIA/BASSA" `SKILL.md:618`, ma certificate dice "MEDIA: ... / BASSA: ..." `SKILL.md:667-668`). |
| Table of contents prevedibile | 3 | `XRAY-TEMPLATES.md:3-15` ha ToC; `SKILL.md` no — affidata a heading H2/H3. Dato il volume (834 righe), una ToC esplicita in `SKILL.md` ridurrebbe friction. Vedi `SKILL.md:1-22`. |

**Punteggio sezione 5 (somma 6 dimensioni):** 15/30 — sotto la soglia operativa enterprise (>=24).

**Gap-list specifici:**
- L-01: Nessuna ToC in `SKILL.md` (834 righe).
- L-02: 3 copie di "anti-razionalizzazione" (blocchi EXTREMELY-IMPORTANT + Tabella + Vincoli) — consolidare.
- L-03: 5 inconsistenze di naming attive (ROLE/PROFILO; POS/Positivi; Phase/Fase; M_FINAL/MFINAL; ALTA-MEDIA-BASSA/MEDIO-MEDIA-MEDIO).
- L-04: Phase 2 (Test Strategy Confluence) non-bloccante ma posizionata tra due hard-gate — review posizionamento.
- L-05: Sub-phase 4a→4b→4c→4d generano confusione di nesting (4a non genera output, 4b genera, 4c valuta, 4d audita) — considerare rinomina (4a = "Pre-flight TC", 4b = "Generate", 4c = "Verify Bijection+Specificity", 4d = "Audit").

---

## 6. Test Coverage Matrix

### 6.1 Stato testing esistente

| Workflow branch | Test esiste? | Tipo test | Golden output? | Edge case coperti |
|-----------------|:-----------:|-----------|:-------------:|-------------------|
| Trigger detection (10 should_trigger=true) | ✅ | Trigger eval `evals/eval-sets/siae-qa/trigger.json:2-11` | No (solo boolean) | No |
| Trigger rejection (10 should_trigger=false) | ✅ | Trigger eval `evals/eval-sets/siae-qa/trigger.json:13-22` | No | No |
| Phase 0 — Smart Req Typing (6 tipi) | ❌ | — | — | — |
| Phase 0 — Confidence band (HIGH/MEDIUM/LOW branching) | ❌ | — | — | — |
| Phase 1 Tier 1 (MCP Jira) — AC presenti | ❌ | — | — | — |
| Phase 1 Tier 1 — AC vuoti, fallback description → comments → Confluence | ❌ | — | — | — |
| Phase 1 Tier 2 (Documento) — validation loop | ❌ | — | — | — |
| Phase 1 Tier 2 — spec enumerativa (cap 3 AC non si applica) | ❌ | — | — | — |
| Phase 1 Tier 3 (Conversazione) | ❌ | — | — | — |
| Phase 1.5 — serializzazione completa | ❌ | — | — | — |
| Phase 1.5 — Matrix A (lookup, mandatory, optional, formato, valore fisso) | ❌ | — | — | — |
| Phase 1.5 — Matrix B (regole composte, max 16, "esiti distinti") | ❌ | — | — | — |
| Phase 1.5 — Matrix C (no ruoli vs ruoli) | ❌ | — | — | — |
| Phase 1.5 — J1_MATRIX PASS al primo tentativo | ❌ | — | — | — |
| Phase 1.5 — J1_MATRIX FAIL → retry Agent → max 2 iter → escalation | ❌ | — | — | — |
| Phase 1.5 — J2_MATRIX duplicati identificati e rimossi | ❌ | — | — | — |
| Phase 1.5 — Partial failure Agent A (`SKILL.md:386`) | ❌ | — | — | — |
| Phase 2 — Tier 1 Confluence trovato vs WARNING | ❌ | — | — | — |
| Phase 3 — Test Plan struttura | ❌ | — | — | — |
| Phase 4a — developer aggiunge righe vs no | ❌ | — | — | — |
| Phase 4b — generazione 1 TC per riga (bijection check) | ❌ | — | — | — |
| Phase 4b — TC con `condition` multi-valore (H-07) | ❌ | — | — | — |
| Phase 4c — Gate #2 PASS al primo run | ❌ | — | — | — |
| Phase 4c — Gate #2 FAIL → rigenerazione selettiva → max 2 iter | ❌ | — | — | — |
| Phase 4c — Escalation asimmetrica (J3 PASS, J4 FAIL > 2 iter) | ❌ | — | — | — |
| Phase 4d — J5 gap ALTA/MEDIA/BASSA | ❌ | — | — | — |
| Phase 4d — developer aggiunge TC → rilancia Gate #2 | ❌ | — | — | — |
| Phase 4d — CONDITIONAL PASS | ❌ | — | — | — |
| Phase 5 — Tier 1 MCP create TC + raccolta chiavi | ❌ | — | — | — |
| Phase 5 — Tier 2/3 CSV semicolon valido | ❌ | — | — | — |
| Phase 5 — Mappatura ID → chiavi Jira | ❌ | — | — | — |

**Coverage workflow:** **2/31 branch = 6.5%**.

### 6.2 Missing edge cases (lista esplicita)

- **MEC-01:** Spec con 0 lookup tables, 0 regole composte → M_B/M_C dovrebbero essere vuote senza fallire J1_MATRIX.
- **MEC-02:** Spec con 100+ campi → M_FINAL può eccedere il context window per Phase 4b. Nessuna chunking strategy in `SKILL.md`.
- **MEC-03:** Spec in lingua diversa dall'italiano (es. EN, FR).
- **MEC-04:** AC con caratteri Unicode (apostrofo, accenti, simboli musicali per dominio SIAE).
- **MEC-05:** CSV con valori contenenti il separatore `;` — il template `reference/xray-csv-template.md:46` dice "non usare virgolette doppie a meno che il testo contenga il separatore" ma non specifica escaping.
- **MEC-06:** Story ID assente in Tier 2 (`SKILL.md:204` chiede esplicitamente ma non c'è eval).
- **MEC-07:** Agent tool negato in Phase 1.5 (`SKILL.md:802-811` documentato, mai testato).
- **MEC-08:** Write tool negato in Phase 1.5 (`SKILL.md:792-796` solo per CSV Tier 3, non per MFINAL.md).
- **MEC-09:** Spec con regola composta a 5 campi binari → 2^5=32 combinazioni → trigger H-09 ("ridotto per complessità").
- **MEC-10:** Cross-sezione vincolo referenziale con 5 sezioni dipendenti → 5 righe NEG simmetriche.
- **MEC-11:** Phase 0 confidence LOW per stack non riconosciuto (es. SAP, mainframe COBOL).
- **MEC-12:** Question-tree file `reference/question-trees.md` non trovato → fallback `SKILL.md:153-158` (mai testato).
- **MEC-13:** XRAY-TEMPLATES.md non trovato → fallback `SKILL.md:465-472`.
- **MEC-14:** Run concorrenti su due story diverse → MFINAL.md collision (H-13).
- **MEC-15:** J5 score < soglia desiderata ma developer accetta gap → CONDITIONAL PASS (H-15).

**Untested paths summary:** 31 branch workflow, 15 edge case → **46 path totali non testati**.

### 6.3 Golden output assessment

- **Esistenza:** Nessun golden output identificato nel filesystem.
  - Ricerca: `find skills/siae-qa -type f | xargs grep -l "golden\|fixture\|test_"` → solo SKILL.md (self-reference).
  - `evals/eval-sets/siae-qa/` contiene solo `trigger.json`.
- **Conseguenza:** Nessuna regressione catturata su modifiche al workflow. Esempi pericolosi:
  - Cambio del titolo "esempio TC" in `SKILL.md:484-491` → nessun test fallirebbe.
  - Refactor di M_FINAL schema da 6 a 7 colonne → nessun test fallirebbe.

---

## 7. Enterprise Maturity Scorecard

| # | Dimensione | Score (1-5) | Evidence + motivazione |
|---|------------|:-----------:|------------------------|
| 1 | Specification clarity | 3 | Workflow chiaro (5 fasi, 4 sub-phase), hard-gate documentati. Ma 17 hotspot non-determinismo (Phase 4) e doppio source of truth con XRAY-TEMPLATES.md obsoleto abbassano il rating. `SKILL.md:439` (Phase 4a) vs `XRAY-TEMPLATES.md:110-124` (Phase 4a vecchio). |
| 2 | Reproducibility | 2 | H-01, H-03, H-07, H-08, H-09 producono divergenze su stesso input. CSV format (O-15) è l'unico output bit-by-bit deterministico. |
| 3 | Observability | 3 | Formato fisso J1/J2/J3/J4 + GATE #2 REPORT + COVERAGE CERTIFICATE permette parsing. Tracciabilità `matrix_row_id` nel campo Description è eccellente (`SKILL.md:482`). Ma: nessun timestamp standardizzato, nessun esecuzione log, nessun coverage_certificate persistito (O-13). |
| 4 | Error handling | 3 | Partial failure (`SKILL.md:386-389`) e Permission Denied (`SKILL.md:790-822`) coperti per pattern principali. Gap: nessuna policy per "Matrix A genera matrix_row_id duplicati", "MFINAL.md write fallito a metà", "MCP Xray crea TC parzialmente". |
| 5 | Versioning & change control | 1 | Frontmatter `SKILL.md:1-7` ha solo `name` e `description` — **nessun `version`, nessun `last_modified`, nessun changelog**. Plugin version (`marketplace.json:13` = 1.49.0) non rispecchia versione skill. Modifica recente verso M_FINAL non documentata nel file. |
| 6 | Documentation completeness | 2 | XRAY-TEMPLATES.md ha 4 sezioni dead (Riepilogo Copertura, Matrice Scenari, Domande Elicitazione, Checklist). question-trees.md e xray-csv-template.md sono allineate. Nessun rationale documentato per le scelte di design (perché 75% threshold? perché max 16? perché 3 AC cap?). |
| 7 | Output schema enforceability | 1 | **Zero schema JSON formali.** Tutti gli output (M_FINAL, TC_DRAFT, certificate, mappatura, J-reports) sono markdown/testo libero con pattern fissi descritti in prosa. Impossibile validare programmaticamente in pre-export. |
| 8 | Idempotency | 2 | Ri-eseguire la skill sulla stessa story produce M_FINAL diverso (H-08, H-09, H-10) e prefissi TC diversi (H-01). MFINAL.md sovrascritto senza versionamento. Re-run "perde" la prima esecuzione. |
| 9 | Failure modes documentation | 3 | Sezione "Permission Denied Handling" (`SKILL.md:790-822`) + "QUANDO SEI BLOCCATO" (`SKILL.md:826-834`) coprono ~6 failure mode. Manca: documentazione di cosa succede se J5 fallisce internamente, se MCP Xray crea TC a metà, se CSV import Xray rifiuta header. |
| 10 | Test determinism | 1 | I 2 test esistenti (trigger.json) sono `should_trigger: bool` — deterministici per costruzione. Ma coprono solo trigger, non workflow. **Nessun functional/e2e/golden test** sul workflow output. Stesso input non è verificabile per regressione. |
| **TOT** | | **24 / 50** | **Bronze tier — production-usable con rischi noti** |

### Top-3 gap critici (dalla scorecard)

1. **Dim. 5 + 7 (Versioning + Schema)**: 1+1 = 2/10. La skill non ha né version control né schema enforceability — significa che ogni modifica al SKILL.md o agli output non può essere tracciata né validata. Gold tier richiede `version: x.y.z`, changelog inline, schemi JSON parsabili.
2. **Dim. 10 (Test determinism)**: 1/5. 0 functional eval, 0 golden output. La skill non ha rete di sicurezza per regressioni.
3. **Dim. 2 (Reproducibility)**: 2/5. 17 hotspot identificati. Senza fix dei naming inconsistenti (H-01, H-03) e delle soglie ambigue (H-07/8/9/10), la skill produce output divergenti.

---

## 8. Findings — Critical Issues

### F-CRIT-01 — Doppio schema prefisso TC (POS/NEG/EDGE/ROLE vs no-prefix/EDGE/NEG/PROFILO)

- **Hotspot:** H-01
- **Evidence:** `SKILL.md:495` ⊥ `XRAY-TEMPLATES.md:70,82-85,204`
- **Impact:** Output non deterministico sul campo `Scenario (descrizione)` — colonna esportata in CSV/Jira che alimenta dashboard Xray, filtri di report e siae-automation.
- **Severity:** CRITICAL

### F-CRIT-02 — XRAY-TEMPLATES.md sezioni "Matrice Scenari" / "Riepilogo Copertura" / "Domande Elicitazione" / "Checklist" descrivono workflow pre-M_FINAL

- **Hotspot:** H-02, H-03, H-04, H-06
- **Evidence:** `XRAY-TEMPLATES.md:95-150,189-213`
- **Impact:** Il "deliverable" referenziato dalla checklist (`SKILL.md:751-754`) non verifica i bloccanti reali (M_FINAL, Gate, certificate). Self-dichiarazione di "completato" possibile senza i bloccanti.
- **Severity:** CRITICAL

### F-CRIT-03 — Zero functional/e2e test sul workflow output

- **Hotspot:** intera sezione 6
- **Evidence:** `evals/eval-sets/siae-qa/` contiene solo `trigger.json`. `evals/trigger-evals/siae-qa.json` è **duplicato byte-identico**.
- **Impact:** 31 branch workflow + 15 edge case non testati. Modifiche allo SKILL.md non producono regressioni rilevabili.
- **Severity:** CRITICAL

### F-CRIT-04 — Nessuno schema JSON formale per M_FINAL, TC_DRAFT, coverage_certificate

- **Hotspot:** Phase 6 dim. 7
- **Evidence:** Tutti gli output sono descritti in prosa. Esempio: `SKILL.md:654-671` template Coverage Certificate è un blocco markdown senza schema.
- **Impact:** Impossibile validare programmaticamente; siae-automation deve fare parsing fragile della mappatura O-16.
- **Severity:** CRITICAL

### F-HIGH-01 — SKILL.md frontmatter senza `version`, senza changelog inline

- **Hotspot:** Phase 6 dim. 5
- **Evidence:** `SKILL.md:1-7`
- **Impact:** Impossibile tracciare quando il refactor M_FINAL è stato introdotto, su quali story è stata usata la vecchia matrice scenari.
- **Severity:** HIGH

### F-HIGH-02 — MFINAL.md / TC_DRAFT.md scritti in path ambiguo ("directory del progetto corrente")

- **Hotspot:** H-13
- **Evidence:** `SKILL.md:379,499`
- **Impact:** Run concorrenti collidono; nessuna policy di cleanup; nessuna persistenza versionata.
- **Severity:** HIGH

### F-HIGH-03 — Coverage Certificate (O-13) e Mappatura ID (O-16) non salvati su file

- **Hotspot:** Output catalog (sez. 2.3)
- **Evidence:** `SKILL.md:654-671` e `XRAY-TEMPLATES.md:154-176` — entrambi descritti come "output finale" ma nessun Write tool referenziato. Mappatura "Salva la mappatura come output della skill" (`XRAY-TEMPLATES.md:176`) è imperativa ma senza target path.
- **Impact:** Handoff verso collaudo e siae-automation perde dati se conversazione viene compattata o chiusa.
- **Severity:** HIGH

### F-HIGH-04 — "Set di valori rappresentativo" / "Esiti distinti" / "Max 16 combinazioni" senza regola di selezione

- **Hotspot:** H-07, H-09, H-10
- **Evidence:** `SKILL.md:493,321,323`
- **Impact:** Matrix B non deterministica → M_FINAL non deterministica → TC divergenti.
- **Severity:** HIGH

### F-HIGH-05 — `evals/trigger-evals/siae-qa.json` duplicato byte-identico di `evals/eval-sets/siae-qa/trigger.json`

- **Hotspot:** sez. 2.1
- **Evidence:** Entrambi i file hanno 20 entry identiche.
- **Impact:** Doppia manutenzione, drift garantito nel tempo.
- **Severity:** HIGH

---

## 9. Findings — Minor Issues

### F-MED-01 — `SKILL.md:167` riferimento orfano a "Phase 4a (matrice scenari)" — H-05

### F-MED-02 — Confidence band (`XRAY-TEMPLATES.md:30-33`) non riproducibile da segnali boolean — H-11

### F-MED-03 — Naming inconsistente `MEDIO/MEDIA/BASSA` per priorità gap (`SKILL.md:618` vs `SKILL.md:667-668`)

### F-MED-04 — `Automazione`/`NRT` modificabili pre-Gate #2 ma fuori M_FINAL schema — H-17

### F-MED-05 — "CONDITIONAL PASS" trigger senza campo nel template certificate — H-15

### F-MED-06 — `coverage_score` di J5 non operazionalizzato — H-14

### F-MED-07 — "Un sì o ok" valido in `SKILL.md:298` ma invalido in `SKILL.md:202-203` — H-16

### F-MED-08 — Massimo 3 AC per requisito senza criterio di selezione — H-08

### F-MED-09 — `SKILL.md` 834 righe senza Table of Contents

### F-LOW-01 — Tabella Anti-Razionalizzazione (32 righe, `SKILL.md:715-747`) overlap con Vincoli Non Negoziabili (12 punti, `SKILL.md:758-772`) e blocchi EXTREMELY-IMPORTANT (×12)

### F-LOW-02 — 12 blocchi `<EXTREMELY-IMPORTANT>` — densità eccessiva diluisce il segnale di priorità

### F-LOW-03 — Inconsistenza ortografica "Phase" vs "Fase" mescolate nello stesso doc

### F-LOW-04 — `XRAY-TEMPLATES.md` ha ToC ma `SKILL.md` no (asimmetria UX)

### F-LOW-05 — `[POS]` esempio in `SKILL.md:486` contraddice "Nessun prefisso = scenario positivo" di `XRAY-TEMPLATES.md:82`

### F-LOW-06 — `M_FINAL` (underscore in SKILL.md prosa) vs `MFINAL.md` (no underscore in filename) — confusione tipografica

---

## 10. Remediation Plan

### 10.1 Tabella completa raccomandazioni

| ID | Categoria | Severity | Effort | File:section | Before | After (proposta) | Test di accettazione |
|----|-----------|:--------:|:------:|--------------|--------|------------------|----------------------|
| **R-001** | Determinismo | CRITICAL | M | `XRAY-TEMPLATES.md:70-85,99-106,110-124,128-150,189-213` | Sezioni "Matrice Scenari", "Riepilogo Copertura", "Domande Elicitazione", "Checklist di Verifica", "Prefissi di Categoria" descrivono workflow pre-M_FINAL (4 categorie Positivi/Edge/Negativi/Profilazioni; prefissi [EDGE]/[NEG]/[PROFILO]) | Riscrivere le 4 sezioni allineate a M_FINAL: `Distribuzione: N POS / N NEG / N EDGE / N ROLE`; prefissi `[POS]/[NEG]/[EDGE]/[ROLE]`; checklist con voci M_FINAL/Gate#1/Gate#2/J5/coverage_certificate/mappatura | Diff atomico: tutte le occorrenze di `PROFILO` → `ROLE`; `Positivi/Edge/Negativi/Profilazioni` → `POS/NEG/EDGE/ROLE`; checklist deve contenere i 7 nuovi item (verificare con grep) |
| **R-002** | Determinismo | CRITICAL | S | `SKILL.md:495` ⊥ `XRAY-TEMPLATES.md:82` | `SKILL.md:495`: "[POS], [NEG], [EDGE], [ROLE]" vs `XRAY-TEMPLATES.md:82`: "Nessun prefisso = scenario positivo (happy path)" | Decidere: **tutti i TC hanno prefisso obbligatorio** (consigliato) → uniformare `XRAY-TEMPLATES.md:82-85` a `[POS]/[NEG]/[EDGE]/[ROLE]`; aggiornare esempi righe 64-71 di `reference/xray-csv-template.md` con prefisso [POS] | grep -c '\[POS\]' su sample TC = numero righe POS di M_FINAL |
| **R-003** | Spec | CRITICAL | M | `SKILL.md:1-7` + nuovo `reference/schemas/` | Nessuno schema JSON formale per M_FINAL, TC_DRAFT, coverage_certificate | Aggiungere `reference/schemas/m_final.schema.json`, `reference/schemas/tc_draft.schema.json`, `reference/schemas/coverage_certificate.schema.json` (JSON Schema draft 2020-12). Aggiungere validator script `reference/scripts/validate_outputs.py` | Validator esegue successo su 3 golden output di esempio (R-005) |
| **R-004** | Spec | CRITICAL | S | `SKILL.md:1-7` frontmatter | `name`, `description` only | Aggiungere `version: 2.0.0` (M_FINAL refactor), `last_modified: 2026-04-13`, `changelog_ref: CHANGELOG.md#siae-qa` | grep `version:` su skills/siae-qa/SKILL.md ritorna 1 risultato |
| **R-005** | Test | CRITICAL | L | Nuovo `evals/eval-sets/siae-qa/golden/` | Solo `trigger.json` (10+10) | Aggiungere 3 golden fixture: (1) `enumerative_spec/` (spec migrazione CSV con 12 campi+lookup), (2) `functional_be/` (story BE standard con 4 AC), (3) `role_based/` (story Auth con 3 ruoli). Ogni fixture: `input.md` + `expected_mfinal.json` + `expected_tc_draft.json` + `expected_certificate.json` | Test runner Python esegue confronto strutturale (campi, conteggi, prefissi) — 0 diff |
| **R-006** | Test | CRITICAL | M | `evals/functional_eval.py` (estendere) | No functional eval per siae-qa | Aggiungere caso `siae-qa_workflow`: Phase 0 → 1.5 → 4b → Gate #2. Verifica: bijection TC↔M_FINAL, specificity di campione, formato GATE #2 REPORT parsabile | functional_eval reporter chiude PASS su 3 golden |
| **R-007** | Determinismo | HIGH | S | `SKILL.md:493` | "1 TC con un set di valori rappresentativo (es. importo=1500, valuta=EUR)" | "1 TC con i valori **frontiera bassi** del range condition (primo valore del primo set valido nell'ordine sintattico della spec). Es. condizione `importo > 1000 AND valuta IN (EUR, USD)` → importo=1001, valuta=EUR." | Stesso input AND/OR → stesso TC bit-by-bit |
| **R-008** | Determinismo | HIGH | S | `SKILL.md:197` | "massimo 3 AC per requisito" | "Massimo 3 AC per requisito, selezionati nell'ordine: (a) happy path principale, (b) primo errore di validazione esplicitato nel testo, (c) primo edge case esplicitato nel testo. Se >3 candidati: lista completa va aggiunta come righe addizionali in Phase 1.5 M_FINAL — NON scartare AC, sposta granularità da Phase 1 a Phase 1.5." | Test con 7 AC candidati: output sempre 3 AC nello stesso ordine |
| **R-009** | Determinismo | HIGH | S | `SKILL.md:321,323` | "Mantieni solo combinazioni con esiti DISTINTI" + "max 16 combinazioni; se superi, annota ridotto" | "Esito distinto = differenza nello status code restituito O nel messaggio di errore class (errore validazione vs autorizzazione vs business). Se > 16 combinazioni: selezione pairwise covering (algoritmo IPOG). Annota `reduction_strategy: pairwise_ipog` in source_ref." | Spec con 5 boolean → 32 combo → 16 selezionate con copertura pairwise; deterministico run-to-run |
| **R-010** | Spec | HIGH | S | `SKILL.md:379,499` | "directory del progetto corrente" | Specificare path canonico: `docs/qa/{STORY_ID}/MFINAL.md`, `docs/qa/{STORY_ID}/TC_DRAFT.md`, `docs/qa/{STORY_ID}/coverage_certificate.json`. Aggiungere policy cleanup: file esistenti → suffix `.bak.{timestamp}`. | Run concorrenti su 2 story diverse: 4 file separati creati, 0 collision |
| **R-011** | Spec | HIGH | S | `SKILL.md:670-673` + nuovo step Phase 5 | Coverage Certificate visualizzato in chat ma non persistito | Aggiungere step "Write coverage_certificate.json in docs/qa/{STORY_ID}/" prima di Phase 5. Schema definito in R-003. | File esiste post-export; parsing JSON valido |
| **R-012** | Spec | HIGH | S | `XRAY-TEMPLATES.md:154-176` + nuovo step Phase 5 | Mappatura ID descritta ma non salvata | Aggiungere step Write `docs/qa/{STORY_ID}/xray_id_mapping.json` con schema `{ csv_id: int, xray_key: string, scenario_title: string }[]` come output Phase 5. Input obbligatorio per siae-automation. | File presente; siae-automation può leggerlo |
| **R-013** | Test | HIGH | S | `evals/eval-sets/siae-qa/trigger.json` ↔ `evals/trigger-evals/siae-qa.json` | File duplicati byte-identico | Eliminare uno dei due. Aggiungere link simbolico O dichiarare il file canonical in README evals. | `diff` su due path attesi non duplicate o entrambi puntano allo stesso file |
| **R-014** | Determinismo | MEDIUM | S | `SKILL.md:298` ⊥ `SKILL.md:202-203` | Definizione conflittuale di "conferma valida" | Unificare: "Conferma valida = risposta esplicita affermativa (`sì`, `confermato`, `ok` ESCLUSIVAMENTE seguito da newline o EOF) ENTRO la stessa user turn della richiesta. Risposte ambigue (`forse`, `boh`, silenzio) → richiedi nuovamente." | grep "conferma valida" → singola definizione |
| **R-015** | Spec | MEDIUM | S | `SKILL.md:617-618` | `coverage_score: % righe M_FINAL con TC di qualità verificata` | Definire formula: `coverage_score = (count(matrix_row_id ∈ TC_DRAFT WHERE J3_PASS AND J4_PASS) / count(M_FINAL.rows)) * 100`. Aggiungere soglia warning: `score < 90% → certificato segnato CONDITIONAL` | J5 produce stesso score su stesso input |
| **R-016** | Spec | MEDIUM | S | `SKILL.md:654-671` | Template certificate senza campo `status` | Aggiungere riga: `Stato: FULL_PASS / CONDITIONAL_PASS / FAIL`. CONDITIONAL_PASS trigger automatico se: (a) gap J5 MEDIA aperti, (b) coverage_score < 90%. | grep `Stato:` su 3 golden certificate restituisce 3 status diversi |
| **R-017** | Spec | MEDIUM | S | `SKILL.md:167` | "Questa card e' l'input aggiuntivo per Phase 4a (matrice scenari)" | "Questa card è input per il blocco serializzazione di Phase 1.5: campo `info ruolo/permesso` per Matrix C, campo `stack tecnologico` per scelta esempi in Matrix A." | grep "Phase 4a (matrice scenari)" → 0 risultati |
| **R-018** | Determinismo | MEDIUM | S | `SKILL.md:502` + nuovo step 4b | Automazione/NRT modificabili "prima del gate" ma fuori M_FINAL | Aggiungere step in Phase 4b: "Default deterministico: `Automazione=N`, `NRT=Y` (come da `SKILL.md:834`). Il developer può sovrascrivere solo dopo Gate #2 PASS, pre-export, e la modifica viene registrata in `coverage_certificate.json` campo `developer_overrides`." | TC default sempre `N/Y`; override richiede registro |
| **R-019** | Spec | MEDIUM | M | `XRAY-TEMPLATES.md:30-33` | Confidence "HIGH (>= 90%)" ma derivazione da segnali boolean | Definire formula: `confidence = min(100, 30 * signal_count_strong + 15 * signal_count_weak)`. HIGH = ≥90 (i.e., 3+ forti o 2 forti+2 deboli). | Stesso elenco di segnali → stessa band |
| **R-020** | Logica/ordine | LOW | S | `SKILL.md:1-50` | Nessuna ToC | Aggiungere ToC dopo `> Tipo: Rigid` (riga 43): elenco H2 con anchor link | grep `^## ` → ToC contiene tutti i headings |
| **R-021** | Logica/ordine | LOW | M | `SKILL.md:715-747` ⊥ `SKILL.md:758-772` ⊥ blocchi EXTREMELY-IMPORTANT | Triplicazione "anti-razionalizzazione" | Consolidare: spostare le 32 righe di "Anti-Razionalizzazione" in `reference/anti-rationalization.md`; SKILL.md mantiene solo i 12 "Vincoli Non Negoziabili" + max 5 blocchi `<EXTREMELY-IMPORTANT>` (uno per ogni hard-gate) | `wc -l SKILL.md` riduce di ~50 righe; nessuna regola persa |
| **R-022** | Logica/ordine | LOW | S | `SKILL.md` + `XRAY-TEMPLATES.md` | Mix `Phase` / `Fase` | Standardizzare: `Phase` per i numeri (`Phase 0`, `Phase 1`), `Fase` non più usato. | grep `^### Fase` → 0 risultati |
| **R-023** | Logica/ordine | LOW | S | `SKILL.md:617-618,654-671` | `ALTA/MEDIA/BASSA` vs `MEDIO/MEDIA/MEDIO` | Standardizzare: `HIGH / MEDIUM / LOW` (consistenza con confidence band). Aggiornare template certificate. | grep `ALTA\|MEDIO\|BASSA` → 0 risultati su priorità gap |

### 10.2 Top 5 prioritized actions (Severity DESC, Effort ASC)

| Rank | ID | Severity | Effort | Sintesi |
|:---:|----|:--------:|:------:|---------|
| 1 | **R-002** | CRITICAL | S | Uniformare prefisso TC `[POS]/[NEG]/[EDGE]/[ROLE]` (sostituire `PROFILO` + "nessun prefisso = positivo"). Edit chirurgico. Sblocca H-01 |
| 2 | **R-004** | CRITICAL | S | Aggiungere `version: 2.0.0` + `last_modified` al frontmatter SKILL.md. 3 righe |
| 3 | **R-001** | CRITICAL | M | Riscrivere 4 sezioni di `XRAY-TEMPLATES.md` allineate a M_FINAL. Sblocca H-02, H-03, H-04, H-06 |
| 4 | **R-003** | CRITICAL | M | Schemi JSON per M_FINAL/TC_DRAFT/certificate + validator Python. Sblocca dim. 7 della scorecard |
| 5 | **R-005** | CRITICAL | L | 3 golden fixture + harness eval. Sblocca dim. 10 |

### 10.3 Roadmap suggerita

**Sprint 1 (5 giorni)** — Stop the bleeding (4 quick win + 2 critical):
- R-002 (1h) — uniforma prefisso TC
- R-004 (15 min) — versioning frontmatter
- R-013 (15 min) — dedup file eval
- R-022 (30 min) — `Fase` → `Phase`
- R-001 (4h) — riscrivi XRAY-TEMPLATES.md sezioni dead
- R-010 (1h) — path canonico MFINAL.md/TC_DRAFT.md

**Sprint 2 (5 giorni)** — Determinismo:
- R-007 (1h) — set valori frontiera per condition multi
- R-008 (1h) — criterio selezione 3 AC
- R-009 (3h) — pairwise IPOG + reduction_strategy
- R-014 (30 min) — definizione "conferma valida" unica
- R-018 (1h) — default deterministico Automazione/NRT
- R-019 (2h) — formula confidence

**Sprint 3 (5 giorni)** — Spec hardening + Test:
- R-003 (1d) — 3 JSON schemas + validator
- R-011 (1h) — persist coverage_certificate.json
- R-012 (1h) — persist xray_id_mapping.json
- R-015 (1h) — formula coverage_score
- R-016 (1h) — campo `Stato` nel certificate
- R-005 (2d) — 3 golden fixture
- R-006 (1d) — functional eval esteso

**Backlog (priorità inferiore):**
- R-017, R-020, R-021, R-023 — cleanup logico (ToC, anti-rationalization consolidation, naming priorità)

---

## 11. Appendix — Evidence Catalog

Citazioni testuali raw per ogni claim del report. Path relativo a `skills/siae-qa/`.

### A.1 Prefisso TC inconsistente (F-CRIT-01, H-01)

```
SKILL.md:495     **Prefisso titolo:** usa il `test_type` della riga (`[POS]`, `[NEG]`, `[EDGE]`, `[ROLE]`).
SKILL.md:486     Titolo:        [POS] CATEGORY = "F" → migrazione come feature
XRAY-TEMPLATES.md:70   | Scenario (descrizione) | Stringa | Si (prima riga) | Titolo del Test Case — includi la categoria: es. `[EDGE] ...`, `[NEG] ...`, `[PROFILO] ...` |
XRAY-TEMPLATES.md:82-85
                 - Nessun prefisso = scenario positivo (happy path)
                 - `[EDGE]` = edge case (limite, vuoto, volume estremo)
                 - `[NEG]` = scenario negativo / alternativo (errore, input non valido, dipendenza assente)
                 - `[PROFILO]` = scenario specifico di ruolo / profilazione
XRAY-TEMPLATES.md:204  - [ ] I titoli Scenario usano i prefissi `[EDGE]`, `[NEG]`, `[PROFILO]` dove appropriato
```

### A.2 Phase 4a dead doc (F-CRIT-02, H-02)

```
SKILL.md:439-456
   #### 4a — Verifica e completamento M_FINAL [input: Fase 1.5]
   **Input:** M_FINAL prodotta da Fase 1.5 (Gate #1 già PASS).
   Non è più una fase di elicitazione scenari astratti. La matrice guida la generazione.
   1. **Mostra M_FINAL** al developer in forma tabellare compatta:
      - Totale righe (= TC attesi)
      - Distribuzione: N POS / N NEG / N EDGE / N ROLE
      - Entità coperte
   2. **Chiedi una sola domanda:** "La matrice ha {N} righe, stimati {N} TC. ..."
   ...

XRAY-TEMPLATES.md:110-124
   ## Template Matrice Scenari
   Output atteso della fase 4a — matrice scenari compilata prima della generazione:
   ```
   Categoria              | Scenari identificati
   -----------------------|-----------------------------------------------
   Positivi (happy path)  | [lista da AC + eventuali varianti]
   Edge case              | [lista da domande o da AC]
   Alternativi/negativi   | [lista da domande o da AC]
   Profilazioni/ruoli     | [lista da domande, o "N/A - nessun controllo ruolo"]
   ```
   ...
   **Non puoi procedere alla generazione con categorie non valutate.**
```

### A.3 Riepilogo Copertura obsoleto (F-CRIT-02, H-03)

```
SKILL.md:447     - Distribuzione: N POS / N NEG / N EDGE / N ROLE

XRAY-TEMPLATES.md:99-106
   ```
   Riepilogo copertura:
     Positivi:    N TC
     Edge case:   N TC
     Negativi:    N TC
     Profilazioni: N TC
     TOTALE:      N TC
   ```
```

### A.4 Checklist non aggiornata (F-CRIT-02, H-04)

```
SKILL.md:751-754
   ## CHECKLIST DI VERIFICA
   Vedi [XRAY-TEMPLATES.md](XRAY-TEMPLATES.md) sezione "Checklist di Verifica" per la checklist completa.
   **Non riesci a spuntare tutte le caselle? Il workflow non e' completo. Ricomincia dalla fase bloccata.**

XRAY-TEMPLATES.md:200
   - [ ] Matrice scenari compilata (4 categorie valutate: positivi, edge, negativi, profilazioni)
XRAY-TEMPLATES.md:203
   - [ ] Presenti TC per scenari positivi, edge case, negativi e profilazioni (se applicabili)
```
La checklist (`XRAY-TEMPLATES.md:189-213`) non contiene voci su: MFINAL.md, Gate #1 (J1/J2), Gate #2 (J3/J4), J5 audit, coverage_certificate, mappatura ID Xray.

### A.5 Test eval (F-CRIT-03)

```
evals/eval-sets/siae-qa/
  └── trigger.json  (10 should_trigger=true + 10 should_trigger=false)

evals/trigger-evals/siae-qa.json  (byte-identical duplicate)

Tutto il workflow output: 0 fixture, 0 golden, 0 functional eval.
```

### A.6 Schema enforceability (F-CRIT-04)

`SKILL.md:234-241` (M_FINAL schema in tabella markdown), `SKILL.md:484-491` (TC esempio in code-block), `SKILL.md:654-671` (Certificate template in code-block). Nessun file `.json` schema in repo.

### A.7 Versioning (F-HIGH-01)

```
SKILL.md:1-7
   ---
   name: siae-qa
   description: >
     Genera documentazione test formale per Xray a completamento implementazione.
     Trigger: completamento brainstorming (Fase 2), completamento ciclo TDD (Fase 5),
     /forge-qa.
   ---
```

### A.8 Path ambiguo (F-HIGH-02, H-13)

```
SKILL.md:379  Usa Write tool per salvare M_FINAL su `MFINAL.md` nella directory del progetto corrente.
SKILL.md:499  Usa Write tool per salvare tutti i TC generati su `TC_DRAFT.md` nella directory del progetto.
```

### A.9 Output non persistito (F-HIGH-03)

```
SKILL.md:654-671  Coverage Certificate (formato testuale, no Write step)
XRAY-TEMPLATES.md:154-176  Mappatura ID (formato testuale, "Salva la mappatura come output della skill" senza target)
```

### A.10 Set rappresentativo / esiti distinti / max 16 (F-HIGH-04, H-07/9/10)

```
SKILL.md:493  ...genera **1 TC** con un set di valori rappresentativo (es. importo=1500, valuta=EUR)...
SKILL.md:321  Mantieni solo combinazioni con esiti DISTINTI
SKILL.md:323  - Limite: max 16 combinazioni per regola; se superi, annota "ridotto per complessità"
```

### A.11 Eval duplicato (F-HIGH-05)

```
$ diff evals/eval-sets/siae-qa/trigger.json evals/trigger-evals/siae-qa.json
(nessun output — identici)
```

### A.12 Phase 4a residuo (F-MED-01, H-05)

```
SKILL.md:167  Questa card e' l'input aggiuntivo per Phase 4a (matrice scenari).
```

### A.13 Confidence band (F-MED-02, H-11)

```
XRAY-TEMPLATES.md:30-33
   **Confidence:**
   - **HIGH (>= 90%):** 2+ segnali forti convergenti
   - **MEDIUM (60-89%):** 1 segnale forte o 2+ deboli
   - **LOW (< 60%):** segnali ambigui o assenti
```

### A.14 Priorità inconsistente (F-MED-03)

```
SKILL.md:618    lista gap prioritizzata (ALTA / MEDIA / BASSA)
SKILL.md:667-668
   J5 Gap MEDIA aperti:  N (sprint successivo)
   J5 Gap BASSA aperti:  N (opzionali)
SKILL.md:122-123  | 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-qa |
```

### A.15 Automazione/NRT (F-MED-04, H-17)

```
SKILL.md:502  Il developer puo' modificare `Automazione` e `NRT` prima di procedere.
SKILL.md:834  | Developer non sa quali campi Automazione/NRT usare | Default: Automazione=N, NRT=Y. ...
```
Default deterministico non è nel template TC (`SKILL.md:484-491`).

### A.16 CONDITIONAL PASS (F-MED-05, H-15)

```
SKILL.md:640  → Procedi direttamente a Fase 5 (export) con il certificate "CONDITIONAL PASS"
SKILL.md:654-671  (template Certificate non contiene il campo "CONDITIONAL PASS")
```

### A.17 coverage_score (F-MED-06, H-14)

```
SKILL.md:617-618
     - coverage_score: % righe M_FINAL con TC di qualità verificata
     - lista gap prioritizzata (ALTA / MEDIA / BASSA)
```
Definizione non riproducibile (cfr. J4 specificità: `SKILL.md:562`).

### A.18 Conferma valida inconsistente (F-MED-07, H-16)

```
SKILL.md:202-203
   Se l'utente non risponde o risponde in modo ambiguo: **blocca e chiedi di nuovo esplicitamente** ...
   Un silenzio o un "ok" generico non è una conferma valida.
SKILL.md:298
   Non lanciare Matrix A/B/C senza risposta esplicita. Un "sì" o "ok" è sufficiente ...
```

### A.19 Cap 3 AC (F-MED-08, H-08)

```
SKILL.md:197  Granularità: per requisiti funzionali standard massimo 3 AC.
```

### A.20 Duplicazione anti-razionalizzazione (F-LOW-01)

```
SKILL.md:715-747   Tabella Anti-Razionalizzazione (32 righe)
SKILL.md:758-772   Vincoli Non Negoziabili (13 punti)
SKILL.md:30-41, 222-232, 342-351, 511-522, 646-650, 803-806  (×6 blocchi EXTREMELY-IMPORTANT)
```

### A.21 Mix Phase/Fase (F-LOW-03)

```
SKILL.md:133  ## Phase 0 — Smart Req Typing
SKILL.md:171  ## WORKFLOW A 5 FASI
SKILL.md:173  ### Fase 1 — Lettura AC da Jira
SKILL.md:217  ### Fase 1.5 — Coverage Matrix Builder
```

---

## Open Questions (richiedono input umano)

1. **Q-01:** La direzione di refactor è "M_FINAL replaces Matrice Scenari" (uniformare a POS/NEG/EDGE/ROLE) o "M_FINAL coesiste con Matrice Scenari" (XRAY-TEMPLATES.md mantiene 4-categorie per scenari fuori dalla spec strutturata)? — Determina se R-001 sostituisce o estende le sezioni obsolete.
2. **Q-02:** Il `coverage_certificate` deve essere checked-in nel repo (es. `docs/qa/{STORY_ID}/`) o solo allegato alla user story Jira? — Determina policy R-011.
3. **Q-03:** Esiste un consumer dell'output certificate diverso da siae-automation? (Confluence sync? Dashboard? Slack notification?) — Influenza schema JSON e campi mandatory.
4. **Q-04:** La soglia J4 = 75% è coerente con altre skill DevForge? (`siae-tdd`, `siae-verification`) — Audit cross-skill non in scope ma serve per evitare drift.
5. **Q-05:** `Tier 1 + Phase 1.5 Agent tool` richiede MCP atlassian E Agent tool simultaneamente disponibili. Cosa succede se uno è abilitato ma l'altro no? `SKILL.md:802-822` documenta Agent tool denied; manca caso "MCP up + Agent down" e "MCP down + Agent up + Tier 1 in pre-flight".

---

**Fine report. Audit completato in 7 fasi sequenziali, 21 raccomandazioni, 23 evidence citate.**
