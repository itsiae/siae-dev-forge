---
task: 01
title: Fix 5 MAJOR + 1 CRITICAL da auto-review PR #215
size: S
blocks: [02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13]
---

# Task 1 — Fix 5 MAJOR + 1 CRITICAL (PR #215 auto-review)

Assorbiti i finding di self-review documentati nel body di PR #215. Prima
task PR #2 per evitare che l'audit si trascini oltre.

## Finding da fixare

### CRITICAL #1 — `hooks/pre-commit` commento fall-through fuorviante

**File**: `hooks/pre-commit`
**Linea**: ~88 (dentro `if DEVFORGE_SKIP_GIT_GATE=1` branch)
**Attuale**: commento `# fall through to quality gate (not blocking)` errato —
non c'è un fall-through esplicito nel flusso.
**Fix**: riscrivere il commento spiegando che il branch continua implicitamente
nel quality gate sotto (già strutturato come if/elif/else con `:`  nobreak).

### MAJOR #1 — `compute_state_hash` non include `design_doc_mtime`

**File**: `hooks/devforge-context`
**Impatto**: edit di design doc non triggera re-emission del context
(stato resta uguale → hash uguale → dedup). L'utente aggiorna design ma
Claude non vede refresh.
**Fix**: aggiungere `design_doc_mtime` al materiale di hash:

```bash
DESIGN_DOC=$(ls -1t docs/plans/*-design.md 2>/dev/null | head -1)
DESIGN_MTIME=$(stat -f %m "$DESIGN_DOC" 2>/dev/null || stat -c %Y "$DESIGN_DOC" 2>/dev/null || echo 0)
# include DESIGN_MTIME nel material di hash
```

### MAJOR #2 — `assert_injection_reduction.sh` inquina `$HOME` reale

**File**: `tests/compression-regression/assert_injection_reduction.sh`
**Attuale**: `HOME=$X echo '{}' | bash hook.sh` modifica HOME del processo
ma non isola sufficientemente (se hook scrive fuori da `$HOME`, pollution).
**Fix**: usare TMPHOME dedicato + cleanup:

```bash
TMPHOME=$(mktemp -d)
trap "rm -rf $TMPHOME" EXIT
HOME="$TMPHOME" bash hook.sh
```

### MAJOR #3 — `escape_for_json` non gestisce `\t`, `\r`, control chars

**File**: `hooks/pre-commit` (già fixato in commit c50362a?), `hooks/stop-gate`
(linea 106)
**Attuale**: gestisce `\\`, `"`, `\n`, `\r`, `\t` ma NON escape di altri
control chars (0x00-0x1F).
**Fix**: aggiungere escape hex per byte < 0x20:

```bash
escape_for_json() {
    local s="$1"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\r'/\\r}"
    s="${s//$'\t'/\\t}"
    # control chars 0x00-0x1F (escluso \n \r \t già gestiti)
    s=$(printf '%s' "$s" | LC_ALL=C sed $'s/[\x00-\x08\x0b\x0c\x0e-\x1f]/?/g')
    printf '%s' "$s"
}
```

Centralizzare in `lib/json-escape.sh` e source da entrambi i consumer.

### MAJOR #4 — `devforge-context` write hash PRIMA di `cat EOF`

**File**: `hooks/devforge-context`
**Attuale**: salva nuovo hash nel file di state PRIMA di emettere il context.
Se `cat <<EOF` fallisce (pipe broken, disk full), hash aggiornato ma output
mai emesso → successive run skippano l'emission (dedup falso positivo).
**Fix**: emettere context PRIMA, scrivere hash DOPO conferma emission.

```bash
# OUTPUT context block
if cat <<EOF
{...}
EOF
then
    # successo emission → aggiorna hash
    echo "$NEW_HASH" > "$HASH_FILE.tmp" && mv "$HASH_FILE.tmp" "$HASH_FILE"
fi
```

### MAJOR #5 — (coincidente con SECURITY) `grep` regex non ancorate

**File**: vari hook
**Attuale**: `grep -qE "[/:]itsiae/"` usa regex (ok) ma alcuni grep usano
pattern non fixed-string dove non serve.
**Fix**: dove il match è substring letterale, preferire `grep -qF`. Dove
la regex è necessaria, mantenere `-E` e documentare.
(Nota: minore priorità, defense-in-depth, non bug funzionale.)

## Acceptance

- [ ] `hooks/pre-commit` commento CRITICAL chiarito
- [ ] `hooks/devforge-context` include `design_doc_mtime` in state hash
- [ ] `tests/compression-regression/assert_injection_reduction.sh` usa TMPHOME
- [ ] `lib/json-escape.sh` creato + source da pre-commit + stop-gate + devforge-context
- [ ] `hooks/devforge-context` emit-then-hash ordering corretto
- [ ] Test: 51/51 regression suite PR #1 continua a PASS
- [ ] 1 test nuovo: `devforge-context` triggera re-emission su design doc mtime change

## Out of scope

Non tocchiamo logica di gate in questo task. Solo robustezza/cleanup.
Task 5+ introduce task-scope.
