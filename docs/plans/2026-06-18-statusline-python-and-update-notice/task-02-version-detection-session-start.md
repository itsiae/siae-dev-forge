# Task 02 — Feature 2a: detection cambio versione (session-start)

**Stato:** [DONE]
**File toccati:** `tests/hooks/test_session_start_plugin_update.sh` (nuovo), `hooks/session-start`
**AC coperti:** 4, 5, 6 (parte detection), 7, 8
**Stima:** Umano ~1.5 · Augmented ~0.75

## Ciclo TDD

### RED — scrivi il test (deve fallire)

Crea `tests/hooks/test_session_start_plugin_update.sh`. Poiché `session-start` è un hook
complesso (rete, identità), il test estrae e prova la funzione `_devforge_detect_plugin_update`
in isolamento sorgendola da un ambiente controllato, OPPURE — più semplice e robusto —
definisce inline una copia della funzione e ne testa la logica con `PLUGIN_ROOT`,
`DEVFORGE_SESSION_DIR` e `HOME` fittizi.

Scelta: testare la funzione **estraendola** dal file `hooks/session-start` non è banale (è
embedded). Per robustezza, il test verifica il **contratto osservabile**: dato un sandbox
`HOME` e una `DEVFORGE_SESSION_DIR`, dopo l'esecuzione della funzione i file
`~/.claude/.devforge-plugin-version` e `${DEVFORGE_SESSION_DIR}/.plugin-updated` hanno il
contenuto atteso. Il test sorgia la funzione via `source <(sed -n '/_devforge_detect_plugin_update()/,/^}/p' hooks/session-start)`.

```bash
#!/usr/bin/env bash
# Test: _devforge_detect_plugin_update — first-run / no-change / change / dev-mode (Feature 2a)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK="$(cd "$SCRIPT_DIR/../../hooks" && pwd)/session-start"
PASS=0; FAIL=0

# Estrae la funzione dal hook reale (single source of truth)
extract_fn() { sed -n '/^_devforge_detect_plugin_update()/,/^}/p' "$HOOK"; }

run_case() {
  local desc="$1" plugin_root="$2" last_seen_init="$3"
  local tmp; tmp="$(mktemp -d)"
  export HOME="$tmp/home"; mkdir -p "$HOME/.claude"
  export PLUGIN_ROOT="$plugin_root"
  export DEVFORGE_SESSION_DIR="$tmp/session"; mkdir -p "$DEVFORGE_SESSION_DIR"
  [ -n "$last_seen_init" ] && printf '%s' "$last_seen_init" > "$HOME/.claude/.devforge-plugin-version"
  # shellcheck disable=SC1090
  source <(extract_fn)
  _devforge_detect_plugin_update || true
  # echo risultati per asserzione dal chiamante
  printf '%s|%s' \
    "$(cat "$HOME/.claude/.devforge-plugin-version" 2>/dev/null || echo MISSING)" \
    "$(cat "$DEVFORGE_SESSION_DIR/.plugin-updated" 2>/dev/null || echo NOFLAG)"
  rm -rf "$tmp"
}

assert_eq() { # desc expected actual
  if [ "$2" = "$3" ]; then PASS=$((PASS+1)); echo "  PASS  $1";
  else FAIL=$((FAIL+1)); echo "  FAIL  $1 (atteso='$2' ottenuto='$3')"; fi
}

# Caso A — first-run (no last-seen): scrive versione, nessun flag
R="$(run_case "first-run" "/x/siae-devforge/1.91.0" "")"
assert_eq "first-run: last_seen scritto, no flag" "1.91.0|NOFLAG" "$R"

# Caso B — no-change (last-seen == current): nessun flag
R="$(run_case "no-change" "/x/siae-devforge/1.91.0" "1.91.0")"
assert_eq "no-change: nessun flag" "1.91.0|NOFLAG" "$R"

# Caso C — change (last-seen != current): flag scritto + last-seen aggiornato
R="$(run_case "change" "/x/siae-devforge/1.92.0" "1.91.0")"
assert_eq "change: flag=1.92.0, last-seen aggiornato" "1.92.0|1.92.0" "$R"

# Caso D — dev-mode non-semver senza jq: skip silenzioso (last-seen invariato/non scritto, no flag)
# PLUGIN_ROOT basename = "siae-dev-forge" (non semver). Senza jq disponibile resta non-determinabile.
R="$(run_case "dev-mode" "/x/siae-dev-forge" "")"
assert_eq "dev-mode: nessuna scrittura, no flag" "MISSING|NOFLAG" "$R"

echo "  TOTALE: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
```

