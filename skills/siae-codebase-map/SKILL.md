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

**Se `docs/CODEBASE_MAP.md` esiste:**
1. Leggi il campo `last_mapped` dal frontmatter YAML
2. Controlla i cambiamenti da quella data:
   ```bash
   git log --oneline --since="<last_mapped>"
   ```
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

## Troubleshooting

| Problema | Soluzione |
|----------|-----------|
| `tiktoken not installed` | `pip install tiktoken` oppure usa `uv run` |
| `python not found` | Prova `python3`, `python`, o `uv run` |
| Codebase troppo grande | Aumenta il numero di subagent, limita a `src/` |
| Git non disponibile | Usa il diff del conteggio file come fallback |
