# Design: TDD Gate — Skip file esterni al repo

**Data:** 2026-03-30
**Autore:** DevForge Brainstorming
**Stato:** Approvato
**Story Points:** 2 SP-Umano / 1 SP-Augmented

## Contesto

Il TDD gate (`hooks/tdd-gate`) blocca Edit/Write su file con estensione produzione
(`.py`, `.ts`, `.java`, ecc.) se `siae-tdd` non e' stata invocata nella sessione.

**Problema:** Il gate blocca anche file che si trovano **fuori dal repository corrente**
(es. script one-shot in `~/hackhathon siae2026/genera_traccia.py`). Questi file non
sono codice di produzione del progetto e non dovrebbero essere soggetti al gate TDD.

## Decisione

**Approccio A: File fuori dal repo git → ALLOW**

Aggiungere un check nel `tdd-gate` dopo l'estrazione di `FILE_PATH` e prima del check
estensione. Se il file non e' sotto la working directory del repo DevForge → ALLOW.

### Approcci scartati

- **Whitelist directory** (`scripts/`, `tools/`): troppo specifico, non copre file in root
  o in altri repository.
- **Non git-tracked + non in src/**: piu' complesso, rischio false negative per file nuovi
  legittimi. Incrementabile in futuro se necessario.

## Implementazione

### Dove: `hooks/tdd-gate`, dopo riga 26 (check FILE_PATH vuoto), prima di riga 29

### Logica

```bash
# Skip files outside the plugin's git repository
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
GIT_ROOT="$(git -C "$HOOK_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
if [ -n "$GIT_ROOT" ] && [[ "$FILE_PATH" != "$GIT_ROOT"/* ]]; then
    echo '{}'
    exit 0
fi
```

### Comportamento

| Scenario | FILE_PATH | Risultato |
|----------|-----------|-----------|
| File in altro repo | `/Users/x/hackhathon/genera.py` | ALLOW (fuori repo) |
| File in /tmp | `/tmp/script.py` | ALLOW (fuori repo) |
| File produzione in repo | `hooks/../src/main.py` | Prosegui check normali |
| File test in repo | `tests/foo.test.ts` | ALLOW (excluded path, come prima) |
| git non disponibile | qualsiasi | Skip check, prosegui normalmente |

### Gestione errori

- `git rev-parse` fallisce → `GIT_ROOT=""` → check saltato (graceful fallback)
- Path con spazi → gestito da double-quoting

## Criteri di accettazione

- [ ] File con estensione prod fuori dal repo non vengono bloccati
- [ ] File con estensione prod dentro il repo continuano ad essere bloccati senza siae-tdd
- [ ] Se git non e' disponibile, il gate funziona come prima (nessuna regressione)
- [ ] Path con spazi funzionano correttamente

## Rischi

- **Basso:** nessun impatto sulla protezione interna al repo
- Il check e' puramente additivo (nuovo exit point prima dei check esistenti)
