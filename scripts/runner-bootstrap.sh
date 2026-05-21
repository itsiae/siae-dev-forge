#!/usr/bin/env bash
# runner-bootstrap.sh — auto-ensure di tutti i runner security DevForge.
#
# Invocato automaticamente da hook review-evidence/pr-gate all'inizio
# dell'esecuzione. Per ogni runner core (SAST + secrets + IaC) tenta install
# in parallelo via `devforge-install-runners.sh --ensure <tool>`.
#
# Caratteristiche:
#   * Non-blocking: exit 0 sempre, anche se uno o piu' runner falliscono.
#   * Throttled: max 4 install paralleli (evita brew/pip lock contention).
#   * Idempotent: runner gia' installati exit silent.
#   * Cooldown: sentinel `~/.claude/.devforge-runner-bootstrap-last`
#     evita ri-esecuzione entro 1h dall'ultima.
#   * Logged: warning rossi ANSI emessi da --ensure su stderr (TTY-aware).
#
# Tool core (security primary):
#   cross:  semgrep, gitleaks
#   python: bandit, pip-audit
#   aws:    tfsec, checkov
#
# I tool meno critici (eslint, ts-unused-exports, swiftlint, ktlint, tflint,
# vulture, pyright, detekt, cfn-lint, spotbugs) NON sono in bootstrap auto
# per non saturare cold-start. Vengono installati su `--ensure` esplicito.
#
# Uso:
#   bash scripts/runner-bootstrap.sh           # background ensure
#   bash scripts/runner-bootstrap.sh --sync    # sync (blocking, per test)

set -uo pipefail

# Estendi PATH per coprire install user-space comuni (brew, pip --user, npm prefix)
_DEVFORGE_USER_BINS=(
    "/opt/homebrew/bin"
    "/opt/homebrew/sbin"
    "${HOME}/.local/bin"
    "${HOME}/Library/Python/3.9/bin"
    "${HOME}/Library/Python/3.10/bin"
    "${HOME}/Library/Python/3.11/bin"
    "${HOME}/Library/Python/3.12/bin"
    "${HOME}/Library/Python/3.13/bin"
    "${HOME}/.npm-global/bin"
)
for _bin in "${_DEVFORGE_USER_BINS[@]}"; do
    [ -d "$_bin" ] && case ":$PATH:" in *":$_bin:"*) ;; *) PATH="$_bin:$PATH" ;; esac
done
export PATH

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
INSTALLER="${PLUGIN_ROOT}/scripts/devforge-install-runners.sh"

# Cooldown sentinel: evita ri-bootstrap entro 1h
SENTINEL="${HOME}/.claude/.devforge-runner-bootstrap-last"
COOLDOWN_SEC="${DEVFORGE_BOOTSTRAP_COOLDOWN:-3600}"

# Skip se cooldown attivo
if [ -f "$SENTINEL" ]; then
    LAST=$(cat "$SENTINEL" 2>/dev/null || echo 0)
    NOW=$(date +%s)
    if [ $((NOW - LAST)) -lt "$COOLDOWN_SEC" ]; then
        exit 0
    fi
fi

# Verifica installer presente
if [ ! -x "$INSTALLER" ] && [ ! -f "$INSTALLER" ]; then
    exit 0  # silent, no installer = no bootstrap
fi

# Runner core (priorità security)
CORE_RUNNERS=(semgrep gitleaks bandit pip-audit tfsec checkov)

# Mode: sync (blocking) o async (default)
MODE="async"
if [ "${1:-}" = "--sync" ]; then
    MODE="sync"
fi

# Update sentinel PRIMA di lanciare (debounce concurrent calls)
mkdir -p "${HOME}/.claude" 2>/dev/null
date +%s > "$SENTINEL" 2>/dev/null || true

# Per ogni runner: --ensure (lazy install + warning rosso). 4 in parallelo max.
_ensure_one() {
    local tool="$1"
    # Timeout 60s per runner — evita hang lunghi
    DEVFORGE_RUNNER_ENSURE_TIMEOUT=60 bash "$INSTALLER" --ensure "$tool" 2>&1 | \
        grep -v '^\[INFO\]\|^\[OK\]' >&2 || true
}

if [ "$MODE" = "sync" ]; then
    # Sync: utile per test/CI
    for tool in "${CORE_RUNNERS[@]}"; do
        _ensure_one "$tool"
    done
else
    # Async: throttled parallel via background jobs + wait
    MAX_PAR=4
    pids=()
    for tool in "${CORE_RUNNERS[@]}"; do
        _ensure_one "$tool" &
        pids+=($!)
        if [ "${#pids[@]}" -ge "$MAX_PAR" ]; then
            wait "${pids[0]}" 2>/dev/null || true
            pids=("${pids[@]:1}")
        fi
    done
    for pid in "${pids[@]}"; do
        wait "$pid" 2>/dev/null || true
    done
fi

exit 0
