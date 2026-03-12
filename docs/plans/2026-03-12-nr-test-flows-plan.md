# nr-test-flows — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Rinominare `siae-frontend-flows` in `nr-test-flows` e rendere deterministico l'output della skill tramite 5 pattern meccanici, L5 tier e regole di priorità code-derivable.
**Architettura:** Rename della directory + refactoring chirurgico di `flow-map-template.yaml` ed `evidence-patterns.md` (reference files) + patch a `SKILL.md` (Step 2d e Step 3). Il workflow a 6 step, CONFIRMED/INFERRED/UNVERIFIED e le regole varianti wizard restano invariati.
**Stack:** Markdown, YAML (skill DevForge)
**SP:** 5

---

### Task 1: Rename directory + aggiorna tutti i riferimenti [DONE]

**File coinvolti:**
- Rinomina: `skills/siae-frontend-flows/` → `skills/nr-test-flows/`
- Modifica: `skills/nr-test-flows/SKILL.md` (frontmatter + banner)
- Modifica: `skills/using-devforge/SKILL.md` (riga catalogo)
- Modifica: `commands/forge-flows.md` (riferimento skill)

**Step 1: Rinomina la directory**

```bash
mv skills/siae-frontend-flows skills/nr-test-flows
```

Output atteso: nessun output, directory rinominata.

**Step 2: Verifica che la directory esista con il nuovo nome**

```bash
ls skills/nr-test-flows/
```

Output atteso:
```
SKILL.md
reference/
```

**Step 3: Aggiorna il frontmatter di SKILL.md**

Nel file `skills/nr-test-flows/SKILL.md`, sostituisci:

```yaml
---
name: siae-frontend-flows
description: >
  Analizza repository frontend (web/mobile) e genera automaticamente una test list
  organizzata per sezione navigazionale, pronta per Xray. Trigger: analisi flussi utente,
  generazione test case da navigazione, /forge-flows, repo Vue/React/Angular/Ionic/Flutter
  senza test list QA, team QA deve mappare sezioni a mano.
---
```

con:

```yaml
---
name: nr-test-flows
description: >
  Analizza repository frontend/mobile e genera NRT flow map + test list deterministici
  pronti per Xray. Trigger: no-regression test flows, NRT suite, /forge-flows,
  repo Vue/React/Angular/Ionic/Flutter, team QA deve mappare flussi per regressione.
---
```

**Step 4: Aggiorna il banner in SKILL.md**

Sostituisci:
```
║              🔨 DevForge · FRONTEND FLOWS                      ║
```
con:
```
║              🔨 DevForge · NR TEST FLOWS                       ║
```

**Step 5: Aggiorna il titolo h1 e pre-flight card in SKILL.md**

Sostituisci:
```
# SIAE Frontend Flows — Test List da Navigazione
```
con:
```
# NR Test Flows — No-Regression Test List da Navigazione
```

Sostituisci tutte le occorrenze di `siae-frontend-flows` nel body di SKILL.md con `nr-test-flows`:

```bash
grep -n "siae-frontend-flows" skills/nr-test-flows/SKILL.md
```

Output atteso: lista righe con il vecchio nome nelle pre-flight card. Sostituisci ciascuna.

**Step 6: Aggiorna `commands/forge-flows.md`**

Contenuto attuale:
```markdown
Invoca la skill siae-devforge:siae-frontend-flows e seguila esattamente come ti viene presentata.
```

Sostituisci con:
```markdown
Invoca la skill siae-devforge:nr-test-flows e seguila esattamente come ti viene presentata.
```

**Step 7: Aggiorna la riga catalogo in `skills/using-devforge/SKILL.md`**

Cerca la riga:
```
| siae-frontend-flows | Analizza repository frontend...
```

Sostituiscila con:
```
| nr-test-flows | no-regression test flows, NRT suite, /forge-flows, repo Vue/React/Angular/Ionic/Flutter, team QA deve mappare flussi per regressione | Flexible | 5. Testing / QA |
```

**Step 8: Verifica che non rimangano riferimenti al vecchio nome**

```bash
grep -r "siae-frontend-flows" skills/ commands/ .claude-plugin/
```

Output atteso: nessun match (o solo file non coinvolti da questo piano).

