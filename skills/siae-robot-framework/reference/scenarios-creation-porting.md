# Scenario A — Creazione Test da Zero
# Scenario C — Porting Android ↔ iOS

---

## SCENARIO A — Creazione da Zero

### A.1 Sequenza operativa

1. Determina la pagina target dal nome del file richiesto
2. Esegui Knowledge Acquisition (Step 2 SKILL.md)
3. Crea prima il Page resource, poi il file .robot
4. Applica Best Practice Layer (BP-1..6) su tutto

### A.2 Struttura Page resource obbligatoria

```robotframework
*** Settings ***
Library    AppiumLibrary
Resource   ../common.resource

*** Variables ***
# Locatori — gerarchia: accessibility_id > resource-id > xpath semantico > class chain > predicate string
${LOGIN_USERNAME_FIELD}       accessibility_id=username_field
${LOGIN_PASSWORD_FIELD}       accessibility_id=password_field
${LOGIN_SUBMIT_BUTTON}        accessibility_id=login_button
${LOGIN_ERROR_MESSAGE}        xpath=//android.widget.TextView[@resource-id='com.siae.app:id/error_msg']

*** Keywords ***
Assert Login Page Loaded
    [Documentation]    Verifica che la pagina di login sia visibile e pronta
    Wait And Assert Element Visible    ${LOGIN_USERNAME_FIELD}

Input Login Credentials
    [Documentation]    Inserisce username e password nei rispettivi campi
    [Arguments]    ${username}    ${password}
    Wait And Input Text    ${LOGIN_USERNAME_FIELD}    ${username}
    Wait And Input Text    ${LOGIN_PASSWORD_FIELD}    ${password}

Submit Login Form
    [Documentation]    Preme il bottone di submit e attende la navigazione
    Wait And Click    ${LOGIN_SUBMIT_BUTTON}

Perform Login
    [Documentation]    Keyword composita: inserisce credenziali e submitta
    [Arguments]    ${username}    ${password}
    Input Login Credentials    ${username}    ${password}
    Submit Login Form
```

### A.3 Struttura file .robot obbligatoria

```robotframework
*** Settings ***
Resource    ../resources/LoginPage.resource
Resource    ../resources/HomePage.resource
Suite Setup       Open SIAE Application
Suite Teardown    Close SIAE Application
Test Setup        Reset App State
Test Teardown     Capture Screenshot On Failure

*** Variables ***
${USERNAME}    ${ENV_USERNAME}
${PASSWORD}    ${ENV_PASSWORD}

*** Test Cases ***
TC01_LoginConCredenzialiValide
    [Documentation]    Verifica il login con credenziali valide — smoke test
    [Tags]    smoke    login    android
    Assert Login Page Loaded
    Perform Login    ${USERNAME}    ${PASSWORD}
    Assert Home Page Loaded

TC02_LoginConPasswordErrata
    [Documentation]    Verifica il messaggio di errore con password errata
    [Tags]    regression    login    android
    Assert Login Page Loaded
    Perform Login    ${USERNAME}    wrong_password
    Assert Login Error Displayed

*** Keywords ***
# Nessuna keyword nei file .robot — solo nei Page resource
```

**Regola**: nessuna keyword nel file .robot. Tutto va nel Page resource.

### A.4 Variante iOS (creazione da zero su iOS)

Se la piattaforma target è iOS, usa locatori iOS nel Page resource:

```robotframework
*** Settings ***
Library    AppiumLibrary
Resource   ../../common.resource

*** Variables ***
# Locatori iOS — gerarchia: accessibility_id > xpath XCUIElement > class chain > predicate string
${LOGIN_USERNAME_FIELD}       accessibility_id=username_field
${LOGIN_PASSWORD_FIELD}       accessibility_id=password_field
${LOGIN_SUBMIT_BUTTON}        accessibility_id=login_button
${LOGIN_ERROR_MESSAGE}        xpath=//XCUIElementTypeStaticText[@name='login_error']

*** Keywords ***
Assert Login Page Loaded
    [Documentation]    Verifica che la pagina di login sia visibile e pronta (iOS)
    Wait And Assert Element Visible    ${LOGIN_USERNAME_FIELD}
```

