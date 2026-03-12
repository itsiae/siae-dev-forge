---
name: nr-test-flows
description: >
  Analizza repository frontend/mobile e genera NRT flow map + test list deterministici
  pronti per Xray. Trigger: no-regression test flows, NRT suite, /forge-flows,
  repo Vue/React/Angular/Ionic/Flutter, team QA deve mappare flussi per regressione.
---

# NR Test Flows — No-Regression Test List da Navigazione

```
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║                                                                  ║
║              🔨 DevForge · NR TEST FLOWS                       ║
║         "Il codice si forgia. Il developer cresce."             ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Flexible | **Fase SDLC:** 5. Testing / QA

---

## ISTRUZIONE DI APERTURA — Esegui prima di tutto

Mostra il banner qui sopra in output, letteralmente, prima di qualsiasi altra azione.
Poi mostra immediatamente la pre-flight card di apertura (sezione successiva).

---

## LA LEGGE DI FERRO

```
NESSUN TEST CASE SENZA FLOW MAP APPROVATA.
NESSUNA SEZIONE NELLA FLOW MAP SENZA CITARE IL FILE SORGENTE CHE LA PROVA.
```

---

## ANTI-HALLUCINATION PROTOCOL — NON NEGOZIABILE

```
MAI MAPPARE UNA SEZIONE O UN FLUSSO SENZA CITARE FILE:RIGA SORGENTE.
SE NON HAI LETTO IL FILE, LA SEZIONE NON ESISTE.
```

### Confidence Tag Obbligatori

```
[CONFIRMED]      evidenza letta direttamente dal codice (router, component, guard)
[INFERRED]       directory structure o naming convention — DEVI citare file:riga
[UNVERIFIED]     nessuna evidenza — nel Gap Report, MAI rimosso o nascosto
```

### Gerarchia Fonti

```
TIER 1 — Router config    route declarations, path definitions, lazy imports
TIER 2 — Component files  view/page components, tab structures
TIER 3 — Guard/Middleware auth guards, navigation middleware, route meta
TIER 4 — API calls        fetch/axios calls in components (rivela sezioni con dati)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VIETATO   README, commenti liberi, nomi di file senza averli letti, memoria
```

---

## Quando si Applica

- Repo frontend (Vue, React, Angular, Ionic, Flutter, Nuxt, Drupal, Strapi) senza test list QA
- Team QA deve mappare i flussi utente prima di scrivere i test case
- Invocazione `/forge-flows`
- Input: path locale (cwd) oppure GitHub URL / `org/repo` (via gh CLI, GitHub REST API, o clone manuale)

**NON usare quando:**
- Il repo è un backend puro (API-only, nessuna UI)
- La test list esiste già e solo l'export in Xray è necessario (usa `siae-qa`)

---

## Input Accettati

```
/forge-flows                           → analizza cwd
/forge-flows ./path/to/repo            → path locale relativo
/forge-flows /absolute/path/to/repo    → path locale assoluto
/forge-flows https://github.com/org/repo  → GitHub URL via MCP
/forge-flows org/repo                  → shorthand GitHub via MCP
```

---

## PRE-FLIGHT CARD DI APERTURA

Dopo il banner, mostra questa card prima di iniziare il workflow:

| 🟡 MEDIO (reversibile) — 🔨 DevForge · nr-test-flows |
|:---|
| 📁 Repository: `{path o URL}` |
| 🔍 Framework: `{da rilevare — CONFIRMED \| INFERRED}` |
| 📡 Tier export: `Tier 1 MCP Atlassian / Tier 3 CSV` |
| 🎫 Story Jira: `{da confermare allo Step 5 — HARD GATE}` |
| 1. 🖥️ Azione: Framework detection + harvest file rilevanti |
| 2. 📝 Azione: Costruzione Flow Map YAML per sezione navigazionale |
| 3. ✏️ Azione: Generazione test list (happy path + NEG + EDGE + PROFILO) |
| 4. 📤 Azione: Export Xray (Tier 1 MCP o Tier 3 CSV con separatore `;`) |
| 💡 Perché: Analisi navigazione frontend per produrre test list QA pronta per Xray |
| 🚫 Se NO: Analisi non eseguita — test list non generata |

---

## WORKFLOW A 6 STEP

```
1. INGEST     → Framework detection + harvest file rilevanti
2. MAP        → Flow map YAML strutturata per sezione navigazionale
3. PRIORITIZE → Tag flussi CRITICAL/HIGH/MEDIUM
4. GENERATE   → Test list organizzata per sezione (happy path + edge + neg + profilo)
5. REVIEW     → Presentazione in chat → HARD GATE approvazione utente
6. EXPORT     → Push Xray (Tier 1 MCP | Tier 3 CSV con sep ;)
```

---

### Step 1 — INGEST: Framework Detection + Harvest

🟢 SICURO

#### 1a — Framework Detection

Applica la matrice in `reference/framework-detection-matrix.md` nell'ordine L1 → L2 → L3.

**Regole di precedenza mix:**
- `ionic.config.json` presente → **Ionic + {framework base}** (Ionic wins)
- `nuxt.config.ts` presente → **Nuxt** (non Vue puro)
- `pubspec.yaml` con `flutter:` → **Flutter**

Annuncia il risultato:
```
Framework: {nome} [{versione}]
Confidence: CONFIRMED | INFERRED
Evidenza L1: {file:riga o "N/A"}
Evidenza L2: {package.json:dipendenza o "N/A"}
```

#### 1b — Harvest File Rilevanti

Usa i pattern in `reference/evidence-patterns.md` per il framework rilevato.

**File da raccogliere (priorità decrescente):**

1. File router principale (route declarations)
2. Directory views/pages/screens (enumerate i file presenti)
3. File guard/middleware (auth protection)
4. File layout (struttura navigazionale top-level)
5. Store auth (se rilevante per guard)
6. Costanti route (se presenti)
7. File i18n (nav keys → rivela sezioni senza leggere router)

**Soglia subagent paralleli:** se il repo ha > 30 file rilevanti da analizzare, usa i subagent paralleli (vedi sezione "Subagent Paralleli" sotto).

#### 1c — Harvest per Repository Remoti (GitHub CLI + fallback API)

Se l'input è un URL GitHub o `org/repo`, applica questo schema di priorità:

```
Tier A — gh CLI (preferito)
  Verifica: gh auth status
  Comandi: gh repo clone {org/repo} /tmp/siae-flows-{timestamp}/repo
           oppure gh api repos/{org/repo}/contents/{path} per singoli file

