# DEBUG ENGINE — Robot Framework / Appium

Motore di regole autonomo per la classificazione e risoluzione di failure RF/Appium.
Claude esegue le regole in ordine senza chiedere all'utente come procedere.

---

## Classificazione preliminare del failure

Leggi il log e classifica l'errore in base al messaggio principale:

| Messaggio chiave nel log | Categoria | Note |
|--------------------------|-----------|------|
| `NoSuchElementException`, `Element not found`, `No match for` | CATEGORIA 1 | Locatore rotto o pagina non caricata |
| `ElementNotInteractableException`, `Element is not interactable` | CATEGORIA 1-R1.x | Elemento coperto da overlay o disabled — vedi R1.8 |
| `InvalidElementStateException` | CATEGORIA 1 | Campo non editabile o disabled |
| `TimeoutException`, `Stale element`, `StaleElementReference` | CATEGORIA 2 | Timing o UI refresh |
| `SessionNotCreatedException`, `Could not start a new session` | CATEGORIA 3-R1 | Problema infrastrutturale (non nel test) |
| `WebDriverException: An unknown server-side error` | CATEGORIA 3-R2 | App crash o errore Appium |
| `All devices are busy`, `Allocated session timed out` | CATEGORIA 3-R3 | BS infrastructure |
| `App not found`, `Invalid app url` | CATEGORIA 3-R4 | BS app upload |
| `Expected '...' but got '...'`, `should be visible but is not` | CATEGORIA 4 | Assertion fallita |
| Qualsiasi altro errore non in tabella | **CATEGORIA 0** | Errore non classificato — vedi sotto |

**CATEGORIA 0 — Errore non classificato:**
Se il messaggio non corrisponde a nessuna riga sopra, forza immediatamente STALLO:
```
DEBUG STALLO (CATEGORIA 0 — errore non classificato):
Messaggio: <testo esatto dell'errore>
Diagnosi: errore fuori dalle categorie note (infrastruttura CI, driver incompatibile, rete)
Richiedo: log completo (`robot --loglevel DEBUG`) + output terminale + versione Appium (`appium --version`)
```
Non tentare fix a caso su errori non classificati.

---

## CATEGORIA 1 — Element Not Found / No Such Element

**R1.1 — Xpath posizionale o con indice?**
- Segnale: `//LinearLayout[2]/Button[1]` oppure `(//Button)[3]`
- Fix: acquisisci dump aggiornato, trova `accessibility_id` o xpath semantico
- BP: applica gerarchia §BP-1 da `best-practices.md`

**R1.2 — App ha cambiato versione, nuovo resource-id?**
- Segnale: `resource-id` nel dump diverso da quello nel .resource
- Fix: aggiorna il locatore nel Page resource con il nuovo id
- Verifica: cerca nel dump aggiornato (ADB / appium-mcp / BS)