**Step 9: Commit**

```bash
git add skills/nr-test-flows/ skills/using-devforge/SKILL.md commands/forge-flows.md
git rm -r --cached skills/siae-frontend-flows/ 2>/dev/null || true
git commit -m "feat(nr-test-flows): rename from siae-frontend-flows, update frontmatter and references"
```

Output atteso: commit creato con messaggio corretto.

---

### Task 2: Nuovo schema `flow-map-template.yaml` [PENDING]

**Dipende da:** Task 1 (directory rinominata)

**File coinvolti:**
- Modifica: `skills/nr-test-flows/reference/flow-map-template.yaml`

**Step 1: Verifica il contenuto attuale**

```bash
head -20 skills/nr-test-flows/reference/flow-map-template.yaml
```

Output atteso: header con `# Flow Map Template — siae-frontend-flows`.

**Step 2: Sostituisci il file con il nuovo schema**

Riscrivi `skills/nr-test-flows/reference/flow-map-template.yaml` con questo contenuto completo:

```yaml
# Flow Map Template — nr-test-flows
#
# Schema deterministico per NRT flow map.
# Flow ID derivato da simboli del codice — NON libero.
# L5 signals obbligatori per ogni flusso.
# Priority evidence obbligatorio — nessun giudizio di dominio.
#
# OBBLIGATORIO: ogni sezione e flusso DEVONO citare il file sorgente (file:riga).
# Se non hai evidenza → confidence: UNVERIFIED (non omettere, non inventare).

flow_map:
  metadata:
    repository: "{nome-repo}"
    framework: "{Vue.js 3 | Nuxt | Angular | React | Ionic+Angular | Flutter | ...}"
    framework_confidence: "CONFIRMED | INFERRED"
    framework_evidence: "{file:riga}"
    generated_at: "{YYYY-MM-DD}"
    analyst: "nr-test-flows"

  sections:

    - id: "section-auth"
      name: "Autenticazione"
      access: "pubblico"           # pubblico | autenticato | ruolo:{nome-ruolo}
      route_prefix: "/auth"
      source: "{file:riga}"        # es. src/router/index.ts:12
      confidence: "CONFIRMED"      # CONFIRMED | INFERRED | UNVERIFIED

      flows:

        - id: "auth--LoginView--POST-auth-login"
          # Formato ID deterministico: {route-slug}--{ComponentName}--{HTTP_METHOD}-{api-path-segment}
          # Se solo navigazione (nessuna API): {route-slug}--{ComponentName}--nav-only
          # Se solo GET: {route-slug}--{ComponentName}--GET-{api-path-segment}
          name: "Login con credenziali"
          priority: "CRITICAL"
          # Regole priority (da evidence-patterns.md § 5 Pattern Meccanici):
          # CRITICAL: canActivate/guard + API mutante, entry point post-login, /auth|/payment|/submit|/sign|/confirm|/delete
          # HIGH: API mutante (P1) senza CRITICAL, form discriminator che cambia payload (P5), rendering per ruolo
          # MEDIUM: solo P4 (submit) senza API, solo P2 (navigation) senza API
          # LOW/SKIP: nessun pattern → component presentazionale, non genera flusso NRT
          priority_evidence:
            rule: "endpoint-path-contains-auth"   # la regola applicata (non il giudizio)
            source_guard: ""                       # file:riga del guard (se applicabile)
            source_api: "{file:riga}"              # es. src/api/auth.ts:12

          trigger: "Apertura app / navigazione a /login"
          entry_point: "{file:riga}"
          confidence: "CONFIRMED"

          steps:
            - step: 1
              action: "Utente visualizza il form di login"
              component: "{file:riga}"
            - step: 2
              action: "Utente inserisce username e password"
              component: "{file:riga}"
            - step: 3
              action: "Utente clicca 'Accedi'"
              component: "{file:riga}"
            - step: 4
              action: "Sistema autentica → redirect alla home"
              component: "{file:riga}"

          api_calls:
            - endpoint: "POST /api/auth/login"
              source: "{file:riga}"
              confidence: "CONFIRMED"

          guards: []

          roles:
            - "tutti gli utenti (non autenticati)"

          # L5 SIGNALS — obbligatorio per ogni flusso (anche se vuoto)
          # Eseguire il grep L5 da evidence-patterns.md § "I 5 Pattern Meccanici" prima di compilare.
          l5_signals:
            store_states: []
            # es. [{store: "src/stores/auth.ts:12", states: ["IDLE","LOADING","SUCCESS","ERROR"]}]
            form_discriminators: []
            # es. [{component: "src/views/LoginView.vue:45", v_if_var: "loginType", branches: ["standard","sso"]}]
            computed_rendering: []
            # es. [{component: "src/views/LoginView.vue:78", condition: "isSsoEnabled", renders: "SsoButton"}]

          # VARIANTS — obbligatorio se form_discriminators non è vuoto
          # Una variant per ogni branch del discriminatore.
          variants: []
          # es.:
          # - variant_id: "auth--LoginView--POST-auth-login--variant-sso"
          #   branch_condition: "loginType === 'sso'"
          #   source: "src/views/LoginView.vue:45"
          #   priority_delta: null  # null = stesso priority del flusso padre

    - id: "section-dashboard"
      name: "Dashboard"
      access: "autenticato"
      route_prefix: "/dashboard"
      source: "{file:riga}"
      confidence: "CONFIRMED"

      flows:

        - id: "dashboard--DashboardView--GET-dashboard-stats"
          name: "Visualizzazione overview"
          priority: "HIGH"
          priority_evidence:
            rule: "get-api-core-content"
            source_guard: "{file:riga}"
            source_api: "{file:riga}"
          trigger: "Navigazione a /dashboard dopo login"
          entry_point: "{file:riga}"
          confidence: "CONFIRMED"
          steps:
            - step: 1
              action: "Sistema carica i dati del dashboard"
              component: "{file:riga}"
            - step: 2
              action: "Utente visualizza widget/statistiche principali"
              component: "{file:riga}"
          api_calls:
            - endpoint: "GET /api/dashboard/stats"
              source: "{file:riga}"
              confidence: "CONFIRMED"
          guards:
            - name: "authGuard"
              source: "{file:riga}"
          roles:
            - "utente standard"
            - "amministratore"
          l5_signals:
            store_states: []
            form_discriminators: []
            computed_rendering: []
          variants: []

    # Template sezione generica — duplica e adatta
    - id: "section-{nome}"
      name: "{Nome Sezione}"
      access: "autenticato"
      route_prefix: "/{path}"
      source: "{file:riga}"
      confidence: "CONFIRMED | INFERRED | UNVERIFIED"

      flows:

        - id: "{route-slug}--{ComponentName}--{HTTP_METHOD}-{api-path-segment}"
          name: "{Descrizione operazione}"
          priority: "HIGH"
          priority_evidence:
            rule: "{regola applicata: mutating-api+canActivate-guard | endpoint-path-contains-auth | mutating-api | form-discriminator-changes-payload | role-based-rendering | submit-no-api | nav-only}"
            source_guard: ""
            source_api: "{file:riga}"
          trigger: "{cosa scatena questo flusso}"
          entry_point: "{file:riga}"
          confidence: "CONFIRMED"
          steps:
            - step: 1
              action: "{azione}"
              component: "{file:riga}"
          api_calls: []
          guards: []
          roles:
            - "{ruolo o profilo}"
          l5_signals:
            store_states: []
            form_discriminators: []
            computed_rendering: []
          variants: []

  # Gap Report — OBBLIGATORIO anche se vuoto
  gap_report:
    - type: "UNVERIFIED_SECTION | MISSING_GUARD_EVIDENCE | API_CALL_UNRESOLVED"
      severity: "CRITICAL | INFO"
      # CRITICAL: gap che potrebbe far mancare una regressione (guard mancante, flusso mutante non mappato)
      # INFO: gap cosmetico (API GET non mappata a sezione, naming incerto)
      description: "{descrizione}"
      evidence_searched: "{lista file cercati}"

  summary:
    total_sections: 0
    total_flows: 0
    total_variants: 0
    by_priority:
      CRITICAL: 0
      HIGH: 0
      MEDIUM: 0
      LOW_SKIP: 0
    by_access:
      pubblico: 0
      autenticato: 0
    by_confidence:
      CONFIRMED: 0
      INFERRED: 0
      UNVERIFIED: 0
    l5_signals_found:
      store_states: 0
      form_discriminators: 0
      variants_generated: 0
    gaps_found:
      CRITICAL: 0
      INFO: 0
```

