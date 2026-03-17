# nr-test-flows — Rename + Deterministic NRT Extraction

**Data:** 2026-03-12
**Autore:** mazzacuv
**Status:** APPROVATO

---

## Contesto

La skill `siae-frontend-flows` produce test list con `NRT=Y` di default per tutti i TC
(documentato in `reference/xray-csv-template.md:37`). Il suo scopo reale è generare
No-Regression Test flows da repository frontend. Il nome "frontend-flows" oscura questo
scopo e porta ad usarla come generatore di test generici invece che come strumento NRT.

Inoltre, l'audit di produzione ha rivelato 6 gap che compromettono il determinismo:
due run indipendenti sullo stesso codebase possono produrre flow map diverse a causa
di definizioni soggettive di "flusso" e criteri di priorità basati sul giudizio.

---

## Goal

1. **Rinominare** `siae-frontend-flows` → `nr-test-flows`
2. **Rendere deterministico** l'output: stesso codebase → stessa flow map, sempre
3. **Aggiungere L5 tier** (state machines, form discriminators) per catturare regressioni invisibili alla sola navigazione

Le modifiche sono concentrate nei reference file (fonte di verità) e nelle regole
operative di SKILL.md. Il workflow a 6 step, il sistema CONFIRMED/INFERRED/UNVERIFIED,
la distinzione mobile/web e la regola varianti wizard sono preservati intatti.

---

## Architettura

### Approccio scelto: Opzione B — Rename + Refactoring Reference Files

Rename del skill + rifacimento di `flow-map-template.yaml` con schema deterministico
+ aggiornamento `evidence-patterns.md` con i 5 pattern meccanici + patch chirurgica a
`SKILL.md` per Step 2d (L5 scan) e Step 3 (regole code-derivable). I file
`test-list-template.md` e `xray-csv-template.md` restano invariati — sono già enterprise-grade.

### File coinvolti

```
skills/siae-frontend-flows/     → rinominata in skills/nr-test-flows/
  SKILL.md                      → modifica: frontmatter, Step 2d, Step 3 rules
  reference/
    flow-map-template.yaml      → modifica: schema deterministico (id, l5_signals, variants, priority_evidence)
    evidence-patterns.md        → modifica: aggiunta sezione "5 Pattern Meccanici" + L5 grep per framework
    test-list-template.md       → invariato
    xray-csv-template.md        → invariato
    framework-detection-matrix.md → invariato

skills/using-devforge/SKILL.md  → modifica: catalogo skill (nome + trigger)
commands/forge-flows.md         → modifica: riferimento skill aggiornato
```

---

## Design Dettagliato

### 1. Rename & Scope

| Da | A |
|:---|:---|
| `skills/siae-frontend-flows/` | `skills/nr-test-flows/` |
| `name: siae-frontend-flows` | `name: nr-test-flows` |
| Banner `FRONTEND FLOWS` | Banner `NR TEST FLOWS` |
| Tutti i riferimenti interni al nome | `nr-test-flows` |
| `using-devforge/SKILL.md` riga catalogo | aggiornata |

Il comando `/forge-flows` resta invariato.

---

### 2. Nuovo Schema `flow-map-template.yaml`

#### Flow ID deterministico

Derivato da 3 simboli del codice, non libero:

```yaml
id: "{route-slug}--{ComponentName}--{HTTP_METHOD}-{api-path-segment}"
# Esempi:
# "auth--LoginView--POST-auth-login"
# "dashboard--DashboardView--GET-dashboard-stats"
# "settings--SettingsView--nav-only"  (nessuna API)
```

Regola: se il flusso ha una API mutante, usa `{HTTP_METHOD}-{path-segment}`.
Se solo GET, usa `GET-{path-segment}`. Se solo navigazione, usa `nav-only`.

#### L5 Signals (obbligatorio per ogni flusso)

```yaml
l5_signals:
  store_states: []
  # es. [{store: "src/stores/auth.ts:12", states: ["IDLE","LOADING","SUCCESS","ERROR"]}]
  form_discriminators: []
  # es. [{component: "src/views/CreateView.vue:45", v_if_var: "tipologia", branches: ["A","B"]}]
  computed_rendering: []
  # es. [{component: "src/views/Dashboard.vue:78", condition: "isAdmin", renders: "AdminPanel"}]
```

