# Test List Template — nr-test-flows

Template per generare la test list organizzata per sezione navigazionale.
Ogni sezione corrisponde a un'area dell'applicazione; ogni flusso a un'operazione utente.

---

## Struttura Test List

```
## Sezione: {NOME} ({accesso: pubblico | autenticato | ruolo:{nome}})

> Route: `{prefix}` | Framework: `{nome}` | Priorità sezione: CRITICAL | HIGH | MEDIUM

### Flusso: {nome flusso} [CRITICAL | HIGH | MEDIUM]

| ID | Scenario | Tipo | Dati di Test |
|----|----------|------|-------------|
| TC-001 | {happy path principale} | Happy Path | {dati specifici o —} |
| TC-002 | [NEG] {scenario negativo principale} | Negativo | {dati non validi} |
| TC-003 | [EDGE] {caso limite principale} | Edge Case | {valori limite} |
| TC-004 | [PROFILO] {ruolo specifico} | Profilazione | {ruolo: admin/user/...} |
```

---

## Regole di Generazione TC

### Numero minimo TC per flusso

| Priorità Flusso | Happy Path | NEG | EDGE | PROFILO | Minimo |
|----------------|-----------|-----|------|---------|--------|
| CRITICAL | 1-2 | 2-3 | 2 | per ruolo | 6+ |
| HIGH | 1 | 1-2 | 1 | se applicabile | 3-5 |
| MEDIUM | 1 | 1 | 0-1 | solo se rilevante | 2-3 |

### Prefissi di Categoria (nel titolo Scenario)

| Prefisso | Quando usarlo |
|---------|---------------|
| _(nessuno)_ | Scenario positivo — happy path, flusso corretto |
| `[NEG]` | Input non valido, errore, dipendenza assente, stato incompatibile |
| `[EDGE]` | Valori limite, lista vuota, input al massimo consentito, doppio click |
| `[PROFILO]` | Comportamento diverso per ruolo/profilo specifico |

---

## Esempio Completo — Sezione Autenticazione

```markdown
## Sezione: Autenticazione (pubblico)

> Route: `/auth` | Framework: Vue.js 3 | Priorità sezione: CRITICAL
> Evidenza: src/router/index.ts:8 [CONFIRMED]

### Flusso: Login con credenziali [CRITICAL]

> Entry point: src/views/LoginView.vue:1 [CONFIRMED]
> Guard: nessuno (sezione pubblica)
> API: POST /api/auth/login (src/api/auth.ts:12 [CONFIRMED])

| ID | Scenario | Tipo | Dati di Test |
|----|----------|------|-------------|
| TC-001 | Accesso con credenziali valide | Happy Path | username: utente.test@siae.it, password: Password1! |
| TC-002 | [NEG] Accesso con password errata | Negativo | username: utente.test@siae.it, password: WrongPass |
| TC-003 | [NEG] Accesso con username non esistente | Negativo | username: nonexistent@siae.it, password: qualsiasi |
| TC-004 | [NEG] Accesso con campi vuoti | Negativo | username: (vuoto), password: (vuoto) |
| TC-005 | [EDGE] Accesso dopo 3 tentativi falliti (lock account) | Edge Case | username: utente.test@siae.it, 4 tentativi |
| TC-006 | [EDGE] Accesso con sessione già attiva (doppio login) | Edge Case | Aprire 2 tab browser |
| TC-007 | [PROFILO] Accesso come amministratore — redirect a /admin | Profilazione | username: admin@siae.it, password: AdminPass1! |

### Flusso: Logout [HIGH]

> Entry point: src/components/AppHeader.vue:45 [CONFIRMED]
> Guard: authGuard (src/router/guards.ts:5 [CONFIRMED])
> API: POST /api/auth/logout (src/api/auth.ts:28 [CONFIRMED])

| ID | Scenario | Tipo | Dati di Test |
|----|----------|------|-------------|
| TC-008 | Logout dalla sessione attiva | Happy Path | — |
| TC-009 | [EDGE] Logout con sessione scaduta (token expirato) | Edge Case | Token scaduto manualmente |
| TC-010 | [NEG] Accesso diretto a pagina autenticata dopo logout | Negativo | Navigazione a /dashboard dopo logout |
```

