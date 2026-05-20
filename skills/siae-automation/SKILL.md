---
name: siae-automation
description: >
  Use when setting up E2E test automation, Playwright/Cypress, or CI/CD test
  pipelines. Configura test automation E2E, setup Playwright/Cypress e pipeline
  CI/CD test. Trigger: automatizza test, setup Playwright, setup Cypress, test
  E2E, test di regressione automatici, CI/CD pipeline test, GitHub Actions
  test.
---

# SIAE Automation — E2E Test Generation & Xray Sync

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨 DevForge · AI Competence Center                  ║
║         "Il codice si forgia. Il developer cresce."              ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Rigid | **Fase SDLC:** 5. Testing / Automation

---

## LA LEGGE DI FERRO

```
NESSUN TEST AUTOMATIZZATO SENZA LISTA TC CONFERMATA DAL DEVELOPER
```

<EXTREMELY-IMPORTANT>
Stai per generare test E2E senza la lista TC confermata dal developer?
FERMATI. La proposta ROI e' un suggerimento — la conferma esplicita e' obbligatoria.

Stai per automatizzare TUTTI i TC senza valutare il ROI?
FERMATI. Automatizzare TC con 15 step o logica ambigua genera test fragili
che si rompono a ogni release. Il ROI serve per scegliere cosa vale la manutenzione.

Stai per procedere senza cercare la TL esistente in Xray?
FERMATI. Una TL potrebbe esistere da un sprint precedente. Non sovrascrivere lavoro fatto.
</EXTREMELY-IMPORTANT>

---

> 📊 **Dai repo itsiae:** I repo con test E2E automatizzati rilevano il 67% dei bug di regressione prima del deploy in collaudo.
> Fonte: analisi su 816 repository GitHub itsiae (60 Java, 44 HCL, 23 Python, 22 TypeScript).

## QUANDO SI APPLICA

- **Dopo siae-qa**: la skill ha prodotto la Test List — questa skill decide quali TC automatizzare e genera i test E2E
- **Invocazione manuale via trigger sentence**: anche su TL già esistenti in Xray
- **Su TL pre-esistente**: se in Xray esiste già una Test List per la Story, la skill la legge e propone cosa aggiungere o automatizzare

---

## RILEVAMENTO CANALE

Prima di qualsiasi altra operazione, rileva il canale analizzando i file nella directory:

| Segnale rilevato | Canale |
|-----------------|--------|
| `.xcworkspace`, `*.xcodeproj`, `ios/` | Mobile — iOS |
| `android/`, `*.apk`, `google-services.json` | Mobile — Android |
| `app.json`, `capacitor.config.ts` | Mobile — cross-platform |
| `cypress.config.ts`, `cypress.config.js`, `cypress/` | Web — Cypress |
| `package.json` con dipendenza `"cypress"` | Web — Cypress |

Se il progetto ha segnali di entrambi i canali, chiedi al developer quale automatizzare in questa sessione.
Se nessun segnale, chiedi: "Stai automatizzando una app mobile (iOS/Android) o un'applicazione web?"

---

## LIVELLI DI INTEGRAZIONE

| Tier | Condizione | Comportamento |
|------|------------|---------------|
| **Tier 1** | MCP Atlassian disponibile | Legge TL da Xray, crea/aggiorna Test Execution, sync risultati automatico |
| **Tier 2** | appium-mcp o Cypress disponibili, no MCP Atlassian | TL fornita manualmente o da CSV siae-qa, genera test, sync manuale |
| **Tier 3** | Nessuna integrazione | Genera test E2E e CSV per import manuale in Xray |

---

## PRE-FLIGHT CARD DI APERTURA

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-automation |
|:---|
| 📱 Canale: `Mobile iOS / Mobile Android / Web` · 📡 Tier: `Tier 1 / 2 / 3` |
| 🎫 TL Xray: `XP-XXX / Non trovata / Da CSV` · 🔢 TC totali TL: `N TC` |
| 🤖 appium-mcp: `Disponibile / Non disponibile` · ☁️ BrowserStack: `Configurato / Mancante` · 🔄 Xray sync: `MCP / CSV` |
| **▼ Azione** |
| 💡 Perche': Leggo prima la TL, poi propongo il piano automation |
| 🚫 Se NO: Workflow automation non inizia |

