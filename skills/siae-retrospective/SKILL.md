---
name: siae-retrospective
description: >
  Estrae lezioni apprese a fine sessione e le persiste in auto-memory.
  Trigger: fine sessione, lezioni apprese, cosa ho imparato, retrospettiva,
  salva per la prossima volta, /forge-retro, REQUIRED da stop-gate hook
  per sessioni produttive (almeno 1 commit).
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

**Output strutturato obbligatorio:**

```
RETROSPECTIVE
═════════════
Sessione: YYYY-MM-DD
Skills usate: N | Commits: M

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
2. **NON** salvare riassunti di attivita' (c'e' git log)
3. **NON** duplicare memory esistenti — aggiorna quelle che ci sono
4. **SEMPRE** applicare il filtro "vale la pena salvare?" prima di persistere
5. **SEMPRE** produrre l'output strutturato RETROSPECTIVE anche se 0 lezioni
