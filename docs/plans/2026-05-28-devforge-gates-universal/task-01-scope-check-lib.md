# Task 01 — Crea `lib/scope-check.sh` + 18 unit test

> **REQUIRED SUB-SKILL:** `siae-tdd`

**Goal:** Esiste `lib/scope-check.sh` con `devforge_gate_scope_active()` che ritorna 0 (attiva) o 1 (skip) basato su `DEVFORGE_GATE_SCOPE` env (con fallback state file). 18 unit test PASS.

**File coinvolti:**
- Crea: `lib/scope-check.sh`
- Crea: `tests/scope_check.test.sh`

---

## Step 1 — Scrivi il test fallente

Crea `tests/scope_check.test.sh` con 18 casi della matrice §6.1 del design.

```bash
#!/usr/bin/env bash
# Unit test per lib/scope-check.sh — matrice 18 casi (design §6.1)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Mock logger (no-op)
devforge_log() { :; }
export -f devforge_log

source "${REPO_ROOT}/lib/scope-check.sh"

PASS=0
FAIL=0
FAIL_DETAILS=""

run_case() {
    local n="$1" scope_env="$2" state_file_content="$3" remote_url="$4" expected_rc="$5" desc="$6"

    # Setup state file
    local sf="${HOME}/.claude/.devforge-gate-scope"
    if [ "$state_file_content" = "__ABSENT__" ]; then
        rm -f "$sf"
    elif [ "$state_file_content" = "__UNREADABLE__" ]; then
        mkdir -p "${HOME}/.claude"
        echo "itsiae" > "$sf"
        chmod 000 "$sf"
    else
        mkdir -p "${HOME}/.claude"
        printf '%s' "$state_file_content" > "$sf"
    fi

    # Setup env
    if [ "$scope_env" = "__UNSET__" ]; then
        unset DEVFORGE_GATE_SCOPE
    else
        export DEVFORGE_GATE_SCOPE="$scope_env"
    fi

    # Run
    local actual_rc=0
    devforge_gate_scope_active "$remote_url" || actual_rc=$?

    # Cleanup unreadable
    if [ "$state_file_content" = "__UNREADABLE__" ]; then
        chmod 644 "$sf" 2>/dev/null || true
        rm -f "$sf"
    fi

    if [ "$actual_rc" = "$expected_rc" ]; then
        PASS=$((PASS + 1))
        printf "  [PASS] #%s %s\n" "$n" "$desc"
    else
        FAIL=$((FAIL + 1))
        FAIL_DETAILS="${FAIL_DETAILS}\n  [FAIL] #${n} ${desc}: expected rc=${expected_rc} got rc=${actual_rc}"
    fi
}

# Matrice 18 casi
run_case  1 __UNSET__   __ABSENT__    "git@github.com:itsiae/foo.git"      0 "default universal + itsiae SSH"
run_case  2 __UNSET__   __ABSENT__    "git@github.com:acme/foo.git"        0 "default universal + acme SSH (NEW)"
run_case  3 __UNSET__   __ABSENT__    "https://github.com/itsiae/foo"      0 "default universal + itsiae HTTPS"
run_case  4 __UNSET__   __ABSENT__    ""                                    0 "default universal + empty remote"
run_case  5 __UNSET__   __ABSENT__    "git@gitlab.com:any/foo.git"         0 "default universal + gitlab"
run_case  6 universal   __ABSENT__    "git@github.com:itsiae/foo.git"      0 "explicit universal"
run_case  7 itsiae      __ABSENT__    "git@github.com:itsiae/foo.git"      0 "opt-in itsiae match SSH"
run_case  8 itsiae      __ABSENT__    "https://github.com/itsiae/foo"      0 "opt-in itsiae match HTTPS"
run_case  9 itsiae      __ABSENT__    "git@github.com:acme/foo.git"        1 "opt-in itsiae no-match"
run_case 10 itsiae      __ABSENT__    ""                                    1 "opt-in itsiae + empty"
run_case 11 itsiae      __ABSENT__    "git@github.com:itsiaefoo/x.git"     1 "regex boundary itsiaefoo"
run_case 12 itsiae      __ABSENT__    "git@github.com:foo-itsiae/x.git"    1 "regex boundary foo-itsiae"
run_case 13 garbage     __ABSENT__    "git@github.com:itsiae/x.git"        0 "garbage value fail-safe universal"
run_case 14 __UNSET__   "universal"   "anything"                            0 "state file universal"
run_case 15 __UNSET__   "itsiae"      "git@github.com:acme/foo.git"        1 "state file itsiae no-match"
run_case 16 universal   "itsiae"      "anything"                            0 "env priority over state"
run_case 17 __UNSET__   "  itsiae  "  "git@github.com:acme/x.git"          1 "state file trim whitespace"
run_case 18 __UNSET__   __UNREADABLE__ "git@github.com:acme/x.git"         0 "state file unreadable → default"

echo
echo "================================"
echo "scope_check.test.sh — Risultati"
echo "  PASS: $PASS / 18"
echo "  FAIL: $FAIL / 18"
[ -n "$FAIL_DETAILS" ] && echo -e "Failures:$FAIL_DETAILS"
echo "================================"

[ "$FAIL" -eq 0 ] || exit 1
exit 0
```

