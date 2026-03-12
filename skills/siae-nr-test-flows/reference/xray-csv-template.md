# Xray CSV Template — nr-test-flows

Template CSV per esportare la test list dei flussi UI in Xray Cloud (Tier 3).
Formato identico a `siae-qa/reference/xray-csv-template.md` con adattamenti per UI flows.

---

## Header Esatto

```
ID;Test  Type;Team Competenza;ID JIRA Story;User Story Description;Scenario (descrizione);Step scenario;Action;Expceted Result;Data;Automazione;NRT
```

**Note critiche:**
- `Test  Type` ha **due spazi** tra `Test` e `Type` — non correggere, è il formato Xray SIAE
- `Expceted Result` — **typo storico mantenuto** per compatibilità import Xray SIAE
- Separatore: `;` (punto e virgola) — mai virgola, mai tab
- Encoding: UTF-8 senza BOM

---

## Colonne

| Colonna | Tipo | Obbligatorio | Note |
|---------|------|-------------|------|
| `ID` | Intero | Sì | Numero sequenziale TC. Righe con stesso ID = stesso TC, step multipli |
| `Test  Type` | Stringa | Sì | `Manual` (due spazi in `Test  Type`) |
| `Team Competenza` | Stringa | No | `QA` |
| `ID JIRA Story` | Stringa | Sì | Es. `PROJ-123` — Story collegata. Per frontend flows: story della feature o epic |
| `User Story Description` | Stringa | Sì (prima riga) | Summary della Story. Solo nella prima riga del TC |
| `Scenario (descrizione)` | Stringa | Sì (prima riga) | Titolo TC con prefisso sezione. Solo nella prima riga |
| `Step scenario` | Intero | Sì | Numero step (1, 2, 3...) |
| `Action` | Stringa | Sì | Azione utente o sistema in questo step |
| `Expceted Result` | Stringa | Sì | Risultato atteso — **typo originale mantenuto** |
| `Data` | Stringa | No | Dati di test specifici. Vuoto se non necessario |
| `Automazione` | Stringa | Sì | `Y` se esiste test automatizzato (Cypress/Appium), `N` altrimenti |
| `NRT` | Stringa | Sì | `Y` (default Non-Regression Test) |

---

## Formato Titolo Scenario per UI Flows

Per i test case di UI flows, il titolo Scenario usa questa convenzione:

```
[Sezione] [Prefisso categoria] Descrizione flusso

Esempi:
  "Autenticazione — Login con credenziali valide"
  "Autenticazione — [NEG] Login con password errata"
  "Dashboard — [EDGE] Visualizzazione senza dati"
  "Gestione Utenti — [PROFILO] Creazione da utente non-admin"
```

**Prefissi:**
- _(nessuno)_ = happy path
- `[NEG]` = scenario negativo
- `[EDGE]` = edge case
- `[PROFILO]` = profilazione/ruolo

---

## Regole Multi-Step per UI Flows

Ogni azione utente è uno step. Tipica struttura step per un flusso web:

```
Step 1: Navigazione alla pagina (o pre-condizione di stato)
Step 2: Inserimento dati / interazione con il componente
Step 3: Azione principale (click button, submit form)
Step 4: Verifica risultato / redirect atteso
```

Per flussi mobili (Ionic/Flutter):

```
Step 1: Apertura app / navigazione alla schermata
Step 2: Interazione con elemento UI
Step 3: Azione principale (tap, swipe, input)
Step 4: Verifica risultato / navigazione attesa
```

---

## Esempio Completo — UI Flow CSV

Test case per la sezione Autenticazione di un'app Vue.js.

