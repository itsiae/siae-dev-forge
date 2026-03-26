# Design Doc — siae-nr-test-flows Evolution

**Data:** 2026-03-26
**Branch:** refactor/migrate-mermaid-to-plantuml
**Autore:** brainstorming via AI as a Judge (4 giudici)
**SP:** 8 SP-Umano / 3 SP-Augmented

---

## Contesto

La skill `siae-nr-test-flows` è stata valutata da 4 giudici AI as a Judge specializzati.
Score composito attuale: **4.4/10** su 4 dimensioni.

| Dimensione | Score | Gap Critico |
|---|---|---|
| Interrogation Logic | 2/10 | Zero domande pre-analisi — cecità contestuale |
| Coverage IT Factory | 5/10 | Next.js/Expo assenti; P6-P10 mancanti |
| Test Ordering | 4/10 | Ordine router-topology, nessun concetto sessione |
| Enterprise Quality | 6.5/10 | No Expected Result Markdown, no Smoke Set |

---

## Decisioni Architetturali

### ADR-1: Question Tree esternalizzato in reference file

**Problema:** SKILL.md è già vicino al limite token (10k). Aggiungere il Question Tree
direttamente (7 blocchi A-G con tabelle impact) lo porterebbe oltre il limite di load.

**Decisione:** Nuovo file `reference/question-tree.md`. SKILL.md aggiunge Step 0 con rimando.

**Alternativa scartata:** inline nel SKILL.md — rischio rottura del load della skill.

### ADR-2: Journey View addizionale, non sostitutivo

**Problema:** Cambiare l'ordinamento di default dell'output rompe i workflow QA esistenti
che si aspettano l'output per-sezione.

**Decisione:** La vista per-sezione rimane default. La Journey View è attivabile con
`--journey` flag e aggiunge una sezione "SESSIONI" in fondo alla test list.

**Alternativa scartata:** sostituzione completa dell'output — breaking change.

### ADR-3: xray-csv-template.md invariato

**Decisione:** Nessuna modifica al template CSV. Il formato Xray è vincolato
all'importatore SIAE specifico (inclusi typo intenzionali: `Expceted Result`, `Test  Type`).

### ADR-4: P6-P10 in evidence-patterns.md, non come sezione separata

**Decisione:** I pattern meccanici aggiuntivi vengono aggiunti come sezione
"Pattern Meccanici Aggiuntivi (P6-P10)" in `evidence-patterns.md`,
che è il file di riferimento naturale per i pattern di estrazione.

---

## Scope — 5 Wave di Modifiche

### Wave 1 — Question Tree (impatto massimo — Judge 1)

**File:** `SKILL.md` + nuovo `reference/question-tree.md`

**Contenuto question-tree.md:**
- Blocco A (sempre): tipo app, operazione business critica, profili utente
- Blocco B (sempre): scope, esclusioni, Jira Story ID
- Blocco C (se guard rilevati): meccanismo auth, scadenza token, enforcement
- Blocco D (se API call): BFF vs microservizi, terze parti critiche, feature flags
- Blocco E (se B2B/multi-tenant): isolamento dati, route con ID dinamico
- Blocco F (se i18n 2+ locale): locale con flussi diversi
- Blocco G (sempre, opzionale): flussi ad alto rischio, flussi da escludere

**Modifiche SKILL.md:**
- Aggiunge Step 0 — CONTEXT INTERVIEW prima di Step 1 INGEST
- Aggiorna Step 3 PRIORITIZE: usa variabili $APP_TYPE e $BUSINESS_CRITICAL_FLOW
- Aggiorna Step 4 GENERATE: usa $USER_ROLES nei TC [PROFILO], $JIRA_STORY nel CSV

**Variabili di sessione iniettate:**
```
$APP_TYPE             → modifica regole CRITICAL in Step 3
$BUSINESS_CRITICAL_FLOW → override CRITICAL (rule: "business-critical-declared")
$USER_ROLES           → sostituisce nomi tecnici nei TC [PROFILO]
$JIRA_STORY           → pre-compila CSV (placeholder se non fornito)
$SCOPE_EXCLUDE        → deny-list in Step 1 INGEST
$SCOPE_DELTA          → harvest limitato al delta branch/PR
$FEATURE_FLAGS        → tag flussi con feature_flag: true
$THIRD_PARTY_APIS     → override CRITICAL per endpoint terze parti
$MULTI_TENANT         → genera TC cross-tenant CRITICAL
```

### Wave 2 — Framework Detection (Judge 2)

**File:** `reference/framework-detection-matrix.md`

**Aggiunge 4 sezioni:**

1. **Next.js**
   - L1: `next.config.js` o `next.config.ts`
   - L2: `"next"` in package.json
   - L3: `app/` con `page.tsx` (App Router) o `pages/` con `_app.tsx` (Pages Router)
   - Precedenza: Next > Nuxt
   - Harvest: `app/**/page.tsx`, `app/**/layout.tsx`, `middleware.ts`
   - Special: `'use server'` = Server Action = P1 equivalente

2. **Expo (React Native)**
   - L1: `app.json` con campo `"expo"` o `app.config.ts`
   - L2: `"expo"` in package.json; `"expo-router"` indica file-based routing
   - Harvest: `app/_layout.tsx`, `app/(tabs)/`, `app/(auth)/`

