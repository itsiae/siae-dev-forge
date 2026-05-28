# Task 04 — Refactor `pr-blind-review-gate` + 7 integration test

> **REQUIRED SUB-SKILL:** `siae-tdd`
> **Dipendenza:** task 01 (lib esistente)

**Goal:** `hooks/pr-blind-review-gate` usa `devforge_gate_scope_active`. 7 scenari integration PASS.

**File coinvolti:**
- Modifica: `hooks/pr-blind-review-gate` (rimuove L63-73 inline)
- Crea: `tests/integration/pr_blind_review_gate.test.sh`

---

## Step 1 — Scrivi il test fallente

Crea `tests/integration/pr_blind_review_gate.test.sh`:

```bash
#!/usr/bin/env bash
# Integration test pr-blind-review-gate — 7 scenari (design §6.2)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
HOOK="${REPO_ROOT}/hooks/pr-blind-review-gate"

PASS=0; FAIL=0; FAIL_DETAILS=""

TMPDIR=$(mktemp -d)
cleanup() {
    rm -rf "$TMPDIR"
    rm -f "${HOME}/.claude/.devforge-gate-scope"
    rm -f "${HOME}/.claude/.devforge-session-skills"
}
trap cleanup EXIT

setup_repo() {
    local remote="$1"
    rm -rf "$TMPDIR/repo"; mkdir -p "$TMPDIR/repo"
    (cd "$TMPDIR/repo" && git init -q && [ -n "$remote" ] && git remote add origin "$remote" || true)
}

run_hook() {
    local cwd="$1" cmd="$2"
    (cd "$cwd" && echo "{\"tool_input\":{\"command\":\"$cmd\"}}" | bash "$HOOK" 2>/dev/null)
}

assert_passes() {
    local n="$1" desc="$2" output="$3"
    if echo "$output" | grep -q '"decision"[[:space:]]*:[[:space:]]*"block"'; then
        FAIL=$((FAIL + 1)); FAIL_DETAILS="${FAIL_DETAILS}\n  [FAIL] ${n} ${desc}"
    else
        PASS=$((PASS + 1)); printf "  [PASS] %s %s\n" "$n" "$desc"
    fi
}
assert_blocks() {
    local n="$1" desc="$2" output="$3"
    if echo "$output" | grep -q '"decision"[[:space:]]*:[[:space:]]*"block"'; then
        PASS=$((PASS + 1)); printf "  [PASS] %s %s\n" "$n" "$desc"
    else
        FAIL=$((FAIL + 1)); FAIL_DETAILS="${FAIL_DETAILS}\n  [FAIL] ${n} ${desc}: ${output}"
    fi
}

mark_validated() { mkdir -p "${HOME}/.claude"; echo "siae-blind-review" >> "${HOME}/.claude/.devforge-session-skills"; }
clear_validated() { rm -f "${HOME}/.claude/.devforge-session-skills"; }

# A-G come pr-premortem ma con marker siae-blind-review e comando 'gh pr create'
clear_validated; mark_validated; setup_repo "git@github.com:itsiae/foo.git"; unset DEVFORGE_GATE_SCOPE
assert_passes A "universal + itsiae + validated" "$(run_hook "$TMPDIR/repo" "gh pr create")"

clear_validated; setup_repo "git@github.com:itsiae/foo.git"
assert_blocks B "universal + itsiae + not validated" "$(run_hook "$TMPDIR/repo" "gh pr create")"

clear_validated; mark_validated; setup_repo "git@github.com:acme/foo.git"
assert_passes C "universal + acme + validated" "$(run_hook "$TMPDIR/repo" "gh pr create")"

clear_validated; setup_repo "git@github.com:acme/foo.git"
assert_blocks D "universal + acme + not validated (NEW)" "$(run_hook "$TMPDIR/repo" "gh pr create")"

clear_validated; setup_repo ""
assert_blocks E "universal + no remote + not validated" "$(run_hook "$TMPDIR/repo" "gh pr create")"

clear_validated; setup_repo "git@github.com:itsiae/foo.git"; export DEVFORGE_GATE_SCOPE=itsiae
assert_blocks F "itsiae scope + itsiae + not validated" "$(run_hook "$TMPDIR/repo" "gh pr create")"

clear_validated; setup_repo "git@github.com:acme/foo.git"; export DEVFORGE_GATE_SCOPE=itsiae
assert_passes G "itsiae scope + acme + not validated (rollback)" "$(run_hook "$TMPDIR/repo" "gh pr create")"

unset DEVFORGE_GATE_SCOPE; clear_validated

echo
echo "pr_blind_review_gate.test.sh — PASS: $PASS / 7 — FAIL: $FAIL / 7"
[ -n "$FAIL_DETAILS" ] && echo -e "$FAIL_DETAILS"
[ "$FAIL" -eq 0 ] || exit 1
```

## Step 2 — Esegui e verifica che fallisce

```bash
bash tests/integration/pr_blind_review_gate.test.sh
```

Atteso: FAIL scenario D (gate no-op fuori itsiae pre-refactor).

## Step 3 — Implementa il refactor

Modifica `hooks/pr-blind-review-gate`:

**Edit 1** — aggiungi `source "${PLUGIN_ROOT}/lib/scope-check.sh" 2>/dev/null || true` nel blocco source esistente (L19-23).

**Edit 2** — sostituisci L62-73:

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
bash -n hooks/pr-blind-review-gate && bash tests/integration/pr_blind_review_gate.test.sh
```

Atteso: `PASS: 7 / 7`, exit 0.

## Step 5 — Commit

```bash
git add hooks/pr-blind-review-gate tests/integration/pr_blind_review_gate.test.sh
git commit -m "refactor(hooks): pr-blind-review-gate uses scope-check lib

Gate active on any git repo by default. 7 integration tests PASS.

Co-Authored-By: SIAE DevForge"
```

---

## Criteri di accettazione

- [ ] `grep -c "grep.*itsiae" hooks/pr-blind-review-gate` = 0
- [ ] `hooks/pr-blind-review-gate` source-a `lib/scope-check.sh`
- [ ] `bash -n hooks/pr-blind-review-gate` exit 0
- [ ] `bash tests/integration/pr_blind_review_gate.test.sh` exit 0 con `PASS: 7 / 7`