```csv
ID;Test  Type;Team Competenza;ID JIRA Story;User Story Description;Scenario (descrizione);Step scenario;Action;Expceted Result;Data;Automazione;NRT
1;Manual;QA;PROJ-100;Come utente voglio accedere all'applicazione con le mie credenziali;Autenticazione — Login con credenziali valide;1;Navigare all'URL dell'applicazione;La pagina di login viene visualizzata con i campi username e password;;N;Y
1;;;;;;2;Inserire username e password validi negli appositi campi;I campi accettano l'input. Nessun errore di validazione mostrato;username: utente.test@siae.it / password: Password1!;N;Y
1;;;;;;3;Cliccare il pulsante "Accedi";Il sistema autentica l'utente e reindirizza alla home page;;N;Y
1;;;;;;4;Verificare la home page;L'utente è autenticato: nome utente visibile nell'header, menu navigazione principale accessibile;;N;Y
2;Manual;QA;PROJ-100;Come utente voglio accedere all'applicazione con le mie credenziali;Autenticazione — [NEG] Login con password errata;1;Navigare all'URL dell'applicazione;La pagina di login viene visualizzata;;N;Y
2;;;;;;2;Inserire username valido e password errata;I campi accettano l'input;username: utente.test@siae.it / password: PasswordErrata;N;Y
2;;;;;;3;Cliccare il pulsante "Accedi";Viene visualizzato il messaggio di errore "Credenziali non valide". L'utente rimane sulla pagina di login. Nessun redirect;;N;Y
3;Manual;QA;PROJ-100;Come utente voglio accedere all'applicazione con le mie credenziali;Autenticazione — [NEG] Login con campi vuoti;1;Navigare all'URL dell'applicazione;La pagina di login viene visualizzata;;N;Y
3;;;;;;2;Lasciare i campi username e password vuoti e cliccare "Accedi";Vengono mostrati i messaggi di validazione obbligatori per entrambi i campi. Il form non viene inviato;;N;Y
4;Manual;QA;PROJ-100;Come utente voglio accedere all'applicazione con le mie credenziali;Autenticazione — [EDGE] Accesso dopo 3 tentativi falliti;1;Eseguire 3 login consecutivi con credenziali errate;Ogni tentativo mostra il messaggio "Credenziali non valide";;N;Y
4;;;;;;2;Tentare un 4° accesso con credenziali corrette;L'account risulta bloccato. Viene mostrato il messaggio di blocco account con istruzioni di recupero;;N;Y
5;Manual;QA;PROJ-100;Come utente voglio accedere all'applicazione con le mie credenziali;Autenticazione — [PROFILO] Login come amministratore;1;Navigare all'URL dell'applicazione;La pagina di login viene visualizzata;;N;Y
5;;;;;;2;Inserire credenziali di un utente con ruolo amministratore;I campi accettano l'input;username: admin@siae.it / password: AdminPass1!;N;Y
5;;;;;;3;Cliccare "Accedi";Il sistema autentica e reindirizza alla dashboard amministrativa (/admin/dashboard), non alla home standard;;N;Y
```

---

## Esempio — Flusso Mobile (Ionic + Angular)

```csv
ID;Test  Type;Team Competenza;ID JIRA Story;User Story Description;Scenario (descrizione);Step scenario;Action;Expceted Result;Data;Automazione;NRT
10;Manual;QA;PROJ-200;Come utente mobile voglio navigare tra le sezioni dell'app via tab bar;Tab Navigation — Navigazione tab Home → Profilo;1;Aprire l'applicazione su dispositivo mobile;L'app si avvia sulla tab Home. La tab bar è visibile in fondo allo schermo con le icone delle sezioni;;N;Y
10;;;;;;2;Tappare sull'icona "Profilo" nella tab bar;La schermata Profilo viene visualizzata. L'icona "Profilo" nella tab bar risulta evidenziata (active state);;N;Y
10;;;;;;3;Tappare nuovamente sull'icona "Profilo" già attiva;La schermata si aggiorna o torna al top della lista (scroll to top behaviour);;N;Y
```

---

## Come Importare in Xray

1. In Jira, vai alla sezione **Xray** nel menu di navigazione
2. Seleziona **Test** → **Import**
3. Scegli il formato **CSV**
4. Carica il file CSV generato
5. Verifica la mappatura colonne nella schermata di preview
6. Conferma l'import

I Test Case vengono creati come issue Xray di tipo `Test`, collegati alla Story nel campo `ID JIRA Story`.

---

## Valori di Default

| Campo | Default | Quando cambiare |
|-------|---------|-----------------|
| `Automazione` | `N` | `Y` solo se esiste un test Cypress o Appium che copre esattamente questo scenario |
| `NRT` | `Y` | `N` solo per TC di feature completamente nuove senza baseline da proteggere |
| `Team Competenza` | `QA` | Modifica raramente — solo se il TC è di competenza Dev o Ops |
| `Data` | (vuoto) | Compila con dati specifici per step che richiedono input precisi |

---

## Typos e Note di Compatibilità

| Campo CSV | Nota |
|-----------|------|
| `Test  Type` | Due spazi tra `Test` e `Type` — mantenere per compatibilità import SIAE |
| `Expceted Result` | Typo storico — mantenere esattamente così in ogni CSV generato |

Questi due "errori" sono intenzionali: corrispondono al template originale dell'importatore Xray SIAE e non devono essere corretti.
