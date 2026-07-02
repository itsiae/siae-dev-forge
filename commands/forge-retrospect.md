---
name: forge-retrospect
description: >
  Auto-retrospective DevForge (port di headroom learn). Estrae lezioni dai
  fallimenti ripetuti dell'ultima sessione (mining del transcript rilevato dal
  hook session-end) e le propone a CLAUDE.md / memory con dry-run/apply.
  Scope personale, nessun dato lascia la macchina.
---

# /forge-retrospect

Invoca la skill `siae-devforge:forge-retrospect` per chiudere il loop "non ripetere
gli stessi errori". Tre modi:

| Invocazione | Modo | Effetto |
|---|---|---|
| `/forge-retrospect` | **MINE** (default) | Analizza il record pending più recente, propone un DIFF di lezioni — **dry-run, non scrive nulla**. |
| `/forge-retrospect --apply` | **APPLY** | Scrive le lezioni dentro la sezione marker `<!-- devforge:retro:start/end -->` di `~/.claude/CLAUDE.md` / memory (idempotente), poi consuma il record. |
| `/forge-retrospect --dismiss` | **DISMISS** | Rimuove il record pending senza scrivere nulla. |

## Cosa fa MINE

1. Trova il record pending più recente in `~/.claude/devforge-state/retro-pending/*.json`
   (scritto dal hook `session-end` quando rileva ≥3 errori o un pattern `(tool,categoria)` ripetuto).
   Se nessuno: "Nessun fallimento pendente." e termina.
2. Costruisce il digest compresso dal `transcript_path` del record:
   ```bash
   python3 -c "from lib.retro.digest import build_digest; print(build_digest('<transcript_path>'))"
   ```
3. Classifica le lezioni con `evidence_count ≥ 2` in `context_file_rule` (CLAUDE.md, fatti stabili)
   vs `memory_file_rule` (memory/, preferenze evolutive).
4. Mostra il DIFF proposto in dry-run (nessuna scrittura).

## Note

- **Dry-run è il default**: nessuna scrittura su CLAUDE.md/memory senza `--apply`.
- Riusa la cornice analitica di `siae-retrospective` (non la duplica).
- Solo-lettura finché non usi `--apply`. Le lezioni team-wide ricorrenti sono un follow-on
  (vedi `docs/plans/2026-06-22-auto-retrospective-design.md` §9).