Tier B — GitHub REST API (fallback se gh non disponibile)
  Verifica: curl disponibile
  Endpoint: GET https://api.github.com/repos/{org}/{repo}/git/trees/HEAD?recursive=1
            GET https://api.github.com/repos/{org}/{repo}/contents/{path}
  Header:   Authorization: Bearer {GITHUB_TOKEN} (se disponibile in env)

Tier C — Clonazione manuale (ultimo fallback)
  Se né gh né curl sono disponibili, chiedi all utente di clonare il repo
  e riprovare con path locale.
```

**Rilevamento automatico — esegui in ordine:**

1. `gh auth status` → se exit 0: usa **Tier A**
2. `curl --version` → se exit 0: usa **Tier B**
3. Altrimenti: usa **Tier C** (chiedi clone manuale)

Mostra questa card prima di procedere (aggiorna `📡 Fonte` con il tier rilevato):

| 🟡 MEDIO (reversibile) — 🔨 DevForge · nr-test-flows |
|:---|
| 📁 Repository: `{org/repo o URL GitHub}` |
| 📡 Fonte: `Tier A — gh CLI / Tier B — GitHub API / Tier C — manuale` |
| 1. ⚡ Azione: Dispatch 3 subagent paralleli per fetch repository remoto |
| 📂 `{org}/router`, `{org}/views`, `{org}/guards` |
| 2. 📝 Azione: Salvataggio output subagent in `/tmp/siae-flows-{timestamp}/` |
| 📂 `/tmp/siae-flows-{timestamp}/routes.yaml`, `sections.yaml`, `auth-api.yaml` |
| 💡 Perché: Harvest remoto necessario — repo non disponibile in locale |
| 🚫 Se NO: Chiedi all utente di clonare il repo e riprovare con path locale |

```
Subagent A: harvest tree struttura repository (ricerca file router, views, guards)
Subagent B: fetch contenuto file router + guard
Subagent C: fetch contenuto file views/pages principali
```

Salva output in `/tmp/siae-flows-{timestamp}/`.

**Annuncia al completamento:**
```
STEP 1 COMPLETATO
Evidenza: {N file letti}
Framework: {nome} [CONFIRMED|INFERRED]
File router trovati: {lista}
File guard trovati: {lista o "nessuno"}
File views/screens trovati: {N file}
Gap trovati: {N elementi UNVERIFIED}
Passaggio al Step 2: SI
```

---

### Step 2 — MAP: Flow Map YAML

🟢 SICURO

Usa il template in `reference/flow-map-template.yaml` per costruire la flow map.

#### Regole di Mapping

**Una sezione = un'area navigazionale distinta** accessibile da:
- Menu principale / navbar
- Tab bar (Ionic, mobile)
- Sidebar / drawer
- Route top-level

**Un flusso = un'operazione dell'utente** in una sezione:
- CRUD operation (crea, leggi, aggiorna, elimina)
- Azione principale (submit form, upload file, pagamento)
- Navigazione inter-sezione (da A a B con contesto)

**Regole anti-hallucination per il mapping:**

```
Per ogni sezione:
  → Cita il file router che dichiara la route (file:riga)
  → Cita il component/view principale (file:riga)
  → Se guard presente: cita il file guard (file:riga)
  → Se nessuna evidenza: confidence: UNVERIFIED → Gap Report

