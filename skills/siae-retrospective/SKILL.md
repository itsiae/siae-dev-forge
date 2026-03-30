---
name: siae-retrospective
description: >
  Estrae lezioni apprese e memoria episodica a fine sessione, persiste in auto-memory.
  Salva sia lezioni astratte (feedback) che narrativa sessione (cosa fatto, decisioni, stato).
  Trigger: fine sessione, lezioni apprese, cosa ho imparato, retrospettiva,
  salva per la prossima volta, /forge-retro, apertura PR, REQUIRED da post-commit-review
  hook su gh pr create.
---

# SIAE Retrospective — Lezioni Apprese Cross-Sessione

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗    ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║    ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║    ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝    ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝     ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝      ║
║              🔨 DevForge · RETROSPECTIVE                       ║
║         "Il codice si forgia. Il developer cresce."            ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Rigid | **Fase SDLC:** Cross-cutting

---

## LA LEGGE DI FERRO

LE LEZIONI NON SALVATE SONO LEZIONI PERSE. OGNI SESSIONE PRODUTTIVA MERITA RIFLESSIONE.

<EXTREMELY-IMPORTANT>
Stai per chiudere una sessione con almeno 1 commit senza aver estratto lezioni?
FERMATI. Il valore di una sessione non e' solo il codice scritto — e' anche
quello che hai imparato. Se non lo salvi, lo perdi.
</EXTREMELY-IMPORTANT>

---

> 📊 **Dai repo itsiae:** Il 67% delle correzioni ripetute tra sessioni riguardava pattern gia' scoperti ma non persistiti.
> Fonte: analisi su 816 repository GitHub itsiae (60 Java, 44 HCL, 23 Python, 22 TypeScript).

## Quando si Applica

**Sempre:**
- Fine sessione con almeno 1 commit (invocata programmaticamente da stop-gate hook)
- Quando l'utente chiede esplicitamente una retrospettiva

**Eccezioni:**
- Sessioni di sola lettura / esplorazione (0 commit)
- Sessioni interrotte prima del primo commit

---

## Istruzioni

### Step 1 — Raccogli

🟢 SICURO

Scansiona la conversazione corrente e identifica:

1. **Errori fatti** — approcci sbagliati, bug introdotti e poi fixati, assunzioni errate
2. **Correzioni ricevute** — feedback dall'utente che ha cambiato il tuo approccio
3. **Approcci validati** — scelte non ovvie che hanno funzionato bene
4. **Sorprese** — comportamenti inattesi del sistema, gotcha del framework, edge case
5. **Pattern scoperti** — convenzioni del progetto non documentate

Per ogni candidato, annota:
- Cosa e' successo (1 frase)
- Perche' e' rilevante per sessioni future
- In quale fase SDLC si e' verificato

### Step 2 — Classifica e Filtra

🟢 SICURO

Per ogni candidato, applica il **filtro "vale la pena salvare?"**:

**Salva SOLO se:**
- Non derivabile dal codice o git history
- Applicabile a sessioni future (non effimera)
- Sorprendente o non ovvia

**NON salvare:**
- Riassunti di cosa e' stato fatto (c'e' `git log`)
- Path di file o struttura progetto (c'e' il codice)
- Fix specifici (c'e' il commit)
- Regole gia' documentate in CLAUDE.md o nelle skill

**Classifica per tipo auto-memory:**

| Tipo | Esempio |
|------|---------|
| `feedback` | "L'utente preferisce un singolo PR per i refactoring in quest'area" |
| `project` | "Il servizio X usa un pattern custom per la validazione ISRC" |
| `user` | "L'utente ha esperienza profonda in Terraform ma e' nuovo a Vue" |
| `reference` | "I bug del pipeline sono tracciati nel progetto Linear INGEST" |

### Step 3 — Persisti

🟡 MEDIO — Scrive file di memoria

Per ogni lezione che supera il filtro:

1. Classifica per tipo: `feedback`, `project`, `user`, `reference`
2. Scrivi il file in `~/.claude/projects/<project>/memory/` con frontmatter:

```markdown
---
name: <nome descrittivo>
description: <una riga — usata per decidere rilevanza in future conversazioni>
type: <feedback|project|user|reference>
---

<contenuto della lezione>

**Why:** <motivazione — perche' questa lezione e' importante>
**How to apply:** <quando e come applicarla in futuro>
```

3. Aggiorna `MEMORY.md` con il puntatore al nuovo file.
   **Se `MEMORY.md` non esiste**, crealo con header `# <Project Name> — Memory Index` e una sezione per tipo.
4. Se esiste gia' una memory sullo stesso tema, **aggiornala** invece di duplicare

**NON salvare in CLAUDE.md. NON salvare nel repo. NON creare file fuori da memory/.**
Il sistema auto-memory e' l'unico canale di persistenza cross-sessione.

### Step 4 — Memoria Episodica

🟡 MEDIO — Scrive file di memoria

La memoria episodica salva la **narrativa della sessione**: cosa e' stato fatto,
quali decisioni sono state prese, dove si e' arrivati. Questo permette alla
sessione successiva di riprendere il contesto senza che l'utente debba rispiegare.

