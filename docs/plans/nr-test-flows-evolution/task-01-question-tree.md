# Task 01 — Crea reference/question-tree.md

**Stato:** [PENDING]
**File:** `skills/siae-nr-test-flows/reference/question-tree.md` (NUOVO)
**Dipendenze:** nessuna

---

## Obiettivo

Creare il file con il Question Tree completo (7 blocchi A-G) che la skill
eseguirà come Step 0 — CONTEXT INTERVIEW prima di analizzare il codice.
Le risposte dell'utente iniettano variabili di sessione usate negli step successivi.

---

## Step 1 — Crea il file

Usa il Write tool per creare:
`skills/siae-nr-test-flows/reference/question-tree.md`

Contenuto completo:

```markdown
# Question Tree — siae-nr-test-flows Step 0

Questo file definisce il protocollo di interrogazione contestuale da eseguire
PRIMA dello Step 1 INGEST. Le risposte dell'utente iniettano variabili di sessione
usate negli step successivi per adattare prioritizzazione, TC e output.

**Tempo stimato:** 2-3 minuti di dialogo.

---

## Variabili di Sessione

Dopo l'intervista, le seguenti variabili devono essere disponibili:

| Variabile | Default | Usata in |
|---|---|---|
| `$APP_TYPE` | `generic` | Step 3 PRIORITIZE — regole CRITICAL aggiuntive |
| `$BUSINESS_CRITICAL_FLOW` | `null` | Step 3 PRIORITIZE — override CRITICAL |
| `$USER_ROLES` | `[]` | Step 4 GENERATE — nomi nei TC [PROFILO] |
| `$JIRA_STORY` | `{STORY-TBD}` | Step 4 GENERATE + Step 6 EXPORT |
| `$SCOPE_EXCLUDE` | `[]` | Step 1 INGEST — deny-list path |
| `$SCOPE_DELTA` | `null` | Step 1 INGEST — harvest limitato |
| `$FEATURE_FLAGS` | `false` | Step 2 MAP — tag flussi |
| `$THIRD_PARTY_APIS` | `[]` | Step 3 PRIORITIZE — override CRITICAL |
| `$MULTI_TENANT` | `false` | Step 4 GENERATE — TC cross-tenant |

---

## BLOCCO A — Contesto Applicativo (sempre obbligatorio)

### A1 — Tipo di applicazione

```
Qual è il tipo di applicazione che sto analizzando?

1. SPA consumer / B2C (e-commerce, self-service, onboarding utenti finali)
2. Portale B2B (workflow multi-step, approvazioni, contratti, fatturazione)
3. Admin panel / backoffice (CRUD, reportistica, gestione operatori)
4. Dashboard analytics (visualizzazione dati, filtri, export report)
5. App mobile consumer (Ionic/Flutter — già rilevabile, conferma dominio)
6. App con workflow approvativo (stati documento, transizioni, notifiche)
7. Altro: [descrizione libera]

→ Imposta $APP_TYPE
```

**Impatto per risposta A1:**

| $APP_TYPE | Effetto in Step 3 PRIORITIZE |
|---|---|
| `b2c-ecommerce` | Funnel acquisto (cart→checkout→payment→confirm) → CRITICAL automatico anche senza keyword URL |
| `b2b-portal` | Transizioni di stato documento → CRITICAL; cerca pattern `POST /{res}/{id}/approve|submit|confirm` |
| `admin-panel` | DELETE/bulk-delete → CRITICAL indipendentemente dal path; aggiunge [EDGE] concorrenza |
| `analytics-dashboard` | La maggior parte dei flussi sarà MEDIUM; aggiunge TC export (CSV/Excel/PDF) |
| `workflow-approvativo` | Ogni transizione stato genera tripla TC: happy/NEG/PROFILO |
| `generic` (default) | Solo regole code-derivable standard |

### A2 — Operazione di business critica

```
Qual è l'operazione di business più critica — quella che, se rotta, blocca il business?
(Risposta libera — es. "la creazione di un contratto", "il checkout del carrello",
"l'approvazione di un adempimento")

