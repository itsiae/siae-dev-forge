# Task 03 — Refactor `tdd-gate` + 7 integration test

> **REQUIRED SUB-SKILL:** `siae-tdd`
> **Dipendenza:** task 01 (lib esistente)

**Goal:** `hooks/tdd-gate` usa `devforge_gate_scope_active`. 7 scenari integration PASS.

**File coinvolti:**
- Modifica: `hooks/tdd-gate` (rimuove L74-79 inline)
- Crea: `tests/integration/tdd_gate.test.sh`

---

## Step 1 — Scrivi il test fallente

Crea `tests/integration/tdd_gate.test.sh`:

```bash
#!/usr/bin/env bash
# Integration test tdd-gate — 7 scenari (design §6.2)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
HOOK="${REPO_ROOT}/hooks/tdd-gate"

PASS=0
FAIL=0
FAIL_DETAILS=""

TMPDIR=$(mktemp -d)
cleanup() {
    rm -rf "$TMPDIR"
    rm -f "${HOME}/.claude/.devforge-gate-scope"
    rm -f "${HOME}/.claude/.devforge-session-skills"
}
trap cleanup EXIT

setup_repo() {
    local remote="$1"
    rm -rf "$TMPDIR/repo"
    mkdir -p "$TMPDIR/repo"
    (cd "$TMPDIR/repo" && git init -q && [ -n "$remote" ] && git remote add origin "$remote" || true)
}

run_hook() {
    local cwd="$1" file_path="$2"
    (cd "$cwd" && echo "{\"tool_input\":{\"file_path\":\"$file_path\",\"new_string\":\"x\"}}" | bash "$HOOK" 2>/dev/null)
}

assert_passes() {
    local n="$1" desc="$2" output="$3"
    if echo "$output" | grep -q '"decision"[[:space:]]*:[[:space:]]*"block"'; then
        FAIL=$((FAIL + 1))
        FAIL_DETAILS="${FAIL_DETAILS}\n  [FAIL] ${n} ${desc}: expected pass got block"
    else
        PASS=$((PASS + 1))
        printf "  [PASS] %s %s\n" "$n" "$desc"
    fi
}

assert_blocks() {
    local n="$1" desc="$2" output="$3"
    if echo "$output" | grep -q '"decision"[[:space:]]*:[[:space:]]*"block"'; then
        PASS=$((PASS + 1))
        printf "  [PASS] %s %s\n" "$n" "$desc"
    else
        FAIL=$((FAIL + 1))
        FAIL_DETAILS="${FAIL_DETAILS}\n  [FAIL] ${n} ${desc}: expected block got pass. Output: $output"
    fi
}

mark_validated() {
    mkdir -p "${HOME}/.claude"
    echo "siae-tdd" >> "${HOME}/.claude/.devforge-session-skills"
}

clear_validated() {
    rm -f "${HOME}/.claude/.devforge-session-skills"
}

PROD_FILE="src/main/foo.java"

# A: universal + itsiae + validated → pass
clear_validated; mark_validated
setup_repo "git@github.com:itsiae/foo.git"
unset DEVFORGE_GATE_SCOPE
out=$(run_hook "$TMPDIR/repo" "$PROD_FILE")
assert_passes A "universal + itsiae + validated" "$out"

# B: universal + itsiae + NOT validated → block
clear_validated
setup_repo "git@github.com:itsiae/foo.git"
out=$(run_hook "$TMPDIR/repo" "$PROD_FILE")
assert_blocks B "universal + itsiae + not validated" "$out"

# C: universal + acme + validated → pass
clear_validated; mark_validated
setup_repo "git@github.com:acme/foo.git"
out=$(run_hook "$TMPDIR/repo" "$PROD_FILE")
assert_passes C "universal + acme + validated" "$out"

# D: universal + acme + NOT validated → block (NEW)
clear_validated
setup_repo "git@github.com:acme/foo.git"
out=$(run_hook "$TMPDIR/repo" "$PROD_FILE")
assert_blocks D "universal + acme + not validated (NEW)" "$out"

# E: universal + no remote + NOT validated → block
clear_validated
setup_repo ""
out=$(run_hook "$TMPDIR/repo" "$PROD_FILE")
assert_blocks E "universal + no remote + not validated" "$out"

# F: itsiae scope + itsiae + NOT validated → block (legacy)
clear_validated
setup_repo "git@github.com:itsiae/foo.git"
export DEVFORGE_GATE_SCOPE=itsiae
out=$(run_hook "$TMPDIR/repo" "$PROD_FILE")
assert_blocks F "itsiae scope + itsiae + not validated" "$out"

# G: itsiae scope + acme + NOT validated → pass (no-op rollback)
clear_validated
setup_repo "git@github.com:acme/foo.git"
export DEVFORGE_GATE_SCOPE=itsiae
out=$(run_hook "$TMPDIR/repo" "$PROD_FILE")
assert_passes G "itsiae scope + acme + not validated (rollback)" "$out"

unset DEVFORGE_GATE_SCOPE
clear_validated

echo
echo "tdd_gate.test.sh — PASS: $PASS / 7 — FAIL: $FAIL / 7"
[ -n "$FAIL_DETAILS" ] && echo -e "$FAIL_DETAILS"
[ "$FAIL" -eq 0 ] || exit 1
```

## Step 2 — Esegui e verifica che fallisce

```bash
bash tests/integration/tdd_gate.test.sh
```

Atteso: FAIL su scenario D (universal + acme + not validated → expected block got pass).

## Step 3 — Implementa il refactor

Modifica `hooks/tdd-gate`:

**Edit 1** — aggiungi `source "${PLUGIN_ROOT}/lib/scope-check.sh" 2>/dev/null || true` nel blocco source esistente (L28-35).

**Edit 2** — sostituisci L73-79:

```bash
# Scope check: DEVFORGE_GATE_SCOPE env (default universal). Vedi lib/scope-check.sh.
REMOTE_URL="$(git -C "$FILE_GIT_ROOT" remote get-url origin 2>/dev/null || true)"
if command -v devforge_gate_scope_active >/dev/null 2>&1 \
   && ! devforge_gate_scope_active "$REMOTE_URL"; then
    echo '{}'
    exit 0
fi
```

## Step 4 — Esegui e verifica che passa

```bash
bash -n hooks/tdd-gate && bash tests/integration/tdd_gate.test.sh
```

Atteso: `PASS: 7 / 7`, exit 0.

## Step 5 — Commit

```bash
git add hooks/tdd-gate tests/integration/tdd_gate.test.sh
git commit -m "refactor(hooks): tdd-gate uses scope-check lib

Gate active on any git repo by default. 7 integration tests PASS.

Co-Authored-By: SIAE DevForge"
```

---

## Criteri di accettazione

- [ ] `grep -c "grep.*itsiae" hooks/tdd-gate` = 0
- [ ] `hooks/tdd-gate` source-a `lib/scope-check.sh`
- [ ] `bash -n hooks/tdd-gate` exit 0
- [ ] `bash tests/integration/tdd_gate.test.sh` exit 0 con `PASS: 7 / 7`
