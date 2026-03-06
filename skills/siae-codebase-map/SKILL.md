---
name: siae-codebase-map
description: >
  mappa questo codebase, documenta l'architettura, /forge-map, onboarding su
  progetto sconosciuto, codebase > 50 file senza docs/CODEBASE_MAP.md
---

# SIAE Codebase Map

```
╔══════════════════════════════════════════════════════════════════╗
║    ███████╗██╗ █████╗ ███████╗    ██████╗ ███████╗██╗   ██╗      ║
║    ██╔════╝██║██╔══██╗██╔════╝    ██╔══██╗██╔════╝██║   ██║      ║
║    ███████╗██║███████║█████╗      ██║  ██║█████╗  ██║   ██║      ║
║    ╚════██║██║██╔══██║██╔══╝      ██║  ██║██╔══╝  ╚██╗ ██╔╝      ║
║    ███████║██║██║  ██║███████╗    ██████╔╝███████╗ ╚████╔╝       ║
║    ╚══════╝╚═╝╚═╝  ╚═╝╚══════╝    ╚═════╝ ╚══════╝  ╚═══╝        ║
║              🗺️ DevForge · SIAE Codebase Map                     ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Tipo:** Flexible | **Fase SDLC:** 1. Init & Setup

**Principio fondamentale:** Claude Opus orchestra, Sonnet legge.
Non far leggere i file del codebase a Opus direttamente — sempre via subagent Sonnet.

---

## Requisiti

```bash
# tiktoken per il conteggio token (gestito automaticamente con uv)
pip install tiktoken
# oppure: uv pip install tiktoken
```

---

## Step 1 — Controlla mappa esistente

**Check esistenza (permission-free):** `Glob("docs/CODEBASE_MAP.md")`

**Se `docs/CODEBASE_MAP.md` esiste:**
1. `Read("docs/CODEBASE_MAP.md")` — leggi il campo `last_mapped` dal frontmatter YAML
2. Controlla i cambiamenti da quella data:
   - **Con Bash:** `git log --oneline --since="<last_mapped>"`
   - **Se Bash negato:** informa l'utente e chiedi di eseguire il comando, oppure procedi con Update Mode per sicurezza
3. Se ci sono modifiche significative → Update Mode (vai al Step 2)
4. Se nessun cambiamento → informa l'utente che la mappa è aggiornata

**Se non esiste:** vai al Step 2 (full mapping).

---

## Step 2 — Scansione del codebase

Esegui lo scanner per ottenere l'albero dei file con conteggio token:

```bash
# Opzione 1: UV (preferita — installa tiktoken automaticamente)
uv run ${CLAUDE_PLUGIN_ROOT}/skills/siae-codebase-map/scripts/scan-codebase.py . --format json

# Opzione 2: Python diretto (richiede tiktoken installato)
python3 ${CLAUDE_PLUGIN_ROOT}/skills/siae-codebase-map/scripts/scan-codebase.py . --format json
```

Output: albero file con token per file, totale token, file skippati.

---

## Step 3 — Pianifica i subagent

Budget per subagent: **150.000 token** (margine sicuro sotto il limite Sonnet 200k).

**Strategia di raggruppamento:**
1. Raggruppa per directory/modulo (mantieni codice correlato insieme)
2. Bilancia i token tra i gruppi
3. Punta a subagent piccoli e numerosi piuttosto che pochi e grandi

**Mapping stack SIAE → raggruppamento:**

| Stack | Strategia |
|-------|-----------|
| **Java** | Per modulo Maven (`src/main/java/it/siae/<modulo>`) |
| **TypeScript** | Per layer (`src/handlers/`, `src/services/`, `src/repositories/`) |
| **Python/Glue** | Per job (`jobs/`, `utils/`, `tests/`) |
| **IaC** | Per ambiente/modulo (`live/`, `modules/`) |
| **Frontend Vue** | Per feature/dominio + `src/components/`, `src/views/`, `src/stores/` |

---

## Step 4 — Dispatch subagent Sonnet in parallelo

**CRITICO: Dispatcha TUTTI i subagent in un singolo messaggio** (chiamate Task parallele).

Usa `subagent_type: "Explore"` e `model: "sonnet"` per ogni gruppo.

**Template prompt subagent:**

```
Stai mappando una parte del codebase SIAE. Leggi e analizza questi file:
- [lista file del gruppo]

Per ogni file documenta:
1. **Scopo**: descrizione in una riga
2. **Export/API pubbliche**: funzioni, classi, tipi esposti
3. **Dipendenze**: import notevoli
4. **Pattern**: convenzioni di design usate
5. **Gotcha**: comportamenti non ovvi, edge case, warning

Identifica anche:
- Come questi file si collegano tra loro
- Entry point e flusso dati
- Dipendenze da config/environment SIAE

