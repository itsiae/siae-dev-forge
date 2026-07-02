---
name: forge-retrospect
description: Auto-retrospective DevForge — estrae lezioni dai fallimenti ripetuti dell'ultima sessione (mining del transcript) e le propone a CLAUDE.md/memory con dry-run/apply. Trigger - "/forge-retrospect", nudge a inizio sessione su fallimenti pendenti.
---

# forge-retrospect — Auto-retrospective (port di headroom learn)

> **Tipo:** On-demand · **Fase SDLC:** Retrospettiva · **Scope:** personale (CLAUDE.md + memory dell'utente)
> Riusa la cornice analitica di `siae-retrospective` per la qualita' delle lezioni; qui aggiunge il loop automatico detect->mine->apply. NON duplica `siae-retrospective`.

## File

- `lib/retro/digest.py` — parser transcript + build_digest (digest compresso per MINE)
- `lib/retro/writer.py` — merge_into_text + write_lessons (marker-section idempotente)
- `lib/retro/scan.py` — DETECT light (soglia errori/pattern, scrive in retro-pending)
- `lib/retro/nudge.py` — NUDGE (una riga sentinel-based, invocata da session-start)
- `~/.claude/devforge-state/retro-pending/` — staging record leggeri

## Modi

### MINE (default — dry-run, NON scrive nulla)

1. Trova il record pending piu' recente in `~/.claude/devforge-state/retro-pending/*.json`.
   Se nessuno: "Nessun fallimento pendente." e termina.
2. Costruisci il digest dal `transcript_path` del record:
   `python3 -c "from lib.retro.digest import build_digest; print(build_digest('<transcript_path>'))"`
3. Analizza il digest INLINE (sei gia' in una sessione Claude — nessun subprocess `claude -p`).
   Estrai lezioni che:
   - hanno `evidence_count` >= 2 (il pattern compare almeno 2 volte — categoria ripetuta o stesso fallimento poi risolto);
   - classifica ognuna come `context_file_rule` (fatto stabile -> CLAUDE.md) o `memory_file_rule` (preferenza evolutiva -> memory/);
   - per i `context_file_rule`, dai `section` (es. nome tool/tema) e `content` (bullet markdown actionable).
4. Mostra il DIFF proposto SENZA scrivere, usando il writer in dry-run:
   `python3 -c "from lib.retro.writer import Lesson, write_lessons; from pathlib import Path; print(write_lessons(Path.home()/'.claude'/'CLAUDE.md', [Lesson('<section>','<content>')], apply=False))"`
5. Chiedi conferma: "Applico con --apply o ignoro con --dismiss?"

### APPLY (`/forge-retrospect --apply`)

1. Stessa analisi di MINE.
2. Scrivi le lezioni con `write_lessons(..., apply=True)`:
   - `context_file_rule` -> `~/.claude/CLAUDE.md` (sezione marker `<!-- devforge:retro:start/end -->`);
   - `memory_file_rule` -> nuovo file in `~/.claude/projects/<hash>/memory/` + pointer in `MEMORY.md` (convenzione memory).
3. Rimuovi il record pending consumato (`rm` del `<sid>.json` in `retro-pending`).
4. Conferma cosa e' stato scritto (idempotente: re-apply non duplica, sezioni umane intatte).

### DISMISS (`/forge-retrospect --dismiss`)

1. Rimuovi il record pending senza scrivere nulla. Conferma "ignorato".

## Vincoli

- Dry-run e' il default: nessuna scrittura su CLAUDE.md/memory senza `--apply`.
- Mai inventare lezioni: ogni lezione deve citare l'evidenza dal digest (`evidence_count` >= 2).
- Scope personale: nessun dato lascia la macchina.
- Per lezioni team-wide ricorrenti -> backlog (Approccio 3 batch-S3, vedi design).
