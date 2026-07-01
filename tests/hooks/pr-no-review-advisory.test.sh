#!/usr/bin/env bash
# pr-no-review-advisory.test.sh — REQ-DF-05: i gate di review scalano ad advisory
# quando la base PR è 'sviluppo' (review facoltativa SIAE); restano strict su main
# o quando --base è omessa. E il template manuale è marcato ULTIMO RICORSO.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fail=0

# Invoca un gate con un comando sintetico (NON esegue gh: passa solo il payload al hook).
run_gate() { # $1=hook $2=command
    printf '{"tool_name":"Bash","tool_input":{"command":"%s"}}' "$2" \
      | bash "$ROOT/hooks/$1" 2>/dev/null
}
_pr="gh pr create"

for GATE in pr-blind-review-gate pr-premortem-gate; do
    OUT=$(run_gate "$GATE" "$_pr --base sviluppo --fill")
    if printf '%s' "$OUT" | grep -q '"decision"[[:space:]]*:[[:space:]]*"block"'; then
        echo "FAIL: $GATE blocca su base=sviluppo (atteso advisory)"; fail=1
    else
        echo "PASS: $GATE non blocca su base=sviluppo (advisory/allow)"
    fi
done

# Manuale = ultimo ricorso: siae-git-env non deve presentare il manuale come primo/unico path.
if grep -qi 'ULTIMO RICORSO\|ultimo ricorso' "$ROOT/skills/siae-git-env/SKILL.md"; then
    echo "PASS: siae-git-env marca il path manuale come ultimo ricorso"
else
    echo "FAIL: siae-git-env non marca il manuale come ultimo ricorso"; fail=1
fi

# pr-gate non deve più usare 'gate bloccante' senza decision:block reale.
if grep -q 'gate bloccante' "$ROOT/hooks/pr-gate"; then
    echo "FAIL: pr-gate usa ancora 'gate bloccante' (linguaggio non onesto)"; fail=1
else
    echo "PASS: pr-gate non usa più 'gate bloccante' (linguaggio advisory onesto)"
fi

exit $fail