Per ogni flusso:
  → Cita il component in cui l'utente esegue l'azione (file:riga)
  → Cita la/le API call se rilevate (file:riga)
  → Se non trovi: confidence: INFERRED con motivazione
```

#### Sezioni Standard da Verificare Sempre

Queste sezioni sono comuni nella maggior parte delle app — verifica se esistono:

| Sezione | Segnali da cercare |
|---------|-------------------|
| Autenticazione | route `/login`, `/auth`, guard redirect, LoginView |
| Home / Dashboard | route `/`, `/home`, `/dashboard`, default redirect post-login |
| Profilo utente | route `/profile`, `/account`, `/settings`, UserProfile |
| Amministrazione | route `/admin`, canActivate AdminGuard, AdminModule |
| Notifiche | route `/notifications`, store notifications, IonBadge |
| Ricerca | route `/search`, SearchView, parametri query |

**Se una sezione non esiste nel repo → non includerla. Documenta nel Gap Report.**

#### 2d — L5 Scan (obbligatorio prima di chiudere ogni sezione)

Per ogni component letto durante il MAP, esegui i grep L5 da `reference/evidence-patterns.md`
§ "L5 Scan — {framework}":

1. **P5 — Form discriminators**: ogni branch `v-if`/`*ngIf` su variabile di form state → aggiungi `variants[]` nel YAML
2. **P3 — Store states**: stati nominati nello store → aggiungi `store_states` in `l5_signals`
3. **Computed rendering su ruolo**: `isAdmin`, `userRole`, `canEdit` → aggiungi `computed_rendering` in `l5_signals`

**Dichiarazione obbligatoria:** anche se il grep non produce risultati, scrivi esplicitamente:
```
L5 scan sezione {nome}: nessun discriminatore rilevato — l5_signals: {}
```

Se non esegui 2d o non dichiari il risultato → la sezione è INCOMPLETA:
aggiungi nel Gap Report un entry `type: L5_SCAN_MISSING, severity: CRITICAL`
e NON procedere al Step 3 PRIORITIZE fino a risoluzione.

#### Output Step 2

File YAML salvato in `/tmp/siae-flows-{timestamp}/flow-map.yaml` (o presentato in chat).

**Annuncia:**
```
STEP 2 COMPLETATO
Evidenza: flow map YAML costruita
Sezioni mappate: {N}
Flussi mappati: {N}
Sezioni UNVERIFIED: {N}
Gap Report: {N elementi}
Passaggio al Step 3: SI
```

---

### Step 3 — PRIORITIZE: Tag Flussi Critici

🟢 SICURO

Assegna a ogni flusso una priorità basandosi su questi criteri:

Applica le regole code-derivable da `reference/evidence-patterns.md` § "Regole Priority":

| Priorità | Regola (code-derivable) | `priority_evidence.rule` |
|----------|------------------------|--------------------------|
| **CRITICAL** | canActivate/redirect guard + P1 (API mutante) | `mutating-api+canActivate-guard` |
| **CRITICAL** | Prima route dopo redirect post-login | `entry-point-post-login` |
| **CRITICAL** | Endpoint contiene `/auth`, `/payment`, `/submit`, `/sign`, `/confirm`, `/delete` | `endpoint-path-contains-{keyword}` |
| **HIGH** | P1 (API mutante) senza pattern CRITICAL | `mutating-api` |
| **HIGH** | P5 (form discriminator) che cambia payload API | `form-discriminator-changes-payload` |
| **HIGH** | Rendering condizionale su ruolo (isAdmin, userRole, canEdit) | `role-based-rendering` |
| **MEDIUM** | Solo P4 (submit) senza API call | `submit-no-api` |
| **MEDIUM** | Solo P2 (router navigation) senza API | `nav-only` |
| **LOW/SKIP** | Nessuno dei 5 pattern → component presentazionale | Non aggiungere alla flow map |

Compila sempre `priority_evidence.rule` con il valore della colonna destra.
Se non riesci a identificare la regola → assegna MEDIUM di default.
Nessun giudizio di dominio: "operazione importante per il business" non è una regola.

**Applica anche i tag di accesso:**
- `pubblico` — sezione accessibile senza autenticazione
- `autenticato` — richiede login (guard rilevato)
- `ruolo:{nome}` — richiede ruolo specifico (guard condizionale per ruolo)

**Annuncia:**
```
STEP 3 COMPLETATO
Evidenza: prioritizzazione completata
CRITICAL: {N flussi}
HIGH: {N flussi}
MEDIUM: {N flussi}
Passaggio al Step 4: SI
```

---

## Subagent Paralleli (Repo > 30 File Rilevanti)

Se il repo supera 30 file rilevanti, dispatcha 3 subagent in parallelo in un singolo blocco:

```
Subagent A — Router + Routes
  Goal: harvest tutti i file router, estrai route declarations, costruisci flow graph
  Output: /tmp/siae-flows-{ts}/routes.yaml