---

## WORKFLOW A 5 FASI

### Fase 1 — Ricerca Test List e mappatura chiavi Xray

**Obiettivo:** ottenere la Test List (TC con chiavi Jira reali) per questa Story e verificare se esiste già una Test Execution di automation.
Non assumere che né la TL né la TE esistano. Cercale sempre prima.

**Tier 1 (MCP Atlassian):**

Le funzioni JQL specifiche di Xray (es. `testPlanWith()`, `testSetsOf()`) sono disponibili solo in Xray Server, non in Xray Cloud. In Xray Cloud usa Jira JQL standard:

1. Cerca il Test Plan per nome e sprint:
   ```
   JQL: issueType = "Test Plan"
        AND summary ~ "{Story summary o STORY_ID}"
        AND sprint = "{sprint corrente}"
   ```
   Se non trovi nulla: cerca più ampio:
   ```
   JQL: issueType = "Test Plan" AND summary ~ "{STORY_ID}"
   ```

2. Se il Test Plan non è trovato via JQL: chiedi al developer la chiave diretta (es. `XP-123`). Non insistere con JQL — in Xray Cloud i Test Plan non sono sempre linkati alla Story via campo standard.

3. Se il Test Plan esiste: leggi i TC collegati (ID Jira reale, summary, Automazione, NRT, step).
   - Distingui TC già marcati `Automazione=Y` da quelli con `Automazione=N`.

4. Cerca Test Execution automation già esistenti:
   ```
   JQL: issueType = "Test Execution" AND summary ~ "[AUTOMATION]" AND sprint = "{sprint}"
   ```
   - Se esiste: non creare duplicati. Aggiornala con i nuovi TC confermati.
   - Se non esiste: sarà creata in Fase 4.W0 (web) o Fase 5 (mobile).

**Tier 3 (no MCP) — input manuale con mappatura chiavi:**

Chiedi al developer:
> "Hai già importato i TC in Xray dalla sessione siae-qa? Se sì, ho bisogno della mappatura tra gli ID del CSV e le chiavi Jira assegnate da Xray."

Se ha la mappatura → raccoglila:
```
ID CSV → Chiave Xray    Scenario
1      → PROJ-456       Verifica login credenziali valide
2      → PROJ-457       [EDGE] Login campo vuoto
3      → PROJ-458       [NEG] Login password errata
```

Se non ha ancora importato il CSV → importa prima con siae-qa, poi torna qui.
Se non ricorda le chiavi → chiedi di aprire Xray, filtrare per Story `{STORY_ID}` e comunicare le chiavi.

**Questa mappatura è l'input critico della skill**: senza le chiavi Jira reali, i titoli `it()` negli spec Cypress non possono matchare con Xray. Non procedere alla Fase 2 senza di essa.

**Output atteso Fase 1:**
```
TL trovata: XP-123 "Test Plan RIPART-847 Sprint 24"
  TC totali: N
  Con Automazione=Y: N  ← già flaggati da siae-qa
  Con Automazione=N: N  ← candidati da valutare per ROI

Mappatura chiavi disponibile:
  1 → PROJ-456   Verifica login credenziali valide
  2 → PROJ-457   [EDGE] Login campo vuoto
  ...

Test Execution automation esistente: [XE-456] / Non trovata
```

---

### Fase 2 — Analisi ROI e proposta lista automation

**Obiettivo:** non automatizzare tutto — proporre cosa automatizzare basandosi su valore reale.

Per ogni TC nella TL (sia `Y` che `N`), calcola un **punteggio ROI** con questi criteri:

| Criterio | Punti | Razionale |
|----------|-------|-----------|
| `NRT = Y` | +3 | Gira ad ogni regressione — massimo beneficio da automation |
| Happy path (nessun prefisso) | +2 | Il flusso principale deve sempre essere automatizzato |
| `[EDGE]` o `[NEG]` | +2 | Edge case e negativi automatizzati rilevano regressioni silenziose |
| Step ≤ 5 | +2 | Basso costo di implementazione e manutenzione |
| Step 6–10 | +1 | Costo moderato |
| Step > 10 | −1 | Fragile, costoso da mantenere — valutare se scomporre |
| `[PROFILO]` | +1 | Scenari multi-ruolo beneficiano dell'automazione ripetibile |
| Già `Automazione=Y` | +1 | Il developer lo ha già identificato come candidato |

**Fasce ROI:**

| Punteggio | Fascia | Proposta |
|-----------|--------|----------|
| ≥ 7 | 🟢 ALTO | Automatizza subito — priorità 1 |
| 4–6 | 🟡 MEDIO | Consigliato — buon ritorno |
| 1–3 | 🔴 BASSO | Valuta con il developer — rischio manutenzione elevato |
| ≤ 0 | ⛔ SCONSIGLIATO | Non automatizzare — costo > beneficio |

**Presenta la proposta al developer in forma tabellare:**

```
Proposta automation — RIPART-847
────────────────────────────────────────────────────────────────────
  ID    Scenario                           Cat      Step  NRT  ROI
────────────────────────────────────────────────────────────────────
  TC-1  Verifica login credenziali valide  happy    3     Y    🟢 8
  TC-3  Email non inviata senza royalties  [NEG]    2     Y    🟢 7
  TC-2  PDF con importo totale e dettaglio happy    3     Y    🟡 6
  TC-4  Warning log senza email            [EDGE]   2     N    🟡 5
  TC-7  Login con profilo editore          [PROF]   5     N    🟡 4
  TC-9  Timeout invio email               [EDGE]   12    Y    🔴 2
────────────────────────────────────────────────────────────────────
  Pre-selezionati (Automazione=Y da siae-qa): TC-1, TC-2, TC-3, TC-4
  Nuovi candidati suggeriti:                  TC-7
  Sconsigliati:                               TC-9 (12 step, fragile)
```

Spiega brevemente perché i BASSO/SCONSIGLIATI non convengono. Non darlo per scontato.

---

### Fase 3 — Raffinamento da parte del developer

**Non procedere alla generazione senza conferma esplicita del developer.**

Chiedi:

> "Questa è la lista proposta. Puoi:
> - Confermare la selezione così com'è
> - Aggiungere TC che non sono in lista (dimmi ID e scenario)
> - Rimuovere TC che non vuoi automatizzare ora
> - Posticipare i MEDIO per questo sprint
>
> Quando sei pronto, dimmi la lista finale e partiamo."

**Il developer può aggiungere TC non presenti nella TL originale.** In questo caso:
- Chiedi scenario e steps se non li conosci già
- Calcola il ROI e segnala se è basso prima di generare

**Output atteso Fase 3 — lista confermata:**
```
Lista automation confermata (N TC):
  ✅ TC-1 — Verifica login credenziali valide  [🟢 ALTO]
  ✅ TC-3 — Email non inviata senza royalties  [🟢 ALTO]
  ✅ TC-2 — PDF con importo totale e dettaglio [🟡 MEDIO]
  ✅ TC-7 — Login con profilo editore          [🟡 MEDIO — aggiunto dal developer]
  ⏸ TC-4 — Posticipato dal developer
  ⛔ TC-9 — Escluso (ROI basso, confermato dal developer)
```

---

### Fase 4 — Traduzione TC → Test Prompt + Generazione test E2E

Questa fase ha **due livelli**:

1. **Layer di traduzione (obbligatorio, uguale per tutti i canali):** converte ogni TC confermato in un Test Prompt strutturato e canale-agnostico
2. **Layer di generazione (canale-specifico):** usa il Test Prompt per alimentare appium-mcp (mobile) o generare lo spec Cypress (web)

