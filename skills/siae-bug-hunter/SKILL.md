---
name: siae-bug-hunter
description: >
  Scansiona uno o più repository (FE, BE, BFF) e trova bug REALI già presenti nel codice,
  con passi di riproduzione deterministici per l'utente finale.
  Trigger: bug proattivo, caccia ai bug, bug hunter, scansione bug, pattern anti,
  codice rotto, potenziale bug, analisi pattern bug, verifica pattern rischio,
  /forge-bugs, trova bug, analisi statica bug, bug latenti, trova problemi nel codice.
---

# siae-bug-hunter — Proactive Bug Detection

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨 DevForge · BUG HUNTER                            ║
║         "Il codice si forgia. Il developer cresce."              ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Rigid | **Fase SDLC:** 6. QA Gate

---

## ISTRUZIONE DI APERTURA

Mostra il banner sopra, poi mostra immediatamente la pre-flight card (sezione successiva).

---

## LA LEGGE DI FERRO

```
NESSUN BUG RIPORTATO SENZA FILE:RIGA + PATTERN LETTERALE + PERCORSO UTENTE.
UN BUG SENZA EVIDENZA NEL CODICE È UN'ALLUCINAZIONE.
```

<EXTREMELY-IMPORTANT>
Stai per segnalare un bug?

Hai il file esatto e il numero di riga?
- NO → Non riportare il bug. Torna a leggere il codice.

Il pattern è descritto testualmente (snippet letterale dal codice)?
- NO → Non riportare il bug. Cita il codice esatto.

Esiste un percorso utente che raggiunge quella riga?
- NO → Il bug è dead code. Scartalo.

Hai tentato di FALSIFICARLO (optional chain? type guard? try-catch? dead code?)?
- NO → Fallo prima. Il 30% dei candidati viene falsificato.

Solo quando tutte e 4 le risposte sono SI → riporta il bug come CONFIRMED.
</EXTREMELY-IMPORTANT>

---

## POSIZIONAMENTO NEL CATALOGO

| Skill | Cosa fa | Differenza |
|---|---|---|
| `siae-bug-hunter` | **Trova bug presenti** nel codice (proattivo) | ← questa |
| `siae-nr-test-flows` | Genera test di regressione per il futuro | Non trova bug esistenti |
| `siae-debugging` | Investiga un bug già segnalato (reattivo) | Non fa scansione |
| `siae-security` | Trova vulnerability OWASP/auth | Non copre bug funzionali |

**Usa `siae-bug-hunter` quando:** vuoi sapere cosa è già rotto prima che lo segnalino gli utenti.

---

## PRE-FLIGHT CARD

