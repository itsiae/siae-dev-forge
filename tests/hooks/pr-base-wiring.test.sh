#!/usr/bin/env bash
# pr-base-wiring.test.sh — regressione REQ-DF-03: i siti bash devono classificare/diffare
# contro il base REALE del branch (es. sviluppo), non contro origin/main hardcoded.
# Design: docs/plans/2026-07-01-devforge-siae-conventions-and-flow/design.md (REQ-DF-03 AC1/AC2/AC4)
set -eu
PASS=0; FAIL=0
REPO_ROOT="$(git rev-parse --show-toplevel)"

# Crea main + sviluppo, branch work da sviluppo con un file .py committato SOLO su
# sviluppo (assente su main). Se il diff scope usasse ancora origin/main, il file
# comparirebbe come "nuovo"; col base corretto (sviluppo) il diff di work contiene solo a.md.
_mkrepo_sviluppo_base() {
    local td; td=$(mktemp -d)
    ( cd "$td" && git init -q && git config user.email t@t && git config user.name t \
      && echo base > base.py && git add -A && git commit -qm base && git branch -m main \
      && git checkout -qb sviluppo \
      && echo dev-only > dev-only.py && git add -A && git commit -qm sviluppo-work
      git update-ref refs/remotes/origin/main "$(git rev-parse main)"
      git update-ref refs/remotes/origin/sviluppo "$(git rev-parse sviluppo)"
      git checkout -qb work
      echo x > a.md && git add -A && git commit -qm doc-on-work ) >/dev/null 2>&1
    echo "$td"
}

echo "=== AC-1/AC-2: diff-risk-classifier con base=sviluppo (via resolver) -> low (solo .md su work) ==="
TD=$(_mkrepo_sviluppo_base)
RISK=$( cd "$TD" && source "${REPO_ROOT}/lib/pr-base-resolver.sh" && source "${REPO_ROOT}/lib/diff-risk-classifier.sh" \
        && RESOLVED=$(devforge_resolve_pr_base) && devforge_classify_diff_risk "$RESOLVED" )
if [ "$RISK" = "low" ]; then echo "  PASS"; PASS=$((PASS+1)); else echo "  FAIL: RISK=$RISK (atteso low)"; FAIL=$((FAIL+1)); fi
rm -rf "$TD"

echo "=== AC-1/AC-4: diff-risk-classifier con base=origin/main esplicito -> code (dev-only.py nuovo vs main) ==="
TD=$(_mkrepo_sviluppo_base)
RISK=$( cd "$TD" && source "${REPO_ROOT}/lib/diff-risk-classifier.sh" && devforge_classify_diff_risk "origin/main" )
if [ "$RISK" = "code" ]; then echo "  PASS (conferma bug pre-fix: origin/main include dev-only.py)"; PASS=$((PASS+1)); else echo "  FAIL: RISK=$RISK (atteso code)"; FAIL=$((FAIL+1)); fi
rm -rf "$TD"

echo "=== AC-1/AC-2: resolver risolve sviluppo (merge-base) quando il branch parte da sviluppo ==="
TD=$(_mkrepo_sviluppo_base)
RESOLVED_MB=$( cd "$TD" && source "${REPO_ROOT}/lib/pr-base-resolver.sh" && RESOLVED=$(devforge_resolve_pr_base) && git merge-base HEAD "origin/${RESOLVED}" )
EXPECTED_MB=$( cd "$TD" && git rev-parse sviluppo )
if [ "$RESOLVED_MB" = "$EXPECTED_MB" ]; then echo "  PASS"; PASS=$((PASS+1)); else echo "  FAIL: got=$RESOLVED_MB expected=$EXPECTED_MB"; FAIL=$((FAIL+1)); fi
rm -rf "$TD"

echo "=== AC-1: pr-blind-review-gate/pr-premortem-gate non hardcodano piu' origin/main ==="
for GATE in pr-blind-review-gate pr-premortem-gate; do
    if grep -qF 'devforge_classify_diff_risk "origin/main"' "${REPO_ROOT}/hooks/${GATE}"; then
        echo "  FAIL: ${GATE} ancora hardcoded a origin/main"; FAIL=$((FAIL+1))
    else
        echo "  PASS: ${GATE} non hardcoda origin/main"; PASS=$((PASS+1))
    fi
done

echo "=== AC-1: pr-gate wired al resolver ==="
if grep -q 'devforge_resolve_pr_base' "${REPO_ROOT}/hooks/pr-gate"; then
    echo "  PASS: pr-gate chiama devforge_resolve_pr_base"; PASS=$((PASS+1))
else
    echo "  FAIL: pr-gate non chiama devforge_resolve_pr_base"; FAIL=$((FAIL+1))
fi

echo ""; echo "RESULT: PASS=$PASS FAIL=$FAIL"; [ "$FAIL" -eq 0 ]