Subagent B — Views + Components
  Goal: harvest views/pages/screens, identifica struttura sezioni, tab navigation
  Output: /tmp/siae-flows-{ts}/sections.yaml

Subagent C — Auth + API
  Goal: harvest guard files, auth service, API calls nei components
  Output: /tmp/siae-flows-{ts}/auth-api.yaml
```

**ISTRUZIONE CRITICA per ogni subagent (copia verbatim):**
```
Hai già tutti i dati necessari nel prompt. NON usare Bash se non autorizzato.
Per ogni elemento trovato, cita SEMPRE file:riga come evidenza.
Se non trovi evidenza per un elemento → confidence: UNVERIFIED.
Scrivi il tuo output YAML nel file indicato (usa il Write tool).
Rispondi con UNA SOLA RIGA di conferma al termine.
```

Il parent aggrega i 3 output YAML prima dello Step 2.

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realtà |
|----------|--------|
| "Dal nome del componente si capisce che è la sezione Dashboard" | Il nome non è evidenza. Leggi il file router. Se non c'è route → UNVERIFIED |
| "Sicuramente c'è un login, ogni app ce l'ha" | "Sicuramente" è un'allucinazione. Cerca `/login` nel router. Se non c'è → UNVERIFIED |
| "Ho già visto questa struttura, so com'è fatto" | Pattern da altri repo ≠ evidenza di questo repo. Analizza questo specifico codebase |
| "Il README dice che c'è una sezione Admin" | Il README è documentazione aspirazionale. Solo router e componenti sono fonti valide |
| "Posso inferire i flussi dal nome dei componenti senza leggerli" | L'inferenza senza evidenza è UNVERIFIED. Leggi il file o metti nel Gap Report |
| "Ho abbastanza sezioni, mi fermo qui" | Il mapping è completo quando hai processato tutti i file router, non quando "sembra abbastanza" |
| "Il gap report è imbarazzante, lo ometto" | I gap sono informazione. Una test list con gap espliciti è più utile di una test list con sezioni inventate |
| "Genero i TC direttamente senza la flow map" | LA LEGGE DI FERRO: nessun TC senza flow map approvata. Punto |
| "È ovvio che il guard protegge tutte le route autenticate" | "Ovvio" non è evidenza. Leggi il guard file. Cita il beforeEach o canActivate |
| "L'utente approverà sicuramente la flow map com'è" | L'approvazione allo Step 5 è un HARD GATE. Non anticipare. Presenta e attendi |
| "Ho già scritto il primo TC variante in dettaglio, per gli altri abbrevio" | Ogni variante deve avere lo stesso livello di dettaglio della prima. Abbreviare la seconda variante produce TC inutilizzabili perché non si sa quali campi appaiono. |
| "Per il NEG accesso non autorizzato basta testare l'ID inesistente" | Servono due TC distinti: (1) ID non esistente → 404, (2) ID di un altro utente → 403/404. Sono test di natura diversa: il primo testa la gestione errori, il secondo testa l'autorizzazione. |

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Framework detection (lettura file) | 🟢 Sicuro | No |
| Harvest file locali (Read/Glob) | 🟢 Sicuro | No |
| Fetch file remoti (gh CLI / GitHub REST API) | 🟡 Medio | Si |
| Dispatch subagent paralleli | 🟡 Medio | No (nessuna modifica) |
| Scrittura flow map in `/tmp/` | 🟢 Sicuro | No |
| Presentazione test list in chat | 🟢 Sicuro | No |
| Approvazione utente (Step 5) | 🔴 HARD GATE | Sì — attendi esplicitamente |
| Export CSV (Write file) | 🟡 Medio | Si |
| Push Xray via MCP Atlassian | 🟡 Medio | Si |

---

## Permission Denied Handling

**Se Read/Glob negato (harvest locale):**
1. Chiedi all'utente di fornire il contenuto dei file rilevanti (router, views)
2. Procedi con i dati forniti
3. Marca tutto come `[CONFIRMED]` se dati forniti direttamente dall'utente

**Se repo remoto (GitHub URL / `org/repo`):**
1. Verifica `gh auth status` → usa **Tier A** (gh CLI)
2. Se gh non disponibile, verifica `curl --version` → usa **Tier B** (GitHub REST API)
3. Se né gh né curl disponibili → segnala: `⚠️ gh CLI e curl non disponibili` e chiedi all'utente di clonare il repo localmente e riprovare con path locale (**Tier C**)
4. Non procedere mai con dati inventati indipendentemente dal tier usato

**Se Write negato (export CSV):**
1. Presenta il CSV completo come blocco di codice in chat
2. Indica il path suggerito per il file
3. L'utente copia manualmente

---

## Risorse di Riferimento

- `reference/framework-detection-matrix.md` — detection matrix per 8 framework
- `reference/evidence-patterns.md` — dove cercare route/nav/guard per framework
- `reference/flow-map-template.yaml` — template YAML sezioni/flussi
- `reference/test-list-template.md` — formato test list per sezione
- `reference/xray-csv-template.md` — formato CSV Xray adattato per UI flows

---

---

### Step 4 — GENERATE: Test List per Sezione

🟢 SICURO

Usa il template in `reference/test-list-template.md` per generare i test case.

**La flow map approvata (Step 5) è prerequisito assoluto.**
Se l'utente non ha ancora approvato la flow map → NON generare test case.

#### 4a — Per ogni sezione nella flow map

Per ogni sezione (ordinata per priorità: CRITICAL → HIGH → MEDIUM):

1. Intestazione sezione con access, route, evidenza sorgente
2. Per ogni flusso nella sezione:
   - Genera TC **happy path** (almeno 1 per flusso)
   - Genera TC **[NEG]** negativi/alternativi (almeno 1 per flusso CRITICAL/HIGH)
   - Genera TC **[EDGE]** edge case (almeno 1 per flusso CRITICAL)
   - Genera TC **[PROFILO]** se la sezione ha ruoli/guard diversi

**REGOLA VARIANTI DI FLUSSO — Non negoziabile:**

Se un flusso prevede N scelte iniziali che determinano varianti di schermata/campo/comportamento,
ogni variante è un **sotto-flusso separato** che richiede la propria copertura TC.

```
ERRORE:  un singolo TC "Creazione Permesso — wizard completo" per tutti i tipi di evento
CORRETTO: un TC per ogni tipo di evento che percorre TUTTI gli step descrivendo
          le specificità di quella variante (campi in più/meno, prezzi diversi, UI differente)
