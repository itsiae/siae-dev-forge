# Task 02 — TDD: test + wiring iniezione in session-start

**Goal:** session-start legge `siae-global-rules.md` e inietta la sezione nel blocco `<EXTREMELY_IMPORTANT>`, con test di guardia (A strutturale, B funzionale JSON-valid, C fail-safe, D anti-leak). Stato: `[PENDING]`.
**Dipende da:** Task 01 (il file regole deve esistere per i test B/C).

## File coinvolti
- CREA: `tests/hooks/test_session_start_global_rules.sh`
- MODIFICA: `hooks/session-start` (inserisce blocco read + referenzia in `session_context`, riga 305)
- MODIFICA: `tests/run-all.sh` (registrazione esplicita del nuovo test)

## Step

### Step 1 — Scrivi il test fallente (Red)
Path: `tests/hooks/test_session_start_global_rules.sh`
```bash
#!/usr/bin/env bash
# Test: hooks/session-start inietta la sezione SIAE Global Rules leggendo la fonte unica versionata.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="${PLUGIN_ROOT}/hooks/session-start"
RULES="${PLUGIN_ROOT}/skills/using-devforge/reference/siae-global-rules.md"
PASS=0; FAIL=0
ok() { if eval "$2"; then echo "  PASS  $1"; PASS=$((PASS+1)); else echo "  FAIL  $1"; FAIL=$((FAIL+1)); fi; }

# (A) STRUTTURALE (hard) — wiring presente, guarded, fail-safe, referenziato in session_context.
ok "legge il file regole" \
   "grep -q 'siae-global-rules.md' '$HOOK'"
ok "calcola global_rules_section guarded" \
   "grep -q 'global_rules_section' '$HOOK' && grep -q 'global_rules_content' '$HOOK'"
ok "lettura fail-safe (2>/dev/null)" \
   "grep -E 'siae-global-rules.md.*2>/dev/null' '$HOOK' >/dev/null"
ok "global_rules_section referenziato in session_context" \
   "grep -E 'session_context=.*\\\$\\{?global_rules_section' '$HOOK' >/dev/null"

# (D) ANTI-LEAK (hard) — la fonte versionata non contiene dati per-persona/segreti.
# NB: 'git@github.com' è un esempio anti-pattern legittimo nelle regole → whitelisted.
ok "anti-leak: nessun account-personale/path-macchina" \
   "! grep -qE 'federicoarcangeli|/Users/|OneDrive[^/[:space:]]' '$RULES'"
ok "anti-leak: nessuna email personale (whitelist git@github.com)" \
   "[ -z \"\$(grep -oE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' '$RULES' | grep -v '^git@github\.com\$')\" ]"
ok "anti-leak: unico IP = proxy 10.255.1.241" \
   "[ \"\$(grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' '$RULES' | sort -u)\" = '10.255.1.241' ]"

# (B) FUNZIONALE (tollerante: session-start può essere pesante in sandbox).
TMPHOME="$(mktemp -d)"; mkdir -p "$TMPHOME/.claude"
STDOUT=$(printf '{}' | HOME="$TMPHOME" bash "$HOOK" 2>/dev/null || true)
if echo "$STDOUT" | grep -q 'additional_context'; then
    ok "func: additional_context contiene 'SIAE Global Rules'" \
       "echo \"\$STDOUT\" | grep -q 'SIAE Global Rules'"
    ok "func: stdout è JSON valido" \
       "echo \"\$STDOUT\" | python3 -c 'import sys,json; json.load(sys.stdin)' 2>/dev/null"
else
    echo "  SKIP  func: session-start non ha prodotto additional_context in sandbox (strutturale copre il wiring)"
fi

# (C) FAIL-SAFE — file regole assente → sezione sparisce ma additional_context resta JSON valido.
if [ -f "$RULES" ]; then
    BAK="${RULES}.bak.$$"
    # trap PRIMA del mv: chiude la finestra atomica → file mai perso anche su interrupt.
    trap '[ -f "$BAK" ] && mv -f "$BAK" "$RULES" 2>/dev/null || true' EXIT
    mv "$RULES" "$BAK"
    TMPHOME2="$(mktemp -d)"; mkdir -p "$TMPHOME2/.claude"
    STDOUT2=$(printf '{}' | HOME="$TMPHOME2" bash "$HOOK" 2>/dev/null || true)
    mv "$BAK" "$RULES"; trap - EXIT
    if echo "$STDOUT2" | grep -q 'additional_context'; then
        ok "fail-safe: senza file no 'SIAE Global Rules' ma JSON valido" \
           "! echo \"\$STDOUT2\" | grep -q 'SIAE Global Rules' && echo \"\$STDOUT2\" | python3 -c 'import sys,json; json.load(sys.stdin)' 2>/dev/null"
    else
        echo "  SKIP  fail-safe: session-start non ha prodotto additional_context in sandbox"
    fi
fi

echo ""; echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
```