**R1.3 — Pagina non ancora caricata?**
- Segnale: errore immediato (<1s dall'avvio del test)
- Fix: aggiungi `Wait And Assert Element Visible` sull'entry-point della pagina prima di interagire

**R1.4 — Elemento in scroll container?**
- Segnale: elemento esiste nel dump ma non è interagibile
- Fix: aggiungi `Swipe Up` (con percentuali, non coordinate) prima del `Wait And Click`

**R1.5 — Context sbagliato (webview vs native)?**
- Segnale: log contiene "Could not find element" su elemento noto
- Fix: verifica il context con `Get Contexts`, switcha con `Switch To Context    NATIVE_APP`

```robotframework
# Esempio context switching per app ibride
${contexts}=    Get Contexts
Log    Available contexts: ${contexts}
Switch To Context    NATIVE_APP
# oppure per webview:
Switch To Context    WEBVIEW_com.siae.app
```

**R1.6 — Nessuna delle regole precedenti risolve?**
- Acquisisci dump aggiornato tramite [dump-acquisition.md](dump-acquisition.md)
- Confronta dump attuale con locatore nel .resource
- Identifica la discrepanza e correggi

**R1.7 — Elemento fuori viewport orizzontalmente (tab strip, carosello, ViewPager)?**
- Segnale: elemento visibile nel dump ma non sul display — scroll verticale R1.4 non aiuta
- Fix: aggiungi `Swipe Left` (o `Swipe Right`) prima del `Wait And Click`
  ```robotframework
  Swipe Left    # o Swipe Right — aggiungi keyword in common.resource se assente
  Wait And Click    ${TARGET_TAB}
  ```
- Nota: `common.resource` include solo `Swipe Up` / `Swipe Down`. Aggiungi varianti orizzontali seguendo lo stesso pattern percentuale (no coordinate assolute).

**R1.8 — Elemento non interagibile — overlay, banner, dialog?**
- Segnale: `ElementNotInteractableException` o `Element is not interactable`
- Il dump mostra l'elemento target MA un altro elemento (bottom sheet, dialog, banner) è sovrapposto
- Fix: individua l'elemento overlay nel dump → dimettilo prima di interagire
  ```robotframework
  # Dismissi dialog nativo
  Handle Alert    ACCEPT
  # oppure tappa fuori dalla modal
  Wait And Click    ${OVERLAY_DISMISS_BUTTON}
  # poi riprova
  Wait And Click    ${TARGET_ELEMENT}
  ```
- Se l'overlay è un banner pubblicitario o cookie consent, aggiungi dismissal nel `Suite Setup`

**R1.9 — RecyclerView o lista con lazy loading?**
- Segnale: elemento non trovato ma dovrebbe essere nella lista (scrollando oltre quanto R1.4 ha già scrollato)
- Fix: usa scroll iterativo con verifica condizionale
  ```robotframework
  Wait Until Keyword Succeeds    5x    1s    Scroll Until Element Found    ${TARGET_ELEMENT}
  ```
  `Scroll Until Element Found` è già definita in `common.resource` — non ridefinirla nel Page resource.

---

## CATEGORIA 2 — Timeout / Stale Element

**R2.1 — Timeout default (15s) su operazione lenta?**
- Segnale: `TimeoutException` dopo esattamente 15s
- Fix: usa `timeout=${LONG_TIMEOUT}` (30s) su quella specifica keyword
- **Non aumentare `${DEFAULT_TIMEOUT}` globale** — usa timeout esplicito

**R2.2 — Sleep hardcoded prima del Wait?**
- Segnale: `Sleep` nel codice prima del `Wait`
- Fix: rimuovi Sleep, usa `Wait Until Element Is Visible` con timeout adeguato

**R2.3 — StaleElementReferenceException dopo un'azione?**
- Segnale: `stale element reference` nel log
- Fix: rilocalizza l'elemento dopo l'azione. Non cachare riferimenti tra keyword diverse.

**R2.4 — Loader/spinner blocca l'interazione?**
- Segnale: elemento visibile ma non cliccabile
- Fix: aggiungi `Wait And Assert Element Not Visible    ${LOADER_ELEMENT}` prima dell'interazione

**R2.5 — Implicit wait Appium in conflitto con Wait RF?**
- Segnale: `Wait Until Element Is Visible` timeout inatteso nonostante elemento visibile
- Fix: verifica che `implicitWaitTimeout` nelle capabilities sia 0 (disabilita implicit wait Appium)
  — l'explicit wait di RF e l'implicit wait di Appium interferiscono tra loro

---

## CATEGORIA 3 — Session / App Crash / Appium Error

**R3.1 — SessionNotCreatedException (locale)?**
- Segnale: `Could not start a new session`, `Unable to connect to Appium`
- Azione: non modificare il test — è un problema infrastrutturale
- Checklist diagnostica:
  ```
  adb devices               → device/emulatore connesso?
  lsof -i :4723             → porta Appium in ascolto?
  appium --version          → Appium installato?
  ```
- Dichiara: `SESSION ERROR: Appium non raggiungibile. Verifica: [lista sopra]`

**R3.2 — App crasha durante il test?**
- Segnale: `An unknown server-side error occurred`, app si chiude
- Fix 1: verifica che `${APP_PATH}` punti alla versione corretta
- Fix 2: raccogli logcat: `adb logcat -d > /tmp/logcat.txt` (cerca `FATAL` o `AndroidRuntime`)
  - ⚠️ **Il logcat può contenere token, JWT, credenziali loggati dall'app.** Non committare il file. Aggiungi `logcat*.txt` e `/tmp/logcat.txt` a `.gitignore`.
- Fix 3: aggiungi `Capture Page Screenshot` nel Test Teardown

**R3.3 — BrowserStack: device busy o timeout allocazione?**
- Segnale: `All devices are busy` o timeout nella creazione sessione BS
- Azione: non è un problema del test — è infrastruttura BS
- Dichiara: `BS INFRA: device non disponibile. Riprova o cambia deviceName nelle capabilities.`

**R3.4 — BrowserStack: app non uploadata o path errato?**
- Segnale: `App not found`, `Invalid app url`
- Fix con SDK: verifica il campo `app:` in `browserstack.yml`
  - Se `app: ./app/siae-app.apk` → il file APK/IPA esiste nel path indicato?
  - Se `app: bs://abc123` → l'id BS è quello dell'upload più recente?
- Verifica upload recente:
  ```bash
  curl -u "${BROWSERSTACK_USERNAME}:${BROWSERSTACK_ACCESS_KEY}" \
    https://api-cloud.browserstack.com/app-automate/recent_apps
  ```
- Per upload manuale: vedi [browserstack-sdk-config.md §Upload app manuale](browserstack-sdk-config.md)

**R3.5 — Orientamento/alert inatteso?**
- Segnale: elemento non trovato su pagina nota, schermata diversa dall'attesa
- Fix: aggiungi nel Test Setup:
  ```robotframework
  Handle Alert    ACCEPT
  Set Orientation    PORTRAIT
  ```

---

## CATEGORIA 4 — Assertion Failure

**R4.1 — Testo atteso diverso da testo reale?**
- Segnale: `Expected 'Accedi' but got 'Login'`
- Fix: controlla internazionalizzazione o testo cambiato
- BP: non usare testo visibile come locatore se internazionalizzato → usa `accessibility_id`
- Se testo variabile: usa `Should Contain` invece di `Should Be Equal`

**R4.2 — Elemento non visibile quando dovrebbe esserlo?**
- Fix: aggiungi `Assert` sulla schermata precedente per isolare dove si perde il flusso

**R4.3 — Assertion su testo non ancora caricato?**
- Segnale: fallisce ma manualmente funziona (race condition)
- Fix: aggiungi `Wait And Assert Element Visible` prima dell'assertion
- Oppure: `Wait Until Keyword Succeeds    3x    1s    <keyword con assert>`

**R4.4 — Assertion fallisce solo su BrowserStack?**
- Cause probabili: risoluzione device diversa, OS version, font size
- Fix a: screenshot BS → confronta visivamente con locale
- Fix b: verifica capabilities BS (`platformVersion`, `deviceName`)
- Fix c: usa `Should Contain` invece di `Should Be Equal` per testi sensibili a locale

---

## LOOP DI VERIFICA

Dopo ogni fix applicato:

1. Ri-esegui il test: `robot <file>.robot` (locale) o avvia sessione BS
2. Leggi l'output completo
3. **SE verde** → chiudi il loop, documenta il fix nel `[Documentation]` della keyword
4. **SE ancora KO:**
   - Stesso errore → passa alla regola successiva nella stessa categoria
   - Errore diverso → riclassifica con la tabella di classificazione iniziale
   - Dopo 3 iterazioni senza progresso → dichiara STALLO

## §STALLO — Dichiarazione di stallo

```
DEBUG STALLO: tentati R<x>, R<x+1>, R<x+2> senza successo.
Diagnosi: <cosa è stato escluso>
Ipotesi residue: <lista>
Richiedo: <azione specifica — dump fresco / logcat / screenshot BS / logcat>
```

Non tentare un quarto fix senza prima aver dichiarato lo stallo e ottenuto nuove evidenze.
