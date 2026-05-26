# Checklist ISTQB per revisione TL manuali

> Riferimento operativo per le **FASI 2 e 4** della skill `siae-tl-review`. Leggere
> quando: bisogna validare AC, applicare BVA/EP a un campo, decidere se un TC
> e' eseguibile manualmente, o produrre raccomandazioni ISTQB-compliant.

## Indice

1. [AC Quality Checklist (Fase 2)](#1-ac-quality-checklist-fase-2)
2. [Boundary Value Analysis (BVA)](#2-boundary-value-analysis-bva)
3. [Equivalence Partitioning (EP)](#3-equivalence-partitioning-ep)
4. [Anti-pattern eseguibilita' manuale (Fase 4 / G4)](#4-anti-pattern-eseguibilita-manuale-fase-4--g4)
5. [Checklist IEEE 829 per struttura TC](#5-checklist-ieee-829-per-struttura-tc)
6. [Entry / Exit Criteria di revisione](#6-entry--exit-criteria-di-revisione)
7. [Tassonomia rischi e prioritizzazione raccomandazioni](#7-tassonomia-rischi-e-prioritizzazione-raccomandazioni)

---

## 1. AC Quality Checklist (Fase 2)

Per ogni AC estratto da un requisito, verifica con confidence numerica
(0-100%):

### Domande di qualita' (ognuna abbatte la confidence se la risposta non e' chiara dal testo del requisito)

| # | Domanda | Se "no" → confidence -X% |
|---|---------|--------------------------|
| Q1 | L'AC e' **testabile** con un risultato osservabile da UI? | -20% |
| Q2 | E' specificato il **comportamento atteso** (non solo "deve funzionare")? | -25% |
| Q3 | Sono definiti i **valori di soglia** per criteri quantitativi (tempo, dimensione, count)? | -15% |
| Q4 | E' specificato il **comportamento in caso di errore** o input invalido? | -15% |
| Q5 | Non contiene **termini ambigui** ("appropriato", "corretto", "rapido", "user-friendly")? | -10% |
| Q6 | E' chiaro **chi e' l'attore** (utente loggato? guest? admin?)? | -10% |
| Q7 | Sono specificate le **precondizioni** (stato del sistema, dati pre-esistenti)? | -5% |

Confidence iniziale = 100%. Sottrai i malus per ogni risposta negativa.
**Soglia per procedere (G2/G5): >= 95% su TUTTI gli AC del requisito.**

### Esempi di AC challenge

**AC ambiguo:**
> "Il sistema deve gestire correttamente l'invio del modulo."

Confidence stimata: ~30% (Q1 ❌, Q2 ❌, Q4 ❌, Q5 ❌). Domande da fare:

1. "Cosa significa 'gestire correttamente'? Conferma scritta a video? Email
   di conferma? Redirect? Quali campi devono essere validati lato client vs
   server?"
2. "Cosa succede se l'invio fallisce (rete giu', server 500, validazione
   server-side)? Messaggio specifico? Retry automatico?"
3. "Tempo massimo entro cui il feedback deve apparire?"

**AC ben formato:**
> "Quando l'utente loggato (ruolo `agente`) clicca 'Invia' su un modulo con
> tutti i campi obbligatori compilati validamente, entro 2 secondi appare un
> toast verde 'Modulo inviato' E il modulo viene salvato (verificabile
> aprendo 'Storico → Ultimi 10'). Se la rete e' giu' (timeout > 5s), appare
> toast rosso 'Connessione assente, riprova' senza perdere i dati compilati."

Confidence ~100%: testabile da UI (Q1 ✅), atteso esplicito (Q2 ✅), soglie
specificate (Q3 ✅), errore gestito (Q4 ✅), nessun termine ambiguo (Q5 ✅),
attore chiaro (Q6 ✅), precondizioni chiare (Q7 ✅).

---

## 2. Boundary Value Analysis (BVA)

Per ogni campo di input, identifica i **valori al confine** delle classi di
equivalenza. Sono i punti di errore piu' frequenti.

### Pattern BVA SIAE ricorrenti

| Tipo campo | Boundary da testare |
|------------|---------------------|
| Stringa con lunghezza min/max | `min-1`, `min`, `min+1`, `max-1`, `max`, `max+1`, `0` (vuoto), `null` |
| Numero intero | `min-1`, `min`, `max`, `max+1`, `0`, `-1` se positivi |
| Numero decimale | come intero + casi decimali al limite (es. `0.001`, `0.999`) |
| Data | `min`, `min-1g`, `max`, `max+1g`, oggi, ieri, anno bisestile (`29-feb`) |
| Codice fiscale | 15 char, 16 char, 17 char, vuoto, con caratteri illegali |
| Email | locali min/max, domini min/max, multiple `@` |
| Importo (€) | `0.00`, `0.01`, soglie applicative (es. soglie SIAE per categorie d'aliquota), valori negativi |
| File upload | 0 byte, 1 byte, MAX_SIZE-1, MAX_SIZE, MAX_SIZE+1, estensione corretta/sbagliata |

### Esempio applicato

Campo "Codice opera SIAE" — formato 6 caratteri alfanumerici, obbligatorio:

BVA:
- 0 caratteri (vuoto) → AC negativo "campo obbligatorio"
- 5 caratteri → AC negativo "lunghezza insufficiente"
- 6 caratteri validi → AC positivo
- 7 caratteri → AC negativo "lunghezza eccessiva"
- 6 caratteri con simbolo `@` → AC negativo "caratteri non ammessi"

In Fase 4 verifica che la TL contenga almeno i casi `vuoto`, `lunghezza
errata`, `caratteri non ammessi`. Se manca → gap.

---

## 3. Equivalence Partitioning (EP)

Suddividi il dominio di ogni input in **classi di equivalenza**: valida e
invalide. Un TC per classe.

### Esempio: ruolo utente in webapp SIAE-BTP

Classi:
- Valide: `agente_attivo`, `admin`, `revisore`.
- Invalide: `agente_sospeso`, `guest`, `utente_revocato`, `token_scaduto`.

Per ogni classe invalida si attende un comportamento specifico (redirect a
login? 403? messaggio diverso?). Ogni classe = 1 TC.

### Combinazione con BVA

BVA e' un **caso particolare** di EP: gli elementi al confine sono
rappresentanti privilegiati delle loro classi. Una checklist completa unisce
le due:

1. EP: identifica le classi.
2. BVA: per ogni classe numerica/lunghezza, aggiungi i confini.

---

## 4. Anti-pattern eseguibilita' manuale (Fase 4 / G4)

**Un TC e' NON ESEGUIBILE MANUALMENTE se anche uno solo dei suoi step
contiene riferimenti a:**

### 4.1 Accesso database

Pattern testuali da intercettare in `Action` / `Expected Result`:

- `SELECT`, `INSERT`, `UPDATE`, `DELETE` (SQL diretto).
- "Verifica nella tabella `<nome>`...".
- "Connettiti al DB", "esegui query", "apri DBeaver / SQL Developer / DBA
  tool".
- "Controlla il valore di `<colonna>` per `<chiave>`".

**Riformulazione UI tipica:** verifica lo stato finale tramite una pagina
della webapp che mostra quel dato (es. "Storico", "Dettaglio operazione",
"Log utente"). Se la webapp non lo espone → escludi dalla coverage e segnala
in raccomandazioni.

### 4.2 Accesso log / filesystem server-side

- "tail dei log", "verifica nei log applicativi".
- "controlla `/var/log/...`", "accedi al server tramite ssh".

**Riformulazione UI:** se l'app espone un dashboard di log o un'area di
audit, usalo. Altrimenti escludi.

### 4.3 Deploy / CI/CD

- "esegui deploy", "rilascia in qa", "lancia pipeline".
- "verifica versione deployata".

**Riformulazione UI:** spesso impossibile per QA manuale. Escludi e indica
che il TC va automatizzato (CI gate, non manuale).

### 4.4 API dirette senza UI

- "fai POST a `/api/v1/...`", "chiama l'endpoint con curl/Postman".
- "verifica la response JSON".

**Riformulazione UI:** ogni endpoint REST in genere ha un'azione UI
corrispondente (form, button). Sostituisci. Se non esiste → e' un test API
puro, non un test manuale da TL.

### 4.5 Console developer / network tab

- "apri F12 → Network → verifica header `X-...`".
- "ispeziona il payload della richiesta".

**Riformulazione UI:** verifica solo gli effetti osservabili dalla UI (toast,
redirect, dati visualizzati). Se l'effetto e' invisibile lato utente,
escludi (e' un caso da test automatico).

### 4.6 Strumenti tecnici di sviluppo

- "esegui `npm test`", "lancia lo script `<nome.sh>`".
- "modifica il file di configurazione".

**Esclusione:** sempre. Non sono attivita' del QA manuale.

---

## 5. Checklist IEEE 829 per struttura TC

Per ogni TC della TL, verifica che siano presenti (anche impliciti):

| Elemento IEEE 829 | Dove deve apparire nella TL SIAE-BTP |
|-------------------|---------------------------------------|
| **Identificatore** | Colonna `ID` |
| **Scopo del test** | Colonna `Summary` (titolo) + `Description` (estesa) |
| **Precondizioni** | Inizio della `Description` o primo step (`Action: Apri ... essendo loggato come ...`) |
| **Input** | All'interno degli step (`Action`) |
| **Procedura** | Sequenza step con `Step scenario` numerato |
| **Risultato atteso** | Colonna `Expected Result` di ogni step |
| **Postcondizioni** | Espliciti nell'ultimo step (es. "sessione attiva, dashboard utente") |
| **Riferimento al requisito** | Colonna `ID JIRA Story` |
| **Tipo** | Colonna `Test Type` |

**TC incompleto** se mancano `Expected Result` o `ID JIRA Story` o se le
precondizioni non sono inferibili dagli step. Segnala in Fase 4.

---

## 6. Entry / Exit Criteria di revisione

### Entry Criteria (per iniziare la review — Fase 0)

- TL caricata e validata strutturalmente (G7).
- Almeno una fonte requisiti disponibile (Jira/Doc/Chat).
- QA disponibile a interagire per il challenge degli AC (G2).

### Exit Criteria (per chiudere la review — Fase 5)

- ✅ Tutti i requisiti hanno AC a confidence >= 95% (G2/G5).
- ✅ RTM bidirezionale prodotta (forward + inverse).
- ✅ Tutti i TC analizzati per eseguibilita' manuale (G4).
- ✅ Tutti i gap documentati nella sezione `⚠️ GAP DI COPERTURA` (G6).
- ✅ Raccomandazioni prioritizzate per livello di rischio (CRITICO/ALTO/
  MEDIO/BASSO).
- ☐ Azioni correttive comunicate al team e tracciate (out-of-skill, ma
  segnalato all'utente come passo successivo).

La review e' "chiusa" solo quando i 5 punti sopra sono soddisfatti.
Altrimenti la skill resta in stato "review in corso" e l'utente lo sa.

---

## 7. Tassonomia rischi e prioritizzazione raccomandazioni

Quando produci raccomandazioni nella Fase 5, sezione 5, classificale cosi':

### CRITICO

- Requisito core (login, pagamento, salvataggio dato) **senza alcun TC**
  Happy Path eseguibile.
- TC eseguito sul percorso critico ma con `Expected Result` mancante o
  ambiguo.
- Vulnerabilita' di sicurezza non testata (es. session timeout assente).

**Azione:** blocca rilascio finche' coperto.

### ALTO

- Requisito core con TC Happy Path eseguibile ma **senza casi negativi**.
- Edge case noti (BVA) non testati su campi critici.
- TC critici flaggati `🟠 NON ESEGUIBILE` senza riformulazione UI.

**Azione:** correggi prima del rilascio se possibile, altrimenti documenta
rischio esplicito.

### MEDIO

- Requisito secondario senza alcuni edge case.
- TC orfani che potrebbero indicare requisiti impliciti.
- Inconsistenze nei naming o nella struttura della TL (impatto qualita',
  non funzionalita').

**Azione:** schedulare correzione, non bloccante.

### BASSO

- Refactoring TL (rinaming, riorganizzazione step).
- Espansione coverage non critica (es. ulteriori BVA su campi marginali).

**Azione:** backlog, non bloccante.

---

## 8. Riferimenti normativi richiamati

- **ISTQB Foundation Level Syllabus** v4.0 — sezz. 2.3 (Static Testing), 4.2
  (BVA/EP), 5.1 (Test Management).
- **IEEE 829-2008** — Standard for Software and System Test Documentation.
- **ISO/IEC/IEEE 29119-3:2021** — Software testing — Test documentation.
- **ISTQB Test Manager Syllabus** v3.0 — sez. 5 (Risk-Based Testing).
