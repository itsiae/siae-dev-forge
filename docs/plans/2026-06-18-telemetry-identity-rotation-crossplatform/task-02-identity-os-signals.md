# Task 02 — Segnali identità OS cross-platform (Capability A)

**AC:** AC1, AC5 · **File:** `lib/logger.sh`, `tests/zero-loss/unit/test_logger_identity_signals.sh`

## Obiettivo

Nuova funzione `_devforge_local_identity_signals` che emette 3 campi OS con **parità** mac/Linux/Win:
`os_full_name`, `os_login`, `os_domain`. Best-effort, mai abort sotto `set -euo pipefail`.

## RED — test che fallisce

Crea `tests/zero-loss/unit/test_logger_identity_signals.sh` (parte OS):
- Sorgente `lib/logger.sh`, chiama `_devforge_local_identity_signals`.
- Asserisci output JSON-parsabile contenente le chiavi `os_full_name`, `os_login`, `os_domain`.
- `os_login` non vuoto (fallback whoami).
- Sotto `set -u`: con `USERDOMAIN` unset, nessun abort (test invoca in subshell `set -u`).
- Atteso PRE-fix: FAIL (funzione inesistente).

## GREEN — implementazione

Aggiungi in `lib/logger.sh`:

```bash
# Segnali identità locali (best-effort, parità mac/Linux/Win). Mai abort.
_devforge_local_identity_signals_os() {
    local os_full_name="" os_login="" os_domain="" uname_s
    uname_s=$(uname -s 2>/dev/null || echo "")
    case "$uname_s" in
        Darwin)
            os_full_name=$(id -F 2>/dev/null | head -1 | tr -d '\r' || true) ;;
        Linux)
            if command -v getent >/dev/null 2>&1; then
                os_full_name=$(getent passwd "${USER:-}" 2>/dev/null | cut -d: -f5 | cut -d, -f1 | head -1 | tr -d '\r' || true)
            fi ;;
        MINGW*|MSYS*|CYGWIN*)
            if command -v powershell.exe >/dev/null 2>&1; then
                os_full_name=$(powershell.exe -NoProfile -Command \
                  "(Get-CimInstance Win32_UserAccount -Filter \"Name='\$env:USERNAME'\").FullName" \
                  2>/dev/null | head -1 | tr -d '\r' || true)
            fi ;;
    esac
    os_login="${USERNAME:-${USER:-$(whoami 2>/dev/null || echo "")}}"
    os_domain="${USERDOMAIN:-}"
    # trunc difensivo 128 char
    os_full_name=$(printf '%s' "$os_full_name" | cut -c1-128)
    printf '%s\t%s\t%s' "$os_full_name" "$os_login" "$os_domain"
}
```

(Il wiring in `devforge_identity_bundle` avviene in task-04; qui la funzione è standalone e testata.)

## REFACTOR

Commenti di parità per ramo; verifica nessun uso di flag GNU-only.

## Verifica / Done

- `bash tests/zero-loss/unit/test_logger_identity_signals.sh` PASS (parte OS).
- No-regression suite verde. Marca `[DONE]`.
