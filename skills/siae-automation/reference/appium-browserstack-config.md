# Appium + BrowserStack App Automate — Configurazione di Riferimento

Questo documento è il riferimento tecnico per la Fase 2 (Path Mobile) della skill `siae-automation`.

---

## Capabilities BrowserStack App Automate

Le capabilities vengono passate alla `start_session` di appium-mcp. BrowserStack le interpreta per selezionare il device e l'app.

### Android

```json
{
  "platformName": "Android",
  "appium:deviceName": "Samsung Galaxy S23",
  "appium:platformVersion": "13.0",
  "appium:app": "bs://{APP_URL_DA_UPLOAD}",
  "appium:automationName": "UiAutomator2",
  "appium:newCommandTimeout": 300,
  "bstack:options": {
    "userName": "${BROWSERSTACK_USERNAME}",
    "accessKey": "${BROWSERSTACK_ACCESS_KEY}",
    "projectName": "SIAE {JIRA_PROJECT_KEY}",
    "buildName": "Sprint {SPRINT} — {STORY_ID}",
    "sessionName": "TC-{ID}: {SCENARIO}",
    "debug": true,
    "networkLogs": true
  }
}
```

### iOS

```json
{
  "platformName": "iOS",
  "appium:deviceName": "iPhone 14",
  "appium:platformVersion": "16",
  "appium:app": "bs://{APP_URL_DA_UPLOAD}",
  "appium:automationName": "XCUITest",
  "appium:newCommandTimeout": 300,
  "bstack:options": {
    "userName": "${BROWSERSTACK_USERNAME}",
    "accessKey": "${BROWSERSTACK_ACCESS_KEY}",
    "projectName": "SIAE {JIRA_PROJECT_KEY}",
    "buildName": "Sprint {SPRINT} — {STORY_ID}",
    "sessionName": "TC-{ID}: {SCENARIO}",
    "debug": true,
    "networkLogs": true
  }
}
```

### Device matrix consigliata SIAE

| Priorità | Android | iOS |
|----------|---------|-----|
| P1 | Samsung Galaxy S23 (Android 13) | iPhone 14 (iOS 16) |
| P2 | Google Pixel 7 (Android 13) | iPhone 13 (iOS 15) |
| P3 | Samsung Galaxy A54 (Android 13) | iPad Air 5th gen (iPadOS 16) |

---

## Mapping Action → appium-mcp tool call

Usa questa tabella per tradurre gli step dei TC Xray in sequenze di tool call.

### Pattern di ricerca elementi

Preferisci sempre `accessibility id` (testId) — è più stabile del xpath.
Se l'accessibility ID non è definito nell'app, suggerisci al developer di aggiungerlo:
- Android: `contentDescription` nell'XML layout
- iOS: `accessibilityIdentifier` nel codice Swift/ObjC

```
Ordine di priorità strategia:
1. accessibility id   → veloce, stabile, preferito
2. -ios predicate string / -android uiautomator  → flessibile
3. xpath              → lento, fragile, ultimo tentativo
```

### Tabella mapping

| Step Action | Sequenza tool call |
|-------------|-------------------|
| "Aprire l'app" | `launch_app(bundleId/packageName)` |
| "Navigare alla schermata X" | `find_element(accessibility id, "tab-X")` → `tap_element` |
| "Toccare il pulsante X" | `find_element(accessibility id, "btn-X")` → `tap_element` |
| "Premere X" | `find_element(accessibility id, "X")` → `tap_element` |
| "Inserire testo X nel campo Y" | `find_element(accessibility id, "input-Y")` → `enter_text("X")` |
| "Scorrere verso il basso" | `simulate_gesture([{pointerMove y:0.2}, pointerDown, {pointerMove origin:pointer y:0.6}, pointerUp])` |
| "Scorrere verso l'alto" | `simulate_gesture([{pointerMove y:0.8}, pointerDown, {pointerMove origin:pointer y:-0.6}, pointerUp])` |
| "Swipe da destra a sinistra" | `simulate_gesture([{pointerMove x:0.9 y:0.5}, pointerDown, {pointerMove origin:pointer x:-0.7}, pointerUp])` |