```
┌─ BUG HUNTER — PRE-FLIGHT ────────────────────────────────────────┐
│                                                                    │
│  Input richiesto:                                                  │
│  □ Path del/dei repo da scansionare (o URL GitHub)                │
│  □ Stack tecnologico (se non auto-detectabile)                    │
│                                                                    │
│  Opzionale:                                                        │
│  □ Livello confidenza output (default: CONFIRMED)                 │
│  □ Path da escludere (default: test/ node_modules/ dist/ .git/)   │
│                                                                    │
│  Trigger: /forge-bugs [path|URL]                                  │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## PHASE 0 — CONTEXT INTERVIEW

Poni le seguenti domande (salta se già fornite dall'utente, usa default se l'utente non risponde):

| # | Domanda | Default |
|---|---|---|
| 0a | Quali repo scansionare? (FE / BE / BFF — path o URL GitHub). Opzionale: usa `git diff HEAD~1 --name-only` per identificare i repo coinvolti, ma la scansione avviene sempre sull'intero codebase, non sui soli file modificati. | cwd |
| 0b | Stack tecnologico? | auto-detect |
| 0c | Entry point utente principale? | `src/` → `main.ts` / `index.ts` / `App.tsx` |
| 0d | Livello output? Solo i certi (`CONFIRMED`) / Certi + da verificare manualmente (`CONFIRMED+PROBABLE`) / Tutto inclusi i sospetti (`ALL`) | CONFIRMED |
| 0e | Path da escludere? | `test/ node_modules/ dist/ .git/ __tests__/` |

**Inietta le variabili di sessione:**
```
$REPOS            ← lista path/URL da scansionare
$STACK            ← Java/TypeScript/Python/HCL/auto
$ENTRY_POINT      ← file/modulo di ingresso
$CONFIDENCE       ← CONFIRMED / PROBABLE / ALL
$EXCLUDE_PATHS    ← pattern di esclusione
```

Annuncia: `"Avvio Bug Hunter su {$REPOS}. Stack: {$STACK}. Output: {$CONFIDENCE}."`

---

## PHASE 1 — CODE INGESTION

**Step 1a — Language & Framework Detection**

Leggi `reference/language-registry.md` — tabella "Mappa Linguaggio → Estensioni → Codebase Type".

Rileva i linguaggi presenti esaminando le estensioni dei file e i manifest di progetto:

| Manifest trovato | Linguaggi / Framework |
|---|---|
| `pom.xml` / `build.gradle` | Java, Kotlin |
| `package.json` | TypeScript / JavaScript — poi leggi `dependencies` per Vue/React/Angular/Ionic/Express/NestJS |
| `pubspec.yaml` | Dart / Flutter |
| `requirements.txt` / `pyproject.toml` / `setup.py` | Python — poi controlla FastAPI/Django/Celery/PySpark |
| `go.mod` | Go |
| `*.sbt` / `build.sbt` | Scala |
| `*.csproj` / `*.sln` | C# / ASP.NET |
| `*.tf` / `terragrunt.hcl` | HCL / Terraform |
| `dbt_project.yml` / `*.sql` in `models/` | SQL / dbt |
| `*.sh` / `Makefile` + assenza di altri manifest | Shell / INFRA_SCRIPT |

Inietta `$LANG_IDS` = lista di tutti i LANG_ID rilevati (es. `[JAVA, TYPESCRIPT, VUE]`).

<EXTREMELY-IMPORTANT>
Per ogni file analizzato, determina il suo LANG_ID dalla tabella del registry.
Per ogni bug type, usa SOLO il pattern grep del LANG_ID corrispondente (vedi language-registry.md).
Applicare pattern di un linguaggio sbagliato produce falsi positivi certi.
Repo misti (mono-repo): ogni file ha il proprio LANG_ID — non c'è un unico profilo globale.
</EXTREMELY-IMPORTANT>

**Step 1b — Language & Codebase Type Detection**

Leggi `reference/language-registry.md`:
- §1 per la mappa completa estensioni → LANG_ID → Codebase Type
- §1b per i Python subtypes (FastAPI / Django / Flask / Spark / Celery / dbt)
- §1c per i Dart subtypes (Flutter / Riverpod / Bloc)
- §1d per i TypeScript subtypes (React / Vue2 / Vue3 / Angular / Ionic / Next.js / Nuxt / Express / NestJS / …)
- §2 per i moduli attivi per ogni Codebase Type

Inietta:
- `$LANG_IDS` = tutti i LANG_ID distinti rilevati (es. `[JAVA, VUE3, PYTHON_SPARK]`)
- `$CODEBASE_TYPES` = tutti i Codebase Type distinti (es. `[BE_JAVA, FE_WEB, ETL]`)

Per ogni tipo, annota i moduli attivi da §2 del registry. In un mono-repo ogni partizione di file ha i propri moduli attivi — non applicare moduli ETL a file FE_WEB.

**Step 1c — File Manifest (deterministico)**

Esegui questo comando esatto per costruire il manifest completo. L'output è la **fonte di verità** per tutta la Phase 2 — nessun file può essere analizzato se non è in questo manifest, nessun file nel manifest può essere saltato.

```bash
find $REPO -type f \( \
  -name "*.java" -o -name "*.kt" \
  -o -name "*.ts"  -o -name "*.tsx" -o -name "*.vue" \
  -o -name "*.py" \
  -o -name "*.dart" \
  -o -name "*.tf"  -o -name "*.hcl" \
  -o -name "*.sql" \
  -o -name "*.scala" \
  -o -name "*.go" \
  -o -name "*.sh" -o -name "*.bash" \
\) \
| grep -vE "(test|spec|__tests__|node_modules|dist|build|\.git|vendor|coverage|\.terraform|target)/" \
| LC_ALL=C sort \
> $MANIFEST_PATH   # es. /tmp/bh_manifest.txt
wc -l $MANIFEST_PATH  # → $FILE_COUNT
```

`sort` è obbligatorio: garantisce che lo stesso repo produca sempre lo stesso ordine, rendendo il manifest riproducibile tra run successive.

Il manifest viene poi **suddiviso per tipo** usando i path rilevati in Step 1b:
```bash
# Esempio: separa file ETL da file BE_JAVA
grep -E "(glue_jobs|etl|pipeline|spark)" $MANIFEST_PATH | sort > manifest_ETL.txt
grep -E "src/main/java"                  $MANIFEST_PATH | sort > manifest_BE_JAVA.txt
# ... un manifest_{TYPE}.txt per ogni tipo in $CODEBASE_TYPES
```
Ogni sottoinsieme viene assegnato ai subagent con i moduli attivi definiti in Step 1b.

**Fallback suddivisione (obbligatorio):** Se il grep per un `$CODEBASE_TYPE` non produce almeno 1 file → chiedi conferma del pattern di directory all'utente prima di procedere. Non lanciare subagent su manifest vuoti.

**Step 1d — Tier Selection**

In base a `$FILE_COUNT`, seleziona il tier di esecuzione:

```
┌─────────────────────────────────────────────────────────────────────┐
│  TIER 1 — NANO     ≤ 50 file                                        │
│  Modalità: diretta (nessun subagent)                                │
│  Batch: unico, tutti i file                                         │
│  Moduli: M1-M5 eseguiti sequenzialmente inline                      │
├─────────────────────────────────────────────────────────────────────┤
│  TIER 2 — SMALL    51–200 file                                      │
│  Modalità: 1 subagent per layer (max 3: FE / BE / BFF)              │
│  Ogni subagent esegue tutti i moduli M1-M5 sul proprio layer        │
│  Subagent totali: 2–3                                               │
├─────────────────────────────────────────────────────────────────────┤
│  TIER 3 — MEDIUM   201–600 file                                     │
│  Modalità: 1 subagent per layer × modulo                            │
│  Esempio: FE×M1, FE×M2, FE×M3, BE×M1, BE×M2 … (max 15 subagent)   │
│  Ogni subagent riceve: tutti i file del layer + 1 solo modulo       │
│  Subagent totali: (n_layer) × 5                                     │
├─────────────────────────────────────────────────────────────────────┤
│  TIER 4 — LARGE    601–2000 file                                    │
│  Modalità: batch fissi da 60 file per subagent × modulo             │
│  Slice il manifest in chunk da 60 righe (split -l 60)               │
│  Ogni subagent riceve: chunk_{i}.txt + 1 solo modulo                │
│  Subagent totali: ceil(FILE_COUNT/60) × 5                           │
├─────────────────────────────────────────────────────────────────────┤
│  TIER 5 — ENTERPRISE  > 2000 file                                   │
│  Modalità: batch fissi da 60 file per subagent × modulo             │
│  Pre-filtro: split il manifest per directory radice (es. package),  │
│  poi chunk da 60 per ogni directory × modulo                        │
│  Subagent totali: ceil(FILE_COUNT/60) × 5 (paralleli in wave)       │
└─────────────────────────────────────────────────────────────────────┘
```

**Verifica completezza (obbligatoria dopo il dispatch):**
```bash
# Conta i file assegnati a tutti i subagent e confronta con il manifest
cat chunk_*.txt | wc -l  # deve essere == $FILE_COUNT
diff <(cat chunk_*.txt | sort) $MANIFEST_PATH  # deve essere vuoto
```
Se il diff non è vuoto → blocca l'esecuzione, correggi la partizione prima di procedere.

**Dispatch subagent — prompt template:**
```
Sei un Bug Hunter Subagent.
Tipo codebase: {$CODEBASE_TYPE}     ← es. BE_JAVA / ETL / DWH / IAC / WORKER
Modulo: {M1|M2|M3|M4|M5}
Moduli attivi per questo tipo: {lista da tabella Step 1b — es. M2,M3,M5 per ETL}
Reference modulo:   skills/siae-bug-hunter/reference/module-{N}-*.md
Reference pattern:  skills/siae-bug-hunter/reference/language-registry.md