---

## Esempio Completo — Sezione Dashboard

```markdown
## Sezione: Dashboard (autenticato)

> Route: `/dashboard` | Framework: Vue.js 3 | Priorità sezione: HIGH
> Evidenza: src/router/index.ts:24 [CONFIRMED]
> Guard: authGuard (src/router/guards.ts:5 [CONFIRMED])

### Flusso: Visualizzazione overview dati [HIGH]

> Entry point: src/views/DashboardView.vue:1 [CONFIRMED]
> API: GET /api/dashboard/stats (src/api/dashboard.ts:8 [CONFIRMED])

| ID | Scenario | Tipo | Dati di Test |
|----|----------|------|-------------|
| TC-011 | Visualizzazione dashboard con dati | Happy Path | Utente con dati esistenti |
| TC-012 | [EDGE] Visualizzazione dashboard senza dati (nuovo utente) | Edge Case | Utente appena registrato |
| TC-013 | [NEG] Accesso alla dashboard senza autenticazione | Negativo | Navigazione diretta a /dashboard non autenticato |
| TC-014 | [PROFILO] Dashboard admin — widget aggiuntivi | Profilazione | Ruolo: amministratore |
```

---

## Esempio Completo — Sezione con Operazioni CRUD

```markdown
## Sezione: Gestione Utenti (ruolo:amministratore)

> Route: `/admin/users` | Framework: Angular | Priorità sezione: HIGH
> Evidenza: src/app/admin/admin-routing.module.ts:12 [CONFIRMED]
> Guard: AdminGuard (src/app/core/guards/admin.guard.ts:1 [CONFIRMED])

### Flusso: Creazione nuovo utente [HIGH]

> Entry point: src/app/admin/users/create-user.component.ts:1 [CONFIRMED]
> API: POST /api/admin/users (src/app/core/services/user.service.ts:34 [CONFIRMED])

| ID | Scenario | Tipo | Dati di Test |
|----|----------|------|-------------|
| TC-020 | Creazione utente con tutti i campi validi | Happy Path | nome: Mario Rossi, email: mario.rossi@siae.it, ruolo: user |
| TC-021 | [NEG] Creazione con email già esistente | Negativo | email: esistente@siae.it |
| TC-022 | [NEG] Creazione con email non valida | Negativo | email: non-una-email |
| TC-023 | [NEG] Creazione con campi obbligatori vuoti | Negativo | nome: (vuoto), email: (vuoto) |
| TC-024 | [EDGE] Creazione con nome al limite massimo caratteri | Edge Case | nome: 255 caratteri |
| TC-025 | [PROFILO] Tentativo creazione da utente non-admin | Profilazione | Accesso diretto all'URL come user standard |

### Flusso: Modifica utente esistente [HIGH]

| ID | Scenario | Tipo | Dati di Test |
|----|----------|------|-------------|
| TC-026 | Modifica ruolo utente | Happy Path | Cambio da user a admin |
| TC-027 | [NEG] Modifica utente non esistente (URL manomesso) | Negativo | /admin/users/99999 |
| TC-028 | [EDGE] Modifica senza modificare nessun campo | Edge Case | Submit form invariato |

### Flusso: Eliminazione utente [CRITICAL]

| ID | Scenario | Tipo | Dati di Test |
|----|----------|------|-------------|
| TC-029 | Eliminazione utente con conferma | Happy Path | Utente esistente non-admin |
| TC-030 | [NEG] Eliminazione dell'utente correntemente loggato | Negativo | Admin elimina se stesso |
| TC-031 | [NEG] Eliminazione utente non esistente | Negativo | ID non valido |
| TC-032 | [EDGE] Cancellazione dialog senza confermare | Edge Case | Click "Annulla" nella modale di conferma |
```

---

## Esempio Completo — App Mobile (Ionic + Angular)

> **Regola fondamentale**: Per app mobile (Ionic, Flutter) i path/route sono **identificatori interni**,
> non azioni utente. Ogni step descrive un'interazione UI concreta (tap, swipe, input, scroll).
> "Navigare a /path" non è mai un'azione valida per un utente mobile.

