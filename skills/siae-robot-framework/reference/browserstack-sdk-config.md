# BrowserStack SDK — Configurazione Nativa RF/Appium

Approccio **raccomandato** per l'integrazione BrowserStack con Robot Framework.
L'SDK intercetta la sessione Appium e la reindirizza su cloud BS — il codice dei test non cambia.

---

## Differenza SDK vs Legacy

| | SDK (raccomandato) | Legacy (capabilities-in-URL) |
|---|---|---|
| Credenziali | `browserstack.yml` o env vars | Nelle capabilities del test |
| URL Appium | Locale (l'SDK reindirizza) | `hub-cloud.browserstack.com` hardcoded nel resource |
| Device matrix | `browserstack.yml` | Variabili RF per ogni device |
| Run command | `browserstack-sdk robot ...` | `robot ...` con variabili BS settate |
| Parallelismo | Configurato in `browserstack.yml` | Gestito da `pabot` manualmente |
| Codice test | **Identico** a locale | Richiede keyword dedicate (`Open BrowserStack Android...`) |

**Regola**: usa sempre l'approccio SDK. Il codice dei test è identico alla run locale — solo il comando di esecuzione cambia.

---

## Setup

```bash
pip install browserstack-sdk
```

---

## browserstack.yml — Struttura canonica

Il file va nella **root del progetto** (stessa directory di `tests/`).

```yaml
# --- Credenziali (MAI hardcoded: usa variabili d'ambiente) ---
userName: ${BROWSERSTACK_USERNAME}
accessKey: ${BROWSERSTACK_ACCESS_KEY}

# --- Framework ---
framework: robot
appiumVersion: 2.0.0

# --- App ---
# Opzione A: path locale (l'SDK fa l'upload automatico)
app: ./app/siae-app.apk

# Opzione B: app già uploadata (bs://app_id)
# app: bs://abc123def456

# --- Platform matrix ---
platforms:
  - platformName: android
    deviceName: Samsung Galaxy S23
    osVersion: 13.0
    automationName: UiAutomator2
  - platformName: android
    deviceName: Google Pixel 7
    osVersion: 13.0
    automationName: UiAutomator2

# --- Parallelismo ---
parallelsPerPlatform: 1

# --- Identificazione build ---
projectName: SIAE Mobile App
buildName: ${BUILD_TAG}        # da variabile CI o stringa fissa
sessionName: ${TEST_NAME}      # opzionale: nome del singolo test

# --- Debug ---
debug: true
networkLogs: true
deviceLogs: true
```

---

## browserstack.yml — Versione iOS

```yaml
userName: ${BROWSERSTACK_USERNAME}
accessKey: ${BROWSERSTACK_ACCESS_KEY}

framework: robot
appiumVersion: 2.0.0

# IPA con provisioning profile Ad Hoc o Enterprise
app: ./app/siae-app.ipa

platforms:
  - platformName: iOS
    deviceName: iPhone 15
    osVersion: 17.0
    automationName: XCUITest
  - platformName: iOS
    deviceName: iPhone 14
    osVersion: 16.0
    automationName: XCUITest

parallelsPerPlatform: 1

projectName: SIAE Mobile App iOS
buildName: ${BUILD_TAG}

debug: true
networkLogs: true
```

---

## Run commands

### Test Android BS (con SDK)
```bash
# Run singolo file
browserstack-sdk robot --outputdir results_bs tests/BS/TC01_Login.robot

# Run intera suite
browserstack-sdk robot --outputdir results_bs --log log.html --report report.html tests/BS/

# Run parallelo con pabot
browserstack-sdk pabot --processes 4 --outputdir results_bs tests/BS/
```

### Test iOS BS (con SDK)
```bash
browserstack-sdk robot --outputdir results_bs_ios tests/BS_iOS/TC01_Login.robot

browserstack-sdk pabot --processes 4 --outputdir results_bs_ios tests/BS_iOS/
```

### Variabili d'ambiente richieste
```bash
export BROWSERSTACK_USERNAME=your_username
export BROWSERSTACK_ACCESS_KEY=your_access_key
# oppure nel .env (non versionato):
# BROWSERSTACK_USERNAME=your_username
# BROWSERSTACK_ACCESS_KEY=your_access_key
```

---

## common.resource con SDK

Con l'SDK, **non servono keyword dedicate** per BrowserStack.
`Open SIAE Application` (definita in [common-resource.md](common-resource.md)) funziona invariata
sia in locale che su BS — l'SDK intercetta e reindirizza su cloud BS in modo trasparente.

---

## Struttura directory raccomandata

```
project-root/
├── browserstack.yml              ← Android BS config
├── browserstack-ios.yml          ← iOS BS config (opzionale, o usa flag --config-file)
├── tests/
│   ├── TC01_Login.robot          ← Android locale
│   ├── iOS/
│   │   └── TC01_Login.robot      ← iOS locale
│   ├── BS/
│   │   └── TC01_Login.robot      ← Android BS (stessa struttura locale)
│   └── BS_iOS/
│       └── TC01_Login.robot      ← iOS BS
├── resources/
│   ├── common.resource
│   ├── LoginPage.resource        ← Android locators
│   └── iOS/
│       └── LoginPage.resource    ← iOS locators
└── app/
    ├── siae-app.apk
    └── siae-app.ipa
```

---

## Upload app manuale (alternativa al path locale)

```bash
# Upload APK — restituisce { "app_url": "bs://abc123..." }
curl -u "${BROWSERSTACK_USERNAME}:${BROWSERSTACK_ACCESS_KEY}" \
  -X POST "https://api-cloud.browserstack.com/app-automate/upload" \
  -F "file=@app/siae-app.apk"

# Upload IPA — restituisce { "app_url": "bs://xyz456..." }
curl -u "${BROWSERSTACK_USERNAME}:${BROWSERSTACK_ACCESS_KEY}" \
  -X POST "https://api-cloud.browserstack.com/app-automate/upload" \
  -F "file=@app/siae-app.ipa"
```

**Step obbligatorio dopo l'upload:** copia il valore `app_url` dalla risposta JSON e
aggiornalo nel `browserstack.yml`:
```yaml
# Prima (path locale — upload automatico ad ogni run):
app: ./app/siae-app.apk

# Dopo (id BS — upload già fatto, riuso lo stesso artefatto):
app: bs://abc123def456...
```

L'id BS è valido finché l'app non viene cancellata dal dashboard BS.
Usare `bs://` è preferibile per run frequenti: evita re-upload ad ogni esecuzione.

---

## Verifica upload recente

```bash
curl -u "${BROWSERSTACK_USERNAME}:${BROWSERSTACK_ACCESS_KEY}" \
  "https://api-cloud.browserstack.com/app-automate/recent_apps"
```

---

## Note operative

- **`browserstack.yml` NON va in versioning** se contiene credenziali. Aggiungi a `.gitignore` se usi valori diretti. Se usi `${BROWSERSTACK_USERNAME}` (env var syntax) puoi versionar il file.
- **IPA**: deve avere provisioning profile Ad Hoc o Enterprise. Non funziona con Development profile.
- **Parallelismo**: il numero di sessioni parallele dipende dal piano BS — non superare il limite dell'account.
- **`buildName`**: usa una variabile CI (`${BUILD_TAG}`, `${CI_PIPELINE_ID}`) per distinguere le build nel dashboard BS.