> Nota caso D: il test assume che `jq` possa risolvere `plugin.json` solo se il file esiste in
> `$PLUGIN_ROOT/.claude-plugin/plugin.json`. Nel sandbox `/x/siae-dev-forge` quel file non esiste,
> quindi la branch jq non trova nulla e la guard semver post-fallback fa `return 0` → nessuna scrittura.

Esegui: `bash tests/hooks/test_session_start_plugin_update.sh` → DEVE fallire (funzione inesistente, `extract_fn` vuoto).

### GREEN — implementa

In `hooks/session-start`, il punto di inserimento è subito **dopo** la creazione di
`DEVFORGE_SESSION_DIR` (righe 28-29) e **prima** dell'inizio del blocco di identity resolution.
Ancora di riferimento (righe 27-31 reali del file):

```bash
# Create session state directory
DEVFORGE_SESSION_DIR="${HOME}/.claude/devforge-state/${DEVFORGE_SID}"
mkdir -p "${DEVFORGE_SESSION_DIR}/outbox/acked"
# ↑↑↑ INSERISCI QUI SOTTO la funzione + chiamata ↓↓↓
# Resolve raw identity (before canonicalization)   ← questa riga (~32) resta INVARIATA, viene dopo
USER_RAW_EMAIL=""
```

La funzione usa solo `PLUGIN_ROOT` (riga 16), `HOME`, `DEVFORGE_SESSION_DIR` (riga 28) — tutti già
definiti a questo punto. NON dipende da `USER_RAW_EMAIL`/`IDENTITY_BUNDLE` ecc. Inserire il blocco
esattamente tra `mkdir -p ".../outbox/acked"` e il commento `# Resolve raw identity`:

```bash
# --- Notifica aggiornamento plugin (Feature 2a) — pure-local, no rete ---
_devforge_detect_plugin_update() {
  local current last_seen_file last_seen
  current="$(basename "$PLUGIN_ROOT")"
  # Dev-mode (repo non versionato): basename non è semver → fallback plugin.json
  if ! printf '%s' "$current" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+'; then
    if command -v jq >/dev/null 2>&1 && [ -f "${PLUGIN_ROOT}/.claude-plugin/plugin.json" ]; then
      current="$(jq -r '.version // empty' "${PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null)"
    fi
  fi
  # Post-fallback: se ancora non-semver → versione non determinabile → skip (no scrittura)
  if ! printf '%s' "$current" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+'; then
    return 0
  fi
  [ -z "$current" ] && return 0
  last_seen_file="${HOME}/.claude/.devforge-plugin-version"
  last_seen=""
  [ -f "$last_seen_file" ] && IFS= read -r last_seen < "$last_seen_file" 2>/dev/null || true
  if [ -z "$last_seen" ]; then
    printf '%s' "$current" > "$last_seen_file" 2>/dev/null || true   # prima installazione: nessun avviso
    return 0
  fi
  if [ "$last_seen" != "$current" ]; then
    printf '%s' "$current" > "${DEVFORGE_SESSION_DIR}/.plugin-updated" 2>/dev/null || true
    printf '%s' "$current" > "$last_seen_file" 2>/dev/null || true
  fi
}
_devforge_detect_plugin_update >/dev/null 2>&1 || true
```

Riesegui il test → DEVE passare (PASS=4, FAIL=0).

### REFACTOR

Verifica che la funzione non emetta nulla su stdout (catturato con `>/dev/null 2>&1`) per non
corrompere il JSON `additional_context`. Nessun altro refactor.

## Criteri di completamento

- [ ] Test `test_session_start_plugin_update.sh` esiste e passa (PASS=4, FAIL=0)
- [ ] first-run scrive last-seen, no flag
- [ ] no-change non scrive flag
- [ ] change scrive flag + aggiorna last-seen
- [ ] dev-mode non-semver senza jq → nessuna scrittura (skip silenzioso)
- [ ] `session-start` resta sotto `set -euo pipefail`, chiamata guardata con `>/dev/null 2>&1 || true`