File da analizzare (lista esplicita — analizzali TUTTI):
  {path_1}  [LANG_ID: JAVA]
  {path_2}  [LANG_ID: TYPESCRIPT]
  ...
  {path_K}  [LANG_ID: PYTHON]

Output richiesto: lista candidati nel formato ESATTO (nessuna variazione ammessa):
  [M{N}] {file:riga} | {LANG_ID} | {tipo pattern} | {snippet letterale ≤ 80 char}

IMPORTANTE:
- Analizza ogni file della lista. Non saltarne nessuno.
- Per ogni file: determina il LANG_ID dalla sua estensione (vedi language-registry.md).
- Per ogni bug type del modulo: usa SOLO il pattern grep del LANG_ID di quel file.
- Applica SOLO i moduli attivi elencati sopra.
- NON validare i candidati — solo estrarli. La validazione avviene nel main agent.
- NON aggiungere parole come "CONFIRMED", "PROBABLE", "bug evidente", "ovviamente" — solo il formato tabella sopra.
- Se un file non contiene pattern rilevanti → scrivi: [OK] {file} — nessun candidato
- Se un file non è leggibile → scrivi: [ERROR] {file} — non leggibile
```

**Step 1e — Stack Profile Injection**

Deriva `$STACK_PROFILE` da `$CODEBASE_TYPES`:

| `$CODEBASE_TYPES` contiene | `$STACK_PROFILE` |
|---|---|
| Solo `BE_JAVA` o `BE_KOTLIN` | `JAVA_BE` |
| Solo `FE_WEB` con Vue/React/Angular | `TS_FE` |
| Solo `BE_NODE` o `BE_EXPRESS` o `BE_NEST` | `TS_BE` |
| Solo `DART_FLUTTER` | `DART_FE` |
| Solo `PYTHON_*` (qualsiasi subtype) | `PYTHON_BE` |
| Più di un tipo distinto | `MIXED` |

Inietta `$STACK_PROFILE` → usato in Phase 2 per filtrare le sezioni grep nei moduli M1-M5.

Annuncia: `"Linguaggi: {$LANG_IDS}. Tipi: {$CODEBASE_TYPES}. Stack Profile: {$STACK_PROFILE}. Manifest: {$FILE_COUNT} file. Tier {N}. Subagent: {K} (in parallelo). Avvio Phase 2."`

---

## PHASE 2 — PATTERN EXTRACTION (5 moduli)

Lancia i subagent secondo la strategia determinata in Step 1c.
In modalità diretta (TIER 1, ≤ 50 file): esegui i 5 moduli in sequenza inline.
In modalità sharded: dispatcha i subagent in parallelo, poi raccogli i candidati.

**Regola stack-aware (OBBLIGATORIA per ogni subagent e per la modalità diretta):**
Ogni reference file contiene sezioni grep etichettate per linguaggio (`Java:`, `TypeScript:`, `Python:`).
Esegui **solo** le sezioni che corrispondono a `$STACK_PROFILE` (vedi Step 1e).
Se `$STACK_PROFILE = MIXED` → esegui tutte le sezioni ma etichetta ogni candidato con il linguaggio di origine.

| $STACK_PROFILE | Sezioni grep attive |
|---|---|
| `JAVA_BE` | sezioni `Java:` |
| `TS_FE` | sezioni `TypeScript:` — escludi pattern server-side BE |
| `TS_BE` | sezioni `TypeScript:` — escludi pattern DOM/React/Vue |
| `DART_FE` | sezioni `Flutter/Dart:` (dove presenti) — skip Java/Python |
| `PYTHON_BE` | sezioni `Python:` |
| `MIXED` | tutte le sezioni; per ogni pattern annota il linguaggio |

**Raccolta risultati (modalità sharded):**
Dopo che tutti i subagent completano, aggrega i candidati in un'unica lista ordinata per `file:riga`.
Rimuovi i duplicati cross-subagent (stesso file:riga riportato da moduli diversi → mantieni il modulo più specifico con gerarchia M1 > M5 > M2 > M3 > M4).

**Normalizzazione pre-gate (obbligatoria prima di Phase 3):**
Prima di passare i candidati al Three-Condition Gate:
1. Accetta SOLO righe nel formato esatto: `[M{N}] {file:riga} | {LANG_ID} | {tipo pattern} | {snippet}`
2. Scarta silenziosamente qualsiasi riga che non rispetta il formato (commenti, testo libero, intestazioni)
3. Scarta qualsiasi riga che contenga parole di giudizio: "CONFIRMED", "PROBABLE", "evidente", "ovviamente" → i subagent non classificano
4. Log obbligatorio: `"Normalizzazione: {K} righe ricevute, {J} accettate, {K-J} scartate (malformate o con giudizi)"`

### M1 — API Contract Mismatch
`reference/module-1-api-contract.md`
- Estrae chiamate API da FE, endpoint da BE, trasformazioni da BFF
- Cross-match: path, metodo, request body, response body, tipo, status code
- Output: lista candidati `file:riga | tipo mismatch`

### M2 — State Machine & Business Logic
`reference/module-2-state-logic.md`
- Patterns S1–S4 (state machine) e B1–B6 (logic boundary)
- Output: lista candidati `file:riga | pattern type (S1-S4/B1-B6)`

### M3 — Error Handling Gaps
`reference/module-3-error-handling.md`
- Gaps in FE (Promise, fetch, JSON.parse), BE (catch+log, exception→500), BFF (swallow)
- Output: lista candidati `file:riga | gap type`

### M4 — Async & Race Conditions
`reference/module-4-async-race.md`
- FE: useEffect stale, Promise.all race, optimistic no-rollback, debounce stale closure
- BE: check-then-act, singleton non-thread-safe, @Transactional missing, lazy load, N+1 JPA in loop (BE-CC5)
- Output: lista candidati `file:riga | race type`

### M5 — Data Validation & Boundary
`reference/module-5-data-validation.md`
- Categorie A–I: validation gap, regex mismatch, enum, overflow, truncation, timezone, null-as-string
- Output: lista candidati `file:riga | categoria`

---

## PHASE 3 — EVIDENCE VALIDATION

Leggi `reference/evidence-protocol.md`.

Per ogni candidato dai 5 moduli applica il **Three-Condition Gate**:

```
Condition A — Citation:       file:riga esatto citato
Condition B — Literal Pattern: pattern descritto testualmente
Condition C — Reachable Path:  percorso utente tracciabile