**Raccogli da git e dalla conversazione:**

```bash
git log --oneline HEAD~10..HEAD  # commit della sessione
git branch --show-current         # branch corrente
gh pr list --head $(git branch --show-current) --json number,state,title --jq '.[0]' 2>/dev/null
```

**Scrivi UN file episodico per sessione** in `~/.claude/projects/<project>/memory/`:

```markdown
---
name: session-YYYY-MM-DD-<topic-breve>
description: <1 riga — cosa si stava facendo e dove si e' arrivati>
type: project
---

## Sessione YYYY-MM-DD

**Branch:** <branch corrente>
**PR:** <#numero se esiste> (<stato: aperta/merged/draft>)
**Obiettivo:** <cosa l'utente voleva ottenere — 1 frase>

**Cosa e' stato fatto:**
1. <azione 1>
2. <azione 2>
...

**Decisioni prese:**
- <decisione e motivazione breve>

**Stato:** <completato | PR aperta in review | in corso | bloccato da X>

**Why:** Memoria episodica per ripristinare contesto nella sessione successiva.
**How to apply:** Leggere all'inizio della prossima sessione sullo stesso branch/progetto.
```

**Regole:**
- UN file per sessione, non uno per ogni azione
- Se esiste gia' un file episodico per lo stesso branch, **aggiornalo** (non duplicare)
- Il campo `description` deve essere abbastanza specifico da decidere se e' rilevante
- Non ripetere il contenuto dei commit (c'e' git log) — concentrati su decisioni e stato

**Aggiorna `MEMORY.md`** con il puntatore sotto una sezione `## Episodic`.

---

**Output strutturato obbligatorio:**

```
RETROSPECTIVE
═════════════
Sessione: YYYY-MM-DD
Skills usate: N | Commits: M

Episodica:
  → salvato in memory/project_session_YYYY-MM-DD_xxx.md

Lezioni estratte:
  1. [FEEDBACK] ... → salvato in memory/feedback_xxx.md
  2. [PROJECT] ... → salvato in memory/project_xxx.md
  3. [SCARTATA] ... → motivo: derivabile da git log

Nessuna lezione? → "Sessione pulita, niente da persistere."
```

---

## Tabella Anti-Razionalizzazione

| Pensiero | Realta' |
|----------|---------|
| "Non ho imparato niente di nuovo" | Se hai fatto almeno 1 commit, qualcosa e' successo. Rifletti. |
| "Lo ricordero' la prossima volta" | No, non lo ricorderai. Il contesto si resetta. Salva. |
| "E' troppo specifico per essere utile" | Le lezioni specifiche sono le piu' preziose. Generalizzare troppo le rende inutili. |
| "Il git log basta come memoria" | Il git log dice cosa hai fatto, non cosa hai imparato. |
| "Non vale la pena perdere tempo" | 2 minuti di retrospettiva salvano ore di errori ripetuti. |
| "L'utente non l'ha chiesto" | La retrospettiva e' programmatica. Non serve che la chieda. |
| "Salvo tutto per sicurezza" | Salvare troppo inquina la memoria. Il filtro esiste per un motivo. |
| "Questo e' ovvio, non serve salvarlo" | Se era ovvio, perche' l'errore e' successo? Salva. |

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Scansione conversazione | 🟢 Sicuro | No |
| Classificazione lezioni | 🟢 Sicuro | No |
| Scrittura memory file | 🟡 Medio | No (file personale, non nel repo) |
| Aggiornamento MEMORY.md | 🟡 Medio | No (file personale, non nel repo) |

---

## Vincoli

1. **NON** salvare in CLAUDE.md o nel repository git
2. **NON** duplicare memory esistenti — aggiorna quelle che ci sono
3. **SEMPRE** applicare il filtro "vale la pena salvare?" per le lezioni (Step 1-3)
4. **SEMPRE** produrre l'output strutturato RETROSPECTIVE anche se 0 lezioni
5. **SEMPRE** scrivere la memoria episodica (Step 4) — anche se 0 lezioni astratte

### Pulizia Episodica — Regola di Rotazione

<EXTREMELY-IMPORTANT>
Le memorie episodiche crescono ogni sessione. Senza pulizia, MEMORY.md
supera il limite di 200 righe e il contesto si perde per troncamento.
</EXTREMELY-IMPORTANT>

**Prima di scrivere un nuovo file episodico:**

1. Conta i file episodici esistenti (`project_session_*.md`) nella directory memory/
2. Se ce ne sono **>= 5**, elimina il piu' vecchio (per data nel filename)
3. Rimuovi la riga corrispondente da MEMORY.md

**Eccezione:** NON eliminare file episodici che riferiscono branch/PR ancora aperti.
Verifica con `gh pr list --state open` prima di eliminare.

**Regola:** massimo 5 file episodici in memoria. Le lezioni astratte (feedback, user,
reference) non hanno limite di rotazione — restano finche' sono rilevanti.
