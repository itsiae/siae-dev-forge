# Task 02 — Refactor `pr-premortem-gate` + 7 integration test

> **REQUIRED SUB-SKILL:** `siae-tdd`
> **Dipendenza:** task 01 (lib esistente)

**Goal:** `hooks/pr-premortem-gate` usa `devforge_gate_scope_active` invece del blocco inline `grep itsiae`. 7 scenari integration test PASS.

**File coinvolti:**
- Modifica: `hooks/pr-premortem-gate` (rimuove L61-71 inline, aggiunge source lib + chiamata)
- Crea: `tests/integration/pr_premortem_gate.test.sh`

---

## Step 1 — Scrivi il test fallente

Crea `tests/integration/pr_premortem_gate.test.sh`:

```bash
#!/usr/bin/env bash
# Integration test pr-premortem-gate — 7 scenari (design §6.2)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
HOOK="${REPO_ROOT}/hooks/pr-premortem-gate"

PASS=0
FAIL=0
FAIL_DETAILS=""

# Setup temp git repo
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
    local cwd="$1" command_str="$2"
    (cd "$cwd" && echo "{\"tool_input\":{\"command\":\"$command_str\"}}" | bash "$HOOK" 2>/dev/null)
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
    echo "siae-premortem" >> "${HOME}/.claude/.devforge-session-skills"
}

clear_validated() {
    rm -f "${HOME}/.claude/.devforge-session-skills"
}

# A: universal + itsiae + validated → pass
clear_validated; mark_validated
setup_repo "git@github.com:itsiae/foo.git"
unset DEVFORGE_GATE_SCOPE
out=$(run_hook "$TMPDIR/repo" "gh pr create")
assert_passes A "universal + itsiae + validated" "$out"

# B: universal + itsiae + NOT validated → block
clear_validated
setup_repo "git@github.com:itsiae/foo.git"
out=$(run_hook "$TMPDIR/repo" "gh pr create")
assert_blocks B "universal + itsiae + not validated" "$out"

# C: universal + acme + validated → pass
clear_validated; mark_validated
setup_repo "git@github.com:acme/foo.git"
out=$(run_hook "$TMPDIR/repo" "gh pr create")
assert_passes C "universal + acme + validated" "$out"

# D: universal + acme + NOT validated → block (NEW behavior)
clear_validated
setup_repo "git@github.com:acme/foo.git"
out=$(run_hook "$TMPDIR/repo" "gh pr create")
assert_blocks D "universal + acme + not validated (NEW)" "$out"

# E: universal + no remote + NOT validated → block
clear_validated
setup_repo ""
out=$(run_hook "$TMPDIR/repo" "gh pr create")
assert_blocks E "universal + no remote + not validated" "$out"

# F: itsiae scope + itsiae + NOT validated → block (legacy)
clear_validated
setup_repo "git@github.com:itsiae/foo.git"
export DEVFORGE_GATE_SCOPE=itsiae
out=$(run_hook "$TMPDIR/repo" "gh pr create")
assert_blocks F "itsiae scope + itsiae + not validated" "$out"

# G: itsiae scope + acme + NOT validated → pass (no-op rollback)
clear_validated
setup_repo "git@github.com:acme/foo.git"
export DEVFORGE_GATE_SCOPE=itsiae
out=$(run_hook "$TMPDIR/repo" "gh pr create")
assert_passes G "itsiae scope + acme + not validated (rollback)" "$out"

unset DEVFORGE_GATE_SCOPE
clear_validated

echo
echo "pr_premortem_gate.test.sh — PASS: $PASS / 7 — FAIL: $FAIL / 7"
[ -n "$FAIL_DETAILS" ] && echo -e "$FAIL_DETAILS"
[ "$FAIL" -eq 0 ] || exit 1
```

## Step 2 — Esegui e verifica che fallisce

```bash
bash tests/integration/pr_premortem_gate.test.sh
```

Output atteso: scenario D `[FAIL] D universal + acme + not validated (NEW): expected block got pass` (gate oggi no-op fuori itsiae). Exit 1.

## Step 3 — Implementa il refactor

Modifica `hooks/pr-premortem-gate`:

**Edit 1** — aggiungi source lib dopo L23 (insieme agli altri source). Trasforma L19-23:

```bash
source "${PLUGIN_ROOT}/lib/logger.sh" 2>/dev/null || true
source "${PLUGIN_ROOT}/lib/block-explainer.sh" 2>/dev/null || true
source "${PLUGIN_ROOT}/lib/scope-check.sh" 2>/dev/null || true
if ! source "${PLUGIN_ROOT}/lib/cmd-parser.sh" 2>/dev/null \
   || ! source "${PLUGIN_ROOT}/lib/task-id.sh" 2>/dev/null \
   || ! source "${PLUGIN_ROOT}/lib/evidence-check.sh" 2>/dev/null; then
```

**Edit 2** — sostituisci L61-71 (scope check inline) con:

```bash
# Scope check: DEVFORGE_GATE_SCOPE env (default universal). Vedi lib/scope-check.sh.
GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [ -z "$GIT_ROOT" ]; then
    echo '{}'
    exit 0
fi
REMOTE_URL=$(git -C "$GIT_ROOT" remote get-url origin 2>/dev/null || true)
if command -v devforge_gate_scope_active >/dev/null 2>&1 \
   && ! devforge_gate_scope_active "$REMOTE_URL"; then
    echo '{}'
    exit 0
fi
```

## Step 4 — Esegui e verifica che passa

```bash
bash -n hooks/pr-premortem-gate && echo "syntax OK"
bash tests/integration/pr_premortem_gate.test.sh
```

Output atteso: `pr_premortem_gate.test.sh — PASS: 7 / 7 — FAIL: 0 / 7`. Exit 0.

## Step 5 — Commit

```bash
git add hooks/pr-premortem-gate tests/integration/pr_premortem_gate.test.sh
git commit -m "refactor(hooks): pr-premortem-gate uses scope-check lib

Replaces inline grep itsiae filter with devforge_gate_scope_active().
Gate now active on any git repo by default. 7 integration tests PASS.

Co-Authored-By: SIAE DevForge"
```

---

## Criteri di accettazione

- [ ] `hooks/pr-premortem-gate` non contiene più `grep -qE "[/:]itsiae/"` (verifica `grep -c "grep.*itsiae" hooks/pr-premortem-gate` = 0)
- [ ] `hooks/pr-premortem-gate` source-a `lib/scope-check.sh`
- [ ] `bash -n hooks/pr-premortem-gate` exit 0
- [ ] `bash tests/integration/pr_premortem_gate.test.sh` exit 0 con `PASS: 7 / 7`