```

**Come identificare le varianti:**
- Selettori/radio button che mostrano/nascondono sezioni aggiuntive (es. tipo evento → dati minorenne)
- Scelte che cambiano il calcolo/contenuto degli step successivi (es. tipo musica → diritti connessi nel preventivo)
- Flag/env che attivano parti del form (es. DPCM file obbligatorio)
- Ruoli utente che cambiano le opzioni disponibili

**Regola di granularità:**
```
N varianti significative × priorità CRITICAL = N TC completi (tutti gli step)
N varianti significative × priorità HIGH     = N TC (step chiave + differenze)
N varianti significative × priorità MEDIUM   = 1 TC per variante principale + note sulle differenze
```

**REGOLA UNIFORMITÀ DETTAGLIO VARIANTI — Non negoziabile:**

Quando un flusso genera N varianti TC, ogni variante deve avere lo **stesso livello di dettaglio** della prima. Non abbreviare i TC successivi.

```
ERRORE:  Prima variante → Step 3: "Lo Step 2 'Dati Evento' viene visualizzato con i
                           seguenti campi: chip selector 'Tipo Evento' (vuoto), campi
                           data e orario evento, checkbox 'Tipo di Musica'..."
         Seconda variante → Step 3: "Step 2 visualizzato con campi standard"
                                                         ↑ VIETATO

