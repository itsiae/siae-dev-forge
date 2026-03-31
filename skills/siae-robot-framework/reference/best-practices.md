# Best Practice Layer — RF/Appium SIAE

Regole non negoziabili. Si applicano su tutto ciò che la skill produce o modifica.

---

## BP-1 — Gerarchia Locatori (ordine tassativo)

### 1° accessibility_id
```robotframework
${LOGIN_BUTTON}    accessibility_id=login_button
```
- Stabile tra versioni, cross-platform se allineato
- Usa quando l'elemento ha un accessibility label definito

### 2° resource-id (solo Android)
```robotframework
${USERNAME_FIELD}    id=com.siae.app:id/username_field
```
- Solo Android. Non esiste il concetto in iOS.
- Stabile se il dev non rinomina le risorse

### 3° xpath semantico con attributo
```robotframework
# Android
${ERROR_MSG}    xpath=//android.widget.TextView[@resource-id='com.siae.app:id/error_msg']
${LOGIN_BTN}    xpath=//android.widget.Button[@content-desc='Accedi']

# iOS
${LOGIN_BTN}    xpath=//XCUIElementTypeButton[@name='Accedi']
${TITLE}        xpath=//XCUIElementTypeStaticText[@label='Benvenuto']
```
- MAI copiare xpath Android su iOS — le classi sono diverse

### 4° class chain (solo iOS)
```robotframework
${LOGIN_BTN}    class chain=**/XCUIElementTypeButton[`label == 'Accedi'`]
```
- Solo quando accessibility_id e xpath semantico non funzionano
- Più performante di xpath su iOS

### 5° predicate string (solo iOS, ultimo resort)
```robotframework
${LOGIN_BTN}    predicate string=label == 'Accedi' AND type == 'XCUIElementTypeButton'
```

### VIETATO SEMPRE
```robotframework
# MAI coordinate assolute
Tap    150    300

# MAI xpath posizionale
${ELEM}    xpath=//android.view.View[3]/android.widget.Button[1]

# MAI xpath con indice senza attributo
${ELEM}    xpath=(//Button)[2]

# MAI testo visibile per elementi internazionalizzati
${TITLE}    xpath=//TextView[@text='Benvenuto']    # rompe con cambio lingua
```

---

## BP-2 — Wait Strategy (nessun Sleep libero)

### CORRETTO
```robotframework
Wait And Click    ${BUTTON}
Wait And Click    ${BUTTON}    timeout=${LONG_TIMEOUT}
Wait Until Element Is Visible    ${ELEMENT}    15s
Wait Until Element Is Not Visible    ${LOADER}    ${LONG_TIMEOUT}
```

### VIETATO
```robotframework
Sleep    2s                                      # MAI senza commento
```

### ACCETTABILE (solo se non esiste alternativa osservabile)
```robotframework
Sleep    3s    # motivo: animazione di transizione pagina senza elemento observer
```

### Regola Sleep
Se usi Sleep devi dimostrare che non esiste un elemento osservabile che segnali il completamento.
Formato obbligatorio: `Sleep    ${n}s    # motivo: <spiegazione specifica>`

---

## BP-3 — Credenziali e Dati Sensibili

### VIETATO
```robotframework
${USERNAME}    mario.rossi@siae.it     # MAI hardcoded
${PASSWORD}    Password123             # MAI hardcoded
```

### CORRETTO
```robotframework
${USERNAME}    ${ENV_USERNAME}         # da variabile d'ambiente
${PASSWORD}    ${ENV_PASSWORD}         # da variabile d'ambiente
```

Oppure da file separato non versionato: `variables.yaml` (aggiunto a `.gitignore`).

> ⚠️ **Log masking RF:** quando un test fallisce in debug mode, RF stampa tutte le variabili dello scope.
> Per evitare che `${ENV_PASSWORD}` appaia in chiaro nei log, assegna il valore a una variabile
> con `password` nel nome (RF 5+ maschera automaticamente le variabili il cui nome contiene `password`):
> ```robotframework
> ${password}=    Get Environment Variable    ENV_PASSWORD
> ```
> Oppure usa `Log Variables` solo in debug locale, mai in CI.

### Guard obbligatorio nel Suite Setup

Se le variabili d'ambiente non sono settate, RF le espande come stringa vuota senza errore.
Aggiungi questo guard per fail-fast esplicito:

```robotframework
*** Keywords ***
Validate Test Environment
    [Documentation]    Fail esplicito se le env var obbligatorie non sono settate.
    Should Not Be Empty    ${ENV_USERNAME}     ENV_USERNAME non settata — impossibile proseguire
    Should Not Be Empty    ${ENV_PASSWORD}     ENV_PASSWORD non settata — impossibile proseguire
    Should Not Be Empty    ${APP_PATH}         APP_PATH non settata — impossibile proseguire
```

Chiama `Validate Test Environment` in `Suite Setup` prima di `Open SIAE Application`.

### .gitignore canonico

Aggiungi sempre questi path al `.gitignore` del progetto:
```
variables.yaml
.env
tests/dumps/
logcat*.txt
/tmp/logcat.txt
results*/
*.png
screenshots/
videos/
```

**Nota screenshot/video:** Appium genera automaticamente screenshot on failure e può registrare video. Questi file possono contenere **PII sensibili SIAE** (codici fiscali, IBAN, dati di pagamento diritti d'autore). Non committarli mai nel repository.

---

## BP-4 — Struttura Keyword

### Obbligatorio
```robotframework
Perform Login
    [Documentation]    Inserisce credenziali e submitta il form di login
    [Arguments]    ${username}    ${password}
    Input Login Credentials    ${username}    ${password}
    Submit Login Form

Get Welcome Message
    [Documentation]    Attende visibilità e restituisce il testo del messaggio di benvenuto
    [Arguments]    ${timeout}=${DEFAULT_TIMEOUT}
    Wait Until Element Is Visible    ${WELCOME_MSG}    ${timeout}
    ${text}=    Get Text    ${WELCOME_MSG}
    RETURN    ${text}
```

### Regole
- `[Documentation]` obbligatorio se >2 step O ha argomenti O è composita
- `[Arguments]` con nomi descrittivi: `${username}` non `${arg1}`
- `RETURN` (non `[Return]`, deprecato da RF 5)
- **Keyword di interazione** (tap, swipe, input, navigation) → SEMPRE tramite wrapper da `common.resource`
- **Keyword di query stato** (`Get Text`, `Get Element Attribute`, `Element Should Be Visible`, `Get Element Count`) → possono chiamare AppiumLibrary direttamente SE non richiedono wait logic aggiuntiva

---

## BP-5 — Tag Obbligatori

Ogni test case DEVE avere:
```robotframework
[Tags]    <tipo>    <feature>    <platform>
```

| Campo | Valori standard |
|-------|----------------|
| Tipo | `smoke` \| `regression` \| `e2e` |
| Feature | `login` \| `home` \| `search` \| `payment` \| ... |
| Platform | `android` \| `ios` \| `android-bs` \| `ios-bs` |

Esempio: `[Tags]    smoke    login    android-bs`

---

## BP-6 — Naming Convention (tassativo)

| Cosa | Pattern | Esempio |
|------|---------|---------|
| File .robot | `TCxx_NomeCamelCase.robot` | `TC01_LoginConCredenziali.robot` |
| File resource | `NomePaginaPage.resource` | `LoginPage.resource` |
| Locatori | `${PAGENAME_ELEMENT_DESC}` in UPPERCASE | `${LOGIN_USERNAME_FIELD}` |
| Keywords | Title Case Con Spazi | `Assert Login Page Loaded` |
| Variabili | `${NOME_IN_UPPERCASE}` | `${DEFAULT_TIMEOUT}` |
| Suite/Test | Frase descrittiva | `Login Con Credenziali Valide` |

---

## Tabella Anti-Pattern Tecnici

| Anti-pattern | Perché è vietato | Alternativa |
|-------------|-----------------|-------------|
| Coordinate `x=150 y=300` | Rompe su ogni device con risoluzione diversa | `accessibility_id` o xpath semantico |
| `Sleep 5s` senza commento | Lento e non diagnosticabile | `Wait Until Element Is Visible` |
| `Click Element` diretto | Bypassa il wait strategy | `Wait And Click` da `common.resource` |
| `//LinearLayout[2]/Button[1]` | Rompe a ogni minima modifica UI | xpath con attributo semantico |
| Credenziali hardcoded | Security + manutenibilità | Variabili d'ambiente |
| Import tra Page resource | Accoppiamento implicito | `common.resource` per elementi condivisi |
| Keyword senza `[Documentation]` (>2 step) | Non diagnosticabile in debug | Aggiungi sempre |
| `[Return]` (vecchia sintassi) | Deprecato da RF 5 | `RETURN` |
| Test case con >10 step diretti | Non manutenibile | Componi keyword nel resource |
| Locatore duplicato in più resource | Manutenzione inconsistente | Centralizza in resource condiviso |
