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

## 0.3 Pre-flight Card — Template Unificato a 4 Zone

**Regola fondamentale: la pre-flight card e' OBBLIGATORIA per qualsiasi azione con rischio >= 🟡 MEDIO.**
Non e' opzionale. Non si omette "per velocita'". Si mostra PRIMA che Claude esegua l'azione, non dopo.

**Regola di raggruppamento:** Claude raccoglie TUTTE le operazioni pianificate, le raggruppa per livello di rischio, e mostra **una sola card per livello**.

**Regola multi-step:** se la skill ha piu' fasi, la card va mostrata SEMPRE come ultimo output prima del tool call di esecuzione — anche se era gia' stata mostrata in una fase precedente.

### Come generare una card

<EXTREMELY-IMPORTANT>
NON costruire le card a mano. Usa SEMPRE lo script `design-system/generate-card.py`.

Claude non sa calcolare correttamente la larghezza visiva delle emoji. Lo script gestisce
automaticamente padding, allineamento, wrapping e colori ANSI.
</EXTREMELY-IMPORTANT>

**Uso da Bash (JSON su stdin):**

```bash
echo '{
  "level": "ALTO",
  "skill": "siae-finishing-branch",
  "context": [
    {"emoji": "🌿", "label": "Branch", "value": "feature/PROJ-123-add-login"},
    {"emoji": "🎯", "label": "Target", "value": "sviluppo"}
  ],
  "actions": [
    {"emoji": "🚀", "label": "Push branch + apertura PR", "path": "origin/feature/PROJ-123"}
  ],
  "reason": "Branch pronto, test verdi",
  "ifno": "Il branch resta locale"
}' | python3 design-system/generate-card.py
```

**Flags:**
- `--no-color` — disabilita colori ANSI (per output in file .md)

### Le 4 Zone

Ogni card e' composta da 4 zone in ordine fisso:

| Zona | Nome | Contenuto | Obbligatoria? |
|------|------|-----------|---------------|
| Z1 | **Header** | `🔨 DevForge — [EMOJI] [LIVELLO] ([sottotitolo]) · [skill]` | SEMPRE |
| Z2 | **Contesto** | Righe `emoji label: valore` con stato/ambiente rilevato | Se la skill ha info di contesto |
| Z3 | **Operazioni** | Lista numerata `N. emoji Azione: desc` + `📂 File/Path: path` | Se ci sono azioni da eseguire |
| Z4 | **Footer** | `💡 Perche': motivazione` + `🚫 Se NO: alternativa` | SEMPRE |

### Combinazioni valide

| Caso d'uso | Z1 | Z2 | Z3 | Z4 |
|------------|----|----|----|----|
| Contesto puro (QA/Automation apertura) | ✅ | ✅ | — | ✅ |
| Operazioni pure (documentation publish) | ✅ | — | ✅ | ✅ |
| Contesto + operazioni (finishing-branch, security) | ✅ | ✅ | ✅ | ✅ |

---

## 0.4 Griglia Adattiva

Lo script `generate-card.py` gestisce automaticamente:

- **Larghezza adattiva:** min 60, max 100 caratteri (bordi inclusi)
- **Margine sinistro:** 2 spazi sempre
- **Label column:** allineata a `:` + spazi (18 char)
- **Emoji:** contano 2 char di larghezza display
- **Wrapping testo:** su confini di parola (spazi)
- **Wrapping path:** su `/` per token senza spazi
- **Righe di continuazione:** indent allineato al valore (dopo `:`)
- **Bordi:** MAI sfondati — il contenuto si adatta, non il bordo

---

## 0.5 Bordo e Colore per Livello

| Livello | Bordo | Caratteri | Colore ANSI |
|---------|-------|-----------|-------------|
| 🟢 SICURO | Nessuna card | — | — |
| 🟡 MEDIO | Doppio | `╔═╗ ║ ╠ ╚╝` | `\e[33m` giallo |
| 🔴 ALTO | Pesante | `┏━┓ ┃ ┣ ┗┛` | `\e[31m` rosso |
| 🚨 CRITICO | Pesante | `┏━┓ ┃ ┣ ┗┛` | `\e[1;31m` rosso bold |

Ogni riga della card: `[COLORE]bordo_sx[RESET] contenuto paddato [COLORE]bordo_dx[RESET]`

---

## 0.6 Emoji Catalog

### Z2 Contesto — emoji per campo

| Emoji | Uso |
|-------|-----|
| 📡 | Tier/connessione |
| 🎫 | Ticket Jira/Story |
| ✅ | Disponibilita'/check |
| 📚 | Confluence/docs |
| 🌿 | Branch git |
| 🎯 | Target/base |
| 📝 | Commit/note |
| 🧪 | Test suite |
| 📋 | Piano/modulo |
| 🔢 | Task/numerazione |
| 🤖 | Subagent/bot |
| 📱 | Canale mobile |
| ☁️ | Cloud/BrowserStack |
| 🔄 | Sync/tipo |
| 📦 | Package/dipendenza |
| 📁 | Directory/working dir |
| 🔧 | Comando/config |
| 🔑 | Pattern/secret |
| 📊 | Confidence/stats |
| 🗄️ | Database |
| 🔐 | Credenziali/rotazione |
| 🌍 | Scope/ambiente |
| 🏗️ | Ambiente infra |

### Z3 Operazioni — emoji per azione

| Emoji | Uso |
|-------|-----|
| ✏️ | Creazione file |
| 📝 | Modifica file |
| 🗑️ | Eliminazione |
| 📥 | Installazione dipendenza |
| 🔀 | Refactoring/rinomina |
| 🖥️ | Esecuzione shell |
| 🔧 | Modifica schema/config |
| 📌 | Git commit |
| 🚀 | Git push / PR |
| 📤 | Pubblicazione esterna |
| ⚡ | Dispatch subagent |
| 🧪 | Test |
| ⚠️ | Alert critico |

### Z4 Footer + Z3 Path — fissi

| Emoji | Uso |
|-------|-----|
| 📂 | File/Path (sempre in Z3) |
| 💡 | Perche' (sempre in Z4) |
| 🚫 | Se NO (sempre in Z4) |

---

## Trigger obbligatori per rischio >= 🟡

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