→ Imposta $BUSINESS_CRITICAL_FLOW
```

**Impatto:** il flusso nominato riceve CRITICAL forzato con `rule: "business-critical-declared"`,
indipendentemente dai pattern code-derivable.

Se l'utente risponde "non so" o "nessuna in particolare" → $BUSINESS_CRITICAL_FLOW = null.

### A3 — Profili utente

```
Quanti profili utente distinti esistono? Elencali con i loro nomi di dominio.
(es. "utente standard, operatore, amministratore, supervisore")

→ Imposta $USER_ROLES = [lista nomi]
```

**Impatto:** i nomi di $USER_ROLES sostituiscono i nomi tecnici del codice
(`isAdmin`, `userRole`) nei TC [PROFILO]. Se $USER_ROLES = [] → nessun TC [PROFILO] generato.

---

## BLOCCO B — Scope (sempre obbligatorio)

### B1 — Scope dell'analisi

```
Vuoi coprire l'intera applicazione o uno scope specifico?

1. Intera applicazione (full NRT suite)
2. Solo le sezioni modificate di recente (NRT post-sprint/release)
   → indica branch/tag/PR o elenca le sezioni toccate
3. Solo un sottoinsieme specifico
   → elenca le sezioni da includere

→ Imposta $SCOPE_DELTA (se opzione 2) o filtro sezioni (se opzione 3)
```

### B2 — Esclusioni

```
Ci sono sezioni da ESCLUDERE esplicitamente dall'analisi?
(es. "la sezione Admin è già coperta", "il wizard onboarding è in WIP")

→ Imposta $SCOPE_EXCLUDE = [lista path o sezioni]
```

Se $SCOPE_EXCLUDE non è vuoto: in Step 1 INGEST, i path esclusi vengono
aggiunti al Gap Report come `type: EXCLUDED_BY_USER` senza generare flussi.

### B3 — Jira Story ID

```
Hai già una Story Jira a cui associare questi test?
(Risposta: [ID-JIRA] oppure "no, decido dopo")

→ Imposta $JIRA_STORY
```

Se "no" → $JIRA_STORY = `{STORY-TBD}`. Il placeholder viene usato nei TC fin da Step 4.
Lo Step 5 HARD GATE non cambia — il blocco sull'export rimane se il placeholder non è stato sostituito.

---

## BLOCCO C — Autenticazione (condizionale: se guard rilevati in Step 1 o dichiarati dall'utente)

*Presenta questo blocco SOLO se:*
- *Step 0 è eseguito prima di Step 1: chiedi se l'app ha autenticazione*
- *Step 1 ha già rilevato guard nel codice*

### C1 — Meccanismo di autenticazione

```
Qual è il meccanismo di autenticazione?

1. Token JWT (Bearer) con refresh token
2. Session cookie (server-side session)
3. OAuth2 / OIDC (provider esterno: Keycloak, Auth0, Azure AD...)
4. SAML SSO
5. API Key
6. Nessuna autenticazione (app pubblica)
```

**Impatto per risposta C1:**

| Meccanismo | TC [EDGE] aggiuntivi generati in Step 4 |
|---|---|
| JWT con refresh | Token scaduto a metà wizard (refresh silenzioso o modal?), token manomesso |
| OAuth2/OIDC | Redirect loop (IdP nega), callback con state invalido, sessione IdP scaduta |
| Session cookie | Sessione scaduta server-side durante operazione lunga, cookie cancellato manualmente |

### C2 — Enforcement autorizzazione

```
I ruoli/permessi sono gestiti:

1. Solo lato frontend (guard che nasconde route)
2. Solo lato API (401/403)
3. Entrambi (frontend nasconde UI, API rifiuta richieste)
4. Non so
```

**Impatto per risposta C2:**

| Enforcement | Effetto su TC [NEG] di accesso non autorizzato |
|---|---|
| Solo frontend | TC [NEG] accesso URL diretto → CRITICAL (la protezione frontend-only è un bug di sicurezza) |
| Solo API | TC [NEG] accesso URL → MEDIUM (l'API blocca comunque) |
| Entrambi | TC [NEG] accesso URL → HIGH |

---

## BLOCCO D — Integrazioni (condizionale: se P1 rileva API call)

### D1 — Terze parti critiche

```
Ci sono API esterne di terze parti che, se cambiano, rompono flussi critici?
(es. "Stripe per pagamenti", "DocuSign per firme", "SendGrid per email")

