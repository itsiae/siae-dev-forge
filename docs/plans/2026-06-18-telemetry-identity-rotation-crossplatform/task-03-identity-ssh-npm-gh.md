# Task 03 — Segnali identità SSH / npm / gh (Capability A)

**AC:** AC1, AC2, AC5 · **File:** `lib/logger.sh`, `tests/zero-loss/unit/test_logger_identity_signals.sh`

## Obiettivo

Estendere i segnali identità con `ssh_fingerprint`, `npm_email`, `gh_email`. Nessuna rete nel path
di default: `gh_email` opt-in; `npm_email` locale + timeout-guard. Determinismo e normalizzazione.

## RED — test che fallisce

Aggiungi a `test_logger_identity_signals.sh`:
- SSH 0 chiavi (`~/.ssh` vuota) → `ssh_fingerprint` vuoto, nessun abort.
- SSH 2 chiavi → fingerprint **deterministico** (stesso valore su 2 invocazioni; prima `*.pub` per `sort`).
- npm che stampa `undefined` (shim `npm` fake) → `npm_email` normalizzato a "" (non "undefined").
- `gh_email` opt-in: senza `DEVFORGE_IDENTITY_GH=1`, `gh` NON viene invocato (shim `gh` che scrive
  un marker file → marker assente). Con `=1`, invocato con timeout.
- Atteso PRE-fix: FAIL.

## GREEN — implementazione

```bash
_devforge_local_identity_signals_tools() {
    local ssh_fp="" npm_email="" gh_email="" key
    # SSH: prima chiave pubblica in ordine, hash via helper portabile. Mai chiavi private.
    if [ -d "${HOME}/.ssh" ]; then
        key=$(ls -1 "${HOME}/.ssh/"*.pub 2>/dev/null | sort | head -1)
        if [ -n "$key" ] && [ -r "$key" ]; then
            ssh_fp=$(ssh-keygen -lf "$key" 2>/dev/null | awk '{print $2}' | head -1 | tr -d '\r' || true)
        fi
    fi
    # npm: locale, guard + timeout (net_run) + normalizza undefined/null/""
    if command -v npm >/dev/null 2>&1; then
        local _v
        _v=$(net_run 2 npm config get email 2>/dev/null | head -1 | tr -d '\r' || true)
        case "$_v" in undefined|null|"") _v="" ;; esac
        npm_email="$_v"
    fi
    # gh: OPT-IN (rete) — default off per non bloccare session-start su proxy SIAE
    if [ "${DEVFORGE_IDENTITY_GH:-}" = "1" ] && command -v gh >/dev/null 2>&1; then
        gh_email=$(net_run 3 gh api user --jq '.email' 2>/dev/null | head -1 | tr -d '\r' || true)
        case "$gh_email" in null) gh_email="" ;; esac
    fi
    printf '%s\t%s\t%s' "$ssh_fp" "$npm_email" "$gh_email"
}
```

**Timeout via `net_run` esistente** (BLOCK-1): `lib/net-timeout.sh` espone già `net_run <secs> <cmd...>`
(portabile, no binario `timeout`). NON creare un wrapper nuovo. `logger.sh` **non** sorgenzia
`net-timeout.sh` oggi → aggiungere in cima a `lib/logger.sh` (dopo la def di `DEVFORGE_LIB_DIR`,
~riga 57), un source guardato e idempotente:

```bash
# net_run per timeout portabili nei segnali identità (best-effort: assenza = nessun timeout, no abort)
if ! command -v net_run >/dev/null 2>&1 && [ -f "${DEVFORGE_LIB_DIR}/net-timeout.sh" ]; then
    # shellcheck disable=SC1091
    . "${DEVFORGE_LIB_DIR}/net-timeout.sh" 2>/dev/null || true
fi
```
Fallback difensivo dentro le chiamate: se `net_run` resta indefinito (file assente), sostituire con
chiamata diretta guardata `command -v net_run >/dev/null 2>&1 && net_run 2 ... || (npm ... )` —
ma con il source sopra è garantito presente.

## REFACTOR

Verifica che il source di `net-timeout.sh` non introduca side-effect (la lib definisce solo
funzioni). Commenti opt-in/parità. Nessun duplicato di timeout.

## Verifica / Done

- `bash tests/zero-loss/unit/test_logger_identity_signals.sh` PASS (parte tools).
- No-regression suite verde. Marca `[DONE]`.