CORRETTO: Ogni variante enumera esplicitamente i campi visibili ad ogni step.
```

**Checklist per ogni step di ogni variante TC:**

- **Cosa appare**: campi, sezioni, componenti — enumerarli tutti
- **Cosa NON appare**: es. "la sezione BirthdayForm NON viene mostrata" (anche l'assenza va dichiarata)
- **Stato visivo**: chip selezionato, checkbox checked, toggle disabilitato, pulsante attivo/disattivo
- **Dati risultanti**: es. "tipo musica risultante sarà id='V' (Solo Dal Vivo)"
- **Effetto sugli step successivi**: es. "il preventivo a Step 3 non includerà i Diritti Connessi"

**Esempio corretto — wizard con tipo evento:**
```
✅ TC-010: Crea Permesso — Matrimonio + Musica dal vivo
           Step 1: selezione locale → Step 2: form Matrimonio senza sezione minorenne,
           musica "dal vivo" senza DPCM → Step 3: preventivo CON SOLO diritto d'autore,
           SENZA diritti connessi → Step 4-5: ...

✅ TC-011: Crea Permesso — Compleanno minorenne + Musica registrata
           Step 1: selezione locale → Step 2: form CON sezione dati minorenne (nome,
           cognome, CF, genere, luogo/nazione nascita, data nascita), musica
           "registrata" → Step 3: preventivo CON diritto d'autore E diritti connessi
           → Step 4-5: ...

❌ TC-010: Crea Permesso — wizard completo (happy path)
           [troppo generico — non specifica quale tipo evento, quali campi compaiono,
            quale preventivo viene generato]
```

#### 4b — Linee guida per la generazione step-based

Ogni test case nella test list sarà poi convertito in step Xray. Scrivi i passi
come azioni concrete dell'utente (non come descrizioni astratte):

```
✅ CORRETTO: "Toccare il pulsante 'Accedi' nella schermata di login"
❌ ERRATO:  "L'utente esegue il login"

✅ CORRETTO: "Inserire 'admin@siae.it' nel campo Email"
❌ ERRATO:  "Inserire credenziali valide"
```

**REGOLA FONDAMENTALE — Mobile vs Web per riferimenti a path/route:**

| Framework | Regola |
|-----------|--------|
| **Ionic / Flutter** (mobile) | **MAI** usare "navigare a /path" come step. I path sono identificatori interni della flow map, non azioni utente. Ogni step deve descrivere l'interazione UI concreta (tap, swipe, input, scroll). |
| **Web** (Vue, React, Angular, Nuxt) | "Navigare a /path" è accettabile **solo** in scenari `[EDGE]` o `[NEG]` di sicurezza (accesso diretto URL manomesso, token assente). Per i flussi normali, anche su web, dettaglia i click/form/navigazione passo passo. |

**Traduzione path → step UI per app mobile:**

```
❌ ERRATO  (mobile): "Navigare a /auth/welcome/fulfillments/summary"
✅ CORRETTO (mobile):
  Step 1: Aprire l'app e completare il login
  Step 2: Nella schermata Home, toccare la sezione 'Adempimenti'
  Step 3: Toccare l'opera desiderata dalla lista
  Step 4: Verificare che la schermata riepilogo adempimenti sia visualizzata