Il layer di traduzione è separato dal canale intenzionalmente: lo stesso TC può essere portato su mobile e web senza riscrivere nulla.

---

#### Step 4.0 — Layer di traduzione: TC → Test Prompt

Per ogni TC nella lista confermata, produci un **Test Prompt strutturato** nel seguente formato.
Questo è l'output intermedio da cui entrambi i path (mobile e web) partono.

```
TEST PROMPT — {TC-ID}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Story:       {STORY_ID}
Scenario:    {Scenario (descrizione) dal TC Xray}
Categoria:   {happy path / [EDGE] / [NEG] / [PROFILO]}
Precondizioni: {condizioni iniziali implicite o esplicite}

Step 1
  Intent:    {navigate | tap | input | verify | scroll | read}
  Action:    "{testo Action dal TC}"
  Target:    "{elemento UI coinvolto — nome descrittivo}"
  Data:      "{dato di test, se presente nel campo Data}"
  Expected:  "{testo Expected Result dal TC}"

Step 2
  Intent:    {navigate | tap | input | verify | scroll | read}
  Action:    "{testo Action dal TC}"
  Target:    "{elemento UI coinvolto}"
  Data:      "{dato di test}"
  Expected:  "{testo Expected Result dal TC}"

[... ripeti per ogni step ...]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Regole di traduzione per il campo `Intent`:**

| Parole chiave nell'Action | Intent assegnato |
|--------------------------|-----------------|
| aprire, navigare, andare, accedere, aprire l'app | `navigate` |
| toccare, premere, cliccare, selezionare, scegliere | `tap` |
| inserire, digitare, scrivere, compilare | `input` |
| verificare, controllare, confermare, assicurarsi | `verify` |
| scorrere, scrollare, swipe | `scroll` |
| leggere, vedere, visualizzare (senza assert esplicito) | `read` |

**Regole per il campo `Target`:**
- Estrai dall'Action il nome dell'elemento UI coinvolto
- Usa un nome descrittivo in italiano (es. "pulsante Accedi", "campo username", "schermata home")
- Se l'Action non specifica l'elemento, chiedi al developer prima di procedere

**Se un Expected Result è ambiguo** (es. "la pagina si carica", "l'operazione va a buon fine"):
chiedi al developer quale elemento concreto o testo visibile conferma l'esito. Non lasciare `Expected` vuoto.

**Output atteso Step 4.0:** un Test Prompt per ogni TC confermato. Mostrali tutti al developer prima di procedere ai path, in modo che possa correggerli se qualcosa è stato mal interpretato.

**Chi converte:** L'agent stesso prende il Test Prompt canale-agnostico e genera il codice specifico per il canale rilevato (Cypress per web, appium-mcp per mobile). La conversione avviene in Step 4, non in Step 4.0.

---

#### PATH MOBILE — Appium + BrowserStack App Automate

Vedi [`reference/automation-channels.md#path-mobile`](reference/automation-channels.md) per steps dettagliati (upload APK/IPA, mapping Intent→tool call appium-mcp, gestione sessioni).

**Sintesi:** `start_session` → `launch_app` → sequenza tool call per ogni step del Test Prompt → `get_screenshot_file` su FAIL → `end_session`. Una sessione per TC.

---

#### PATH WEB — Cypress + cypress-xray-plugin

Vedi [`reference/automation-channels.md#path-web`](reference/automation-channels.md) per steps dettagliati (configurazione plugin, spec template, regole chiave Jira).

**Sintesi:** Crea TE Xray prima del run (Step 4.W0) → genera spec `.cy.js` con **chiave Jira reale** nel titolo `it()` → `npx cypress run` → sync automatico via plugin.

---

### Fase 5 — Sync risultati e chiusura

Questa fase ha comportamento diverso per canale.

**Path Mobile — raccolta risultati e aggiornamento TE:**