## Step 2 — Esegui e verifica che fallisce

```bash
bash tests/scope_check.test.sh
```

Output atteso: `bash: tests/scope_check.test.sh: lib/scope-check.sh: No such file or directory` oppure `devforge_gate_scope_active: command not found`. Exit code != 0.

## Step 3 — Implementa il codice minimo

Crea `lib/scope-check.sh`:

```bash
#!/usr/bin/env bash
# DevForge — Shared scope check for workflow gates.
# Single source of truth for the DEVFORGE_GATE_SCOPE policy.
#
# Usage: source this file, then call devforge_gate_scope_active "$REMOTE_URL"
#   - return 0 → gate should activate (proceed with validation)
#   - return 1 → gate should no-op (skip enforcement)
#
# Reads env (priority: env > state file > default):
#   DEVFORGE_GATE_SCOPE — "universal" (default) | "itsiae"
# Reads state file fallback (per env propagation issues in Claude Code subprocess hooks):
#   ~/.claude/.devforge-gate-scope (single line: "universal" or "itsiae")

devforge_gate_scope_active() {
    local remote_url="${1:-}"
    local scope="${DEVFORGE_GATE_SCOPE:-}"

    if [ -z "$scope" ] && [ -r "${HOME}/.claude/.devforge-gate-scope" ]; then
        scope=$(head -n1 "${HOME}/.claude/.devforge-gate-scope" 2>/dev/null | tr -d '[:space:]')
    fi

    scope="${scope:-universal}"

    case "$scope" in
        universal)
            return 0
            ;;
        itsiae)
            if echo "$remote_url" | grep -qE "[/:]itsiae/"; then
                return 0
            fi
            return 1
            ;;
        *)
            command -v devforge_log >/dev/null 2>&1 \
                && devforge_log "gate_scope_unknown_value" "warning" \
                   "{\"value\":\"${scope}\",\"fallback\":\"universal\"}" \
                   2>/dev/null || true
            return 0
            ;;
    esac
}
```

## Step 4 — Esegui e verifica che passa

```bash
bash tests/scope_check.test.sh
echo "exit_code=$?"
```

Output atteso:
```
  [PASS] #1 default universal + itsiae SSH
  [PASS] #2 default universal + acme SSH (NEW)
  ... (18 PASS)
================================
scope_check.test.sh — Risultati
  PASS: 18 / 18
  FAIL: 0 / 18
================================
exit_code=0
```

## Step 5 — Commit

```bash
git add lib/scope-check.sh tests/scope_check.test.sh
git commit -m "feat(lib): add scope-check.sh for universal gate enforcement

Shared library exposing devforge_gate_scope_active() that reads
DEVFORGE_GATE_SCOPE env (fallback state file). Default universal,
opt-in itsiae preserves legacy behavior. 18 unit tests PASS.

Co-Authored-By: SIAE DevForge"
```

---

## Criteri di accettazione

- [ ] `lib/scope-check.sh` esiste con `devforge_gate_scope_active()` esportata
- [ ] `tests/scope_check.test.sh` esiste con 18 casi
- [ ] `bash tests/scope_check.test.sh` exit 0
- [ ] Output mostra `PASS: 18 / 18`
- [ ] `bash -n lib/scope-check.sh` exit 0 (syntax valida)
- [ ] Test eseguiti con `set -euo pipefail`, no unbound var
