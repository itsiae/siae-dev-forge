#!/usr/bin/env bash
# T-WIRE — test strutturale: i 3 hook con call di rete reali sorgiano net-timeout.sh
# e avvolgono OGNI call github (gh/git di rete) in net_run.
# Esclude commenti, heredoc letterali e token-matcher (case "$TOOL_COMMAND"),
# che non sono bash eseguito (memory: falso positivo pr-gate:248).
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PASS=0; FAIL=0
ok(){ echo "  PASS: $1"; PASS=$((PASS+1)); }
ko(){ echo "  FAIL: $1 ($2)"; FAIL=$((FAIL+1)); }

HOOKS="session-start pr-release-gate post-commit-review"

for h in $HOOKS; do
    f="${PLUGIN_ROOT}/hooks/${h}"

    # 1) source di net-timeout.sh presente
    if grep -qE 'source[^#]*lib/net-timeout\.sh' "$f"; then
        ok "${h}: sorgia net-timeout.sh"
    else
        ko "${h}: source mancante" "no source lib/net-timeout.sh"
    fi

    # 2) nessuna call github in command-substitution senza net_run.
    #    Match solo call reali in $(...): gh <verbo di rete> | git <fetch/pull/ls-remote>.
    #    Esclude righe-commento e righe con net_run.
    unwrapped=$(grep -nE '\$\(([^)]*)(gh (pr view|pr list|pr comment|repo view|api|release list)|git (fetch|pull|ls-remote))' "$f" \
        | grep -vE '^\s*[0-9]+:\s*#' \
        | grep -v 'net_run' || true)
    if [ -z "$unwrapped" ]; then
        ok "${h}: tutte le call github avvolte da net_run"
    else
        ko "${h}: call github nuda" "$(echo "$unwrapped" | head -1)"
    fi
done

# 3) Regressione: la catena obsoleta timeout/gtimeout/perl per gh release NON deve
#    piu' esistere in session-start (sostituita da net_run).
if grep -qE 'perl -e .*fork.*alarm' "${PLUGIN_ROOT}/hooks/session-start"; then
    ko "session-start: perl-fork residuo" "catena timeout obsoleta non rimossa"
else
    ok "session-start: catena perl-fork rimossa"
fi

echo "net-resilience-wiring: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
