# Cypress + cypress-xray-plugin — Configurazione di Riferimento

Questo documento è il riferimento tecnico per il Path Web della skill `siae-automation`.
Cypress è usato in **JavaScript** (`.js`, non TypeScript).

---

## Installazione cypress-xray-plugin

```bash
npm install --save-dev cypress-xray-plugin
```

Versione supportata: `^8.x` (compatibile con Cypress 13+).

---

## Configurazione cypress.config.js

```js
// cypress.config.js
const { defineConfig } = require('cypress');
const { configureXrayPlugin } = require('cypress-xray-plugin');

module.exports = defineConfig({
  e2e: {
    async setupNodeEvents(on, config) {
      await configureXrayPlugin(on, config, {
        jira: {
          projectKey: 'PROJ',                          // chiave progetto Jira
          url: 'https://{workspace}.atlassian.net',    // URL Jira Cloud
        },
        xray: {
          uploadResults: true,                          // sync automatico post-run
          testExecutionIssueKey: 'XE-456',             // Test Execution da Fase 1 o Fase 5
        },
        plugin: {
          overwriteIssueSummary: false,                // non sovrascrivere titolo TC in Xray
        },
      });
      return config;
    },
    specPattern: 'cypress/e2e/**/*.cy.js',
    supportFile: 'cypress/support/e2e.js',
    videosFolder: 'cypress/videos',
    screenshotsFolder: 'cypress/screenshots',
  },
});
```

### Variabili d'ambiente richieste

```bash
# Xray Cloud API (per sync risultati)
export XRAY_CLIENT_ID="your-xray-client-id"
export XRAY_CLIENT_SECRET="your-xray-client-secret"

# Jira auth (per creare/aggiornare issue)
export JIRA_API_TOKEN="your-jira-api-token"
export JIRA_USERNAME="your-email@siae.it"
```

Aggiungi queste variabili al file `.env` locale (non committare) o ai repository secrets CI/CD.

---

## Formato spec Cypress generato dalla skill

Gli spec sono prodotti a partire dal **Test Prompt** (Step 4.0 di siae-automation), non direttamente dagli step del TC Xray.
Il Test Prompt è l'output intermedio che normalizza Action + Expected Result in campi `Intent / Target / Data / Expected` — la generazione Cypress li traduce in comandi `cy.*`.

### Regola chiave: il titolo `it()` deve contenere la chiave Jira reale del TC

```js
it('PROJ-456: Verifica login con credenziali valide', () => { ... });
```

Il plugin usa il titolo per fare il match con il TC in Xray cercando la **chiave Jira** (es. `PROJ-456`).
**Non usare** `TC-1:` o indici sequenziali — cypress-xray-plugin non li riconosce.
La chiave Jira reale viene dalla mappatura prodotta da siae-qa Fase 5 (ID CSV → chiave Xray).

---

## Template spec `.cy.js`

File generato in: `cypress/e2e/{STORY_ID}/{PROJ-KEY}-{slug}.cy.js`

```js
// cypress/e2e/PROJ-123/PROJ-456-login-credenziali-valide.cy.js
// Generato da: siae-automation — Test Prompt PROJ-456
// Chiave Xray: PROJ-456 (dalla mappatura ID CSV → chiave Jira prodotta da siae-qa)

describe('PROJ-123 — {User Story Description}', () => {

  beforeEach(() => {
    cy.clearCookies();
    cy.clearLocalStorage();
  });

  it('PROJ-456: {Scenario (descrizione dal TC Xray)}', () => {

    // Step 1 — {Action dal Test Prompt}
    cy.visit('/login');
    // Expected: {Expected dal Test Prompt}
    cy.get('[data-testid="login-form"]').should('be.visible');

    // Step 2 — {Action dal Test Prompt}
    cy.get('[data-testid="username"]').type('{Data dal Test Prompt}');
    cy.get('[data-testid="password"]').type('{Data dal Test Prompt}');
    // Expected: {Expected dal Test Prompt}
    cy.get('[data-testid="username"]').should('have.value', '{Data}');

    // Step 3 — {Action dal Test Prompt}
    cy.get('[data-testid="login-button"]').click();
    // Expected: {Expected dal Test Prompt}
    cy.url().should('include', '/dashboard');
    cy.contains('{testo atteso}').should('be.visible');

  });

});
```

---

## Tabella Intent → Comando Cypress

Questa tabella viene usata dallo Step 4.2 per tradurre il Test Prompt in comandi:

