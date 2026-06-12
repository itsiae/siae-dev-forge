# Task 02 — `has_tests` robusto + `tests_files_changed`

**Stato:** [PENDING]
**Dipendenze:** nessuna
**File:** `hooks/post-commit-review` (modifica), `tests/hooks/test_has_tests_enrichment.sh` (nuovo)
**Metodo:** TDD — test PRIMA, poi modifica.

## Obiettivo

Ampliare il pattern di detection test (`__tests__/`, `conftest`) e aggiungere il campo
`tests_files_changed` (int) nel payload `commit_created`, senza alterare campi esistenti.

## Step 1 — Test (`tests/hooks/test_has_tests_enrichment.sh`)

Il calcolo `has_tests` in `post-commit-review:53-57` è un grep su `CHANGED_FILES`. Il test
isola la LOGICA di detection replicando il pattern atteso e verificando i casi; inoltre fa
un test E2E del payload tramite un repo fixture + esecuzione hook.

```bash
#!/usr/bin/env bash
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PASS=0; FAIL=0
ok(){ echo "  PASS: $1"; PASS=$((PASS+1)); }
ko(){ echo "  FAIL: $1 ($2)"; FAIL=$((FAIL+1)); }

# Pattern atteso DOPO la modifica (deve essere identico a quello nel hook)
PATTERN='(Test\.|_test\.|\.test\.|\.spec\.|/test/|/tests/|/__tests__/|conftest|^test_|^tests/)'

detect(){ echo "$1" | grep -qE "$PATTERN" && echo true || echo false; }
count(){ echo "$1" | grep -cE "$PATTERN" || true; }

# T5 — __tests__/ → true
{ [ "$(detect 'src/__tests__/a.test.ts')" = "true" ]; } && ok "T5 __tests__/" || ko "T5" "no match"
# T6 — conftest → true
{ [ "$(detect 'tests/conftest.py')" = "true" ] && [ "$(detect 'conftest.py')" = "true" ]; } && ok "T6 conftest" || ko "T6" "no match"
# pre-esistenti ancora coperti (no-regression del pattern)
for f in 'src/UserServiceTest.java' 'pkg/util_test.go' 'a.spec.ts' 'src/test/X.java' 'tests/test_main.py'; do
  [ "$(detect "$f")" = "true" ] || ko "pattern-regress" "$f non match"
done
[ "$FAIL" -eq 0 ] && ok "pattern pre-esistenti coperti"

# T7 — commit senza test → false, count 0
multi=$'src/app.ts\nREADME.md'
{ [ "$(detect "$multi")" = "false" ] && [ "$(count "$multi")" = "0" ]; } && ok "T7 no-test false/0" || ko "T7" "detect=$(detect "$multi") count=$(count "$multi")"

# T8 — 3 file test su 5 → count 3, has_tests true
five=$'src/a.ts\nsrc/__tests__/a.test.ts\nsrc/b.ts\ntests/test_b.py\nlib/conftest.py'
{ [ "$(count "$five")" = "3" ] && [ "$(detect "$five")" = "true" ]; } && ok "T8 count=3" || ko "T8" "count=$(count "$five")"

# Verifica che il hook reale usi LO STESSO pattern (grep nel sorgente)
HOOK="$PLUGIN_ROOT/hooks/post-commit-review"
grep -q '/__tests__/' "$HOOK" && grep -q 'conftest' "$HOOK" && ok "hook contiene pattern nuovi" || ko "hook pattern" "manca __tests__ o conftest"
grep -q 'tests_files_changed' "$HOOK" && ok "hook emette tests_files_changed" || ko "hook field" "manca tests_files_changed"

echo "has_tests-enrichment: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
```

Esegui: `bash tests/hooks/test_has_tests_enrichment.sh` → RED (hook senza pattern/campo nuovi).

## Step 2 — Modifica `hooks/post-commit-review`

**(a)** Riga 55 — ampliare il pattern (aggiungere `/__tests__/` e `conftest`):

```bash
    if echo "$CHANGED_FILES" | grep -qE '(Test\.|_test\.|\.test\.|\.spec\.|/test/|/tests/|/__tests__/|conftest|^test_|^tests/)'; then
        HAS_TESTS="true"
    fi
```

**(b)** Subito dopo il blocco `HAS_TESTS` (≈ riga 57) — conteggio file test:

```bash
    TESTS_FILES_COUNT=$(echo "$CHANGED_FILES" | grep -cE '(Test\.|_test\.|\.test\.|\.spec\.|/test/|/tests/|/__tests__/|conftest|^test_|^tests/)' 2>/dev/null || true)
    TESTS_FILES_COUNT=${TESTS_FILES_COUNT:-0}
```

(uso `|| true` + `${:-0}` per evitare il doppio-stdout di `grep -c` su no-match — vedi `feedback_bash_grep_count_fallback`)

**(c)** Riga 78 — aggiungere il campo nel payload `commit_created` (DOPO `has_tests`, PRIMA di `${TOKEN_META}`):

```bash
    devforge_log "commit_created" "success" \
        "{\"commit_sha\":\"${CURRENT_HEAD}\",\"files_changed\":${FILES_CHANGED:-0},\"insertions\":${INSERTIONS:-0},\"deletions\":${DELETIONS:-0},\"has_tests\":${HAS_TESTS},\"tests_files_changed\":${TESTS_FILES_COUNT}${TOKEN_META}}"
```

`has_tests` resta boolean; `tests_files_changed` è nuovo campo int. Nessun campo esistente alterato.

Esegui di nuovo → GREEN.

## Criteri di accettazione

- [ ] Test RED prima, GREEN dopo (T5,T6,T7,T8 + no-regression pattern).
- [ ] Pattern del test e del hook IDENTICI (T verifica via grep sul sorgente).
- [ ] `tests_files_changed` int nel payload, `has_tests` invariato boolean.
- [ ] Nessun campo pre-esistente di `commit_created` modificato (verificato in task-03/T9).
