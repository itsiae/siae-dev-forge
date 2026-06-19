# Task 02 — Implementa _devforge_ensure_auth + wiring (GREEN)

**Tipo:** impl (TDD GREEN) · **AC:** AC1, AC2, AC3, AC6, AC7 · **File:** `lib/logger.sh`

## Obiettivo

Far passare i test di Task 01 aggiungendo la lazy resolution di `auth_email`.

## Implementazione

### 1. Aggiungi l'helper `_devforge_ensure_auth`

In `lib/logger.sh`, **dopo** `devforge_resolve_auth_identity` (termina a riga ~408) e
**prima** di `devforge_log` (riga ~631). Inserisci:

```sh
# Lazy auth resolution: se DEVFORGE_AUTH_EMAIL non è pinnato (hook senza
# devforge_init_session, o sessione partita con plugin vecchio), risolvi inline
# da ~/.claude.json. Cache flag per-process: 1 lettura max/processo hook.
# Flag settato INCONDIZIONATAMENTE (trade-off documentato in design.md): i processi
# hook sono short-lived, un fallimento transitorio resta confinato al processo corrente.
_devforge_ensure_auth() {
    [ -n "${_DEVFORGE_AUTH_RESOLVED:-}" ] && return 0
    _DEVFORGE_AUTH_RESOLVED=1
    if [ -z "${DEVFORGE_AUTH_EMAIL:-}" ]; then
        local _auth _rest
        _auth=$(devforge_resolve_auth_identity 2>/dev/null || printf '|||')
        DEVFORGE_AUTH_EMAIL="${_auth%%|*}"
        _rest="${_auth#*|}"
        DEVFORGE_AUTH_ACCOUNT_UUID="${_rest%%|*}"
    fi
}
```

### 2. Aggiungi la chiamata in `devforge_log`

In `devforge_log`, la riga `repo_remote=$(git remote get-url origin ...)` è seguita da
`auth_email_v="${DEVFORGE_AUTH_EMAIL:-}"` (riga ~680). Inserisci `_devforge_ensure_auth`
**prima** di leggere `auth_email_v`:

```sh
    repo_remote=$(git remote get-url origin 2>/dev/null || echo "")
    _devforge_ensure_auth                      # <-- NUOVA
    auth_email_v="${DEVFORGE_AUTH_EMAIL:-}"
```

### 3. Stessa chiamata in `devforge_log_timed`

Identico punto in `devforge_log_timed` (`auth_email_v="${DEVFORGE_AUTH_EMAIL:-}"` a riga 765,
preceduta da `repo_remote=…` a riga 764): inserisci `_devforge_ensure_auth` tra le due.
Verifica i numeri reali con `grep -n 'auth_email_v=' lib/logger.sh` prima di editare.

## Verifica GREEN

```bash
bash tests/hooks/test_lazy_auth_resolution.sh ; echo "exit=$?"
```

**Atteso:** `PASS test_lazy_auth_resolution`, exit 0. Verifica via exit code.

## No-regression immediata

```bash
bash tests/hooks/test_log_toplevel_attribution.sh ; echo "exit=$?"
bash tests/hooks/test_init_session_auth_pin.sh ; echo "exit=$?"
```

Entrambi exit 0 (il pin mantiene precedenza, lazy non interferisce).

## Done quando

- Helper + 2 chiamate inserite.
- Task 01 verde (exit 0).
- I due test no-regression sopra verdi.
