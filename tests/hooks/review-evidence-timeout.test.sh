#!/usr/bin/env bash
# review-evidence-timeout.test.sh — REQ-DF-05: il timeout dichiarato in hooks.json
# per review-evidence deve essere >= massima attesa lock interna in hooks/review-evidence,
# altrimenti l'harness uccide il hook a meta' attesa → fail-closed spurio su gh pr create.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fail=0

# Attesa lock interna: max N in `for _ in $(seq 1 N)` dentro hooks/review-evidence.
MAX_WAIT=$(grep -oE 'seq 1 [0-9]+' "$ROOT/hooks/review-evidence" | grep -oE '[0-9]+' | sort -rn | head -1)
[ -z "$MAX_WAIT" ] && MAX_WAIT=30

# Timeout dichiarato (minimo tra le occorrenze review-evidence in hooks.json).
DECLARED=$(python3 - "$ROOT/hooks/hooks.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
mins=[]
def walk(o):
    if isinstance(o,dict):
        if 'review-evidence' in json.dumps(o) and 'timeout' in o:
            mins.append(o['timeout'])
        for v in o.values(): walk(v)
    elif isinstance(o,list):
        for v in o: walk(v)
walk(d)
print(min(mins) if mins else 0)
PY
)

if [ "$DECLARED" -lt "$MAX_WAIT" ]; then
    echo "FAIL: review-evidence timeout dichiarato=$DECLARED < attesa lock=$MAX_WAIT"
    fail=1
else
    echo "PASS: timeout=$DECLARED >= attesa lock=$MAX_WAIT"
fi
exit $fail