| Intent (dal Test Prompt) | Comando Cypress | Selettore preferito |
|--------------------------|----------------|---------------------|
| `navigate` | `cy.visit('{path}')` | — |
| `tap` | `cy.get('[data-testid="{Target}"]').click()` | `data-testid` → `aria-label` → testo |
| `input` | `cy.get('[data-testid="{Target}"]').type('{Data}')` | `data-testid` |
| `verify` (testo visibile) | `cy.contains('{Expected}').should('be.visible')` | — |
| `verify` (valore campo) | `cy.get('[data-testid="{Target}"]').should('have.value', '{Expected}')` | `data-testid` |
| `verify` (URL) | `cy.url().should('include', '{Expected}')` | — |
| `verify` (elemento assente) | `cy.get('[data-testid="{Target}"]').should('not.exist')` | `data-testid` |
| `scroll` | `cy.get('[data-testid="{Target}"]').scrollIntoView()` | `data-testid` |
| `read` | `cy.get('[data-testid="{Target}"]').invoke('text').then((text) => { expect(text).to.include('{Expected}'); })` | `data-testid` |

### Selettori: ordine di priorità

```
1. data-testid   →  cy.get('[data-testid="..."]')          stabile, preferito
2. aria-label    →  cy.get('[aria-label="..."]')           accessibile
3. role + name   →  cy.get('[role="button"][name="..."]')  semantico
4. testo         →  cy.contains('testo')                   fragile se il testo cambia
5. class/id CSS  →  cy.get('.class') / cy.get('#id')       fragile, evitare
```

Se `data-testid` non è presente nell'elemento, segnala al developer di aggiungerlo prima di generare lo spec.

### Attese su chiamate API

Non usare `cy.wait(N)` con timeout fisso. Usa intercept:

```js
cy.intercept('POST', '/api/endpoint').as('myRequest');
cy.get('[data-testid="submit"]').click();
cy.wait('@myRequest');
cy.contains('Operazione completata').should('be.visible');
```

---

## Esecuzione

### Run locale

```bash
# Tutti i TC di una Story
npx cypress run --spec "cypress/e2e/PROJ-123/**/*.cy.js"

# TC singolo
npx cypress run --spec "cypress/e2e/PROJ-123/TC-1-login-credenziali-valide.cy.js"

# Con browser visibile (debug)
npx cypress open
```

### Run in CI (GitHub Actions)

```yaml
- name: Run Cypress automation tests
  run: npx cypress run --spec "cypress/e2e/${{ env.STORY_ID }}/**/*.cy.js"
  env:
    XRAY_CLIENT_ID: ${{ secrets.XRAY_CLIENT_ID }}
    XRAY_CLIENT_SECRET: ${{ secrets.XRAY_CLIENT_SECRET }}
    JIRA_API_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
    JIRA_USERNAME: ${{ secrets.JIRA_USERNAME }}
```

---

## Verifica sync Xray post-run

Dopo il run, cypress-xray-plugin stampa nel log:

```
[cypress-xray-plugin] Uploading results to Xray...
[cypress-xray-plugin] Test execution XE-456 updated successfully
  PROJ-456: PASS
  PROJ-458: FAIL → "Expected 'Benvenuto' to be visible but was not"
```

Se il sync non avviene (nessun log del plugin):
1. Verifica che `uploadResults: true` sia in `cypress.config.js`
2. Verifica le env vars `XRAY_CLIENT_ID` e `XRAY_CLIENT_SECRET`
3. Verifica che `testExecutionIssueKey` esista in Xray e non sia in stato chiuso
4. Fallback manuale: vedi sezione JUnit XML sotto

### Fallback manuale con JUnit XML

```bash
# Genera JUnit XML durante il run
npx cypress run \
  --reporter junit \
  --reporter-options "mochaFile=cypress/results/results.xml" \
  --spec "cypress/e2e/{story-id}/**/*.cy.js"

# Importa risultati su Xray via API
curl -H "Content-Type: text/xml" \
  -X POST "https://xray.cloud.getxray.app/api/v1/import/execution/junit?projectKey=PROJ&testExecKey=XE-456" \
  -H "Authorization: Bearer {XRAY_TOKEN}" \
  --data @cypress/results/results.xml
```

---

## Troubleshooting

| Problema | Causa probabile | Soluzione |
|----------|----------------|-----------|
| Plugin non sincronizza i risultati | `testExecutionIssueKey` errata o TE chiusa in Xray | Crea nuova TE aperta, aggiorna `cypress.config.js` |
| `it()` non matchato con TC Xray | Titolo usa `TC-{N}:` invece della chiave Jira reale | Correggi con la chiave Xray reale: `PROJ-456: scenario`. Usa la mappatura prodotta da siae-qa. |
| Test fallisce in CI ma passa in locale | Variabile d'ambiente mancante o timing asincrono | Verifica env CI, sostituisci `cy.wait(N)` con `cy.intercept` |
| `data-testid` non trovato | Attributo non presente nel codice | Chiedi al developer di aggiungere `data-testid` all'elemento |
| Video non registrato | Path `videosFolder` non configurato | Verifica `videosFolder: 'cypress/videos'` in config |
| Timeout su elemento | Elemento appare dopo caricamento async | Usa `cy.intercept` + `cy.wait('@alias')` invece di timeout fisso |
| `require('cypress-xray-plugin')` non trovato | Plugin non installato | `npm install --save-dev cypress-xray-plugin` |
