# Task 00 — Spike: verifica bloccante cross-platform

**Stato:** PENDING
**Tipo:** Spike (investigazione; output = nota decisionale, nessun codice di produzione)
**Dipende da:** nessuno
**Blocca:** task-02, task-03, task-08
**Output:** `docs/plans/2026-06-14-dev-identity-rootcause-crossplatform/findings-task-00.md`

## Obiettivo
Risolvere empiricamente le due incognite che biforcano il design (BLOCK-1, BLOCK-3):
1. `node` è su PATH negli hook Claude Code su Windows nativo?
2. Claude Code onora `CLAUDE_CONFIG_DIR` (mac + Windows)?

## Procedura
1. **node su PATH (proxy telemetrico):** misurare la frequenza del warning catalogo
   emesso quando `node` manca in `hooks/session-start:194` (skills-core.js).
   - Locale: contare in `~/.claude/devforge-activity.jsonl` gli eventi con fallback catalogo.
   - S3: filtrare per host/OS Windows e calcolare la % di sessioni con `node` assente.
2. **node negli hook (test diretto):** su una macchina Windows con Claude Code nativo +
   Git for Windows, eseguire un hook di prova che stampa
   `command -v node || echo MISSING` e `command -v python3 || echo MISSING`. Registrare l'esito.
3. **CLAUDE_CONFIG_DIR:** su mac e Windows lanciare Claude Code con
   `CLAUDE_CONFIG_DIR=/tmp/persona-A` e verificare quale file viene letto
   (`$CLAUDE_CONFIG_DIR/.claude.json` vs `~/.claude.json`) tramite il probe del task-08.

## Criteri di accettazione
- `findings-task-00.md` documenta: (a) % sessioni Windows con node assente; (b) esito node/python3 negli hook Windows; (c) `CLAUDE_CONFIG_DIR` onorato si/no su mac e Win.
- Decisione registrata: F2 node-first (se node affidabile) **oppure** python3 prerequisito Windows obbligatorio nell'installer; P2 isolamento via `CLAUDE_CONFIG_DIR` **oppure** fallback HOME-isolato obbligatorio.

## Nota di sblocco
Se una macchina Windows non è disponibile in sessione, il task produce comunque il
piano di misura + la decisione condizionale esplicita. I task a valle NON restano
bloccati: implementano la fallback chain completa (`node→python3→degraded`), corretta
in ENTRAMBI gli esiti. La verifica empirica determina solo il prerequisito documentato
nell'installer, non la logica del codice.