Se non ci sono segnali L5: `l5_signals: {}` — mai omettere il campo.

#### Variants (obbligatorio se form_discriminators non è vuoto)

```yaml
variants:
  - variant_id: "{flow-id}--variant-{branch-value}"
    branch_condition: "tipologia === 'A'"
    source: "{file:riga}"
    priority_delta: null  # o CRITICAL/HIGH/MEDIUM se diverso dal flusso padre
```

#### Priority Evidence (audit trail deterministico)

```yaml
priority: "CRITICAL"
priority_evidence:
  rule: "mutating-api+canActivate-guard"
  source_guard: "src/router/guards.ts:14"
  source_api: "src/api/auth.ts:28"
```

---

### 3. Sezione "5 Pattern Meccanici" in `evidence-patterns.md`

Da aggiungere **all'inizio del file**, prima dei framework:

```
## I 5 Pattern Meccanici di Estrazione Flussi NRT

Un flusso NRT = uno di questi 5 pattern, cercabili con grep.
NON esiste un flusso che non corrisponda ad almeno uno di questi pattern.

P1 — Mutating API call
     Grep: axios\.post|axios\.put|axios\.delete|axios\.patch|fetch.*POST|fetch.*PUT
     → un flusso per ogni call + il component che la ospita

P2 — Router navigation in handler
     Grep: router\.push|navigate\(|\$router\.push|this\.router\.navigate
     → un flusso per ogni navigazione programmatica in @click/@submit

P3 — Store action con state transition
     Grep: (in store file) function|action con stato prima/dopo nominati
     → un flusso per ogni transizione nominata

P4 — Form submit handler
     Grep: @submit|handleSubmit|onSubmit|v-on:submit
     → un flusso per ogni submit handler

P5 — Form discriminator (crea variants)
     Grep: v-if="|*ngIf="|{condition &&}| su variabile di form state
     → una variant per ogni branch distinto
     ATTENZIONE: escludere isAuthenticated, isAdmin, isLoading → sono guard/P3
     INCLUDERE: tipologia, tipo, categoria, step, mode → discriminatori di flusso
```

Aggiunta grep L5 per ogni framework nella sezione framework specifica. Esempio Vue.js 3:

```
### L5 Scan — Vue.js 3 (obbligatorio in Step 2d)

# Form discriminators (P5)
Grep: v-if="[a-zA-Z]+\s*==
      Escludi match con: isAuthenticated|isAdmin|isLoading|isError|show
      Includi: ogni altra variabile → form discriminator

# Store states (P3)
Grep (in src/stores/): const [a-zA-Z]+ = ref\(|const [a-zA-Z]+ = reactive\(
      poi cerca azioni che modificano lo stato

# Computed rendering (basato su ruolo)
Grep: computed\(|:class=|v-if.*Role|v-if.*role|v-if.*isAdmin
```

---

### 4. Regole Priority Code-Derivable in `SKILL.md` — Step 3

Sostituisce la tabella soggettiva attuale:

```
CRITICAL se almeno uno di:
  → il component ha canActivate/redirect guard E almeno un P1 (API mutante)
  → è la prima route dopo redirect post-login (entry point autenticato)
  → l'API endpoint contiene: /auth, /payment, /submit, /sign, /confirm, /delete

HIGH se almeno uno di:
  → P1 (API mutante) senza pattern CRITICAL
  → P5 (form discriminator) con branches che cambiano payload API
  → rendering condizionale basato su ruolo utente (isAdmin, userRole, canEdit)

MEDIUM se:
  → solo P4 (submit) senza API call
  → solo P2 (router navigation) senza API

LOW / SKIP se:
  → nessuno dei 5 pattern → component presentazionale, non genera flusso NRT
```

Compila sempre `priority_evidence.rule` con la regola applicata.

---

### 5. Modifiche Chirurgiche a `SKILL.md`

#### Step 2 MAP — sotto-step 2d (aggiunto dopo 2c o come chiusura del MAP step)

