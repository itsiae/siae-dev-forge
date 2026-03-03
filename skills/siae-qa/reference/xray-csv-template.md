# Xray CSV Import — Template di Riferimento SIAE

Questo documento definisce il formato CSV usato per importare Test Case in Xray Cloud quando non e' disponibile l'integrazione MCP o REST API (Tier 3).

---

## Colonne

| Colonna | Tipo | Obbligatorio | Valori validi / Note |
|---------|------|-------------|----------------------|
| `ID` | Intero | Si | Numero sequenziale del Test Case. Righe con stesso ID = stesso TC, step multipli. |
| `Test  Type` | Stringa | Si | `Manual` (nota: due spazi prima di `Type` — mantenere per compatibilita') |
| `Team Competenza` | Stringa | No | `QA` — identifica il team responsabile |
| `ID JIRA Story` | Stringa | Si | Es. `PROJ-123` — chiave Jira della User Story collegata |
| `User Story Description` | Stringa | Si (prima riga) | Summary della User Story Jira. Solo nella prima riga del TC. |
| `Scenario (descrizione)` | Stringa | Si (prima riga) | Titolo del Test Case. Solo nella prima riga del TC. |
| `Step scenario` | Intero | Si | Numero dello step (1, 2, 3...) |
| `Action` | Stringa | Si | Azione dell'utente o del sistema in questo step |
| `Expceted Result` | Stringa | Si | Risultato atteso — **typo originale mantenuto** (non correggere: e' il nome colonna del template SIAE) |
| `Data` | Stringa | No | Dati di test specifici per lo step. Lasciare vuoto se non necessario. |
| `Automazione` | Stringa | Si | `Y` se esiste un test automatizzato che copre questo TC, `N` altrimenti |
| `NRT` | Stringa | Si | `Y` (default, Non-Regression Test) o `N` |

---

## Regole Multi-Step

```
Stesso ID = stesso Test Case con piu' step.

Prima riga del TC: tutti i campi compilati.
Righe successive: solo ID, Step scenario, Action, Expceted Result.
I campi Test Type, Team Competenza, ID JIRA Story, User Story Description,
Scenario (descrizione), Data, Automazione, NRT rimangono VUOTI nelle righe
successive dello stesso TC.
```

---

## Note di Encoding e Formato

- **Encoding:** UTF-8 (senza BOM)
- **Separatore:** `;` (punto e virgola — non virgola, non tab)
- **Header:** obbligatorio in prima riga — deve corrispondere esattamente ai nomi colonna
- **Newline:** LF (Unix) o CRLF (Windows) — entrambi accettati da Xray
- **Campi con testo lungo:** non usare virgolette doppie a meno che il testo contenga il separatore `;`

---

## Header Esatto

```
ID;Test  Type;Team Competenza;ID JIRA Story;User Story Description;Scenario (descrizione);Step scenario;Action;Expceted Result;Data;Automazione;NRT
```

**Attenzione:** il nome colonna `Test  Type` ha **due spazi** tra `Test` e `Type`. Non correggere — e' il formato atteso dall'import Xray SIAE.

---

## Esempio Completo

Due Test Case, 3 step ciascuno.

```csv
ID;Test  Type;Team Competenza;ID JIRA Story;User Story Description;Scenario (descrizione);Step scenario;Action;Expceted Result;Data;Automazione;NRT
1;Manual;QA;PROJ-123;Come utente voglio accedere al portale con credenziali valide;Verifica login con credenziali valide;1;Aprire il portale SIAE all'URL di collaudo;La pagina di login viene visualizzata con i campi username e password;;N;Y
1;;;;;;2;Inserire username e password validi nei rispettivi campi;I campi accettano l'input senza errori di validazione;;N;Y
1;;;;;;3;Premere il pulsante "Accedi";L'utente viene reindirizzato alla home page con il proprio nome visualizzato nell'header;;N;Y
2;Manual;QA;PROJ-123;Come utente voglio accedere al portale con credenziali valide;Verifica login con credenziali errate;1;Aprire il portale SIAE all'URL di collaudo;La pagina di login viene visualizzata;;N;Y
2;;;;;;2;Inserire username corretto e password errata;I campi accettano l'input;;N;Y
2;;;;;;3;Premere il pulsante "Accedi";Viene visualizzato il messaggio di errore "Credenziali non valide". L'utente rimane sulla pagina di login.;;N;Y
```

---

## Come Importare in Xray

1. In Jira, vai alla sezione **Xray** nel menu di navigazione
2. Seleziona **Test** → **Import**
3. Scegli il formato **CSV**
4. Carica il file CSV generato dalla skill siae-qa
5. Verifica la mappatura colonne nella schermata di preview
6. Conferma l'import

L'import crea i Test Case come issue Xray di tipo `Test`, collegati automaticamente alla Story Jira indicata nel campo `ID JIRA Story`.

---

## Valori di Default Raccomandati

| Campo | Default | Quando cambiare |
|-------|---------|-----------------|
| `Automazione` | `N` | Imposta `Y` solo se esiste un test automatizzato (JUnit, vitest, pytest) che copre esattamente questo scenario |
| `NRT` | `Y` | Imposta `N` solo per TC di nuova funzionalita' che non hanno ancora una baseline da proteggere |
| `Team Competenza` | `QA` | Modifica se il TC e' di competenza di un altro team (es. `Dev`, `Ops`) |
| `Data` | (vuoto) | Compila con dati specifici se il TC richiede input precisi (es. codice fiscale di test, importo specifico) |