Rispondi in markdown con header chiari per file/modulo.
```

---

## Step 5 — Sintetizza i report

1. **Merge** tutti i report dei subagent
2. **Deduplicazione** analisi sovrapposte
3. **Cross-cutting concerns** (pattern trasversali, gotcha comuni)
4. **Diagramma architetturale** con relazioni tra moduli (Mermaid)
5. **Navigation paths** per task comuni SIAE

---

## Step 6 — Scrivi `docs/CODEBASE_MAP.md`

**Prima di scrivere, recupera il timestamp reale:**
```bash
date -u +"%Y-%m-%dT%H:%M:%SZ"
```

🟡 MEDIO — Mostra pre-flight card prima di scrivere

```bash
echo '{
  "level": "MEDIO",
  "skill": "siae-codebase-map",
  "context": [
    {"emoji": "📊", "label": "File analizzati", "value": "<N> file, <N> token"},
    {"emoji": "🤖", "label": "Subagent", "value": "<N> report sintetizzati"}
  ],
  "actions": [
    {"emoji": "✏️", "label": "Scrittura mappa codebase", "path": "docs/CODEBASE_MAP.md"}
  ],
  "reason": "Analisi completa, mappa pronta per scrittura",
  "ifno": "La mappa non viene scritta, analisi disponibile solo in chat"
}' | python3 design-system/generate-card.py
```

Struttura del file:

````markdown
---
last_mapped: YYYY-MM-DDTHH:MM:SSZ
total_files: N
total_tokens: N
stack: [java|ts-frontend|ts-backend|python|iac]
---

# Codebase Map — [Nome Progetto]

> Auto-generato da DevForge siae-codebase-map. Ultimo aggiornamento: [data]

## Panoramica Sistema

[Diagramma Mermaid architettura ad alto livello]

## Struttura Directory

[Albero con annotazioni scopo]

## Guida Moduli

### [Nome Modulo]
**Scopo**: [descrizione]
**Entry point**: [file]
**File chiave**:
| File | Scopo | Token |
|------|-------|-------|

**Export principali**: [API]
**Dipendenze**: [cosa usa]
**Dipendenti**: [chi la usa]

## Flusso Dati

[Sequence diagram Mermaid per flussi principali]

## Convenzioni SIAE Osservate

[Naming, pattern, stile rilevati]

## Gotcha

[Comportamenti non ovvi, warning]

## Navigation Guide

**Per aggiungere un endpoint**: [file da toccare]
**Per aggiungere un componente**: [file da toccare]
**Per modificare l'autenticazione**: [file da toccare]
````

---

## Step 7 — Aggiorna `CLAUDE.md`

🟡 MEDIO — Mostra pre-flight card prima di aggiornare

```bash
echo '{
  "level": "MEDIO",
  "skill": "siae-codebase-map",
  "context": [
    {"emoji": "📋", "label": "Sezione", "value": "Architettura Codebase"},
    {"emoji": "🔄", "label": "Tipo", "value": "<nuovo | aggiornamento>"}
  ],
  "actions": [
    {"emoji": "📝", "label": "Aggiornamento sezione architettura", "path": "CLAUDE.md"}
  ],
  "reason": "Mappa aggiornata, CLAUDE.md da sincronizzare",
  "ifno": "CLAUDE.md non aggiornato, future sessioni usano info vecchie"
}' | python3 design-system/generate-card.py
```

Aggiungi o aggiorna la sezione architettura:

```markdown
## Architettura Codebase

[2-3 frasi di sintesi]

**Stack**: [tecnologie principali]
**Struttura**: [layout ad alto livello]

Per l'architettura dettagliata: [docs/CODEBASE_MAP.md](docs/CODEBASE_MAP.md)
```

---

## Update Mode

Quando la mappa esiste già:

1. Identifica file cambiati da git o diff scanner
2. Dispatcha subagent SOLO per i moduli cambiati
3. Merge dell'analisi nuova con la mappa esistente
4. Aggiorna `last_mapped` con il timestamp reale (`date -u`)
5. Preserva le sezioni non modificate

---

## Budget Token di Riferimento

| Modello | Context | Budget sicuro per subagent |
|---------|---------|--------------------------|
| Sonnet  | 200k    | 150.000 token |
| Haiku   | 200k    | 100.000 token (economico, meno preciso) |

---

## Classificazione Rischio Operazioni

| Operazione | Livello | Card |
|-----------|---------|------|
| Controllo mappa esistente | 🟢 Sicuro | No |
| Scansione codebase (scanner) | 🟢 Sicuro | No |
| Dispatch subagent Explore | 🟡 Medio | No |
| Scrittura `docs/CODEBASE_MAP.md` | 🟡 Medio | Si |
| Aggiornamento `CLAUDE.md` | 🟡 Medio | Si |
| Git commit | 🟡 Medio | No (commit locale) |

---

## Permission Denied Handling

**Step 1 (Controlla mappa) — parzialmente permission-free:**
- `Glob("docs/CODEBASE_MAP.md")` + `Read` — permission-free
- `git log`: se Bash negato, chiedi all'utente o procedi con Update Mode

**Step 2 (Scansione codebase) — fallback permission-free:**
- **Con Bash:** usa lo scanner Python (`scan-codebase.py`)
- **Se Bash negato:** usa `Glob("**/*.{java,ts,py,tf,vue,hcl}")` per ottenere l'albero file. Non avrai il conteggio token, ma la struttura directory e' sufficiente per pianificare i subagent

**Step 6-7 (Scrivi CODEBASE_MAP.md e CLAUDE.md) — Write richiesto:**
- **Se Write negato:** presenta il contenuto completo del documento come output testuale in chat
- Indica il path dove salvarlo: `docs/CODEBASE_MAP.md`
- L'utente puo' copiare manualmente

**Fasi completabili senza permessi:** Step 1 (Glob/Read), Step 2 (Glob fallback), Step 3-5 (subagent/analisi)
**Fasi che richiedono permessi:** Step 2 (Bash per scanner), Step 6-7 (Write per output file)

Se i permessi sono negati:
1. Completa tutte le fasi di analisi con Glob/Read/subagent
2. Presenta il documento generato come output testuale
3. NON entrare in loop di retry su tool negato
4. NON dichiarare completamento per fasi non eseguite

---

## Troubleshooting

| Problema | Soluzione |
|----------|-----------|
| `tiktoken not installed` | `pip install tiktoken` oppure usa `uv run` |
| `python not found` | Prova `python3`, `python`, o `uv run` |
| Codebase troppo grande | Aumenta il numero di subagent, limita a `src/` |
| Git non disponibile | Usa il diff del conteggio file come fallback |