→ Imposta $THIRD_PARTY_APIS = [lista servizi]
```

**Impatto:** i flussi che chiamano queste API ricevono CRITICAL forzato
con `rule: "third-party-critical-api"`. Si aggiungono TC [EDGE] per degrado
del servizio (timeout, risposta malformata, codice errore).

### D2 — Feature flags

```
L'applicazione usa feature flags?

1. No
2. Sì — sistema interno (env variables, config file)
3. Sì — sistema esterno (LaunchDarkly, Unleash, Split.io...)

→ Imposta $FEATURE_FLAGS = true/false
```

**Impatto se $FEATURE_FLAGS = true:** i flussi dietro flag vengono mappati con
`feature_flag: true` nel YAML. Per ogni flusso con flag: aggiunge 2 TC extra
(comportamento flag ON, graceful degradation flag OFF).

---

## BLOCCO E — Multi-tenancy (condizionale: se A1 = B2B o admin)

### E1 — Isolamento dati

```
L'applicazione è multi-tenant?

1. No — una sola organizzazione
2. Sì — ogni tenant vede solo i propri dati (isolamento per org_id/tenant_id)
3. Sì — con livelli di visibilità tra tenant

→ Imposta $MULTI_TENANT = true/false
```

**Impatto se $MULTI_TENANT = true:** per ogni sezione con dati filtrati per tenant,
aggiunge TC [PROFILO] CRITICAL: "utente del tenant A non vede dati del tenant B"
con `rule: "multi-tenant-isolation"`.

---

## BLOCCO F — Internazionalizzazione (condizionale: se i18n con 2+ locale rilevate)

### F1 — Flussi per locale

```
Le locale diverse producono flussi diversi o solo testi diversi?

1. Solo testi diversi (stesso flusso per tutte le lingue)
2. Flussi diversi per locale (es. pagamento diverso per IT vs DE)
3. Funzionalità disponibili solo in certi mercati
   → elenca le locale con comportamento diverso
```

**Impatto se opzione 2 o 3:** ogni locale con comportamento diverso genera
una variant nel flusso corrispondente. Le variant locale-specific per flussi
CRITICAL/HIGH ricevono la stessa priorità del flusso padre.

---

## BLOCCO G — Priorità Business (opzionale ma fortemente consigliato)

### G1 — Flussi ad alto rischio di regressione

```
Oltre all'operazione core (A2), ci sono flussi che sai già essere
ad alto rischio di regressione?
(es. "il calcolo del preventivo è cambiato di recente",
"la sezione notifiche ha avuto 3 bug in produzione nell'ultimo mese")
```

**Impatto:** i flussi nominati ricevono CRITICAL con `rule: "regression-risk-declared"`.
Il numero minimo di TC per questi flussi raddoppia.

### G2 — Flussi da escludere

```
Ci sono flussi che NON vuoi testare?
(es. "il wizard onboarding è in WIP", "la sezione analytics usa dati mock")
```

**Impatto:** aggiunge i flussi nominati a $SCOPE_EXCLUDE con `type: EXCLUDED_BY_USER`.

---

## Formato Output Step 0

Al termine dell'intervista, annuncia:

```
STEP 0 COMPLETATO — CONTEXT INTERVIEW
$APP_TYPE:               {valore}
$BUSINESS_CRITICAL_FLOW: {valore o "nessuno dichiarato"}
$USER_ROLES:             {lista o "da rilevare dal codice"}
$JIRA_STORY:             {ID o "{STORY-TBD}"}
$SCOPE_EXCLUDE:          {lista o "nessuna esclusione"}
$FEATURE_FLAGS:          {true/false}
$THIRD_PARTY_APIS:       {lista o "nessuna"}
$MULTI_TENANT:           {true/false}
Passaggio al Step 1 INGEST: SI
```
```

---

## Step 2 — Verifica

Dopo aver creato il file, verifica che esista:

```
Glob: skills/siae-nr-test-flows/reference/question-tree.md
Expected: 1 file trovato
```

---

## Commit

Nessun commit separato — il commit avviene alla fine con tutti i file del piano.