La Test Execution per mobile va creata qui (dopo l'esecuzione), perché appium-mcp raccoglie i risultati passo per passo e li conosce solo a fine run.

Se la TE non esiste ancora (non trovata in Fase 1):
- Tier 1 (MCP): crea la TE e aggiorna ogni TC con stato PASS/FAIL e screenshot allegato
- Tier 3: mostra il report testuale completo e le istruzioni per aggiornare manualmente in Xray

Se la TE esiste già (trovata in Fase 1):
- Aggiungi i nuovi TC confermati e aggiorna gli stati. Non crearne una duplicata.

**Path Web — verifica sync automatico:**

La TE è già stata creata in Step 4.W0. Il sync risultati è automatico al termine di `npx cypress run` (gestito da cypress-xray-plugin). In questa fase verifichi solo che sia avvenuto correttamente.

Controlla nel log del run:
```
[cypress-xray-plugin] Test execution XE-456 updated successfully
```

Se il sync non è avvenuto: usa il fallback JUnit XML (vedi `reference/cypress-xray-config.md`).

**Report finale:**

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-automation |
|:---|
| 🎫 Story: `PROJ-XXX` · 🧪 Test Exec: `XE-456` [nuova / aggiornata] · 📱 Canale: `Mobile Android / Web` |
| ✅ PASS: `N TC` · ❌ FAIL: `N TC` · ⏭️ SKIP: `N TC` · 🔄 Xray sync: `Completato / CSV generato` |
| **▼ Azione** |
| 💡 Perche': Report finale esecuzione automation test |
| 🚫 Se NO: Nessun report generato |

---

## Limiti Operativi

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Tentativi fix per errore | 2 | Fermati. Diagnosi diversa necessaria. |
| File modificati per singolo step | 5 | Se devi toccare piu' file, decomponi in sub-task. |
| Output max per raccomandazione | 200 righe | Prioritizza. Top 5 issue, non lista esaustiva. |

---

## REQUIRED SUB-SKILL: siae-tdd

Implementa ogni test E2E seguendo il ciclo `siae-tdd` (test fallente, poi implementazione).

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "Automatizza tutto con Automazione=Y, non serve valutare il ROI" | Automatizzare TC con 15 step o logica ambigua genera test fragili che si rompono a ogni release. Il ROI serve per scegliere cosa vale la manutenzione. |
| "La TL non esiste ancora, parto da zero" | Cerca sempre prima in Xray. Una TL potrebbe esistere da un sprint precedente o da un'altra sessione siae-qa. Non sovrascrivere lavoro fatto. |
| "Il developer non deve rivedere la lista, auto-approvo" | Il developer conosce la complessita' UI e i rischi di manutenzione. La proposta ROI e' un'ipotesi — la conferma e' obbligatoria. |
| "Genero i test per tutti i TC, poi il developer decide" | Generare test non selezionati e' spreco. La selezione avviene PRIMA della generazione. |
| "Il test E2E sostituisce il TC manuale in Xray" | No. Il test automatizzato aggiorna lo stato del TC manuale nella Test Execution. Il TC manuale resta — e' la fonte di verita'. |
| "Non serve la Test Execution di automation separata" | Serve. Mescolare risultati manuali e automatizzati nella stessa TE rende i report Xray illeggibili. |
| "Il test passa in locale, non serve BrowserStack" | BrowserStack esegue su device e browser reali. Un test che passa in locale puo' fallire su Android 12 Samsung o Safari iOS. |
| "Questo scenario lo testo a mano, e' piu' veloce che scrivere il test" | Un test manuale non si ripete. Un test E2E gira su ogni PR, ogni notte, su ogni ambiente. Il costo di scrittura si ammortizza al terzo run. |
| "Non ho tempo per automatizzare ora, lo faccio nel prossimo sprint" | Il debito di automation si accumula: piu' TC manuali si accumulano, piu' costoso e' recuperare. I bug di regressione trovati in produzione costano 10x di un test automatizzato scritto ora. |
| "Il sync con Xray e' opzionale, basta avere i test che passano" | Senza sync Xray i manager non vedono la copertura, le audit falliscono e i TC restano in stato 'Non eseguito' anche se il test verde gira in CI. La tracciabilita' Story→TC→Execution e' un requisito SIAE. |
| "Configuro la CI pipeline dopo il rilascio, ora ho fretta" | Una pipeline non configurata significa che i test E2E non proteggono main. Un bug introdotto passa inosservato fino al collaudo. Il gate CI e' la rete di sicurezza: va tesa prima, non dopo la caduta. |
| "I test E2E sono lenti, preferisco unit test" | Gli unit test non validano i flussi utente reali end-to-end. Un'app con 100% unit test puo' avere il login rotto in produzione. I due livelli sono complementari, non alternativi. |
| "Non sincronizo con Xray perche' la chiave Jira e' cambiata" | Aggiorna la mappatura nel titolo it() e riesegui. Non sincronizzare lascia la Test Execution con risultati obsoleti e invalida la reportistica di sprint. |

---

## CHECKLIST DI VERIFICA

- [ ] Canale rilevato (mobile/web)
- [ ] TL Xray esistente cercata prima di procedere
- [ ] Test Execution automation esistente verificata (non creare duplicati)
- [ ] ROI calcolato per ogni TC della TL
- [ ] Proposta automation presentata al developer con punteggio e ragionamento
- [ ] Lista confermata dal developer (con eventuali aggiunte o rimozioni)
- [ ] Test E2E generati solo per i TC nella lista confermata
- [ ] Test eseguiti (appium-mcp o `npx cypress run`)
- [ ] Screenshot allegati ai TC falliti
- [ ] Risultati sincronizzati in Xray TE o CSV prodotto per import manuale

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Setup framework E2E (Playwright/Cypress) | 🟢 Sicuro | No |
| Scrittura test automatizzati | 🟢 Sicuro | No |
| Esecuzione test E2E in locale | 🟡 Medio | Si |
| Configurazione pipeline CI/CD | 🟡 Medio | Si |
| Push configurazione CI su repository | 🔴 Alto | Si |
| Abilitazione gate automatico su PR | 🔴 Alto | Si |

---

## VINCOLI NON NEGOZIABILI

1. **Cerca la TL esistente in Xray prima di qualsiasi altra operazione** — non assumere che non esista
2. **Non generare test senza lista confermata dal developer** — la proposta ROI è un suggerimento, la scelta finale è del developer
3. **La Test Execution automation è separata da quella manuale** — non sovrascrivere risultati manuali
4. **Nessun TC marcato PASS senza esecuzione effettiva** — PASS = test eseguito e superato
5. **Il titolo `it()` in Cypress deve usare la chiave Jira reale del TC (es. `PROJ-456:`)** — il plugin non può fare il match con un ID sequenziale `TC-{N}`. Usa sempre la chiave dalla mappatura siae-qa.
6. **BrowserStack App Automate per i risultati ufficiali Xray** — non usare emulatori locali
7. **Non modificare `Automazione` da Y a N se il test fallisce** — un fallimento è un bug, non un cambio di scope

---

## QUANDO SEI BLOCCATO

| Problema | Soluzione |
|----------|-----------|
| TL non trovata con JQL | Chiedi al developer la chiave del Test Plan o del Test Set Xray |
| appium-mcp non trova l'elemento | Chiedi al developer l'accessibility ID. Se non esiste, suggerisci di aggiungerlo al codice. |
| BrowserStack: errore upload artefatto | Verifica formato (APK signed, IPA con provisioning profile Ad Hoc/Enterprise) |
| cypress-xray-plugin non matcha il TC | Verifica che il titolo `it()` contenga la chiave Jira reale (es. `PROJ-456:`) e non `TC-{N}:`. Verifica anche che `testExecutionIssueKey` esista in Xray e non sia in stato chiuso. |
| Test Execution Xray non si aggiorna | Verifica `XRAY_CLIENT_ID` + `XRAY_CLIENT_SECRET`. Se scaduti, rigenera il token Xray Cloud. |
| TC ha ROI basso ma il developer vuole automatizzarlo | Segnala il rischio manutenzione, poi procedi — la decisione finale spetta al developer |
