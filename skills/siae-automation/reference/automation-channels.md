# Automation Channels — Dettaglio Path Mobile e Web

Questo file contiene i dettagli implementativi per i due canali di test automation.
Viene referenziato da `SKILL.md` nella Fase 4 del workflow.

---

## PATH MOBILE — Appium + BrowserStack App Automate {#path-mobile}

**Prerequisiti:**
- [ ] `BROWSERSTACK_USERNAME` e `BROWSERSTACK_ACCESS_KEY` in env
- [ ] APK (Android) o IPA (iOS) disponibile o già uploadato su BrowserStack
- [ ] appium-mcp disponibile come MCP tool nella sessione corrente

**Step 4.1 — Upload app (se non già fatto)**

```bash
# Android
curl -u "${BROWSERSTACK_USERNAME}:${BROWSERSTACK_ACCESS_KEY}" \
  -X POST "https://api-cloud.browserstack.com/app-automate/upload" \
  -F "file=@/path/to/app.apk" \
  -F "custom_id=siae-app-{PROJ_KEY}"

# iOS
curl -u "${BROWSERSTACK_USERNAME}:${BROWSERSTACK_ACCESS_KEY}" \
  -X POST "https://api-cloud.browserstack.com/app-automate/upload" \
  -F "file=@/path/to/app.ipa" \
  -F "custom_id=siae-app-{PROJ_KEY}"
```

Il developer fornisce il `app_url` restituito (`bs://xxxx`).

**Step 4.2 — Da Test Prompt a tool call appium-mcp**

Leggi il Test Prompt prodotto in Step 4.0 e per ogni step traduci `Intent` + `Target` + `Data` + `Expected` in sequenze di tool call appium-mcp:

| Intent | Tool call appium-mcp | Strategia ricerca |
|--------|---------------------|-------------------|
| `navigate` | `launch_app` (primo step) o `simulate_gesture` swipe | — |
| `tap` | `find_element` → `tap_element` | `accessibility id` su `Target`, poi `xpath` |
| `input` | `find_element` → `enter_text(Data)` | `accessibility id` su `Target` |
| `verify` (testo) | `find_element` → `get_element_text` → confronta con `Expected` | `accessibility id` o `xpath` |
| `verify` (schermata) | `get_screenshot_file` → analisi visiva rispetto a `Expected` | — |
| `scroll` | `simulate_gesture` con pointerMove normalizzato [0,1] | — |
| `read` | `get_page_source_file` o `get_element_text` | `accessibility id` |

Vedi `reference/appium-browserstack-config.md` per capabilities complete e pattern di gestione errori.

**Step 4.3 — Esecuzione via appium-mcp**

Per ogni TC, esegui in sequenza:
1. `start_session` con capabilities BrowserStack (vedi reference)
2. `launch_app` con bundle ID / package name
3. Per ogni step del Test Prompt: tool call → verifica `Expected` → registra PASS/FAIL
4. Se FAIL: `get_screenshot_file` → nome file `{TC-ID}-step{N}-fail.png`
5. `end_session` (sempre, anche in caso di fallimento)

Una sessione per TC. Non riutilizzare la sessione tra TC diversi — lo stato dell'app potrebbe non essere pulito.

---

## PATH WEB — Cypress + cypress-xray-plugin {#path-web}

**Prerequisiti:**
- [ ] `cypress.config.js` presente nel progetto
- [ ] `cypress-xray-plugin` installato (`npm list cypress-xray-plugin`)
- [ ] `XRAY_CLIENT_ID` e `XRAY_CLIENT_SECRET` in env
- [ ] Mappatura ID → chiavi Jira Xray disponibile (prodotta da siae-qa Fase 5)

**Step 4.W0 — Creazione Test Execution PRIMA dell'esecuzione [OBBLIGATORIO per web]**

cypress-xray-plugin richiede `testExecutionIssueKey` in `cypress.config.js` **prima** del run.
Devi quindi creare la Test Execution adesso, non dopo.

