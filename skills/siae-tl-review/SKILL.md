---
name: siae-tl-review
version: 1.0.0
last_modified: 2026-06-03
description: >
  Revisiona Test List manuali (CSV/XLS/XLSX) rispetto ai requisiti di progetto,
  generando una Matrice di Tracciabilita' Requisiti (RTM) e un report di revisione
  ISTQB. Usa questa skill quando l'utente carica o menziona una test list, test
  case list, TL, file di test, scenari di test, o chiede di "revisionare i test",
  "verificare la copertura dei requisiti", "generare la RTM", "analizzare i test
  case", "controlla se i test coprono le story Jira", "verifica gli edge case",
  "traccia i requisiti sui test". Attivare anche quando l'utente nomina file
  formato SIAE-BTP con colonne ID/Test Type/Team Competenza/ID JIRA Story/Action/
  Expected Result. Richiede interazione guidata multi-fase: NON procedere
  autonomamente senza conferma esplicita a ogni fase.
compatibility:
  optional_mcps:
    - atlassian
  file_types:
    - csv
    - xls
    - xlsx
    - pdf
    - docx
    - md
    - txt
---

# TL Review — Test List Review & Requirements Traceability

> **Tipo:** Rigid Interactive | **Fase SDLC:** 5. Testing / QA Review
> **Standard:** ISTQB Foundation, IEEE 829, ISO/IEC/IEEE 29119

## Scopo

Guidare un QA analyst o Test Lead SIAE in una revisione strutturata e rigorosa di
una Test List (TL) manuale rispetto ai requisiti di progetto, producendo:

1. Una **Matrice di Tracciabilita' Requisiti (RTM)** bidirezionale.
2. Un **Report di Revisione ISTQB** con gap di copertura espliciti.
3. Raccomandazioni prioritizzate per livello di rischio.

Il contesto operativo e' SIAE-BTP: il QA esegue i test **manualmente su browser
Chrome**, senza privilegi tecnici (no deploy, no DB, no terminale). La skill deve
proteggere questa invariante in modo difensivo.

## La regola d'oro

```
NESSUNA RTM SENZA CRITERI DI ACCETTAZIONE CONFERMATI A CONFIDENCE >= 95%.
NESSUN TC "APPROVATO" SE NON E' ESEGUIBILE MANUALMENTE DA BROWSER CHROME.
```

Una RTM costruita su criteri inventati e' peggio di nessuna RTM: induce falsa
sicurezza. Lo stesso vale per TC che richiedono accesso a strumenti tecnici
indisponibili al QA manuale.

---

## GUARDRAIL (non negoziabili)

I guardrail seguenti sono **vincoli forti**: violarli significa produrre un
output che induce in errore il team QA. Spiegali all'utente se chiede di
saltarli, ma non aggirarli.