```
#### 2d — L5 Scan (obbligatorio prima di chiudere ogni sezione)

Per ogni component letto durante il MAP, esegui il grep L5 da evidence-patterns.md:
1. Cerca form discriminators (P5) → aggiungi variants[] nel YAML
2. Cerca store states (P3) → aggiungi store_states in l5_signals
3. Cerca computed rendering su ruoli → aggiungi computed_rendering in l5_signals

Se non esegui 2d → la sezione è INCOMPLETA.
Dichiara esplicitamente "L5 scan: nessun discriminatore rilevato" se il grep
non produce risultati — non omettere il check.
```

#### Step 3 PRIORITIZE — sostituisce tabella

```
Applica le regole CRITICAL/HIGH/MEDIUM/LOW/SKIP da evidence-patterns.md
§ "I 5 Pattern Meccanici". Compila priority_evidence per ogni flusso.
Nessun giudizio di dominio ammesso: se non riesci a codificare la regola
che ha attivato la priorità, il flusso va in MEDIUM di default.
```

#### Frontmatter description

```yaml
description: >
  Analizza repository frontend/mobile e genera NRT flow map + test list deterministici
  pronti per Xray. Trigger: no-regression test flows, NRT suite, /forge-flows,
  repo Vue/React/Angular/Ionic/Flutter, team QA deve mappare flussi per regressione.
```

---

## Criteri di Accettazione

- [ ] `skills/nr-test-flows/` esiste, `skills/siae-frontend-flows/` rimosso
- [ ] `name: nr-test-flows` nel frontmatter di SKILL.md
- [ ] Banner aggiornato a `NR TEST FLOWS`
- [ ] `using-devforge/SKILL.md` catalogo: nome + trigger aggiornati
- [ ] `commands/forge-flows.md` invoca `siae-devforge:nr-test-flows`
- [ ] `flow-map-template.yaml`: flow ID deterministico, `l5_signals`, `variants[]`, `priority_evidence` presenti
- [ ] `evidence-patterns.md`: sezione "5 Pattern Meccanici" all'inizio + L5 grep per Vue, Angular, React, Flutter
- [ ] `SKILL.md` Step 2 ha sotto-step `2d — L5 Scan` obbligatorio con dichiarazione esplicita
- [ ] `SKILL.md` Step 3 ha riferimento alle regole code-derivable (vecchia tabella soggettiva rimossa)
- [ ] `SKILL.md` frontmatter `description` aggiornata con trigger NRT
- [ ] Workflow a 6 step, CONFIRMED/INFERRED/UNVERIFIED, distinzione mobile/web e regola varianti wizard INVARIATI

---

## Stima Story Points

**5 SP** — 2-3 giorni

| Task | SP |
|:---|:---:|
| Task 1: Rename directory + tutti i riferimenti (SKILL.md frontmatter, banner, using-devforge, forge-flows.md) | 1 |
| Task 2: Nuovo `flow-map-template.yaml` (schema deterministico: id, l5_signals, variants, priority_evidence) | 1 |
| Task 3: Update `evidence-patterns.md` (sezione 5 Pattern Meccanici + L5 grep per 4 framework) | 1 |
| Task 4: Update `SKILL.md` body (Step 2d, Step 3 rules code-derivable) | 1 |
| Task 5: Verifica coerenza interna + smoke test su codebase reale | 1 |

---

## Trade-off Registrati

- **Flow ID backward incompatible**: le flow map esistenti generare con `siae-frontend-flows`
  usano ID liberi — non sono compatibili con il nuovo schema. Scelta consapevole: i flussi NRT
  devono essere rigenerati sul nuovo schema per essere deterministici. Il vecchio output
  non era NRT-grade.

- **Grep L5 genera falsi positivi su v-if semplici**: il filtro "escludi isAuthenticated/isAdmin"
  non è exhaustivo. Preferito un approccio conservativo (includi e poi il QA scarta)
  rispetto a uno restrittivo (escludi e perdi varianti).

- **P3 (store state transitions) richiede lettura store file**: aumenta il file count dell'INGEST.
  Accettabile: le regressioni più insidiose stanno esattamente nei store.
