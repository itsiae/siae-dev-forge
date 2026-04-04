---
name: siae-robot-framework
description: >
  Use when: file .robot/.resource aperti/creati/modificati, errori Appium/BrowserStack nel
  terminale, porting Android↔iOS, refactor o debug test RF mobile. NOT per Cypress/web
  (→ siae-automation) o bug codice applicativo non-RF (→ siae-debugging).
backbone_role: specialist
backbone_stage: tdd
hard_gate: false
---

# SIAE Robot Framework — Appium Mobile Test Automation

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🔨 DevForge · SIAE ROBOT FRAMEWORK                  ║
║         "Il codice si forgia. Il developer cresce."              ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Rigid | **Fase SDLC:** 4. Implementation / 5. Testing

---

## LA LEGGE DI FERRO

```
NESSUNA AZIONE SU FILE .ROBOT O .RESOURCE SENZA INTENT DETECTION E KNOWLEDGE ACQUISITION COMPLETATI
```

<EXTREMELY-IMPORTANT>
Stai per scrivere un locatore senza dump o file di riferimento disponibile?
FERMATI. Un locatore senza base = test che fallisce al primo run. Dichiara LOCATORE MANCANTE.

Stai per produrre codice RF prima di classificare lo scenario?
FERMATI. Lo scenario determina il workflow. Classificalo prima.

Stai per usare Sleep senza commento o xpath posizionale?
FERMATI. Questi sono anti-pattern bloccanti. Vedi §BP in reference/best-practices.md.
</EXTREMELY-IMPORTANT>

---

## Quando si Applica

**Attivazione automatica su:**
- Qualsiasi file `.robot` o `.resource` aperto, creato, modificato
- Errore nel terminale proveniente da Appium, robot, pabot, AppiumLibrary
- Errore di sessione BrowserStack (BS) visibile nel log
- Messaggio utente con: "crea test", "porta su iOS/Android", "refactor .robot", "porting", "debug test mobile"

**Non si applica:**
- Test Cypress, Playwright, test web → `siae-automation`
- ROI Xray, Test Execution, sync risultati → `siae-automation`
- Bug su codice applicativo (non sui test) → `siae-debugging`

---

## ALGORITMO PRINCIPALE

Esegui sempre in questo ordine. Non saltare step.

### Step 1 — Intent Detection

🟢 SICURO

Classifica lo scenario leggendo file aperti, messaggio utente, errori presenti:

| Scenario | Segnali | Workflow |
|----------|---------|----------|
| **A — Creazione** | File .robot assente o vuoto; nessun Page resource per quella pagina | [reference/scenarios-creation-porting.md §A](reference/scenarios-creation-porting.md) |
| **B — Manutenzione** | Test esistente da modificare (senza errore attivo); logica da aggiornare | [reference/scenarios-maintenance-refactor.md §B](reference/scenarios-maintenance-refactor.md) |
| **C — Porting** | File Android esiste, manca iOS (o viceversa); richiesta esplicita porting | [reference/scenarios-creation-porting.md §C](reference/scenarios-creation-porting.md) |
| **D — Refactor** | Test funzionante ma non conforme alle best practice | [reference/scenarios-maintenance-refactor.md §D](reference/scenarios-maintenance-refactor.md) |
| **E — Debug** | Stack trace Appium, `SessionNotCreatedException`, `NoSuchElementException`, report BS fallito | [reference/debug-engine.md](reference/debug-engine.md) |

**Tie-breaking:**
- Ambiguo A/C: esiste già un file .robot per la stessa feature in altra piattaforma? → C, altrimenti → A
- Ambiguo A/B: il file .robot esiste ma è quasi vuoto (solo `*** Settings ***`)? → A (completamento). Il file .robot esiste e ha test case? → B (manutenzione). **Non creare un secondo Page resource** se `*Page.resource` esiste già.
- Ambiguo B/E: c'è un errore attivo nel terminale o nel log? → E, altrimenti → B. **Se lo scenario cambia da B a E durante l'esecuzione, aggiorna il campo scenario nell'OUTPUT DELLA SKILL.**
- Ambiguo B/D: il test fallisce? → B. Il test passa ma ha anti-pattern? → D. Il test è skippato con anti-pattern strutturali? → D.
- Ambiguo C/D: il file iOS esiste ma contiene xpath Android copiati? → C (porting da rifare), non D.

---

### Step 2 — Knowledge Acquisition

🟢 SICURO

Prima di produrre qualsiasi codice, raccogli conoscenza in questo ordine:

