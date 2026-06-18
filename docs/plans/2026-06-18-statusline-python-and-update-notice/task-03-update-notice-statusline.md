# Task 03 — Feature 2b: display flag aggiornamento (statusline)

**Stato:** [PENDING]
**File toccati:** `tests/statusline/test_statusline_plugin_update.sh` (nuovo), `statusline/devforge-statusline.sh`
**AC coperti:** 6 (parte display)
**Stima:** Umano ~0.5 · Augmented ~0.25

## Ciclo TDD

### RED — scrivi il test (deve fallire)

Se la dir non esiste ancora (creata nel task-01): `mkdir -p tests/statusline`.

Crea `tests/statusline/test_statusline_plugin_update.sh`. Il test crea una
`DEVFORGE_SESSION_DIR` fittizia, ci scrive il flag `.plugin-updated`, forza lo statusline a
usare quella sid e verifica che l'output contenga "DevForge aggiornato a v...". Poi un caso
senza flag → assenza messaggio.

Per far sì che lo statusline risolva la `DEVFORGE_SESSION_DIR` fittizia, si scrive il SID file
`~/.claude/.devforge-session-id` (in un HOME sandbox) con un sid noto e si crea la dir
corrispondente `~/.claude/devforge-state/<sid>/` con dentro il flag. `devforge_init_session`
(chiamato dallo statusline a riga 25) leggerà quel sid.

```bash
#!/usr/bin/env bash
# Test: statusline mostra avviso aggiornamento quando esiste flag .plugin-updated (Feature 2b)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATUSLINE="$(cd "$SCRIPT_DIR/../../statusline" && pwd)/devforge-statusline.sh"
PASS=0; FAIL=0

setup_home_with_sid() { # sid flag_content(optional)
  local tmp; tmp="$(mktemp -d)"
  mkdir -p "$tmp/.claude/devforge-state/$1"
  printf '%s' "$1" > "$tmp/.claude/.devforge-session-id"
  [ -n "${2:-}" ] && printf '%s' "$2" > "$tmp/.claude/devforge-state/$1/.plugin-updated"
  printf '%s' "$tmp"
}

# --- Caso 1: flag presente → messaggio mostrato ---
H1="$(setup_home_with_sid "testsid1" "1.92.0")"
OUT1="$(printf '{}' | HOME="$H1" bash "$STATUSLINE" 2>/dev/null || true)"
if printf '%s' "$OUT1" | grep -q "DevForge aggiornato a v1.92.0"; then
  PASS=$((PASS+1)); echo "  PASS  flag presente → avviso aggiornamento mostrato"
else
  FAIL=$((FAIL+1)); echo "  FAIL  flag presente → avviso NON mostrato"; printf 'OUT: %s\n' "$OUT1"
fi
rm -rf "$H1"

# --- Caso 2: nessun flag → nessun messaggio ---
H2="$(setup_home_with_sid "testsid2" "")"
OUT2="$(printf '{}' | HOME="$H2" bash "$STATUSLINE" 2>/dev/null || true)"
if printf '%s' "$OUT2" | grep -q "DevForge aggiornato"; then
  FAIL=$((FAIL+1)); echo "  FAIL  nessun flag → avviso mostrato erroneamente"
else
  PASS=$((PASS+1)); echo "  PASS  nessun flag → nessun avviso"
fi
rm -rf "$H2"

echo "  TOTALE: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
```

> Nota diagnostica (verificata col plan-reviewer): il percorso principale (sandbox `HOME` + SID file)
> FUNZIONA — `devforge_init_session` (lib/logger.sh) ricalcola `DEVFORGE_SID_FILE="${HOME}/.claude/.devforge-session-id"`
> dall'`HOME` del sandbox e ricostruisce `DEVFORGE_SESSION_DIR="${HOME}/.claude/devforge-state/${sid}"`.
> ⚠️ NON usare come fallback `export DEVFORGE_SESSION_DIR=...`: `devforge_init_session` esegue
> un'assegnazione **incondizionata** che sovrascrive qualsiasi valore pre-esportato → il fallback
> non avrebbe effetto. Se il caso 1 fallisce, la causa è la struttura del sandbox HOME (SID file o
> dir mancante), non l'env var: verificare che `~/.claude/.devforge-session-id` e
> `~/.claude/devforge-state/<sid>/.plugin-updated` esistano nell'HOME sandbox.

Esegui: `bash tests/statusline/test_statusline_plugin_update.sh` → DEVE fallire (display non implementato).

### GREEN — implementa

In `statusline/devforge-statusline.sh`, dopo il blocco di lettura state-file (dopo la sezione
"Batch counter" ~riga 147) e prima o dentro la sezione warning (riga ~256), aggiungi la lettura
del flag; poi nella sezione `WARN_STR` aggiungi il segmento di display.

Lettura (insieme agli altri `read_file`, ~riga 147):
```bash
# Plugin update flag (scritto da hooks/session-start)
PLUGIN_UPDATED_VER=""
if [ -n "${DEVFORGE_SESSION_DIR:-}" ] && [ -f "${DEVFORGE_SESSION_DIR}/.plugin-updated" ]; then
  read -r PLUGIN_UPDATED_VER < "${DEVFORGE_SESSION_DIR}/.plugin-updated" 2>/dev/null || true
fi
PLUGIN_UPDATED_VER="${PLUGIN_UPDATED_VER//[^0-9a-zA-Z.\-]/}"
```

Display (nella sezione warning, dopo il blocco python3 del Task 01):
```bash
if [ -n "$PLUGIN_UPDATED_VER" ]; then
  WARN_STR="${WARN_STR:+$WARN_STR }$(printf '%b🆙 DevForge aggiornato a v%s%b' "$GREEN" "$PLUGIN_UPDATED_VER" "$RESET")"
fi
```

Riesegui il test → DEVE passare (PASS=2, FAIL=0).

### REFACTOR

Verifica che la sanitize `[^0-9a-zA-Z.\-]` rimuova `\` e caratteri pericolosi per `printf %b`.
Nessun altro refactor.

## Criteri di completamento

- [ ] Test `test_statusline_plugin_update.sh` esiste e passa (PASS=2, FAIL=0)
- [ ] flag presente → "DevForge aggiornato a vX.Y.Z" (verde)
- [ ] nessun flag → nessun messaggio
- [ ] versione sanitizzata prima di `printf %b`
