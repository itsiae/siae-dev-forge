# Design Doc — siae-bug-hunter

**Data:** 2026-03-26
**Branch:** feat/siae-bug-hunter
**Autore:** AI-as-a-Judge — 7 giudici paralleli
**SP:** 13 SP-Umano / 5 SP-Augmented

---

## Contesto

La skill `siae-bug-hunter` nasce per coprire un gap preciso nel catalogo DevForge:

| Skill esistente | Cosa fa | Cosa NON fa |
|---|---|---|
| `siae-nr-test-flows` | Genera test di regressione per il futuro | Non trova bug già presenti |
| `siae-debugging` | Investiga un bug già segnalato | Non fa scansione proattiva |
| `siae-security` | Trova vulnerability OWASP/auth | Non copre bug funzionali utente |
| **`siae-bug-hunter`** | **Trova bug già presenti nel codice, deterministicamente** | — |

Il mandato è: *dato uno o più repo (FE, BE, BFF), analizza staticamente il codice seguendo
regole non negoziabili e produci un elenco di bug che un utente reale può incontrare,
con passi di riproduzione immediatamente azionabili.*

Score composito valutato dai 7 giudici prima del design: **gap CRITICO** — nessuna skill
nel catalogo copre questo quadrante.

---

## Decisioni Architetturali (ADR)

### ADR-1: Tipo Rigid, non Flexible

**Problema:** Una skill di bug detection che ammette salti di fase produce
output di qualità variabile e non confrontabile tra run.

**Decisione:** `siae-bug-hunter` è **Rigid**. Le fasi sono sequenziali e non saltabili.
Il singolo modulo opzionale è il `Context Interview` (Phase 0), che però
ha valori default se l'utente salta le domande.

**Alternativa scartata:** Flexible con moduli a scelta dell'utente —
permetterebbe di eseguire solo J3 (error handling) tralasciando J1 (API contract),
producendo un false sense of completeness.

---

### ADR-2: 5 Moduli di Detection + 1 Validatore Evidence

**Problema:** Un singolo LLM che analizza il codebase per bug può allucinare.
Il metodo AI-as-a-Judge con 7 agenti paralleli ha mostrato che i falsi positivi
si riducono drammaticamente quando ogni modulo ha un mandato stretto
e il validatore (J6) applica il protocollo a 3 condizioni prima di promuovere
un candidato a bug confermato.

**Decisione:**

| Modulo | Lens | Fonte design |
|---|---|---|
| M1 — API Contract | Disallineamenti FE↔BE↔BFF nei contratti | Judge 1 |
| M2 — State & Logic | Macchine a stati, calcoli, null, boundary | Judge 2 |
| M3 — Error Handling | Eccezioni swallowed, silent failure | Judge 3 |
| M4 — Async & Race | Race condition, stale closure, ottimistic update | Judge 4 |
| M5 — Data Validation | Validation gap cross-repo, overflow, timezone | Judge 5 |
| V6 — Evidence Gate | Three-Condition Gate, falsificatori | Judge 6 |

**Alternativa scartata:** Modulo singolo generico — nessuna profondità
di analisi garantita.

---

### ADR-3: Three-Condition Gate come filtro obbligatorio (no bypass)

**Problema:** LLM produce candidati bug a bassa evidenza che inquinano il report.

**Decisione:** Prima di promuovere un candidato a bug riportato, il V6
applica obbligatoriamente le 3 condizioni:

```
Condition A — Citation: file:riga esatto citato nel codice sorgente
Condition B — Literal Pattern: il pattern descritto testualmente (non inferito)
Condition C — Reachable Path: percorso utente che raggiunge quella riga
```

Se anche una sola condizione manca → il candidato è SUSPECT (solo in appendice)
o viene scartato. **Non esiste bypass a questo gate.**

**Alternativa scartata:** Soglia di confidenza a percentuale — introduce
ambiguità e deriva tra run diversi.

---

### ADR-4: 3 livelli di confidenza, non 5

**Problema:** Più livelli aumentano la sfumatura ma riducono il determinismo.
Un report con 5 livelli di confidenza porta i lettori a negoziare i confini
invece di agire.

**Decisione:** Solo 3 livelli:
- **CONFIRMED**: A + B + C + nessun falsificatore
- **PROBABLE**: A + B + C inferita dalla struttura del codice
- **SUSPECT**: solo A — solo in appendice, non contato come bug

**Alternativa scartata:** HIGH/MEDIUM/LOW/INFO/FALSE_POSITIVE —
troppo soggettivo, non determinabile staticamente.

---

### ADR-5: Input default = repo locali clonati

**Problema:** Integrazione con GitHub CLI aumenta la dipendenza da auth tokens
e latenza di rete; non aggiunge valore per l'uso principale (developer
locale che vuole scansionare il proprio codebase).

**Decisione:**
- Default: path locali (`/forge-bugs` su cwd oppure `/forge-bugs ./path/to/repo`)
- Alternativa supportata: URL GitHub via `gh clone` in `/tmp/`
- **Non supportato**: analisi su diff/PR — insufficiente per pattern analysis
  che richiede contesto globale