1. **File esistenti** — leggi tutti i `*Page.resource` presenti. I locatori esistenti rivelano pattern approvati.
2. **Dump esistenti** — cerca `tests/dumps/<PageName>Dump.xml` e varianti iOS/BS.
3. **Inferenza** — se ci sono N Page resource della stessa app, i pattern UI sono noti. Usa questa conoscenza prima di acquisire dump.
4. **Acquisizione dump** (solo se 1-3 sono insufficienti per elementi specifici) → vedi [reference/dump-acquisition.md](reference/dump-acquisition.md)

**Regola blocco locatori:** se non riesci a determinare un locatore conforme, dichiara:
```
LOCATORE MANCANTE: <NomeElemento>
Motivo: <perché non è derivabile>
Azione: acquisizione dump per <PageName> tramite reference/dump-acquisition.md
```
**Non scrivere placeholder `# TODO: locatore` nei file.**

---

### Step 3 — Scenario Execution

🟡 MEDIO — Mostra pre-flight card prima di creare o modificare file

| 🟡 MEDIO (reversibile) — 🔨 DevForge · siae-robot-framework |
|:---|
| 🎯 Scenario: `A / B / C / D / E` · 📂 File target: `<path file>` |
| 🧠 Conoscenza usata: `file esistenti / dump esistenti / dump acquisito via <canale>` |
| **▼ Azione** |
| 1. ✏️ Applica il workflow dello scenario rilevato (vedi reference/) |
| 💡 Perche': ogni scenario ha sequenza operativa e vincoli diversi |
| 🚫 Se NO: nessun file viene creato o modificato |

Segui il workflow specifico in reference/ per lo scenario rilevato.

---

### Step 4 — Best Practice Layer

🟢 SICURO

Applica su tutto ciò che produci o modifichi. Nessuna eccezione.

Regole principali (dettaglio in [reference/best-practices.md](reference/best-practices.md)):
- **BP-1** Gerarchia locatori: `accessibility_id` > `resource-id` > `xpath semantico` > `class chain (iOS)` > `predicate string (iOS)`
- **BP-2** Nessun `Sleep` senza commento esplicito con motivazione
- **BP-3** Nessuna credenziale hardcoded — sempre da variabile d'ambiente
- **BP-4** `[Documentation]` su ogni keyword con >2 step o argomenti
- **BP-5** Tag obbligatori: `[Tags]    <tipo>    <feature>    <platform>`
- **BP-6** Naming: `TCxx_NomeCamelCase.robot` | `NomePaginaPage.resource` | `${PAGENAME_ELEMENT_DESC}`
- **BP-7** BrowserStack: usa sempre l'SDK (`browserstack-sdk robot/pabot`). MAI credenziali nelle capabilities del test — vanno in `browserstack.yml` via env vars.

---

### Step 5 — Verify

🟡 MEDIO

- **In debug (E):** ri-esegui il test dopo ogni fix. Leggi l'output completo. Vedi loop di verifica in [reference/debug-engine.md §LOOP](reference/debug-engine.md).
- **In creazione/modifica:** autorevisa contro la checklist BP-4 + D.1 di [reference/scenarios-maintenance-refactor.md](reference/scenarios-maintenance-refactor.md).
- **Prima di dichiarare un file "pronto" o un test "funzionante":** invoca `siae-verification` (REQUIRED SUB-SKILL — vedi sezione dedicata in fondo).

**Nota test-first per RF:** `siae-tdd` si applica al codice applicativo (Java/TypeScript/Python), non ai file `.robot`. La qualità dei test RF è garantita da questa skill tramite BP-1..6 + Knowledge Acquisition obbligatoria. Nessun ciclo RED-GREEN-REFACTOR separato è richiesto per i file `.robot`.

---

## OUTPUT DELLA SKILL

Dopo ogni operazione, dichiara:
```
SKILL ATTIVA — scenario: <A|B|C|D|E>
Conoscenza usata: <fonte>
File prodotti/modificati: <lista>
Best practice applicate: <lista BP>
Warning: <se presenti>
```

