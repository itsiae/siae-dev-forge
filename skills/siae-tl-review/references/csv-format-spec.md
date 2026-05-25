# Specifica formato CSV/XLS — SIAE-BTP Test List

> Riferimento operativo per la **FASE 0** della skill `siae-tl-review`. Leggere
> quando: la skill deve validare un file di input, il formato osservato devia
> dallo standard, o l'utente chiede chiarimenti su una colonna.

## 1. Estensioni accettate

| Estensione | Note |
|------------|------|
| `.csv`     | Default SIAE-BTP. Separatore standard `;` (punto e virgola), encoding `UTF-8` o `UTF-8 BOM`. |
| `.xls`     | Formato Excel legacy (BIFF). Parsare con libreria xls-compatibile. |
| `.xlsx`    | Excel moderno (Office Open XML). Default per export da Jira/Xray. |

**Bloccare** (Guardrail G7) qualsiasi altra estensione con messaggio:

> "Il file `<nome>.<ext>` non e' supportato. Formati accettati: .csv, .xls,
> .xlsx. Esporta nuovamente la TL nel formato corretto e ripeti l'operazione."

## 2. Colonne attese (formato SIAE-BTP standard)

Ordine canonico osservato negli export ufficiali:

| # | Colonna              | Obbligatoria | Descrizione |
|---|----------------------|--------------|-------------|
| 1 | `ID`                 | ✅ (per riga TC) | Identificatore univoco TC (es. `TC-001`). Vuoto sulle righe step. |
| 2 | `Test Type`          | Raccomandata  | Manual / Automated / Exploratory / Regression. |
| 3 | `Team Competenza`    | Raccomandata  | Team owner del TC (es. "Frontend", "Backend", "QA Cluster Arancione"). |
| 4 | `ID JIRA Story`      | Raccomandata  | Story ID di riferimento (es. `BTP-123`). |
| 5 | `User Story Description` | Raccomandata | Testo della story Jira (spesso replicato dalla story). |
| 6 | `Summary`            | Raccomandata  | Titolo breve del TC (max ~120 char). |
| 7 | `Description`        | Raccomandata  | Descrizione estesa del TC, contesto, precondizioni. |
| 8 | `Step scenario`      | ✅ (per step) | Identificatore o numero dello step (`1`, `2`, `2.1`). |
| 9 | `Action`             | ✅            | Azione che il QA esegue (imperativo: "Clicca su...", "Inserisci..."). |
| 10 | `Expected Result`   | ✅            | Risultato atteso, verificabile visivamente da UI. |

**Colonne obbligatorie minime per non bloccare ingestion (G7):** `ID`,
`Action`, `Expected Result`. Se ne manca anche una sola → blocco con messaggio:

> "Il file e' privo della/e colonna/e obbligatoria/e: `<lista>`. Verifica
> l'header (prima riga del CSV) e ri-esporta. Specifica completa: vedi
> references/csv-format-spec.md."

## 3. Struttura gerarchica (TC + Step)

Il formato SIAE-BTP usa una struttura padre-figlio implicita: **una riga con
`ID` valorizzato apre un TC; le righe successive con `ID` vuoto sono i suoi
step**.

```csv
ID;Test Type;Team Competenza;ID JIRA Story;User Story Description;Summary;Description;Step scenario;Action;Expected Result
TC-001;Manual;QA Cluster Arancione;BTP-123;"Come utente loggato voglio...";Login OK;Login con credenziali valide;1;Apri https://btp.siae.it;La home di login e' visibile
;;;;;;;2;Inserisci username valido nel campo "Utente";Il campo accetta l'input senza errori
;;;;;;;3;Inserisci password valida nel campo "Password";Il campo maschera l'input
;;;;;;;4;Clicca "Accedi";La dashboard utente e' visibile entro 3 secondi
TC-002;Manual;QA Cluster Arancione;BTP-123;"Come utente loggato voglio...";Login KO password errata;Login con password errata;1;Apri https://btp.siae.it;La home di login e' visibile
;;;;;;;2;Inserisci username valido;...
```

**Regola di parsing:**
- Riga N ha `ID` non vuoto → e' un nuovo TC. Memorizza header del TC.
- Riga N+1..N+k con `ID` vuoto → step del TC corrente. Append in
  `steps[]` del TC.
- Prima riga senza `ID` quando non c'e' TC corrente → **anomalia
  strutturale**, segnalare.

## 4. Encoding e separatori

| Aspetto         | Default SIAE-BTP | Fallback |
|-----------------|-------------------|----------|
| Separatore CSV  | `;` (semicolon)   | `,` se la prima riga non parsa con `;`. |
| Encoding        | `UTF-8` (con o senza BOM) | `latin-1` (ISO-8859-1) — proporre fallback se UTF-8 fallisce su caratteri accentati. |
| Delimitatore stringa | `"` (doppi apici) | Stesso. |
| Newline interno cella | `\n` racchiuso tra `"..."` | Stesso. |

Se l'auto-detect del separatore e' ambiguo, **chiedi conferma all'utente**:

> "Ho rilevato il separatore `;`. Confermi? (Altrimenti specifica)"

## 5. Anomalie strutturali ricorrenti

Da segnalare nel riepilogo di ingestion (Fase 0):

| Anomalia | Descrizione | Severita' |
|----------|-------------|-----------|
| Step orfano | Riga senza `ID` ma con nessun TC precedente. | ⚠️ Alta |
| TC senza step | Riga TC seguita immediatamente da un'altra riga TC. | ⚠️ Alta |
| `Expected Result` vuoto | Step con `Action` ma senza atteso. | ⚠️ Media |
| `ID JIRA Story` vuoto | TC non tracciabile a story. | ⚠️ Media (gestito anche in Fase 4) |
| `ID` duplicato | Due TC con stesso identificatore. | ⛔ Bloccante |
| Header non riconosciuto | Colonne con nomi non standard. | ⚠️ Media — chiedere mapping all'utente |
| Encoding rotto | Caratteri sostituiti con `?` o `�`. | ⛔ Bloccante — chiedere ri-export UTF-8 |
| BOM doppio | File con BOM in prima E seconda colonna. | ⚠️ Bassa — strip silenzioso |

## 6. Esempio di file valido minimale

```csv
ID;Action;Expected Result
TC-001;Apri la home;La home e' visibile
;Clicca "Login";Si apre il form di login
TC-002;Apri la home;La home e' visibile
;Clicca "Logout";Il sistema torna a login
```

Questo file passa G7 (ha le 3 colonne obbligatorie). La skill segnalera' nel
report che `Test Type`, `Team`, `Story` non sono disponibili.

## 7. Esempio di output di ingestion

```markdown
## Ingestion completata

- File: SIAE_BTP_TestList_ClusterArancione.csv (12 KB, UTF-8, sep `;`)
- Test Case identificati: 42
- ID Jira Story distinti referenziati: 5 (BTP-101, BTP-102, BTP-103, BTP-104, BTP-105)
- Step totali: 187 (media 4.5 step/TC)
- Test Type rilevati: Manual (40), Exploratory (2)
- Team Competenza rilevati: QA Cluster Arancione (42)
- ⚠️ Anomalie strutturali:
  - 1 step orfano alla riga 45 — verra' ignorato
  - 3 TC senza ID Jira Story (TC-019, TC-027, TC-040) — verranno flaggati in Fase 3
  - 1 Expected Result vuoto (TC-033, step 4) — verra' segnalato in Fase 4

**Vuoi procedere alla Fase 1 (Raccolta dei Requisiti)?**
```