### **G1 — Sequenzialita' delle fasi**
**Mai procedere alla fase successiva senza aver completato e fatto confermare
quella corrente.** Il flusso e' Fase 0 → 1 → 2 → 3 → 4 → 5. A ogni transizione,
mostra un riepilogo e chiedi conferma esplicita ("Confermi di procedere alla
Fase N?"). Motivazione: prevenire revisioni incomplete che il QA "scopre" solo
in fase di esecuzione.

### **G2 — Vietato inventare criteri di accettazione**
**Se un requisito e' ambiguo, fai challenge all'utente fino a confidence >= 95%
su tutti i criteri di accettazione (AC), PRIMA di procedere.** Non riempire i
buchi con assunzioni "plausibili". Motivazione: la RTM e' uno strumento di
audit; basarla su AC inventati e' un difetto strutturale che propaga errori in
tutte le fasi successive.

**Lo stesso vincolo si applica ai TC proposti nelle Fasi 4 e 5.**
Se in F4 (analisi BVA/EP, criterio 4) si identifica l'assenza di un TC per un
boundary value o una classe di equivalenza, **NON generare il TC come artefatto
concreto**. Documentare il gap come raccomandazione in F5 con label
`[IPOTESI — richiede conferma QA]`, ancorandola esplicitamente all'AC che la
origina. Se l'AC non e' nel materiale fornito, il gap e' "Non verificabile dal
materiale".

### **G3 — Autenticazione Jira obbligatoria**
**Se l'utente sceglie l'opzione Jira ma l'MCP Atlassian non e' configurato,
risolvi il Personal Access Token (PAT) Jira PRIMA di qualsiasi chiamata API**,
seguendo la policy a 3 livelli (vedi Fase 1 Opzione A):
1. Env var `JIRA_PAT` / `ATLASSIAN_PAT` se gia' esportata.
2. File `~/.config/siae-tl-review/credentials` (permission `0600`) se l'utente
   l'ha salvato in una sessione precedente.
3. Prompt interattivo in chat (in-session, scartato a fine sessione).

Mai procedere senza autenticazione valida. Motivazione: sicurezza,
audit-traceability, prevenzione di chiamate cieche a sistemi enterprise.

### **G8 — PAT non in chiaro negli artefatti**
**Il valore del PAT Jira non deve MAI comparire in chiaro in:**
- Report finale (`siae-tl-review-report-*.md`).
- File RTM salvati in `./QA-REVIEW/`.
- Output mostrati a video oltre la riga di conferma "PAT ricevuto, lunghezza
  N caratteri, prefisso `XXXX...`" (mostra solo i primi 4 + lunghezza).
- Log di errore in caso di chiamata API fallita (mascherare con `***`).

Se l'utente sceglie di **persistere** il PAT (livello L2), la skill deve:
1. Creare `~/.config/siae-tl-review/` con `mkdir -p` e permission `0700`.
2. Scrivere `~/.config/siae-tl-review/credentials` con permission `0600`.
3. Mostrare a video solo: `PAT salvato in ~/.config/siae-tl-review/credentials
   (permission 0600). Per rimuoverlo: rm ~/.config/siae-tl-review/credentials`.

Motivazione: il PAT e' un secret enterprise SIAE; un leak nel transcript di
sessione (che puo' essere condiviso, salvato, indicizzato) e' un incidente
di sicurezza non recuperabile per rotazione del token.

### **G9 — Scope gate per TL multi-team/multi-sprint**
**In presenza di TL con team distinti (colonna "Team Competenza") o Jira Story /
Sprint di iterazioni multiple, NON analizzare l'intera TL senza aver prima
chiesto all'utente quale sottoinsieme esaminare.** Prima di procedere alla Fase
1, presentare l'elenco dei Team Competenza distinti e delle Jira Story / Sprint
rilevati, e chiedere se analizzare tutto o un sottoinsieme.

Se l'utente sceglie un sottoinsieme, escludere i TC fuori scope **prima** della
generazione della RTM. I TC esclusi NON compaiono nella vista inversa: non sono
orfani — sono fuori scope. Documentare il filtro applicato nell'intestazione del
report (sezione 1 "Scope della Revisione") e nel naming degli artefatti (C2).

Motivazione: una TL multi-team ingurgitata integralmente produce TC orfani da
scope errato indistinguibili da orfani reali, gonfiando i gap con falsi positivi
strutturali che il team confonderà con gap reali.

### **G4 — Eseguibilita' manuale come precondizione di approvazione**
**Nessun Test Case puo' essere "approvato" se richiede:**
- accesso a deploy/CI/CD,
- accesso diretto a database (DML/DDL),
- accesso al terminale o filesystem del server,
- chiamate API dirette senza UI,
- strumenti di sviluppo (debugger, log server-side),
- qualsiasi privilegio non disponibile a un QA manuale su Chrome.

Questi TC vanno **flaggati `NON ESEGUIBILE MANUALMENTE`**, e per ciascuno la
skill deve:
1. Proporre una **riformulazione eseguibile da UI** se esiste un percorso
   alternativo (es. verificare lo stato finale tramite una pagina della webapp
   invece di una query DB).
2. Altrimenti **escluderlo dalla coverage effettiva** e listarlo nel report.

Motivazione: il contesto operativo SIAE-BTP non prevede QA tecnici. Un TC
inesguibile e' un TC fittizio.

### **G5 — RTM bloccata su confidence < 95%**
**Non generare la RTM se anche un solo requisito ha AC con confidence < 95%.**
La skill deve elencare i requisiti incompleti e tornare in Fase 2 per chiudere
i gap. Motivazione: una RTM parziale ma silenziosamente "completa" sui falsi-OK
e' peggio di un blocco esplicito.

### **G6 — Sezione GAP DI COPERTURA sempre presente**
**Il report finale (Fase 5) deve SEMPRE contenere la sezione
`⚠️ GAP DI COPERTURA`**, anche se vuota (in tal caso scrivere "Nessun gap
rilevato" con motivazione esplicita). La sezione elenca:
- Requisiti senza almeno un TC per ogni happy path identificato.
- Edge case / casi negativi non coperti.
- Edge case / casi negativi coperti ma flaggati `NON ESEGUIBILE MANUALMENTE`.

Motivazione: il valore di una review e' nei rischi che porta in superficie,
non nei "tutto ok" rassicuranti.

### **G7 — Validazione input bloccante**
**Prima di qualsiasi ingestion, valida il file di input.** Bloccare con
messaggio chiaro se:
- Il file non e' `.csv` / `.xls` / `.xlsx`.
- Mancano le colonne obbligatorie `ID`, `Action`, `Expected Result`.
- Il file e' vuoto o ha 0 righe-dati.
- L'encoding non e' decodificabile (proporre `utf-8` / `latin-1` come fallback).

Messaggio di errore: deve includere (a) cosa manca, (b) come correggere, (c)
riferimento a `references/csv-format-spec.md`. Motivazione: gli errori
silenziosi in ingestion producono RTM falsate senza che nessuno se ne accorga.

---

## Flusso operativo a 6 fasi

> **Stile interazione:** ogni fase termina con un riepilogo + richiesta di
> conferma. Usa elenchi numerati per le scelte. Non saltare fasi anche se
> l'utente sembra impaziente: la skill esiste perche' la pressione del tempo
> e' il primo fattore di errore in una review.

### FASE 0 — Validazione e Ingestion del file (Guardrail G7)

**Obiettivo:** caricare la TL e verificarne la struttura.

**Procedura:**

1. Chiedi all'utente il path del file TL (o accetta l'allegato se presente).
2. Verifica l'estensione: `.csv`, `.xls`, `.xlsx`. Altrimenti blocca (G7).
3. Verifica le colonne obbligatorie attese (`ID`, `Action`, `Expected Result`).
   Le colonne complete attese sono documentate in
   `references/csv-format-spec.md` — leggi quel file se la struttura del file
   utente devia dal formato SIAE-BTP standard.
4. Parsa la struttura gerarchica: ogni riga con `ID` valorizzato e' un Test
   Case; le righe successive con `ID` vuoto sono **step di scenario** del TC
   precedente. Vedi `references/csv-format-spec.md` per le regole di parsing
   dettagliate, separatori (`;` standard SIAE-BTP), e gestione delle celle
   multiriga.
5. Produci un **riepilogo di ingestion** in questo formato:

```markdown
## Ingestion completata

- File: <path>
- Test Case identificati: N
- ID Jira Story distinti referenziati: M
- Step totali: S (media S/N per TC)
- Test Type rilevati: <lista>
- Team Competenza rilevati: <lista>
- ⚠️ Anomalie strutturali: <elenco o "nessuna">

**Vuoi procedere alla Fase 1 (Raccolta dei Requisiti)?**
```

6. **Scope gate (G9):** se la TL contiene Team Competenza distinti **oppure**
   Jira Story / Sprint di piu' iterazioni, mostra prima di procedere:

   ```
   Team Competenza rilevati: [lista]
   Jira Story / Sprint distinti: [lista]

   Vuoi analizzare:
   A) L'intera TL (N TC)
   B) Un sottoinsieme — indica i team e/o le story da includere
   ```

   Se l'utente sceglie B, filtra i TC **subito** e memorizza il filtro per il
   naming degli artefatti in Fase 5. I TC esclusi non compaiono nell'analisi
   ne' nella vista inversa.

7. **Stop fino a conferma esplicita** (G1).

---

### FASE 1 — Raccolta dei Requisiti

**Obiettivo:** acquisire l'elenco dei requisiti contro cui revisionare la TL.

**Presenta all'utente le 3 opzioni:**

```
1. Jira Story/Stories (recupero automatico o via PAT)
2. Documento dei Requisiti (PDF, DOCX, MD, TXT, testo incollato)
3. Chat interattiva (descrizione guidata dei requisiti)
```

#### Opzione A — Jira

1. Verifica disponibilita' MCP Atlassian (es. `mcp__atlassian__read_jira_issue`).
2. Se **disponibile**: chiedi gli Story ID (formato `BTP-123` o lista
   `BTP-123, BTP-124`). Recupera le story via API.
3. Se **non disponibile**: applica G3 + G8 — risolvi il PAT Jira con questa
   **policy a 3 livelli (in ordine di priorita'):**

   **L1 — Env var (preferito, zero interazione):**
   - Controlla `$JIRA_PAT`, poi `$ATLASSIAN_PAT`, poi `$JIRA_API_TOKEN`.
   - Se trovato: usa direttamente. A video conferma solo:
     `PAT trovato in env var <NOME>. Procedo.` (NON stampare il valore).

   **L2 — File salvato in sessione precedente:**
   - Controlla `~/.config/siae-tl-review/credentials` (formato `JIRA_PAT=<valore>`).
   - Se trovato e leggibile (permission `0600`): caricalo. A video:
     `PAT trovato in ~/.config/siae-tl-review/credentials. Procedo.`
   - Se trovato ma permission non sono `0600`: avvisa e chiedi se correggere
     (`chmod 600`) o ignorare e passare a L3.

   **L3 — Prompt interattivo (fallback):**
   - Chiedi il PAT con messaggio:
     > "L'integrazione automatica con Jira non e' attiva in questa sessione.
     > Per recuperare le story serve un Personal Access Token Jira. Puoi
     > generarlo da Jira → Profile → Personal Access Tokens.
     >
     > Incollalo qui."
   - Dopo l'input, mostra solo conferma mascherata:
     `PAT ricevuto (lunghezza N caratteri, prefisso XXXX...). Procedo.`
   - **Poi chiedi**:
     > "Vuoi salvarlo per le sessioni future in
     > `~/.config/siae-tl-review/credentials` con permission `0600`?
     > [y/N] (default: NO, scartato a fine sessione)"
   - Se l'utente conferma `y`: crea la directory con `mkdir -p ~/.config/siae-tl-review && chmod 0700 ~/.config/siae-tl-review`, poi scrivi
     il file con `chmod 0600`. Conferma con il path e l'istruzione di
     rimozione (vedi G8).
   - Se l'utente rifiuta o non risponde: usa il PAT solo in-session, non
     persistere. A fine processo, dimentica il valore (non riscriverlo nei
     report).

   Non procedere a chiamate API senza PAT valido (G3). Non rivelare il PAT
   in nessun output, log o file (G8).

#### Opzione B — Documento

1. Accetta path file (PDF, DOCX, MD, TXT) o testo incollato.
2. Estrai i requisiti funzionali in forma strutturata, una entry per requisito:

```markdown
- **R-01** — [titolo breve]
  - Descrizione: ...
  - Riferimento: <file>:<sezione/pagina>
```

#### Opzione C — Chat interattiva

1. Guida l'utente con domande mirate, un requisito alla volta:
   > "Descrivimi il primo requisito funzionale. Dopo ogni requisito ti chiedo
   > conferma prima di passare al successivo."
2. Conferma ogni requisito prima di registrarlo.

**Output di Fase 1:** lista numerata `R-01..R-NN` di requisiti, ciascuno con
descrizione e fonte. Chiedi conferma e procedi alla Fase 2.

---

### FASE 2 — Estrazione e Validazione AC (Guardrail G2, G5)

**Obiettivo:** per ogni requisito, derivare i criteri di accettazione (AC) ed
elevare la confidence a >= 95%.

**Procedura per ciascun requisito:**

1. **Estrai AC candidati** dal testo del requisito, in stile Given-When-Then o
   tabellare (vedi `references/istqb-checklist.md` sezione "AC quality
   checklist").
2. **Calcola confidence interna** (0–100%) su ciascun AC. La confidence
   considera:
   - Ambiguita' lessicale ("appropriato", "corretto", "rapido").
   - Mancanza di valori di soglia ("performante" → senza ms).
   - Assenza di definizione del comportamento di errore.
   - Casi limite non specificati.
3. **Se confidence < 95% su anche un solo AC**, formula domande di challenge
   specifiche (non generiche!). Esempi:
   > - "R-03, AC-2: il messaggio di errore deve essere visibile per quanti
   >   secondi? E' bloccante o dismissibile?"
   > - "R-05, AC-1: 'invio rapido' significa < 1 secondo, < 5 secondi, o e'
   >   misurato lato server (TTFB) vs lato utente?"
   > - "R-07: in caso di doppio invio entro 500ms, comportamento atteso? A)
   >   ignora il secondo, B) errore visibile, C) altro?"
4. **Continua finche' tutti gli AC del requisito hanno confidence >= 95%**.
5. **Mostra all'utente la lista finale degli AC confermati** e chiedi
   approvazione esplicita prima di passare al requisito successivo.

**Quando tutti i requisiti hanno AC confermati**, riepiloga in tabella:

```markdown
| Requisito | # AC | Confidence media | Stato       |
|-----------|------|------------------|-------------|
| R-01      | 3    | 98%              | ✅ Confermato |
| R-02      | 5    | 96%              | ✅ Confermato |
| ...       | ...  | ...              | ...         |
```

**Solo se TUTTI i requisiti sono `✅ Confermato`** (G5) chiedi conferma di
procedere alla Fase 3.

---

### FASE 3 — Generazione della RTM

**Obiettivo:** produrre la Matrice di Tracciabilita' bidirezionale.

**Formato obbligatorio** (vedi `references/rtm-template.md` per template
completo con esempi compilati):

```markdown
| ID Req | Descrizione | AC | TC Correlati (ID TL) | Tipo Copertura | Gap |
|--------|-------------|----|----|----------------|-----|
| R-01   | Login OK    | AC-1, AC-2 | TC-001, TC-002 | Happy Path ✅ | Nessuno |
| R-01   | Login OK    | AC-3 | TC-003 | Edge Case ⚠️ | Manca caso "password scaduta" |
| R-02   | Logout      | AC-1 | (nessuno) | Non Coperto 🔴 | TC mancante |
```

**Legenda `Tipo Copertura`:**
- `Happy Path ✅` — flusso principale coperto.
- `Edge Case ⚠️` — caso limite coperto (BVA / EP — vedi
  `references/istqb-checklist.md`).
- `Caso Negativo ❌` — flusso di errore/eccezione coperto.
- `Non Coperto 🔴` — nessun TC eseguibile manualmente per questo AC.

**Bidirezionalita':** dopo la RTM principale, produci una vista inversa
**preliminare** (solo TC orfani noti a questo punto). Avvisa esplicitamente
che la colonna Note verra' completata al termine della Fase 4:

```markdown
## Vista inversa — TC → Requisiti
> ⚠️ Colonna Note preliminare — verra' aggiornata con i flag di Fase 4
> (NON ESEGUIBILE, step incompleti, gap BVA/EP).

| TC ID | Mappato a | Note |
|-------|-----------|------|
| TC-001 | R-01.AC-1, R-01.AC-2 | |
| TC-099 | (nessuno) | ⚠️ TC orfano — nessun requisito mappato |
```

I TC orfani vanno segnalati come gap (potrebbero indicare requisiti impliciti
non documentati, oppure test obsoleti).

**La colonna Note della vista inversa viene aggiornata al termine della Fase 4**
con i flag emersi dall'analisi. Regola di aggregazione — per ogni TC:

| Condizione rilevata in F4 | Valore da inserire in Note |
|---------------------------|---------------------------|
| TC non mappato a nessun requisito | `⚠️ TC orfano` |
| TC flaggato NON ESEGUIBILE MANUALMENTE | `❌ NON ESEGUIBILE — <motivo sintetico>` |
| TC con step incompleti (Expected Result assente/generico) | `⚠️ Step incompleti — step N` |
| Gap BVA/EP documentato come [IPOTESI] in F5 | `[IPOTESI BVA/EP] — vedi F5 Raccomandazioni` |

Se un TC ha piu' evidenze, concatenarle con ` | `. Se nessuna evidenza: cella vuota.

Chiedi conferma RTM e procedi alla Fase 4.

---

### FASE 4 — Analisi di Copertura e Revisione TC (Guardrail G4)

**Obiettivo:** revisionare ogni TC della TL contro 5 criteri ISTQB. Riferimento
completo: `references/istqb-checklist.md` (BVA, EP, IEEE 829, checklist
manualita').

**Per ciascun TC, verifica:**

1. **Eseguibilita' manuale (G4):** il TC e' eseguibile da QA su Chrome senza
   privilegi tecnici? Cerca anti-pattern nel testo `Action` / `Expected Result`:
   - "esegui query SQL ...", "verifica nel DB ...", "tail dei log ...".
   - "deploy ...", "rilascia in ...", "fai ssh ...".
   - "chiama l'endpoint REST con curl ...", "Postman", "API client".
   - "apri la console developer per ...", "verifica nel network tab ...".

   Se rilevato → flagga `NON ESEGUIBILE MANUALMENTE`. Proponi riformulazione UI
   (es. "verifica nel DB" → "verifica nella sezione Storico ordini della
   webapp") o escludi dalla coverage.

2. **Completezza step (IEEE 829):** ogni step ha `Action` E `Expected Result`?
   TC con `Expected Result` vuoto / generico ("OK", "funziona") sono
   incompleti.

3. **Copertura Happy Path:** per ogni requisito esiste almeno 1 TC che
   esercita il percorso principale degli AC?

4. **Copertura Edge Case / Negativi (solo da materiale fornito):** verifica se
   nella TL esistono TC per BVA (es. lunghezza minima/massima campi) e per
   Equivalence Partitioning negativo (input invalidi, permessi insufficienti,
   timeout). Vedi `references/istqb-checklist.md` per la checklist BVA/EP.

   **Vincolo G2-esteso:** se manca un TC per un boundary value o classe di
   equivalenza, **NON generarlo e NON proporlo come artefatto concreto**.
   Documentare il gap come raccomandazione in Fase 5 con label
   `[IPOTESI — richiede conferma QA]`, ancorata all'AC che lo origina.
   Questo vincolo sovrascrive qualsiasi ragionamento applicativo plausibile:
   un TC dedotto senza requisito esplicito e' un caso inventato.

5. **Tracciabilita' (G6):** ogni TC e' presente nella RTM (Fase 3)? TC orfani
   → flag in report.

Produci una tabella di triage TC:

```markdown
| TC ID | Eseguibile? | Step OK? | Tipo | Note |
|-------|-------------|----------|------|------|
| TC-001 | ✅ | ✅ | Happy Path | |
| TC-045 | ❌ NON ESEGUIBILE | ⚠️ | Negativo | Richiede query DB. Riformulazione: verifica via UI Storico |
| TC-099 | ✅ | ❌ Expected Result vuoto | Edge | Step 3 manca atteso |
```

**Al termine della tabella triage**, aggiorna la colonna Note della vista inversa
nella RTM (`rtm-<data>.md` gia' salvata) applicando la regola di aggregazione
definita in Fase 3. Mostra la vista inversa aggiornata in chat e confirma il
salvataggio del file.

---

### FASE 5 — Report di Revisione Finale (Guardrail G6)

**Obiettivo:** consolidare tutto in un documento ISTQB-compliant.

**Persistenza artefatti — directory `./QA-REVIEW/<nome-file-TL>/`:**

Tutti gli artefatti vanno salvati in una subdirectory denominata con il nome del
file TL (senza estensione), relativa al **current working directory**:

1. Creare la directory on-demand:
   `mkdir -p ./QA-REVIEW/<nome-file-TL>/`
2. Salvare in `./QA-REVIEW/<nome-file-TL>/`:
   - `siae-tl-review-report-<YYYY-MM-DD>.md` — report finale (questa fase).
   - `rtm-<YYYY-MM-DD>.md` — RTM bidirezionale (Fase 3, gia' offerta).
   - `ac-validated-<YYYY-MM-DD>.md` — AC confermati (appendice Fase 2),
     opzionale ma raccomandato come traccia di audit.

   Esempio: file `SIAE_BTP_TestList_ClusterArancione.csv`
   → `./QA-REVIEW/SIAE_BTP_TestList_ClusterArancione/siae-tl-review-report-2026-06-03.md`

3. Se lo scope e' un sottoinsieme (filtro applicato in F0 via G9), aggiungere
   il filtro al nome della subdirectory usando doppio underscore come separatore:
   → `./QA-REVIEW/SIAE_BTP_TestList_ClusterArancione__TeamAlpha/...`

4. Se la directory esiste gia' con file dello stesso giorno: chiedere
   all'utente se sovrascrivere o usare suffisso `-<HHmm>`.

**Nessun PAT, credenziale o segreto in chiaro in questi file (G8).**

**Struttura obbligatoria** (Markdown, output in chat + salvataggio in
`./QA-REVIEW/<nome-file-TL>/siae-tl-review-report-<YYYY-MM-DD>.md`):

```markdown
# Report di Revisione Test List — [Nome Progetto] — [Data]

## Executive Summary
[max 5 righe: copertura % happy path, # gap critici, # TC non eseguibili,
rischio complessivo, raccomandazione top-1]

## 1. Scope della Revisione
- TL analizzata: <file>
- Requisiti analizzati: R-01..R-NN (fonte: Jira/Doc/Chat)
- Standard applicati: ISTQB Foundation, IEEE 829, ISO/IEC/IEEE 29119

## 2. Matrice di Tracciabilita' (RTM)
[tabella FASE 3 + vista inversa]

## 3. Analisi di Copertura
### 3.1 Happy Path Coverage
[Per ogni requisito: % AC coperti da happy path TC eseguibili]
### 3.2 Edge Case Coverage (BVA + EP)
### 3.3 Casi Negativi Coverage

## 4. ⚠️ GAP DI COPERTURA
### 4.1 Requisiti senza copertura completa degli Happy Path
### 4.2 Edge Case / Casi Negativi non coperti
### 4.3 Test Case flaggati NON ESEGUIBILE MANUALMENTE
### 4.4 Test Case orfani (non tracciati a requisiti)

## 5. Raccomandazioni ISTQB (prioritizzate)
- **CRITICO** — [azione, requisito impattato, owner suggerito]
- **ALTO** — ...
- **MEDIO** — [IPOTESI — richiede conferma QA] Manca TC per boundary value di R-NN.AC-M (campo X: lunghezza max non testata). Ancorare a R-NN.AC-M prima di aggiungere TC.
- **BASSO** — ...

## 6. Entry/Exit Criteria di Revisione
- ☑ Tutti i requisiti hanno AC a confidence >= 95%
- ☑ RTM bidirezionale prodotta
- ☑ Tutti i TC analizzati per eseguibilita' manuale
- ☑ Gap di copertura documentati
- ☐ Azioni correttive comunicate e prese in carico (TBD)

## Appendice A — Criteri di Accettazione Validati
[Per ogni R-NN: lista AC confermati durante challenge]

## Appendice B — Glossario e Riferimenti
- ISTQB Foundation — Sez. 2.3 (Static Testing)
- IEEE 829 — Test Documentation
- ISO/IEC/IEEE 29119-3 — Test Documentation
```

Sezione 4 (G6) sempre presente, anche se vuota — in tal caso scrivere
"Nessun gap rilevato. Motivazione: ..." con argomentazione esplicita.

**Cross-link obbligatori tra artefatti:**

Ogni sezione del report che cita TC o AC deve includere un anchor link esplicito:
- `[R-01](rtm-<data>.md#r-01)` per riferimenti a requisiti nella RTM.
- `[TC-045](#tc-045)` per riferimenti a singoli TC nella tabella triage.

La RTM salvata in `rtm-<YYYY-MM-DD>.md` deve avere un header `### <ID Req>` per
ogni requisito (es. `### R-01`), in modo che il report possa linkare
direttamente con `[R-01](rtm-<data>.md#r-01)`.

La tabella triage TC prodotta in Fase 4 deve essere inclusa in appendice del
report con righe identificabili (es. header di sezione `### TC-NNN`) per ogni
TC non eseguibile o con anomalie, in modo che le sezioni Gap e Raccomandazioni
possano linkare direttamente.

**Modalita' compatta (attiva automaticamente per TL > 30 TC):**

In chat mostrare la tabella triage aggregata per area funzionale (derivata dalla
colonna "Jira Story" o "Team Competenza"). Per ogni area: # TC totali,
# eseguibili, # non eseguibili, # con step incompleti, gap BVA rilevati.

Il dettaglio TC per TC va **sempre incluso nel file salvato** (Appendice C del
report) indipendentemente dalla modalita' compatta — questo garantisce che i
cross-link `[TC-NNN](#tc-nnn)` nelle sezioni Gap e Raccomandazioni siano sempre
risolvibili. In chat il dettaglio e' mostrato solo su richiesta esplicita.

**Chiedi all'utente:**
1. Conferma di aver salvato gli artefatti in `./QA-REVIEW/` (la skill lo fa
   di default — conferma il path assoluto risolto da `pwd`).
2. Vuoi aprire ticket Jira per i gap CRITICI/ALTO?
3. La revisione e' chiusa o vuoi raffinare qualche sezione?

---

## Best practice ISTQB richiamate

Quando applichi le tecniche, leggi le sezioni rilevanti di
`references/istqb-checklist.md`:

- **IEEE 829 / ISO 29119:** struttura TC (precondizioni, step, expected,
  postcondizioni).
- **Boundary Value Analysis (BVA):** valori limite per ogni campo di input.
- **Equivalence Partitioning (EP):** classi di equivalenza valide e invalide.
- **Traceability bidirezionale:** ogni requisito → ≥ 1 TC; ogni TC → ≥ 1
  requisito.
- **Coverage Criteria minima:** almeno 1 TC per happy path di ogni AC. Edge e
  negativi a copertura risk-based.
- **Entry/Exit Criteria:** la revisione e' completa solo quando tutti i gap
  sono documentati e comunicati all'utente.

---

## Reference files (leggere on-demand)

- `references/csv-format-spec.md` — specifica formato CSV SIAE-BTP, regole di
  parsing, esempi di anomalie ricorrenti.
- `references/rtm-template.md` — template RTM compilato con esempi reali
  multi-requisito multi-TC.
- `references/istqb-checklist.md` — checklist ISTQB completa: AC quality, BVA,
  EP, eseguibilita' manuale, anti-pattern.

Carica solo quello che serve nella fase corrente (progressive disclosure).

---

## Anti-pattern da evitare

- **"Veloce e via":** saltare il challenge sugli AC perche' "sembra ovvio".
  Quasi sempre sbagliato — il primo requisito che sembra ovvio nasconde
  l'ambiguita' piu' costosa.
- **"Coverage finta":** approvare TC `NON ESEGUIBILE MANUALMENTE` per
  raggiungere il 100% di coverage formale. La coverage reale e' quella
  eseguibile.
- **"RTM sola andata":** produrre solo la vista requisito → TC senza
  bidirezionale. I TC orfani sono un indicatore importante di requisiti
  impliciti / test obsoleti.
- **"Gap nascosti":** chiudere il report senza sezione 4 (G6) perche' "tutto
  ok". Esplicitare "nessun gap" con motivazione e' diverso da non parlarne.
