# DevForge Visual Design System

Questo documento è il riferimento visivo **obbligatorio** per TUTTE le skill del plugin `siae-devforge`.
Ogni skill generata, ogni risposta durante l'esecuzione di una skill, e ogni output DevForge
deve rispettare le convenzioni definite qui.

Le skill possono includere questo file con un riferimento diretto oppure incorporarne le sezioni
rilevanti nel proprio `SKILL.md`. In ogni caso, le regole qui descritte hanno precedenza assoluta.

---

## 0.1 Banner di Avvio

Mostra questo banner ASCII all'inizio di ogni esecuzione skill:

```
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║                                                                  ║
║              🔨  DevForge  ·  AI Competence Center               ║
║         "Il codice si forgia. Il developer cresce."              ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 0.2 Codifica Colori / Rischio

Ogni azione ha un livello di rischio con colore ANSI associato — sia nelle etichette di testo che nella pre-flight card.

| Livello  | Emoji | Significato                        | ANSI         | Quando si usa                                  |
|----------|-------|------------------------------------|--------------|------------------------------------------------|
| Sicuro   | 🟢    | Solo lettura, nessun effetto       | `\e[32m`     | Lettura file, analisi, spiegazioni             |
| Medio    | 🟡    | Modifiche locali, reversibili      | `\e[33m`     | Scrittura file, modifica codice, test run      |
| Alto     | 🔴    | Difficile da annullare             | `\e[31m`     | Operazioni git, chiamate API esterne, delete   |
| Critico  | 🚨    | Irreversibile o impatto esteso     | `\e[1;31m`   | Push remoto, modifiche config CI/CD, segreti   |

Reset colore dopo ogni etichetta: `\e[0m`

Usa il colore ANSI per colorare:
- le etichette di rischio inline (es. `\e[33m🟡 MEDIO\e[0m`)
- l'intera pre-flight card (bordo + testo)
- i prefissi degli step nelle istruzioni della skill

---

## 0.3 Pre-flight Card — Permission Mindfulness

**Regola di raggruppamento:** prima di iniziare qualsiasi sequenza di azioni, Claude raccoglie TUTTE le operazioni pianificate, le raggruppa per livello di rischio, e mostra **una sola card per livello** — con tutte le operazioni di quel livello elencate al suo interno. L'utente vede il piano completo in una volta sola, non N popup separati.

**Regola fondamentale: la pre-flight card è OBBLIGATORIA per qualsiasi azione con rischio ≥ 🟡 MEDIO.**
Non è opzionale. Non si omette "per velocità". Si mostra PRIMA che Claude esegua l'azione, non dopo.

**Regola multi-step:** se la skill è strutturata in più fasi (es. Step 3 = conferma piano, Step 4 = esecuzione), la card va mostrata SEMPRE come ultimo output prima del tool call di esecuzione — anche se era già stata mostrata in una fase precedente. Lo scope può cambiare tra una fase e l'altra.

**Regola operazioni fuori flusso:** se la tabella di classificazione di una skill elenca operazioni non presenti nel flusso standard (es. `git push`, `rm`, `deploy`), la card rimane obbligatoria se l'utente le richiede esplicitamente. Nella tabella di classificazione aggiungi una nota che indica quale tipo di card usare per ciascuna:
- operazione 🔴 ALTO → card con bordo `┏━┓` rosso
- operazione 🚨 CRITICO → card con bordo `┏━┓` rosso grassetto

Il colore della card comunica il livello a colpo d'occhio: giallo → medio, rosso → alto, rosso grassetto → critico.

---

### Come costruire una card raggruppata

Struttura delle righe operazione (colonne allineate a 17 caratteri):
```
  N.  Azione:    [descrizione dell'azione]
      File/Path: [percorso esatto del file]
```
Struttura footer (motivazione e alternativa condivise per tutte le operazioni del gruppo):
```
  Perché:        [motivazione valida per tutte le operazioni del gruppo]
  Se NO:         [cosa succede se l'utente rifiuta l'intero gruppo]
```

---

### Card 🟡 MEDIO — bordo doppio · `\e[33m` giallo · `\e[0m` reset

```
╔══════════════════════════════════════════════════════════════════╗
║  🔨 DevForge — 🟡 MEDIO (reversibile)  ·  [N] operazioni         ║
╠══════════════════════════════════════════════════════════════════╣
║  1.  Azione:    [descrizione prima operazione]                   ║
║      File/Path: [percorso/del/file1]                             ║
║  2.  Azione:    [descrizione seconda operazione]                 ║
║      File/Path: [percorso/del/file2]                             ║
╠══════════════════════════════════════════════════════════════════╣
║  Perché:        [motivazione contestuale in italiano]            ║
║  Se NO:         [cosa succede se rifiuti]                        ║
╠══════════════════════════════════════════════════════════════════╣
║  ⬆️  Leggi prima, poi decidi nella dialog qui sopra              ║
╚══════════════════════════════════════════════════════════════════╝
```

### Card 🔴 ALTO — bordo pesante · `\e[31m` rosso · `\e[0m` reset

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  🔨 DevForge — 🔴 ALTO (difficile da annullare)  ·  [operazione] ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃  1.  Azione:    [descrizione prima operazione]                   ┃
┃      File/Path: [percorso/del/file1]                             ┃
┃  2.  Azione:    [descrizione seconda operazione]                 ┃
┃      File/Path: [percorso/del/file2]                             ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃  Perché:        [motivazione contestuale in italiano]            ┃
┃  Se NO:         [cosa succede se rifiuti]                        ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃  ⬆️  Leggi prima, poi decidi nella dialog qui sopra              ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

### Card 🚨 CRITICO — bordo pesante · `\e[1;31m` rosso grassetto · `\e[0m` reset

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  🔨 DevForge — 🚨 CRITICO (irreversibile)  ·  [operazione]       ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃  1.  Azione:    [descrizione prima operazione]                   ┃
┃      File/Path: [percorso/del/file1]                             ┃
┃  2.  Azione:    [descrizione seconda operazione]                 ┃
┃      File/Path: [percorso/del/file2]                             ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃  Perché:        [motivazione contestuale in italiano]            ┃
┃  Se NO:         [cosa succede se rifiuti]                        ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃  ⬆️  Leggi prima, poi decidi nella dialog qui sopra              ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

---

## Trigger obbligatori per rischio ≥ 🟡

| Categoria          | Esempi di azione                                              | Livello |
|--------------------|---------------------------------------------------------------|---------|
| Scrittura file     | Creare, modificare, sovrascrivere qualsiasi file              | 🟡      |
| Eliminazione       | Cancellare file, righe di codice, blocchi, funzioni           | 🔴      |
| Esecuzione shell   | Bash con side-effect: npm install, pip install, mkdir, mv     | 🟡      |
| Database / schema  | ALTER TABLE, DROP, DELETE, modifiche a migration              | 🔴      |
| Sicurezza          | Lettura/scrittura di chiavi, token, .env, credenziali         | 🚨      |
| Dipendenze         | Aggiunta, rimozione, upgrade di package                       | 🟡      |
| Operazioni git     | commit, push, merge, rebase, reset, branch delete             | 🔴      |
| CI/CD e config     | Modifica a pipeline, Dockerfile, workflow, infra-as-code      | 🚨      |
| Chiamate API esterne | Richieste HTTP a servizi esterni, webhook, invio messaggi   | 🔴      |
| Refactoring esteso | Rinominare simboli, spostare moduli, cambiare interfacce      | 🟡      |

---

## Regole di compilazione

- Compila ogni campo in modo specifico e contestuale, MAI generico
- Il campo **Rischio** deve usare uno dei quattro livelli della tabella 0.2
- Il campo **Alternativa** deve descrivere concretamente cosa succede se l'utente nega
- Se l'azione tocca più categorie, usa il livello più alto tra quelli applicabili
- Per azioni 🟢 (solo lettura, analisi, spiegazioni): la card NON si mostra