**Step 3: Verifica campi chiave presenti**

```bash
grep -c "priority_evidence" skills/nr-test-flows/reference/flow-map-template.yaml
```

Output atteso: `3` (almeno 3 occorrenze — una per ogni flow + template)

```bash
grep -c "l5_signals" skills/nr-test-flows/reference/flow-map-template.yaml
```

Output atteso: `3` (almeno 3 occorrenze)

```bash
grep -c "variant_id\|variants:" skills/nr-test-flows/reference/flow-map-template.yaml
```

Output atteso: numero > 0

**Step 4: Commit**

```bash
git add skills/nr-test-flows/reference/flow-map-template.yaml
git commit -m "feat(nr-test-flows): deterministic flow-map schema with L5 signals, variants, priority_evidence"
```

---

### Task 3: Update `evidence-patterns.md` — 5 Pattern Meccanici + L5 grep [PENDING]

**Dipende da:** Task 1

**File coinvolti:**
- Modifica: `skills/nr-test-flows/reference/evidence-patterns.md`

**Step 1: Aggiungi la sezione "I 5 Pattern Meccanici" all'INIZIO del file**

Inserisci **prima** di `## ANTI-HALLUCINATION PROTOCOL` il seguente blocco:

```markdown
## I 5 Pattern Meccanici di Estrazione Flussi NRT

Un flusso NRT = uno di questi 5 pattern, cercabili con grep/Grep tool.
NON esiste un flusso che non corrisponda ad almeno uno di questi pattern.
Se un component non ha nessun pattern → LOW/SKIP, non genera flusso NRT.

| Pattern | Grep | Produce |
|---------|------|---------|
| **P1 — Mutating API call** | `axios\.post\|axios\.put\|axios\.delete\|axios\.patch\|fetch.*POST\|fetch.*PUT` | 1 flusso per call + component che la ospita |
| **P2 — Router navigation in handler** | `router\.push\|navigate\(\|\$router\.push\|this\.router\.navigate` | 1 flusso per navigazione programmatica in @click/@submit |
| **P3 — Store action con state transition** | (in store file) funzioni che modificano stato nominato | 1 flusso per transizione nominata |
| **P4 — Form submit handler** | `@submit\|handleSubmit\|onSubmit\|v-on:submit` | 1 flusso per submit handler |
| **P5 — Form discriminator** | `v-if="\|*ngIf="\|{condition &&}` su variabile di form state | 1 variant per branch distinto |

### Regole P5 — Distinguere form discriminator da guard

```
INCLUDI (form discriminator → variants):
  tipologia, tipo, categoria, step, mode, fase, stato_form, tipoEvento

ESCLUDI (guard/auth → non crea variants, già coperto da TIER 3):
  isAuthenticated, isAdmin, isLoading, isError, showError, hasPermission
```

### Regole Priority — Code-Derivable (Step 3 di nr-test-flows)

```
CRITICAL se almeno uno di:
  → component ha canActivate/redirect guard E almeno un P1 (API mutante)
    rule: "mutating-api+canActivate-guard"
  → è la prima route dopo redirect post-login (entry point autenticato)
    rule: "entry-point-post-login"
  → API endpoint contiene: /auth, /payment, /submit, /sign, /confirm, /delete
    rule: "endpoint-path-contains-{keyword}"

HIGH se almeno uno di:
  → P1 (API mutante) senza pattern CRITICAL
    rule: "mutating-api"
  → P5 (form discriminator) con branches che cambiano payload API
    rule: "form-discriminator-changes-payload"
  → rendering condizionale su ruolo utente
    rule: "role-based-rendering"

MEDIUM se:
  → solo P4 (submit) senza API call
    rule: "submit-no-api"
  → solo P2 (router navigation) senza API
    rule: "nav-only"

LOW/SKIP se:
  → nessuno dei 5 pattern → component presentazionale, non genera flusso NRT
    Non aggiungere alla flow map.
```

---
```

**Step 2: Aggiungi sezione "L5 Scan" per Vue.js 3**

Nella sezione `## Vue.js 3`, dopo `### Dove cercare le API calls`, aggiungi:

```markdown
### L5 Scan — Vue.js 3 (Step 2d obbligatorio)

```bash
# P5 — Form discriminators (crea variants)
# Cerca v-if su variabili di form state (NON su isAuthenticated/isAdmin/isLoading)
Grep pattern: v-if="[a-zA-Z][a-zA-Z0-9_]*\s*[=!]=
# poi filtra manualmente: escludi isAuthenticated|isAdmin|isLoading|isError|show|has
# Includi: tipologia, tipo, categoria, step, mode, fase

# P3 — Store states
# Cerca in src/stores/: ref() o reactive() con stati nominati
Grep pattern: const [a-zA-Z]+ = ref\(|states:\s*\[
# poi leggi le actions che li modificano

# Computed rendering su ruolo
Grep pattern: v-if.*[Rr]ole|v-if.*[Aa]dmin|:class.*[Rr]ole|computed.*[Pp]ermission
```
```

**Step 3: Aggiungi sezione "L5 Scan" per Angular**

Nella sezione `## Angular`, dopo `### Dove cercare tab/nav structure`, aggiungi:

```markdown
### L5 Scan — Angular (Step 2d obbligatorio)

```bash
# P5 — Form discriminators
Grep pattern: \*ngIf="[a-zA-Z][a-zA-Z0-9_]*\s*[=!]==
# poi filtra: escludi isAuthenticated|isAdmin|isLoading|isError

# P3 — Store states (NgRx)
Grep pattern: createReducer\|on\(.*Action|\.pipe\(select
# oppure (servizi con BehaviorSubject):
Grep pattern: BehaviorSubject<|new BehaviorSubject

# Computed rendering su ruolo
Grep pattern: \*ngIf.*role|hasRole|canAccess|isAdmin
```
```

**Step 4: Aggiungi sezione "L5 Scan" per React**

Nella sezione `## React`, dopo `### Dove cercare le API calls`, aggiungi:

```markdown
### L5 Scan — React (Step 2d obbligatorio)

```bash
# P5 — Form discriminators
Grep pattern: \{[a-zA-Z][a-zA-Z0-9_]*\s*===.*&&|condition\s*&&
# poi filtra: escludi isAuthenticated|isAdmin|isLoading|error

# P3 — Store states (Redux/Zustand)
Grep pattern: createSlice\|useSelector\|slice\.actions|set[A-Z][a-zA-Z]+\(
# Zustand:
Grep pattern: create\(\(set\)

# Computed rendering su ruolo
Grep pattern: user\.role|hasPermission|canEdit|isAdmin
```
```

**Step 5: Aggiungi sezione "L5 Scan" per Flutter**

Nella sezione `## Flutter`, dopo `### Dove cercare le tab navigation`, aggiungi:

```markdown
### L5 Scan — Flutter (Step 2d obbligatorio)

```bash
# P5 — Form discriminators (conditional widget rendering)
Grep pattern: if\s*\([a-zA-Z][a-zA-Z0-9_]*\s*[=!]==.*\)\s*\n?\s*[A-Z]
# cerca blocchi if/switch che rendono widget diversi basati su form state

# P3 — Store states (Riverpod/Bloc/Provider)
Grep pattern: StateNotifier<|Cubit<|BlocBuilder|ChangeNotifier
# poi leggi i metodi che cambiano stato

# Computed rendering su ruolo
Grep pattern: userRole|hasPermission|isAdmin|canEdit
```
```

**Step 6: Verifica sezioni aggiunte**

```bash
grep -c "I 5 Pattern Meccanici" skills/nr-test-flows/reference/evidence-patterns.md
```

Output atteso: `1`

```bash
grep -c "L5 Scan" skills/nr-test-flows/reference/evidence-patterns.md
```

Output atteso: `4` (Vue, Angular, React, Flutter)

**Step 7: Commit**

```bash
git add skills/nr-test-flows/reference/evidence-patterns.md
git commit -m "feat(nr-test-flows): add 5 mechanical patterns and L5 scan sections to evidence-patterns"
```

---

### Task 4: Update `SKILL.md` body — Step 2d e Step 3 code-derivable rules [PENDING]

**Dipende da:** Task 1

**File coinvolti:**
- Modifica: `skills/nr-test-flows/SKILL.md`

**Step 1: Aggiungi Step 2d — L5 Scan dopo Step 2 MAP**

Trova il blocco di chiusura di Step 2 (la sezione `#### Output Step 2`). Subito dopo l'annuncio di Step 2, aggiungi il nuovo sotto-step:

```markdown
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

Se non esegui 2d o non dichiari il risultato → la sezione è INCOMPLETA.
```

**Step 2: Sostituisci la tabella priorità in Step 3 PRIORITIZE**

Trova il blocco:

```markdown
| Priorità | Criteri |
|----------|---------|
| **CRITICAL** | Blocca l'accesso all'app (login, auth flow) / operazione core del business (pagamento, submit documentazione) / perdita dati se fallisce |
| **HIGH** | Funzionalità principale della sezione (crea record, aggiorna stato) / flusso usato da tutti gli utenti / operazione irreversibile |
| **MEDIUM** | Funzionalità secondaria (filtri, sorting, export) / configurazione profilo / operazioni raramente eseguite |
```

Sostituisci con:

```markdown
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
```

**Step 3: Verifica Step 2d presente**

```bash
grep -c "2d — L5 Scan" skills/nr-test-flows/SKILL.md
```

Output atteso: `1`

**Step 4: Verifica vecchia tabella soggettiva rimossa**

```bash
grep -c "operazione core del business" skills/nr-test-flows/SKILL.md
```

Output atteso: `0`

**Step 5: Verifica nuova tabella presente**

```bash
grep -c "priority_evidence.rule" skills/nr-test-flows/SKILL.md
```

Output atteso: `1` (almeno nella tabella)

**Step 6: Commit**

```bash
git add skills/nr-test-flows/SKILL.md
git commit -m "feat(nr-test-flows): add Step 2d L5 scan and replace subjective priority table with code-derivable rules"
```

---

### Task 5: Verifica coerenza interna [PENDING]

**Dipende da:** Task 1, 2, 3, 4

**File coinvolti:** tutti i file di `skills/nr-test-flows/` (sola lettura)

**Step 1: Nessun riferimento al vecchio nome rimasto**

```bash
grep -r "siae-frontend-flows" skills/ commands/ .claude-plugin/
```

Output atteso: nessun match.

**Step 2: Coerenza flow ID format documentato sia in SKILL.md che in template**

```bash
grep -c "route-slug.*ComponentName.*HTTP_METHOD" skills/nr-test-flows/reference/flow-map-template.yaml
grep -c "route-slug.*ComponentName.*HTTP_METHOD" skills/nr-test-flows/SKILL.md
```

Output atteso: entrambi > 0 (il formato è documentato in entrambi i file)

**Step 3: L5 scan documentato sia in evidence-patterns che in SKILL.md**

```bash
grep -c "L5 Scan\|L5 scan\|l5_signals" skills/nr-test-flows/SKILL.md
grep -c "L5 Scan" skills/nr-test-flows/reference/evidence-patterns.md
```

Output atteso: entrambi > 0

**Step 4: 5 Pattern Meccanici referenziati da SKILL.md**

```bash
grep -c "5 Pattern Meccanici\|evidence-patterns" skills/nr-test-flows/SKILL.md
```

Output atteso: > 0

**Step 5: Smoke test strutturale — conteggio sezioni SKILL.md**

```bash
grep -c "^###" skills/nr-test-flows/SKILL.md
```

Output atteso: numero uguale o superiore alla versione precedente (il workflow a 6 step è invariato — aggiungiamo 2d, non rimuoviamo step)

**Step 6: Catalogo using-devforge aggiornato**

```bash
grep "nr-test-flows" skills/using-devforge/SKILL.md
```

Output atteso: riga con `nr-test-flows` e trigger NRT.

**Step 7: Commit finale**

```bash
git add -A
git commit -m "chore(nr-test-flows): verify internal coherence — all references updated"
```

Output atteso: "nothing to commit" (tutto già committato nei task precedenti) oppure commit con eventuali fix minori.
