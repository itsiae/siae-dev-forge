#!/usr/bin/env bash
# DevForge plugin-version — helper di osservabilità versione plugin.
# Sourcabile e testabile in isolamento. NESSUN side-effect al source.
#
# Filosofia (design 2026-06-19 plugin-update-safety): il rollout è gestito dal
# meccanismo NATIVO di Claude Code (autoUpdate org-wide via remote-settings).
# Qui NON si aggiorna nulla: si osserva soltanto la versione effettiva vs latest
# per telemetria + notice informativo. Niente claude plugin update / rm -rf / git pull.

# _ver_lt A B — vero (rc 0) se A < B. Confronto numerico per campi major.minor.patch.
# I suffissi prerelease (-rc1, ...) sono scartati: il chiamante esclude le prerelease a monte.
# Robusto su 1.9.0 vs 1.10.0 (dove lo string-compare e sort -V sui suffissi sbagliano).
_ver_lt() {
    local a="${1%%-*}" b="${2%%-*}"
    local IFS=.
    # shellcheck disable=SC2206
    local -a A=($a) B=($b)
    local i x y
    for i in 0 1 2; do
        x=$((10#${A[i]:-0})); y=$((10#${B[i]:-0}))
        [ "$x" -lt "$y" ] && return 0
        [ "$x" -gt "$y" ] && return 1
    done
    return 1   # uguali → non minore
}

# _ver_is_semver V — vero se V è semver puro X.Y.Z (senza suffisso).
_ver_is_semver() {
    case "$1" in
        *[!0-9.]*) return 1 ;;
    esac
    printf '%s' "$1" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'
}

# devforge_installed_version PLUGIN_ROOT — versione EFFETTIVA caricata da Claude.
# Preferisce il registry installed_plugins.json (cosa gira davvero), fallback al
# plugin.json del PLUGIN_ROOT (può essere "eager" se il clone è già git-pullato).
# Stampa la versione o "unknown".
devforge_installed_version() {
    local plugin_root="$1"
    local reg="${HOME}/.claude/plugins/installed_plugins.json"
    local v=""
    if [ -f "$reg" ]; then
        # primo campo "version":"X.Y.Z" sotto la chiave siae-devforge (best-effort, senza jq)
        v=$(grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' "$reg" 2>/dev/null \
            | head -1 | sed 's/.*"version"[[:space:]]*:[[:space:]]*"//;s/"$//')
    fi
    if [ -z "$v" ] && [ -n "$plugin_root" ] && [ -f "${plugin_root}/.claude-plugin/plugin.json" ]; then
        v=$(grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' "${plugin_root}/.claude-plugin/plugin.json" 2>/dev/null \
            | head -1 | sed 's/.*"version"[[:space:]]*:[[:space:]]*"//;s/"$//')
    fi
    printf '%s' "${v:-unknown}"
}

# devforge_latest_release — ultima release STABILE (prerelease escluse) da GitHub.
# Richiede gh + net_run già disponibili nell'ambiente del chiamante. Stampa "" se non risolvibile.
# Best-effort, degrada in silenzio: nessun errore propagato.
devforge_latest_release() {
    command -v gh >/dev/null 2>&1 || { printf ''; return 0; }
    command -v net_run >/dev/null 2>&1 || { printf ''; return 0; }
    local tag=""
    # via 1: flag nativa (gh recenti)
    tag=$(net_run 5 gh release list --repo itsiae/siae-dev-forge --exclude-pre-releases \
            --limit 1 --json tagName --jq '.[0].tagName' 2>/dev/null || echo "")
    # via 2 (fallback gh vecchi senza la flag): filtra isPrerelease lato jq
    if [ -z "$tag" ]; then
        tag=$(net_run 5 gh release list --repo itsiae/siae-dev-forge --limit 20 \
                --json tagName,isPrerelease --jq 'map(select(.isPrerelease|not))|.[0].tagName' 2>/dev/null || echo "")
    fi
    printf '%s' "${tag#v}"
}