Tier 1 (MCP): crea la TE in Xray:
```
Summary: [AUTOMATION] {Story summary} — {Sprint}
TC collegati: lista confermata dalla Fase 3
```
Raccogli la chiave assegnata (es. `XE-456`) — ti servirà al passo successivo.

Tier 3 (no MCP):
- Chiedi al developer di creare manualmente in Xray una Test Execution con il titolo `[AUTOMATION] {Story summary} — {Sprint}` e di comunicarti la chiave assegnata (es. `XE-456`)
- Non procedere alla generazione degli spec finché non hai questa chiave

**Step 4.1 — Configurazione plugin (se non presente)**

```js
// cypress.config.js
const { defineConfig } = require('cypress');
const { configureXrayPlugin } = require('cypress-xray-plugin');

module.exports = defineConfig({
  e2e: {
    async setupNodeEvents(on, config) {
      await configureXrayPlugin(on, config, {
        jira: {
          projectKey: '{JIRA_PROJECT_KEY}',
          url: 'https://{workspace}.atlassian.net',
        },
        xray: {
          uploadResults: true,
          testExecutionIssueKey: '{XE-456}',
        },
        plugin: { overwriteIssueSummary: false },
      });
      return config;
    },
    specPattern: 'cypress/e2e/**/*.cy.js',
  },
});
```

**Step 4.2 — Da Test Prompt a spec Cypress**

| Intent | Comando Cypress | Selettore preferito |
|--------|----------------|---------------------|
| `navigate` | `cy.visit('{path}')` | — |
| `tap` | `cy.get('[data-testid="{Target}"]').click()` | `data-testid` → `aria-label` → testo |
| `input` | `cy.get('[data-testid="{Target}"]').type('{Data}')` | `data-testid` |
| `verify` (testo) | `cy.contains('{Expected}').should('be.visible')` | — |
| `verify` (URL) | `cy.url().should('include', '{Expected}')` | — |
| `verify` (assenza) | `cy.get('[data-testid="{Target}"]').should('not.exist')` | — |
| `scroll` | `cy.get('[data-testid="{Target}"]').scrollIntoView()` | `data-testid` |
| `read` | `cy.get('[data-testid="{Target}"]').invoke('text').then(...)` | `data-testid` |

Genera `cypress/e2e/{story-id}/{PROJ-KEY}-{slug}.cy.js`:

```js
// cypress/e2e/{STORY_ID}/{PROJ-KEY}-{slug}.cy.js
describe('{STORY_ID} — {User Story Description}', () => {
  beforeEach(() => {
    cy.clearCookies();
    cy.clearLocalStorage();
  });

  it('{PROJ-KEY}: {Scenario (descrizione)}', () => {
    // Step 1 — {Action dal Test Prompt}
    cy.visit('/{path}');
    cy.get('[data-testid="{Target}"]').should('be.visible');

    // Step 2 — {Action dal Test Prompt}
    cy.get('[data-testid="{Target}"]').type('{Data}');
    cy.contains('{testo atteso}').should('be.visible');
  });
});
```

Regole:
- Il titolo `it()` deve usare la **chiave Jira reale** del TC (es. `PROJ-456`) — NON il sequenziale `TC-{N}`
- Aggiungi il commento `// Chiave Xray: {PROJ-KEY}` in testa al file per tracciabilita'
- Se `Target` non ha un `data-testid` ovvio, segnala al developer e proponi di aggiungerlo prima di generare
- Non usare `.wait(N)` fissi — usa `cy.intercept` + `cy.wait('@alias')` per attese su API

**Step 4.3 — Esecuzione**

```bash
npx cypress run --spec "cypress/e2e/{story-id}/**/*.cy.js"
```

Il plugin sincronizza i risultati su Xray automaticamente al termine del run.
Vedi `reference/cypress-xray-config.md` per troubleshooting e fallback JUnit XML.
