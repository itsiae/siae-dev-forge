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
    # Cleanup esplicito (non RETURN trap): net_run può essere annidato dentro altre
    # funzioni e un trap RETURN resterebbe registrato, rifacendo fire al ritorno dei
    # chiamanti dove $tmp non è più in scope → unbound sotto set -u.

    "$@" >"$tmp" 2>/dev/null &
    local pid=$!
    local waited=0 step_ms=200 budget_ms=$((secs * 1000))

    while kill -0 "$pid" 2>/dev/null; do
        if [ "$waited" -ge "$budget_ms" ]; then
            _net_kill_tree "$pid"
            sleep 0.1
            kill -KILL "$pid" 2>/dev/null || true
            wait "$pid" 2>/dev/null || true
            cat "$tmp"; rm -f "$tmp"
            return 124
        fi
        sleep 0.2
        waited=$((waited + step_ms))
    done

    wait "$pid"; local rc=$?
    cat "$tmp"; rm -f "$tmp"
    return "$rc"
}

# ─── proxy autoconfig VPN-aware ───────────────────────────────────────────────
# Su rete/VPN SIAE il proxy corporate è raggiungibile (github va escluso, resta
# DIRECT). Fuori VPN lo stesso proxy è IRRAGGIUNGIBILE → ogni call non-github si
# appende ~30s prima di morire. Rileviamo dove siamo con un probe TCP a tempo e
# instradiamo di conseguenza. Nessuna env var di override (i gate non si bypassano).

# _devforge_proxy_endpoint — host:port del proxy corporate, da env o default SIAE.
_devforge_proxy_endpoint() {
    local p="${https_proxy:-${HTTPS_PROXY:-${http_proxy:-${HTTP_PROXY:-}}}}"
    p="${p#*://}"; p="${p%%/*}"          # strip scheme + eventuale path
    [ -n "$p" ] && { printf '%s' "$p"; return 0; }
    printf '10.255.1.241:8080'           # fallback: proxy SIAE noto
}

# _devforge_on_siae_net — proxy corporate raggiungibile entro 1s → rete/VPN SIAE.
# /dev/tcp è socket raw (ignora il proxy): è un test di raggiungibilità diretto.
_devforge_on_siae_net() {
    local ep host port; ep="$(_devforge_proxy_endpoint)"
    host="${ep%%:*}"; port="${ep##*:}"
    [ -n "$host" ] && [ -n "$port" ] || return 1
    net_run 1 bash -c 'exec 3<>/dev/tcp/'"$host"'/'"$port" >/dev/null 2>&1
}

# _devforge_proxy_autoconfig — instrada in base alla rete rilevata.
_devforge_proxy_autoconfig() {
    if _devforge_on_siae_net; then
        _devforge_no_proxy_github        # rete SIAE: proxy attivo, github DIRECT
    else
        unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy NO_PROXY no_proxy
    fi
}
_devforge_proxy_autoconfig