```markdown
## Sezione: Adempimenti (autenticato)

> Route: `/auth/welcome/fulfillments` | Framework: Ionic + Angular | Priorità sezione: CRITICAL
> Evidenza: src/app/app-routing.module.ts:87 [CONFIRMED]
> Guard: AlertCleanerGuard, PositionGuard

### Flusso: Completamento opera multi-step [CRITICAL]

> Entry point: src/app/pages/fulfillments/fulfillments.page.ts:1 [CONFIRMED]

| ID | Scenario | Tipo | Dati di Test |
|----|----------|------|-------------|
| TC-040 | Completamento adempimento opera con tutti i dati validi | Happy Path | Opera con titolo, ruolo e ISWC validi |
| TC-041 | [NEG] Tentativo di procedere al riepilogo senza inserire dati opera obbligatori | Negativo | Sezione opera-data con campi vuoti |
| TC-042 | [EDGE] Interruzione flusso a metà (app in background) e ripresa | Edge Case | — |
| TC-043 | [PROFILO] Adempimento con ruolo non principale (co-autore) | Profilazione | Ruolo: co-autore |
```

**Come si scrivono gli step per TC-041 (mobile NEG):**

```
✅ CORRETTO per app mobile:
  Step 1: Aprire l'app e completare il login con credenziali valide
  Step 2: Dalla schermata Home, toccare la voce 'Adempimenti' nella navigazione inferiore
  Step 3: Toccare un'opera dalla lista adempimenti in sospeso
  Step 4: Nella schermata 'Dati Opera', non compilare i campi obbligatori e toccare 'Avanti'
  Step 5: Verificare che l'app mostri un messaggio di validazione e non proceda al riepilogo

❌ ERRATO per app mobile:
  Step 1: Navigare a /auth/welcome/fulfillments/summary senza completare opera-data
```

**Come si scrivono gli step per scenari [NEG] di accesso non autorizzato su mobile:**

```
✅ CORRETTO per app mobile [NEG] accesso senza ruolo:
  Step 1: Aprire l'app con un account che non ha il permesso per la sezione Adempimenti
  Step 2: Verificare che la tab 'Performance' non sia visibile nella barra di navigazione inferiore
  Step 3: (Se presente) Verificare che il tentativo di accesso mostri messaggio di errore appropriato

✅ CORRETTO per web [EDGE] accesso diretto URL (sicurezza):
  Step 1: Con browser non autenticato, navigare direttamente a /admin/dashboard
  Step 2: Verificare il redirect a /login con messaggio appropriato
```

---

## Gap Report nella Test List

Se esistono sezioni o flussi con evidenza UNVERIFIED, documentarli nella test list:

```markdown
## Gap Report

> Sezioni/flussi per cui non è stata trovata evidenza sufficiente.
> Richiedono verifica manuale prima di completare la test list.

| Gap | Descrizione | Evidenza Cercata | Impatto |
|-----|-------------|-----------------|---------|
| UNVERIFIED_SECTION | Sezione "Reportistica" — route /reports rilevata in i18n ma nessun component trovato | src/views/Reports*.vue, src/router/index.ts | Test case non generati per questa sezione |
| MISSING_GUARD | Flusso "Pagamento" — guard non rilevato, accesso non verificato | src/router/guards.ts, src/router/index.ts:45 | TC profilazione ruolo non generabili |
```

---

## Riepilogo Copertura

Alla fine della test list, includi sempre questo riepilogo:

```markdown
## Riepilogo Copertura

| Sezione | Flussi | TC Totali | CRITICAL | HIGH | MEDIUM | Gap |
|---------|--------|-----------|----------|------|--------|-----|
| Autenticazione | 2 | 10 | 7 | 3 | 0 | 0 |
| Dashboard | 1 | 4 | 0 | 3 | 1 | 0 |
| Gestione Utenti | 3 | 13 | 3 | 8 | 2 | 1 |
| **TOTALE** | **6** | **27** | **10** | **14** | **3** | **1** |

Distribuzione per tipo:
  Happy Path:   N TC
  Negativi:     N TC
  Edge Case:    N TC
  Profilazione: N TC
  TOTALE:       N TC
```
