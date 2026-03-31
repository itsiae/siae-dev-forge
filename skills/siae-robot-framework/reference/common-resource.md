# common.resource — Definizione Canonica SIAE

Questo file deve sempre esistere in `resources/common.resource`.
Nessun test o keyword nei Page resource chiama AppiumLibrary direttamente.
Tutti i wrapper sono definiti qui.

---

## File canonico

```robotframework
*** Settings ***
Library    AppiumLibrary

*** Variables ***
${DEFAULT_TIMEOUT}     15s
${DEFAULT_INTERVAL}    0.5s
${LONG_TIMEOUT}        30s
${APPIUM_URL}          http://localhost:4723

*** Keywords ***
Open SIAE Application
    [Documentation]    Apre l'app con le capabilities configurate. Override in Suite Setup.
    [Arguments]    ${platform}=${PLATFORM_NAME}
    Open Application    ${APPIUM_URL}
    ...    platformName=${platform}
    ...    deviceName=${DEVICE_NAME}
    ...    app=${APP_PATH}
    ...    automationName=${AUTOMATION_NAME}
    ...    newCommandTimeout=300

Close SIAE Application
    [Documentation]    Chiude la sessione Appium.
    Close Application

Reset App State
    [Documentation]    Reset dello stato app tra test. Usa in Test Setup.
    # Implementazione specifica per progetto: launch activity, clear state, ecc.
    Pass

Capture Screenshot On Failure
    [Documentation]    Cattura screenshot se il test è fallito. Usa in Test Teardown.
    Run Keyword If Test Failed    Capture Page Screenshot

Wait And Click
    [Documentation]    Attende visibilità elemento e clicca. Wrapper obbligatorio su Click Element.
    [Arguments]    ${locator}    ${timeout}=${DEFAULT_TIMEOUT}
    Wait Until Element Is Visible    ${locator}    ${timeout}
    Click Element    ${locator}

Wait And Input Text
    [Documentation]    Attende visibilità campo e inserisce testo. Wrapper obbligatorio su Input Text.
    [Arguments]    ${locator}    ${text}    ${timeout}=${DEFAULT_TIMEOUT}
    Wait Until Element Is Visible    ${locator}    ${timeout}
    Input Text    ${locator}    ${text}

Wait And Assert Element Visible
    [Documentation]    Asserisce visibilità elemento con timeout configurabile.
    [Arguments]    ${locator}    ${timeout}=${DEFAULT_TIMEOUT}
    Wait Until Element Is Visible    ${locator}    ${timeout}

Wait And Assert Element Not Visible
    [Documentation]    Asserisce che un elemento non sia visibile.
    [Arguments]    ${locator}    ${timeout}=${DEFAULT_TIMEOUT}
    Wait Until Element Is Not Visible    ${locator}    ${timeout}

Wait And Get Text
    [Documentation]    Attende visibilità e restituisce il testo dell'elemento.
    [Arguments]    ${locator}    ${timeout}=${DEFAULT_TIMEOUT}
    Wait Until Element Is Visible    ${locator}    ${timeout}
    ${text}=    Get Text    ${locator}
    RETURN    ${text}

Swipe Up
    [Documentation]    Swipe verticale verso l'alto usando percentuali schermo (no coordinate assolute).
    [Arguments]    ${start_y_pct}=0.8    ${end_y_pct}=0.2
    ${size}=    Get Window Size
    ${width}=   Evaluate    ${size}[width] / 2
    ${start_y}= Evaluate    ${size}[height] * ${start_y_pct}
    ${end_y}=   Evaluate    ${size}[height] * ${end_y_pct}
    Swipe    ${width}    ${start_y}    ${width}    ${end_y}    500

Swipe Down
    [Documentation]    Swipe verticale verso il basso usando percentuali schermo (no coordinate assolute).
    [Arguments]    ${start_y_pct}=0.2    ${end_y_pct}=0.8
    ${size}=    Get Window Size
    ${width}=   Evaluate    ${size}[width] / 2
    ${start_y}= Evaluate    ${size}[height] * ${start_y_pct}
    ${end_y}=   Evaluate    ${size}[height] * ${end_y_pct}
    Swipe    ${width}    ${start_y}    ${width}    ${end_y}    500

Switch To Native Context
    [Documentation]    Switcha al context nativo dell'app. Necessario dopo interazioni con webview.
    Switch To Context    NATIVE_APP

Switch To Webview Context
    [Documentation]    Switcha al context webview. Fornisce il package name come argomento.
    [Arguments]    ${package}=com.siae.app
    ${contexts}=    Get Contexts
    FOR    ${ctx}    IN    @{contexts}
        ${matches}=    Evaluate    'WEBVIEW_${package}' in '${ctx}'
        IF    ${matches}
            Switch To Context    ${ctx}
            RETURN
        END
    END
    Fail    Nessun context WEBVIEW trovato per package: ${package}
```

---

## BrowserStack — Approccio SDK (raccomandato)

Con il BrowserStack SDK (`pip install browserstack-sdk`), il codice dei test è **identico**
alla run locale. L'SDK intercetta la sessione e la reindirizza su cloud BS in modo trasparente.

**Non servono keyword dedicate** `Open BrowserStack Android/iOS Application`.
`Open SIAE Application` funziona senza modifiche — l'URL locale viene sovrascritto dall'SDK.

```bash
# Run Android BS
browserstack-sdk robot --outputdir results_bs tests/BS/

# Run iOS BS
browserstack-sdk pabot --processes 4 --outputdir results_bs_ios tests/BS_iOS/
```

La configurazione dei device e le credenziali stanno in `browserstack.yml` (project root).
Vedi [browserstack-sdk-config.md](browserstack-sdk-config.md) per template Android, iOS e note operative.

---

## Note di implementazione

- **`implicitWaitTimeout`**: non impostare nelle capabilities. Lascia a 0 (default) per evitare conflitti con `Wait Until Element Is Visible` di RF.
- **`newCommandTimeout`**: impostare a 300s per evitare timeout su operazioni lente in BS.
- **Credenziali BS**: sempre da variabili d'ambiente `BROWSERSTACK_USERNAME` / `BROWSERSTACK_ACCESS_KEY`. Non hardcodare mai — né nel codice né in `browserstack.yml`.
- **BrowserStack SDK vs legacy URL**: non usare `hub-cloud.browserstack.com` nell'URL Appium. Quell'approccio richiede credenziali nelle capabilities del test. Usa sempre l'SDK.