❌ ERRATO  (mobile NEG): "Tentare di navigare direttamente a /fulfillments/summary senza opera-data"
✅ CORRETTO (mobile NEG):
  Step 1: Aprire l'app e completare il login
  Step 2: Toccare 'Adempimenti' dalla Home
  Step 3: Non selezionare alcun dato opera e tentare di procedere al riepilogo
  Step 4: Verificare che l'app blocchi la navigazione e mostri il messaggio di errore atteso
```

#### 4c — Scenari standard per flussi UI (da valutare per ogni flusso)

**Navigazione — Web:**
- Route diretta tramite URL (solo per `[EDGE]`/`[NEG]` di sicurezza)
- Browser back dopo operazione
- Refresh pagina a metà flusso (stato perso?)

**Navigazione — Mobile (Ionic/Flutter):**
- Hardware back button / gesture swipe-back durante flusso multi-step
- App in background poi ripresa (stato mantenuto?)
- Deep link diretto a schermata protetta senza login (solo `[EDGE]`)

**Form:**
- Submit con tutti i campi validi
- Submit con campo obbligatorio vuoto
- Submit con formato non valido (email, data, numero)
- Submit doppio (doppio tap su bottone)
- Caratteri speciali / emoji in campo testo

**Autenticazione:**
- Accesso senza token (redirect a login?)
- Token scaduto a metà operazione
- Ruolo insufficiente (403 handling)

**Dati:**
- Lista vuota (empty state UI)
- Lista con 1 elemento
- Lista con molti elementi (scroll/paginazione)
- Operazione su elemento inesistente

**Autorizzazione per risorse per-utente (route `/entity/:id`):**

Ogni volta che esiste una route con ID dinamico (`/permessi/:id`, `/orders/:id`, `/documents/:id`), genera **sempre** questi due TC distinti:

```
[NEG]     Accesso a {entità} con ID non esistente nel sistema
          → Expected: 404 / "Elemento non trovato"
          → Verifica: nessun dato esposto, messaggio errore appropriato

[PROFILO] Accesso a {entità} valida ma appartenente a un altro utente
          → Expected: 403 Forbidden o 404 (oscuramento)
          → Verifica: l utente A non può leggere i dati dell utente B
                      via URL manomesso (/entità/{id-di-B})
          → Motivo: test di autorizzazione — bug frequente nelle SPA
                    che delegano l'auth solo alla UI e non all'API
```

**Esempio:**
```
[NEG]     Dettaglio Permesso — Accesso con ID permesso non esistente
          Step 1: Navigare a /permessi/999999 (ID non presente nel sistema)
          Expected: pagina 404 o "Permesso non trovato"

[PROFILO] Dettaglio Permesso — Accesso a permesso appartenente ad altro utente
          Step 1: Ottenere l ID di un permesso dell utente B (non in lista dell utente A)
          Step 2: Con browser dell utente A navigare a /permessi/{id-utente-B}
          Expected: 403 Forbidden o 404 — dati dell utente B non esposti
```

#### 4d — Riepilogo copertura

Dopo aver generato tutti i TC, mostra il riepilogo:

```
Riepilogo copertura:
  Sezioni:      N
  Flussi:       N
  Happy Path:   N TC
  Negativi:     N TC
  Edge Case:    N TC
  Profilazione: N TC
  TOTALE:       N TC
  Gap Report:   N elementi da verificare
```

---

### Step 5 — REVIEW: Presentazione e Approvazione

🔴 HARD GATE — Non procedere all'export senza approvazione esplicita

**Questo step è non negoziabile. Presentare la test list e attendere.**

#### Presentazione

Mostra la test list completa in chat, organizzata per sezione:

```
=== TEST LIST — {Nome Repository} ===
Framework: {nome} | Sezioni: N | TC Totali: N

[contenuto test-list-template.md compilato]

=== RIEPILOGO COPERTURA ===
[tabella riepilogo]

=== GAP REPORT ===
[elementi UNVERIFIED se presenti]
[vuoto se nessun gap]
```

#### Hard Gate

Dopo la presentazione, chiedi esplicitamente:

```
La flow map e la test list sono pronte per la revisione.

Prima di procedere all'export in Xray, conferma:

