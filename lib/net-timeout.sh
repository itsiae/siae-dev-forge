#!/usr/bin/env bash
# DevForge net-timeout — esecuzione comandi con budget temporale, portabile BSD/macOS.
# Nessun 'timeout' (assente su BSD), nessun 'perl alarm'-via-exec (non sopravvive exec su macOS).

# _devforge_no_proxy_github — esclude github dal proxy corporate.
# Su macchine SIAE NO_PROXY non contiene github → gh (Go) e git (libcurl) instradano
# github attraverso il proxy che non lo raggiunge → i/o timeout ~30s per call.
# github.com è DIRECT nel PAC SIAE: basta escluderlo. Idempotente + exported →
# ereditato da ogni sottoprocesso gh/git dell'hook che sorgia questo file.
_devforge_no_proxy_github() {
    local domains="github.com,api.github.com,.github.com,codeload.github.com,objects.githubusercontent.com,uploads.github.com"
    case ",${NO_PROXY:-}," in
        *,github.com,*) return 0 ;;   # già presente: no-op
    esac
    export NO_PROXY="${NO_PROXY:+${NO_PROXY},}${domains}"
    export no_proxy="${no_proxy:+${no_proxy},}${domains}"
}
_devforge_no_proxy_github

# _net_kill_tree <pid> — termina pid e figli (best-effort sui nipoti via pgrep -P ricorsivo)
_net_kill_tree() {
    local pid="$1" child
    if command -v pgrep >/dev/null 2>&1; then
        for child in $(pgrep -P "$pid" 2>/dev/null); do
            _net_kill_tree "$child"
        done
    fi
    kill -TERM "$pid" 2>/dev/null || true
}

# net_run <secs> <cmd...> — esegue cmd con budget <secs>.
#   - entro budget: stdout di cmd + exit code reale
#   - oltre budget: stdout parziale + return 124, albero processi terminato
net_run() {
    local secs="$1"; shift
    local tmp; tmp=$(mktemp 2>/dev/null) || tmp="${TMPDIR:-/tmp}/net_run.$$"
    # Expand-at-invocation ('...' non "...") → safe anche con path che contengono
    # spazi (es. repo in iCloud). $tmp è local ma resta in scope nel RETURN trap.
    trap 'rm -f "$tmp"' RETURN

    "$@" >"$tmp" 2>/dev/null &
    local pid=$!
    local waited=0 step_ms=200 budget_ms=$((secs * 1000))

    while kill -0 "$pid" 2>/dev/null; do
        if [ "$waited" -ge "$budget_ms" ]; then
            _net_kill_tree "$pid"
            sleep 0.1
            kill -KILL "$pid" 2>/dev/null || true
            wait "$pid" 2>/dev/null || true
            cat "$tmp"
            return 124
        fi
        sleep 0.2
        waited=$((waited + step_ms))
    done

    wait "$pid"; local rc=$?
    cat "$tmp"
    return "$rc"
}