### Tabella asserzioni (Expected Result → verifica)

| Expected Result | Tool call di verifica |
|-----------------|----------------------|
| "Testo X è visibile" | `find_element(accessibility id, "X")` → `get_element_text` → verifica valore |
| "Schermata X è visualizzata" | `get_page_source_file` → cerca tag/elemento caratteristico della schermata |
| "Messaggio di errore X" | `find_element(xpath, "//*[@text='X']")` → `get_element_text` |
| "Elemento X non visibile / assente" | `find_element` → se lancia errore = elemento assente = PASS |
| "Screenshot di stato" | `get_screenshot_file` → analisi visiva dell'immagine |
| "Log di sistema" | `get_device_logs` → cerca la riga attesa |

---

## Pattern di gestione errori

### Elemento non trovato

Se `find_element` non trova l'elemento entro il timeout:
1. Esegui `get_screenshot_file` per catturare lo stato attuale
2. Esegui `get_page_source_file` per ispezionare il DOM
3. Registra FAIL con dettaglio: "Elemento '{accessibility_id}' non trovato — screenshot allegato"
4. Salta gli step successivi dello stesso TC (mark: SKIP) ma continua con il TC successivo
5. **Non terminare l'intera sessione** — chiudi questa sessione e aprine una nuova per il TC successivo

### Timeout di sessione

Se la sessione BrowserStack scade (default 300s):
- Registra FAIL per tutti i TC non completati
- Indica al developer di aumentare `newCommandTimeout` o suddividere i TC in sessioni separate

### App crash

Se l'app crasha durante il test:
1. `get_device_logs` per raccogliere il crash log
2. Registra FAIL: "App crash al step N — log allegato"
3. Termina la sessione con `end_session`
4. Non rieseguire automaticamente — riporta il crash al developer

---

## Sequenza completa per singolo TC

```
1. start_session(capabilities BrowserStack per canale)
2. launch_app(bundleId/packageName)
3. Per ogni step del TC:
   a. Esegui le tool call di Action
   b. Verifica l'Expected Result (asserzione)
   c. Se asserzione FAIL → get_screenshot_file → registra FAIL → vai a 4
   d. Se asserzione PASS → continua con step successivo
4. end_session
5. Registra risultato: PASS (tutti gli step OK) / FAIL (step N fallito, screenshot X)
```

**Nota:** esegui una sessione per TC. Non riutilizzare la stessa sessione tra TC diversi — lo stato dell'app potrebbe non essere pulito.

---

## Upload APK/IPA su BrowserStack

### Android (APK)

```bash
curl -u "${BROWSERSTACK_USERNAME}:${BROWSERSTACK_ACCESS_KEY}" \
  -X POST "https://api-cloud.browserstack.com/app-automate/upload" \
  -F "file=@/path/to/app-debug.apk" \
  -F "custom_id=siae-{PROJ_KEY}-android"
```

Risposta: `{"app_url": "bs://abc123...", "custom_id": "siae-{PROJ_KEY}-android"}`

Usa `app_url` nelle capabilities: `"appium:app": "bs://abc123..."`

### iOS (IPA)

```bash
curl -u "${BROWSERSTACK_USERNAME}:${BROWSERSTACK_ACCESS_KEY}" \
  -X POST "https://api-cloud.browserstack.com/app-automate/upload" \
  -F "file=@/path/to/app.ipa" \
  -F "custom_id=siae-{PROJ_KEY}-ios"
```

**Nota:** l'IPA deve essere firmata con un provisioning profile di tipo Ad Hoc o Enterprise. Non caricare IPA da App Store.

### Riutilizzo app già uploadata

Se l'app è già su BrowserStack con un `custom_id`:
```bash
# Recupera l'app_url dall'ID custom
curl -u "${BROWSERSTACK_USERNAME}:${BROWSERSTACK_ACCESS_KEY}" \
  "https://api-cloud.browserstack.com/app-automate/recent_apps/siae-{PROJ_KEY}-android"
```

Usa il `custom_id` direttamente nelle capabilities invece dell'`app_url` se preferisci:
```json
"appium:app": "siae-{PROJ_KEY}-android"
```