3. **React Native standalone**
   - L1: `android/` + `ios/` nella root + assenza `"expo"`
   - L2: `"react-native"` senza `"expo"` in package.json
   - Harvest: `src/navigation/RootNavigator.tsx`, `src/screens/`

4. **SvelteKit**
   - L1: `svelte.config.js`
   - L2: `"@sveltejs/kit"` in package.json
   - Harvest: `src/routes/**/+page.svelte`, `src/routes/**/+page.server.ts`, `src/hooks.server.ts`

**Precedenza aggiornata:**
```
Ionic > Next.js > Nuxt > Expo > React Native standalone > SvelteKit > Vue > React > Flutter
```

### Wave 3 — Pattern Meccanici P6-P10 (Judge 2)

**File:** `reference/evidence-patterns.md`

**Nuova sezione "Pattern Meccanici Aggiuntivi (P6-P10)":**

| Pattern | Grep | Priorità | TC aggiuntivi |
|---|---|---|---|
| P6 — GraphQL Mutation | `useMutation\|apollo\.mutate\|mutation.*\.gql` | HIGH/CRITICAL | Standard |
| P7 — WebSocket/SSE | `new WebSocket\|socket\.on(\|webSocket(` | MEDIUM | [EDGE] disconnessione+riconnessione |
| P8 — File Upload | `new FormData(\|type=['"]file['"]` | HIGH | [NEG] tipo file, [EDGE] size limit |
| P9 — Wizard Step | `currentStep\|createMachine(\|MatStepper` | MEDIUM/HIGH | TC per step intermedio |
| P10 — Polling | `refetchInterval\|pollInterval\|setInterval.*api` | MEDIUM | [EDGE] timeout, rete intermittente |

**Aggiorna SKILL.md Step 1b:** "Se P6–P10 rilevati, aggiungi alla flow map."
**Aggiorna SKILL.md Step 2:** regole ID deterministico per P6-P10.

### Wave 4 — User Journey Ordering (Judge 3)

**File nuovo:** `reference/journey-ordering-rules.md`

**Contenuto:**
1. Grafo dipendenze (5 regole meccaniche derivabili dal YAML)
2. Business Criticality Score per sezione (tabella lookup)
3. Algoritmo topological sort + raggruppamento sessioni
4. Pattern dipendenza comuni (15 pattern tabellati)

**Modifiche SKILL.md:**
- Aggiunge Step 4b — JOURNEY VIEW (opzionale, attivabile con --journey)
- Flow map template YAML: aggiunge campo opzionale `depends_on[]` per flusso

### Wave 5 — Enterprise Quality (Judge 4)

**File:** `reference/test-list-template.md`

**Modifiche:**
- Aggiunge colonne `Precondizioni` e `Expected Result` nel template Markdown
- Aggiorna tutti gli esempi con le nuove colonne

**Modifiche SKILL.md:**
- Aggiunge Step 4c — SMOKE TEST SELECTION dopo GENERATE
- Logica: primo TC Happy Path di ogni flusso CRITICAL → Labels: "smoke; nrt"
- Output: sezione separata "Smoke Test Set" nella test list
- Annuncio: "Smoke set: {N} TC | Regression suite: {M} TC"

---

## Criteri di Accettazione

- [ ] Step 0 (Question Tree) viene presentato prima di Step 1 INGEST
- [ ] $BUSINESS_CRITICAL_FLOW produce override CRITICAL con rule "business-critical-declared"
- [ ] $SCOPE_EXCLUDE genera entry GAP_REPORT di tipo OUT_OF_SCOPE
- [ ] Next.js rilevato con precedenza su React quando next.config.* presente
- [ ] `'use server'` trattato come P1 in repo Next.js
- [ ] P6 (GraphQL) genera flusso HIGH per mutation con verbo mutante
- [ ] P8 (File Upload) genera TC [NEG] tipo-file e [EDGE] size-limit
- [ ] Journey View attivabile con --journey e produce sezione SESSIONI
- [ ] Smoke Test Set generato automaticamente per tutti i flussi CRITICAL
- [ ] Template Markdown ha colonne Precondizioni e Expected Result
- [ ] xray-csv-template.md NON modificato

---

## File Coinvolti

| File | Tipo | Wave |
|---|---|---|
| `skills/siae-nr-test-flows/SKILL.md` | Modifica | 1, 3, 4, 5 |
| `skills/siae-nr-test-flows/reference/question-tree.md` | Nuovo | 1 |
| `skills/siae-nr-test-flows/reference/framework-detection-matrix.md` | Modifica | 2 |
| `skills/siae-nr-test-flows/reference/evidence-patterns.md` | Modifica | 3 |
| `skills/siae-nr-test-flows/reference/journey-ordering-rules.md` | Nuovo | 4 |
| `skills/siae-nr-test-flows/reference/flow-map-template.yaml` | Modifica minore | 4 |
| `skills/siae-nr-test-flows/reference/test-list-template.md` | Modifica | 5 |
| `skills/siae-nr-test-flows/reference/xray-csv-template.md` | **INVARIATO** | — |