File .robot iOS — inserisci nella directory `tests/iOS/`:
```robotframework
*** Settings ***
Resource    ../../resources/iOS/LoginPage.resource
Suite Setup       Open SIAE Application
Suite Teardown    Close SIAE Application
Test Setup        Reset App State
Test Teardown     Capture Screenshot On Failure

*** Variables ***
${USERNAME}    ${ENV_USERNAME}
${PASSWORD}    ${ENV_PASSWORD}

*** Test Cases ***
TC01_LoginConCredenzialiValide
    [Documentation]    Verifica il login con credenziali valide — smoke test (iOS)
    [Tags]    smoke    login    ios
    Assert Login Page Loaded
    Perform Login    ${USERNAME}    ${PASSWORD}
    Assert Home Page Loaded
```

**MAI** usare `android.widget.*` o `resource-id` in file iOS. Usa `XCUIElementType*` per xpath e `accessibility_id` come prima scelta.

---

## SCENARIO C — Porting Android ↔ iOS

### C.1 Sequenza operativa

1. Leggi il Page resource sorgente (es. `LoginPage.resource` Android)
2. Esegui Knowledge Acquisition per la piattaforma target (dump iOS)
3. Crea il Page resource target con mapping esplicito dei locatori
4. Crea (o aggiorna) il file .robot nella directory target
5. Applica Best Practice Layer con regole cross-platform

### C.2 Struttura directory porting

```
tests/
  TC01_Login.robot              ← Android locale
  iOS/
    TC01_Login.robot            ← iOS locale
  BS/
    TC01_Login.robot            ← Android BrowserStack
  BS_iOS/
    TC01_Login.robot            ← iOS BrowserStack

resources/
  LoginPage.resource            ← Android
  iOS/
    LoginPage.resource          ← iOS
```

### C.3 Mapping locatori Android → iOS (5 regole in ordine)

**REGOLA 1 — accessibility_id identico**
```
Android: accessibility_id=login_button
iOS:     accessibility_id=login_button   ← usa lo stesso SE presente nel dump iOS
```
Verifica nel dump iOS che l'accessibility label esista prima di usarlo.

**REGOLA 2 — resource-id Android → accessibility_id iOS**
```
Android: id=com.siae.app:id/username_field
iOS:     accessibility_id=username_field  ← cerca nel dump iOS per nome semantico
```
Il resource-id non esiste in iOS. Cerca l'elemento per nome semantico.

**REGOLA 3 — xpath semantico con classe corretta per piattaforma**
```
Android: xpath=//android.widget.Button[@content-desc='Accedi']
         xpath=//android.widget.TextView[@text='Benvenuto']
iOS:     xpath=//XCUIElementTypeButton[@name='Accedi']
         xpath=//XCUIElementTypeStaticText[@label='Benvenuto']
```
**MAI copiare xpath Android su iOS** — le classi sono diverse.

**REGOLA 4 — class chain (solo iOS, mai Android)**
```
iOS: class chain=**/XCUIElementTypeButton[`label == 'Accedi'`]
```
Usa solo quando accessibility_id e xpath semantico non funzionano.

**REGOLA 5 — predicate string (solo iOS, ultimo resort)**
```
iOS: predicate string=label == 'Accedi' AND type == 'XCUIElementTypeButton'
```

### C.4 Divergenza UI

Se durante il porting trovi che la UI iOS è strutturalmente diversa dall'Android
(elemento assente, flusso diverso, schermata aggiuntiva), dichiara:

```
DIVERGENZA UI RILEVATA: <descrizione>
Piattaforma sorgente: <comportamento Android>
Piattaforma target:   <comportamento iOS atteso>
Azione: acquisizione dump iOS per <PageName> tramite reference/dump-acquisition.md
```
Non inventare locatori per schermate non viste.

### C.5 Nota simulatore vs device reale

Su simulatore iOS, `accessibility_id` può differire dal device reale (dipende dalla configurazione Xcode).
Se un test verde su simulatore fallisce su BS device reale, verifica il dump direttamente su device fisico.