Se A + B + C + tutti i falsificatori falliscono → CONFIRMED
Se A + B + C inferita + falsificatore F4 (try-catch) → PROBABLE
Se solo A → SUSPECT (solo appendice)
Se A manca → SCARTATO
```

**Deduplica:** se lo stesso bug è rilevato da più moduli, mantieni una sola entry
con il modulo di origine più specifico.

---

## PHASE 4 — OUTPUT

Leggi `reference/bug-report-template.md` per il formato esatto.

**Struttura del report:**

```
# Bug Hunter Report — {repo_name}
Data: {timestamp} | Stack: {stack} | File scansionati: {N}

## Riepilogo
CONFIRMED: {N} | PROBABLE: {M} | SUSPECT: {K}
Candidati esaminati: {TOTAL} | Falsificati: {F} (F1:{f1}, F2:{f2}, F3:{f3}, F4:{f4}, F5:{f5}, F6:{f6}, F7:{f7}) | Scartati (formato): {S}
Priorità: [primo bug CONFIRMED più grave — oppure "Nessun bug confermato trovato nei {N} file scansionati" se CONFIRMED=0]

---
[BUG-001 ... BUG-NNN — ordinati per severità decrescente]
---

## Bugs Probabili (review umano consigliato)
[solo se $CONFIDENCE include PROBABLE]

## Appendice — Sospetti
[inclusa se $CONFIDENCE = CONFIRMED+PROBABLE o ALL — omessa solo se $CONFIDENCE = CONFIRMED]
```

**Ordine di severità:** CRITICAL → HIGH → MEDIUM → LOW

---

## LIMITI ESPLICITI

Questa skill NON rileva:
- Bug di performance (lentezza, timeout) senza data corruption
- Vulnerability OWASP/auth/encryption → usa `siae-security`
- Bug in `node_modules/`, `vendor/`, `dist/`, `__tests__/`
- Bug in librerie di terze parti
- Race condition con finestra temporale < 10ms
- Configuration errors (env vars mancanti)
- Bug che richiedono runtime execution (dipendenti da stato runtime non leggibile staticamente)