1. Le sezioni identificate coprono tutte le aree dell'applicazione che vuoi testare?
2. I test case generati sono sufficienti (puoi richiedere aggiunte o modifiche)?
3. Il campo "ID JIRA Story" è corretto? (es. PROJ-123)
4. I valori "Automazione" (Y/N) sono corretti per i tuoi test automatizzati?

Rispondi "OK" per procedere all'export, oppure indica le modifiche da apportare.
```

**Se l'utente richiede modifiche:**
- Applica le modifiche richieste
- Ri-presenta la sezione modificata
- Chiedi nuova conferma prima di procedere

**NON procedere all'export** se:
- L'utente non ha risposto esplicitamente
- L'utente ha richiesto modifiche non ancora applicate
- Il campo `ID JIRA Story` non è stato fornito

---

### Step 6 — EXPORT: Push Xray

🟡 MEDIO — Mostra pre-flight card prima di esportare

| 🟡 MEDIO (reversibile) — 🔨 DevForge · nr-test-flows |
|:---|
| 📡 Tier: `Tier 1 MCP Atlassian / Tier 3 CSV` |
| 🎫 Story Jira: `{PROJ-XXX}` |
| 📊 TC da esportare: `{N}` in `{N}` sezioni |
| 1. ✏️ Azione: Creazione TC in Xray |
| 📂 `{output.csv o MCP Atlassian}` |
| 💡 Perché: Test list approvata, pronta per Xray |
| 🚫 Se NO: Export non eseguito, test list disponibile solo in chat |

#### Tier 1 — MCP Atlassian (preferito)

Se il tool MCP `atlassian` è disponibile:

1. Per ogni TC nella test list, crea il Test Case in Xray via MCP
2. Associa ogni TC alla Story Jira (`ID JIRA Story`)
3. Registra le chiavi Xray assegnate (es. `PROJ-456`, `PROJ-457`, ...)
4. Mostra la mappatura ID sequenziale → chiave Xray al termine

```
Mappatura TC — {STORY_ID}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ID  →  Chiave Xray   Scenario
  1   →  PROJ-456      Autenticazione — Login con credenziali valide
  2   →  PROJ-457      Autenticazione — [NEG] Login con password errata
  ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### Tier 3 — CSV Export (fallback)

Se MCP non è disponibile:

1. Genera il file CSV seguendo il formato in `reference/xray-csv-template.md`
2. Header esatto: `ID;Test  Type;Team Competenza;ID JIRA Story;User Story Description;Scenario (descrizione);Step scenario;Action;Expceted Result;Data;Automazione;NRT`
3. Separatore: `;` — mai virgola
4. Encoding: UTF-8 senza BOM
5. Ogni test case = righe con stesso ID (multi-step)

**Nome file suggerito:** `test-list-{repo-name}-{YYYY-MM-DD}.csv`

**Se Write negato:** presenta il CSV completo come blocco di codice in chat.

#### Post-Export

Dopo l'export, comunica:

```
Export completato.

Tier usato: {Tier 1 MCP | Tier 3 CSV}
TC esportati: {N}
Story collegata: {PROJ-XXX}

[Se Tier 3]
File CSV: {path o "presentato in chat"}
Import manuale: Xray → Test → Import → CSV → seleziona file

[Se prevedi automazione]
Per generare test automatizzati dai TC con Automazione=Y:
  Usa: siae-automation (/forge-automate)
  Prerequisito: raccogliere le chiavi Xray assegnate ai TC
```

---

## Integrazione SDLC

```
siae-brainstorming (design feature frontend)
    └── nr-test-flows (/forge-flows)
        ├── Step 1-3: INGEST + MAP + PRIORITIZE → flow map YAML
        ├── Step 4:   GENERATE → test list per sezione
        ├── Step 5:   REVIEW → HARD GATE approvazione utente
        └── Step 6:   EXPORT → Tier 1 MCP | Tier 3 CSV
            └── siae-automation (/forge-automate)
                → genera test Cypress (web) o Appium (mobile)
                → per TC con Automazione=Y
```

**Skill correlate:**
- `siae-qa` — genera TC da Acceptance Criteria Jira (use case diverso: da AC, non da navigazione)
- `siae-automation` — automatizza i TC con `Automazione=Y` generati da questa skill
- `siae-microservices-map` — per mappare le dipendenze backend del frontend analizzato