**Alternativa scartata:** URL-first — introduce dipendenza da auth in ogni run.

---

### ADR-6: Reference files per i 5 moduli (non inline in SKILL.md)

**Problema:** SKILL.md con 5 moduli inline supererebbe i 15k token,
compromettendo il load.

**Decisione:** Struttura file:
```
skills/siae-bug-hunter/
  SKILL.md                          ← orchestrazione fasi, max ~500 righe / 10k caratteri
  reference/
    module-1-api-contract.md        ← M1: regole grep + validation
    module-2-state-logic.md         ← M2: S1-S4, B1-B6
    module-3-error-handling.md      ← M3: FE/BE/BFF gaps
    module-4-async-race.md          ← M4: 8 pattern con SPR
    module-5-data-validation.md     ← M5: A-I categorie
    evidence-protocol.md            ← V6: Three-Condition Gate
    bug-report-template.md          ← Template output standard
```

**Alternativa scartata:** Tutto inline in SKILL.md — limite token superato.

**Nota post-implementazione:** il limite originale "max 200 righe" era una stima conservativa.
SKILL.md è cresciuto a ~400 righe con tier system e language detection multi-step.
Il constraint reale è il peso token (~10k caratteri), non il conteggio righe.

---

## Scope — Fasi di Implementazione

### Phase 0: Context Interview

**Domande obbligatorie (con default se saltate):**

| # | Domanda | Default |
|---|---|---|
| 0a | Tipo progetto? (BE/FE/Mobile/IaC/Data) | ALL |
| 0b | Stack tecnologico? | auto-detect |
| 0c | Entry point utente? | src/ main.ts / index.ts |
| 0d | Livello confidenza output? (CONFIRMED / CONFIRMED+PROBABLE / ALL) | CONFIRMED |
| 0e | Path da escludere? | test/ node_modules/ .git dist/ |

**Variabili di sessione iniettate:**
```
$PROJECT_TYPE, $STACK, $ENTRY_POINT, $CONFIDENCE_FILTER, $EXCLUDE_PATHS
```

---

### Phase 1: Code Ingestion

**Steps:**
1. Framework detection (stesso pattern di siae-nr-test-flows)
2. Harvest file rilevanti per layer (handlers, services, repositories, components)
3. Token budgeting: max 80.000 token per Phase 2, max 60 file per modulo (batch size TIER 4/5)
4. Annuncia: "Stack rilevato: {stack}. Avvio 5 moduli di detection."

---

### Phase 2: Pattern Extraction (5 moduli in parallelo)

Ogni modulo esegue le sue regole di estrazione.
Output di ogni modulo: lista candidati con `file:riga + pattern type`.

**M1 — API Contract Mismatch**
- Estrae chiamate API da FE (fetch, axios, HttpClient, Dio, Retrofit)
- Estrae endpoint da BE (@RestController, Express router, FastAPI, Gin)
- Estrae trasformazioni da BFF (aggregation layer, gateway)
- Cross-match: path, metodo, request body, response body, tipo, status code
- Conferma bug: campo usato senza optional chain + assente nella response BE

**M2 — State Machine & Business Logic**
- S1: Enum/costanti senza exhaustive switch → branch non gestiti
- S2: Transizioni di stato senza guard → stato illegale raggiungibile
- S3: Operazione critica (delete/send/charge) senza precondition check
- S4: `if (status == X)` senza `else` + side effect critico dopo
- B1: Divisione senza zero-check
- B2: Date comparison senza timezone normalization
- B3: Float/double per importi currency
- B4: `.find()` / `Optional.get()` senza null-check sul risultato
- B5: `>` vs `>=` inconsistente su stessa variabile
- B6: `list.get(0)` / `array[0]` senza `isEmpty()` guard

**M3 — Error Handling Gaps**
- FE: Promise senza `.catch()`, `fetch()` senza `response.ok`, `JSON.parse()` senza try/catch
- BE: `catch(Exception e)` con solo log (no re-throw), validation exception → 500
- BFF: Errore downstream swallowed, `res.status(200).json({error:...})`
- Conferma: è raggiungibile + l'errore è invisible (silent failure)

**M4 — Async & Race Conditions**
- FE 1.1: `useEffect` con fetch senza AbortController → stale response su navigazione
- FE 1.2: `Promise.all` che modifica stesso stato senza sequencing
- FE 1.3: Optimistic update senza rollback nel `.catch()`
- FE 1.4: Debounce/throttle con closure stantia su stato condiviso
- BE 2.1: Read-then-write senza `@Transactional` → check-then-act non atomico
- BE 2.2: Singleton con `HashMap` mutabile non thread-safe
- BE 2.3: Multipli `.save()` senza `@Transactional` → partial commit
- BE 2.4: Lazy loading JPA fuori da contesto transazionale

