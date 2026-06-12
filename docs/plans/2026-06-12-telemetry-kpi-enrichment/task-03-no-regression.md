# Task 03 — No-regression payload + integrazione hooks.json

**Stato:** [PENDING]
**Dipendenze:** task-01 (hooks.json integro), task-02 (payload modificato)
**File:** `tests/hooks/test_commit_created_no_regression.sh` (nuovo)
**Metodo:** verifica integrata additività.

## Obiettivo

Garantire che il payload `commit_created` mantenga TUTTI i campi pre-esistenti invariati
(solo aggiunta di `tests_files_changed`) e che `hooks.json` resti valido con il nuovo hook.

## Step 1 — Test (`tests/hooks/test_commit_created_no_regression.sh`)

```bash
#!/usr/bin/env bash
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PASS=0; FAIL=0
ok(){ echo "  PASS: $1"; PASS=$((PASS+1)); }
ko(){ echo "  FAIL: $1 ($2)"; FAIL=$((FAIL+1)); }

HOOK="$PLUGIN_ROOT/hooks/post-commit-review"

# T9a — il payload commit_created contiene TUTTI i campi pre-esistenti
LINE=$(grep -n 'devforge_log "commit_created"' "$HOOK" | head -1)
PAYLOAD=$(sed -n "$(echo "$LINE" | cut -d: -f1),+2p" "$HOOK")
for field in 'commit_sha' 'files_changed' 'insertions' 'deletions' 'has_tests'; do
  echo "$PAYLOAD" | grep -q "\"$field\"" && ok "T9a campo preesistente: $field" || ko "T9a $field" "mancante nel payload"
done

# T9b — campo nuovo presente, has_tests ancora boolean (non quotato)
echo "$PAYLOAD" | grep -q '"tests_files_changed":' && ok "T9b tests_files_changed presente" || ko "T9b" "campo nuovo mancante"
echo "$PAYLOAD" | grep -qE '"has_tests":\$\{HAS_TESTS\}' && ok "T9b has_tests boolean (no virgolette)" || ko "T9b has_tests" "has_tests non boolean"

# T9c — hooks.json valido + branch-tracker presente nel matcher PostToolUse Bash
python3 -c 'import json;json.load(open("'"$PLUGIN_ROOT"'/hooks/hooks.json"))' 2>/dev/null && ok "T9c hooks.json JSON valido" || ko "T9c" "JSON invalido"
grep -q 'branch-tracker' "$PLUGIN_ROOT/hooks/hooks.json" && ok "T9c branch-tracker registrato" || ko "T9c branch-tracker" "non in hooks.json"

# T9d — branch-tracker NON nel matcher Edit/Write/PreToolUse (solo PostToolUse Bash)
RES=$(python3 - "$PLUGIN_ROOT/hooks/hooks.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
post_bash=False; elsewhere=False
for grp in d.get("hooks",{}).get("PostToolUse",[]):
    if grp.get("matcher")=="Bash":
        for h in grp.get("hooks",[]):
            if "branch-tracker" in h.get("command",""): post_bash=True
for ev in ("PreToolUse","Stop","SessionStart","UserPromptSubmit"):
    for grp in d.get("hooks",{}).get(ev,[]):
        for h in grp.get("hooks",[]):
            if "branch-tracker" in h.get("command",""): elsewhere=True
print("OK" if (post_bash and not elsewhere) else "FAIL")
PY
)
[ "$RES" = "OK" ] && ok "T9d branch-tracker solo PostToolUse Bash" || ko "T9d" "branch-tracker in matcher non previsto o assente (res=$RES)"

echo "no-regression: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
```

NB: T9d cattura l'output del blocco python in `RES` e lo mappa su `ok`/`ko` (vedi sopra).

## Step 2 — Esecuzione suite completa

Esegui tutti i test del bundle via exit code (non grep PASS):

```bash
for t in tests/hooks/test_branch_tracker.sh \
         tests/hooks/test_has_tests_enrichment.sh \
         tests/hooks/test_commit_created_no_regression.sh \
         tests/hooks/post-commit-review-sha.test.sh; do
    echo "== $t =="; bash "$t"; echo "exit=$?"
done
```

`post-commit-review-sha.test.sh` (esistente) DEVE restare verde: prova che la modifica al
payload non ha rotto il test di `commit_sha` pre-esistente.

## Criteri di accettazione

- [ ] T9a: tutti i campi pre-esistenti (`commit_sha`,`files_changed`,`insertions`,`deletions`,`has_tests`) presenti.
- [ ] T9b: `tests_files_changed` presente, `has_tests` ancora boolean.
- [ ] T9c: `hooks.json` valido, `branch-tracker` nel solo matcher PostToolUse Bash.
- [ ] T9d: branch-tracker NON in altri matcher/eventi.
- [ ] `post-commit-review-sha.test.sh` esistente ancora verde (no-regression reale).