Se bloccata:
```
SKILL BLOCCATA
Motivo: <spiegazione precisa>
Per sbloccare: <azione specifica>
```

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "Scrivo un locatore plausibile e poi sistemo" | Un locatore inventato = test che fallisce silenziosamente. Dichiara LOCATORE MANCANTE. |
| "Il dump e' vecchio, ma i locatori sono stabili" | I locatori cambiano ad ogni release. Acquisisci dump aggiornato se l'elemento e' nuovo. |
| "Sleep 2s funziona, e' piu' veloce" | Sleep rende il test lento e non diagnosticabile. Usa Wait Until Element Is Visible. |
| "Copio xpath Android su iOS, e' lo stesso" | Le classi UI Android e iOS sono diverse. xpath posizionale Android non esiste su iOS. |
| "L'accessibility_id non c'e', uso xpath con indice" | xpath posizionale rompe a ogni minima modifica UI. Richiedi accessibility_id al dev. |
| "Salto Knowledge Acquisition, conosco l'app" | La stessa pagina puo' avere locatori diversi tra versioni. Verifica sempre. |
| "Non serve la pre-flight, e' solo una modifica piccola" | Ogni modifica a un Page resource impatta tutti i test che lo importano. |
| "Passo le credenziali BS nelle capabilities, e' piu' semplice" | Le credenziali nel codice = secret in versioning. Usa sempre browserstack.yml + env vars con l'SDK. |
| "Scrivo la keyword nel .robot, e' piu' comodo" | Nessuna keyword nei .robot. Solo nei Page resource. Questo e' non negoziabile. |
| "Provo un fix, se non funziona ne provo un altro" | Tre fix senza root cause = stallo. Dichiara SKILL BLOCCATA e chiedi dump/logcat. |
| "Posso ignorare il [Documentation] per keyword semplici" | Una keyword senza documentation non e' diagnosticabile in debug. Scrivila sempre. |

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Lettura file .robot / .resource / dump | 🟢 Sicuro | No |
| Classificazione scenario (Intent Detection) | 🟢 Sicuro | No |
| Knowledge Acquisition (lettura dump, inferenza) | 🟢 Sicuro | No |
| Acquisizione dump (ADB / appium-mcp) | 🟡 Medio | Si |
| Creazione / modifica file .robot o .resource | 🟡 Medio | Si |
| Esecuzione test in locale (robot / pabot) | 🟡 Medio | Si |
| Acquisizione dump via BrowserStack | 🔴 Alto | Si |
| Modifica common.resource | 🔴 Alto | Si |

---

## Vincoli

1. **MAI** produrre un locatore senza base (dump, file esistente, o inferenza verificata)
2. **MAI** scrivere keyword nei file .robot — solo nei Page resource
3. **MAI** copiare xpath Android su iOS — le classi UI sono strutturalmente diverse
4. **MAI** hardcodare credenziali o dati sensibili — sempre da variabile d'ambiente
5. **SEMPRE** applicare BP-1..6 su tutto ciò che viene prodotto o modificato
6. **SEMPRE** dichiarare SKILL BLOCCATA dopo 3 tentativi di fix senza progresso
7. **PRE-FLIGHT OBBLIGATORIA** per ogni creazione/modifica file e acquisizione dump

---

## Limiti Operativi

| Vincolo | Limite | Se superato |
|---------|--------|-------------|
| Tentativi fix per stesso errore | 3 | Dichiara SKILL BLOCCATA — vedi reference/debug-engine.md §STALLO |
| File modificati per singola operazione | 5 | Decomponi in operazioni separate |
| Iterazioni acquisizione dump | 1 per canale | Se fallisce, passa al canale successivo nella fallback chain |
| Versione RF minima supportata | RF ≥ 5.0 | `RETURN` e `IF` inline non disponibili su RF < 5. Segnalare incompatibilità. |

---

## REQUIRED SUB-SKILL: siae-verification

Prima di dichiarare qualsiasi test "funzionante" o file "pronto", invoca `siae-verification`.

---

## Risorse Aggiuntive

- [reference/scenarios-creation-porting.md](reference/scenarios-creation-porting.md) — Scenario A (creazione) e C (porting Android↔iOS)
- [reference/scenarios-maintenance-refactor.md](reference/scenarios-maintenance-refactor.md) — Scenario B (manutenzione) e D (refactor + audit checklist)
- [reference/debug-engine.md](reference/debug-engine.md) — Debug engine: CATEGORIA 1-4, loop di verifica, gestione stallo
- [reference/dump-acquisition.md](reference/dump-acquisition.md) — Fallback chain ADB → appium-mcp → BrowserStack
- [reference/best-practices.md](reference/best-practices.md) — BP-1..6 con esempi di codice RF
- [reference/browserstack-sdk-config.md](reference/browserstack-sdk-config.md) — `browserstack.yml` Android + iOS, run commands SDK, upload app
- [reference/common-resource.md](reference/common-resource.md) — common.resource canonico SIAE (approccio SDK-transparent)