**M5 — Data Validation & Boundary**
- A: `required:true` in FE ma `@NotNull` assente in BE (o viceversa)
- B: Regex diversa per stesso campo in FE vs BE (email, CF, IBAN)
- C: Enum BE con valori non mappati nel dropdown FE
- D: `Long` in BE trasmesso come `number` JS → overflow > 2^53
- E: `varchar(N)` in DB ma `maxLength` assente nel FE input
- F: Data salvata UTC, visualizzata senza conversione locale
- G: Campo `null` dal BE renderizzato come stringa `"null"` nel template
- H: Stesso campo con validazione diversa in FE/BE/BFF
- I: Campo obbligatorio in BE opzionale in FE in alcuni flussi

---

### Phase 3: Evidence Validation (V6 — Three-Condition Gate)

Per ogni candidato dai 5 moduli:

**FASE 1 — Citation check (Condition A)**
- Citato il file con path relativo al progetto?
- Citata la riga esatta (numero)?
- Se no → scartato.

**FASE 2 — Literal pattern check (Condition B)**
- Il pattern è descritto testualmente (non inferito)?
- La descrizione include lo snippet letterale (max 5 righe)?
- Se la descrizione è generica ("potrebbe avere NullPointer") → SUSPECT, solo appendice.

**FASE 3 — Reachability check (Condition C)**
- Esiste un percorso utente che raggiunge quella riga?
- L'ingresso può essere: endpoint HTTP pubblico, form utente, scheduled job, webhook
- Se il codepath è dead code (dietro `if (false)`, dopo `return`, in test/) → scartato.

**FASE 4 — Falsification (6 test)**

| Test | Check | Se passa → |
|---|---|---|
| F1 | Optional chaining / null guard a monte? | Declassa o scarta |
| F2 | Type system garantisce non-nullability? | Scarta |
| F3 | Runtime guard esplicito? | Scarta |
| F4 | try-catch contiene il danno? | Declassa a PROBABLE |
| F5 | Dead code / feature flag sempre false? | Scarta |
| F6 | Type narrowing / type guard? | Scarta |

**Promozione finale:**
- A + B + C + tutti 6 test falliti → **CONFIRMED**
- A + B + C inferita + test F4 passa → **PROBABLE**
- Solo A → **SUSPECT** (appendice only)

---

### Phase 4: Output Generation

**Struttura output:**

```markdown
# Bug Hunter Report — {repo_name}
**Data:** {timestamp} | **Stack:** {stack} | **File scansionati:** {N}

## Riepilogo
- CONFIRMED: {N} | PROBABLE: {M} | SUSPECT: {K}
- Azione prioritaria: [descrizione top issue]

---

## BUG-001: [CONFIRMED] [M1-API Contract]

### {VERBO} + {OGGETTO} + {CONTESTO}
(es. "GET /api/users/{id} ritorna `name: null` usato senza null-check nel FE")

| Campo | Valore |
|---|---|
| Confidenza | CONFIRMED |
| Severità | CRITICAL / HIGH / MEDIUM / LOW |
| Modulo | M1 / M2 / M3 / M4 / M5 |
| File FE | `src/pages/UserProfile.tsx:42` |
| File BE | `UserController.java:87` |

**Evidenza (max 5 righe):**
```[codice incriminato con annotazione]```

**Impatto utente:**
{Cosa vede/sperimenta l'utente in italiano semplice}

**Precondizioni:**
- [ ] {precondizione verificabile 1}
- [ ] {precondizione verificabile 2}

**Passi per riprodurre:**
1. {azione atomica, con dato di test specifico}
2. {azione atomica}
3. {azione atomica — cosa osservare}

**Comportamento atteso:** {descrizione}
**Comportamento effettivo:** {descrizione}

**Fix suggerito (opzionale):**
{solo se ovvio dal codice, max 3 righe}

---
```

**Regole writing per i passi di riproduzione:**
1. Ogni passo = 1 azione atomica dell'utente
2. Il dato di test deve essere specifico (non "inserisci un valore invalido" ma "inserisci `' OR '1'='1' --`")
3. Ogni precondizione ha checkbox `[ ]` verificabile
4. L'ultimo passo specifica esplicitamente cosa osservare
5. Se il timing è critico, specificarlo ("Senza attendere, entro 150ms")
6. Se il test modifica stato persistente, aggiungere step di cleanup

---

## Metriche di Successo

| Metrica | Target |
|---|---|
| False positive rate (CONFIRMED) | < 5% |
| Recall su pattern noti | > 80% |
| Determinismo (stesso input → stesso output) | 100% |
| Coverage stack supportati | Spring/Express/FastAPI/Vue/React/Angular = 85% |
| Token budget Phase 2 | < 80.000 token |

---

## Fuori Scope

- Bug di performance (lentezza, timeout) senza data corruption
- Vulnerability OWASP/auth/encryption → usa `siae-security`
- Bug in `node_modules/`, `vendor/`, `dist/`
- Bug in librerie di terze parti
- Race condition con finestra temporale < 10ms (improbabile in produzione)
- Configuration errors (env vars mancanti, wrong .env)

---

## File da creare

```
skills/siae-bug-hunter/
  SKILL.md
  reference/
    module-1-api-contract.md
    module-2-state-logic.md
    module-3-error-handling.md
    module-4-async-race.md
    module-5-data-validation.md
    evidence-protocol.md
    bug-report-template.md
```