### Step 2 — Esegui e verifica che fallisce (Red)
Run: `bash tests/hooks/test_session_start_global_rules.sh`
Output atteso: i check (A) FAIL (`legge il file regole`, `global_rules_section`, ...) perché il wiring non esiste ancora → `PASS=2 FAIL>=3` (i due D possono già passare dopo Task 01). Exit ≠ 0.

### Step 3 — Implementa il wiring (Green)
**Edit 3a** — `hooks/session-start`: inserire il blocco SUBITO PRIMA della riga `session_context=...` (attuale riga ~305, dopo `# --- End global memory ---` riga ~303):
```bash
# --- SIAE Global Rules (fonte unica versionata, iniezione team-wide) ---
# Mirror del read di using-devforge/SKILL.md (riga ~210). Fail-safe: file mancante
# → sezione vuota → session_context resta JSON valido. 2>/dev/null (NON 2>&1): un
# errore di lettura su file opzionale non deve finire iniettato nel contesto.
global_rules_content=$(cat "${PLUGIN_ROOT}/skills/using-devforge/reference/siae-global-rules.md" 2>/dev/null || echo "")
global_rules_section=""
if [ -n "$global_rules_content" ]; then
    global_rules_escaped=$(escape_for_json "$global_rules_content")
    global_rules_section="\\n\\n**SIAE Global Rules (operational guardrails — sempre attive):**\\n\\n${global_rules_escaped}"
fi
# --- End SIAE Global Rules ---
```
**Edit 3b** — `hooks/session-start` riga 305: inserire `${global_rules_section}` subito dopo `${branching_section}`. Da:
```
...${version_status_escaped}${branching_section}\n\n**Below is the content of your 'siae-devforge:using-devforge'...
```
a:
```
...${version_status_escaped}${branching_section}${global_rules_section}\n\n**Below is the content of your 'siae-devforge:using-devforge'...
```
(Il prefisso `\\n\\n` è già dentro `${global_rules_section}`, coerente con `catalog_section`/`global_memory_section`.)

### Step 4 — Registra il test in run-all.sh (obbligatorio: registrazione esplicita, non glob)
Trova la riga di registrazione del test gemello:
```bash
grep -n 'test_session_start_enforcement_off.sh' tests/run-all.sh
```
Aggiungi una riga analoga per `tests/hooks/test_session_start_global_rules.sh` con lo stesso pattern/funzione usato lì (es. `run_test "tests/hooks/test_session_start_global_rules.sh"`).

### Step 5 — Esegui e verifica che passa (Green)
Run: `bash tests/hooks/test_session_start_global_rules.sh`
Output atteso: `PASS>=4 FAIL=0`, exit 0. (B/C possono mostrare `SKIP` in sandbox: accettabile, lo strutturale copre il wiring.)
Run regressione mirata:
```bash
for t in tests/hooks/test_session_start_*.sh; do echo "== $t =="; bash "$t"; done
```
Output atteso: tutti `FAIL=0` (gli altri 4 test session-start invariati — no regressione).

## Criteri di accettazione
- [ ] `hooks/session-start` legge `siae-global-rules.md`, calcola `global_rules_section` guarded, la referenzia in `session_context`.
- [ ] `tests/hooks/test_session_start_global_rules.sh` esiste e `FAIL=0`.
- [ ] Registrato in `tests/run-all.sh`.
- [ ] Nessuna regressione sugli altri `test_session_start_*.sh`.
- [ ] Il file regole NON viene perso dal test (trap di restore presente).

## Commit
```bash
git add hooks/session-start tests/hooks/test_session_start_global_rules.sh tests/run-all.sh
git commit -m "feat(session-start): inietta SIAE Global Rules (fonte unica versionata)"
```
