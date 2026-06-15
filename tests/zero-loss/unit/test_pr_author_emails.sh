#!/usr/bin/env bash
# Unit tests: task-07 — P5: pr_author_emails[] in post-commit-review.
#
# Verifies:
#   1. Repo fittizio con 2 commit con trailer DevForge-Author diversi →
#      pr_author_emails contiene entrambe le email (dedup, ordinate).
#   2. Repo fittizio senza trailer → pr_author_emails = [].
#   3. Shim git che simula git<2.32 (%(trailers:key=...,valueonly) ritorna vuoto,
#      %(trailers) plain ritorna il testo raw) → il ramo sed produce la lista.
#
# Conventions: set -uo pipefail, assert pattern, trap rm EXIT,
# shim PATH (REAL_GIT catturato PRIMA di iniettare lo shim — no ricorsione).
# NESSUN trap EXIT dentro funzioni invocate via $(...).

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
HOOK="${REPO_ROOT}/hooks/post-commit-review"

fail=0
pass=0

assert() {
    local name="$1" actual="$2" expected="$3"
    if [ "$actual" = "$expected" ]; then
        echo "  PASS: $name"
        pass=$((pass + 1))
    else
        echo "  FAIL: $name — expected '$expected' got '$actual'"
        fail=$((fail + 1))
    fi
}

assert_contains() {
    local name="$1" haystack="$2" needle="$3"
    if printf '%s' "$haystack" | grep -qF "$needle"; then
        echo "  PASS: $name (found '$needle')"
        pass=$((pass + 1))
    else
        echo "  FAIL: $name — expected to find '$needle' in: $haystack"
        fail=$((fail + 1))
    fi
}

assert_not_contains() {
    local name="$1" haystack="$2" needle="$3"
    if printf '%s' "$haystack" | grep -qF "$needle"; then
        echo "  FAIL: $name — '$needle' found but should NOT be in: $haystack"
        fail=$((fail + 1))
    else
        echo "  PASS: $name (not found '$needle')"
        pass=$((pass + 1))
    fi
}

# --- Extract _devforge_pr_author_emails_json from hook ---
# The function is defined directly in the hook; we source just the function
# by extracting+sourcing it. This avoids running the full hook.
# We rely on the function being defined with a standard name.

# Helper: compute pr_author_emails JSON using the logic from the hook.
# We source lib/logger.sh (for devforge_sanitize_json_str) and then define
# the function extracted from the hook.
LOGGER="${REPO_ROOT}/lib/logger.sh"

# --- isolated workspace ---
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

OLD_PATH="$PATH"
REAL_GIT=$(PATH="$OLD_PATH" command -v git 2>/dev/null || echo "/usr/bin/git")

# Minimal HOME environment for logger.sh
export HOME="$WORK"
mkdir -p "$WORK/.claude"
echo "testsid" > "$WORK/.claude/.devforge-session-id"
SESSION_DIR="$WORK/.claude/devforge-state/testsid"
mkdir -p "$SESSION_DIR"
cat > "$WORK/.claude.json" <<'EOF'
{
  "oauthAccount": {
    "emailAddress": "pr.test@siae.it",
    "accountUuid": "pr-test-uuid-0001",
    "organizationUuid": "pr-test-org-0001",
    "organizationName": "SIAE PR Test"
  }
}
EOF
export DEVFORGE_CLAUDE_JSON="$WORK/.claude.json"
export DEVFORGE_LOG_FILE="$SESSION_DIR/activity.jsonl"
touch "$DEVFORGE_LOG_FILE"
export DEVFORGE_PINNED_SID="testsid"
export DEVFORGE_SESSION_DIR="$SESSION_DIR"

# Source logger for devforge_sanitize_json_str
# shellcheck disable=SC1090
source "$LOGGER" 2>/dev/null || { echo "FATAL: cannot source $LOGGER"; exit 2; }

# ---------------------------------------------------------------
# Source the helper function _devforge_pr_author_emails_json from the hook.
# We extract only the function definition to avoid running hook mainline code.
# ---------------------------------------------------------------
_source_hook_function() {
    # Extract function body from hook using sed (portable).
    # The function starts with '_devforge_pr_author_emails_json()'
    # and ends at the matching closing brace at col-0.
    local tmp_fn
    tmp_fn=$(mktemp)
    awk '
        /^_devforge_pr_author_emails_json\(\)/ { found=1 }
        found { print }
        found && /^\}[[:space:]]*$/ { found=0; exit }
    ' "$HOOK" > "$tmp_fn"
    # shellcheck disable=SC1090
    source "$tmp_fn" 2>/dev/null
    rm -f "$tmp_fn"
}

_source_hook_function || { echo "FATAL: cannot source _devforge_pr_author_emails_json from hook"; exit 2; }

# Verify function was loaded
if ! declare -f _devforge_pr_author_emails_json >/dev/null 2>&1; then
    echo "FATAL: _devforge_pr_author_emails_json not found in hook after source"
    exit 2
fi

# ---------------------------------------------------------------
# Helper: create a fake git repo with commits under $WORK/<name>
# ---------------------------------------------------------------
make_repo() {
    local repodir="$1"
    mkdir -p "$repodir"
    cd "$repodir"
    "$REAL_GIT" init -b main >/dev/null 2>&1 || "$REAL_GIT" init >/dev/null 2>&1
    "$REAL_GIT" config user.email "tester@siae.it"
    "$REAL_GIT" config user.name "Tester"
    # Create a dummy "origin/main" ref by making a branch origin/main locally
    # (simulates the remote ref used by merge-base)
}

# ---------------------------------------------------------------
echo "=== TEST 1 — 2 commit con 2 email DevForge-Author diverse → array dedup ordinato ==="

REPO1="$WORK/repo1"
make_repo "$REPO1"
cd "$REPO1"

# Base commit (will serve as "origin/main")
touch base.txt
"$REAL_GIT" add base.txt
"$REAL_GIT" commit -m "$(printf 'base commit\n\nDevForge-Author: alice@siae.it')" >/dev/null 2>&1

BASE_SHA=$("$REAL_GIT" rev-parse HEAD)

# Create a local ref simulating origin/main pointing to base
"$REAL_GIT" update-ref refs/remotes/origin/main "$BASE_SHA"

# Commit 1: alice
touch c1.txt
"$REAL_GIT" add c1.txt
"$REAL_GIT" commit -m "$(printf 'commit one\n\nDevForge-Author: alice@siae.it')" >/dev/null 2>&1

# Commit 2: bob
touch c2.txt
"$REAL_GIT" add c2.txt
"$REAL_GIT" commit -m "$(printf 'commit two\n\nDevForge-Author: bob@siae.it')" >/dev/null 2>&1

# Commit 3: alice again (dedup test)
touch c3.txt
"$REAL_GIT" add c3.txt
"$REAL_GIT" commit -m "$(printf 'commit three\n\nDevForge-Author: alice@siae.it')" >/dev/null 2>&1

# Call the function with DEVFORGE_DEFAULT_BRANCH=main in this repo
result=$(cd "$REPO1" && DEVFORGE_DEFAULT_BRANCH=main _devforge_pr_author_emails_json 2>/dev/null)

# Check it is not empty
if [ -n "$result" ]; then
    echo "  PASS: T1a: risultato non vuoto (value=$result)"
    pass=$((pass + 1))
else
    echo "  FAIL: T1a — risultato vuoto"
    fail=$((fail + 1))
fi

assert_contains "T1b: contiene alice@siae.it" "$result" '"alice@siae.it"'
assert_contains "T1c: contiene bob@siae.it" "$result" '"bob@siae.it"'

# Verify it's a valid JSON array with exactly 2 entries (alice appears once, dedup)
entry_count=$(printf '%s' "$result" | grep -o '"[^"]*@[^"]*"' | wc -l | tr -d ' ')
assert "T1d: esattamente 2 entry (dedup)" "$entry_count" "2"

# Verify ordering: alice < bob alphabetically → alice first
first_entry=$(printf '%s' "$result" | grep -o '"[^"]*@[^"]*"' | head -1)
assert "T1e: prima entry ordinata (alice)" "$first_entry" '"alice@siae.it"'

# Verify JSON array syntax
assert_contains "T1f: inizia con [" "$result" "["
assert_contains "T1g: finisce con ]" "$result" "]"

# ---------------------------------------------------------------
echo ""
echo "=== TEST 2 — Repo senza trailer DevForge-Author → [] ==="

REPO2="$WORK/repo2"
make_repo "$REPO2"
cd "$REPO2"

# Base commit (no trailer)
touch base2.txt
"$REAL_GIT" add base2.txt
"$REAL_GIT" commit -m "base commit no trailer" >/dev/null 2>&1

BASE2_SHA=$("$REAL_GIT" rev-parse HEAD)
"$REAL_GIT" update-ref refs/remotes/origin/main "$BASE2_SHA"

# A commit without trailer
touch c4.txt
"$REAL_GIT" add c4.txt
"$REAL_GIT" commit -m "commit without trailer" >/dev/null 2>&1

result2=$(cd "$REPO2" && DEVFORGE_DEFAULT_BRANCH=main _devforge_pr_author_emails_json 2>/dev/null)

assert "T2a: senza trailer → []" "$result2" "[]"

# ---------------------------------------------------------------
echo ""
echo "=== TEST 3 — Shim git<2.32: %(trailers:key=...) vuoto, %(trailers) plain → fallback sed ==="

REPO3="$WORK/repo3"
make_repo "$REPO3"
cd "$REPO3"

# Base commit
touch base3.txt
"$REAL_GIT" add base3.txt
"$REAL_GIT" commit -m "$(printf 'base commit\n\nDevForge-Author: charlie@siae.it')" >/dev/null 2>&1

BASE3_SHA=$("$REAL_GIT" rev-parse HEAD)
"$REAL_GIT" update-ref refs/remotes/origin/main "$BASE3_SHA"

# Two PR commits with trailers
touch c5.txt
"$REAL_GIT" add c5.txt
"$REAL_GIT" commit -m "$(printf 'commit five\n\nDevForge-Author: charlie@siae.it')" >/dev/null 2>&1

touch c6.txt
"$REAL_GIT" add c6.txt
"$REAL_GIT" commit -m "$(printf 'commit six\n\nDevForge-Author: diana@siae.it')" >/dev/null 2>&1

# Build a git shim that simulates git<2.32 behaviour:
#   - When --format='%(trailers:key=DevForge-Author,valueonly)' → return empty
#   - When --format='%(trailers)' → call real git (returns full trailer lines)
#   - Everything else → pass through to real git
SHIM_DIR="$WORK/shims3"
mkdir -p "$SHIM_DIR"
cat > "$SHIM_DIR/git" <<SHIM_EOF
#!/usr/bin/env bash
# Shim simulating git<2.32: %(trailers:key=...,valueonly) returns empty.
# %(trailers) plain works (real git).
# All other commands pass through.
REAL_GIT_BIN="${REAL_GIT}"
args=("\$@")
cmdstr="\$*"
# Detect log with valueonly trailer format
if printf '%s' "\$cmdstr" | grep -q 'trailers:key=.*valueonly'; then
    # Return nothing (simulate old git that does not support valueonly)
    exit 0
fi
exec "\$REAL_GIT_BIN" "\$@"
SHIM_EOF
chmod +x "$SHIM_DIR/git"

# Inject shim into PATH (but not into REAL_GIT which we captured before)
export PATH="$SHIM_DIR:$OLD_PATH"

result3=$(cd "$REPO3" && DEVFORGE_DEFAULT_BRANCH=main _devforge_pr_author_emails_json 2>/dev/null)

# Restore PATH
export PATH="$OLD_PATH"

if [ -n "$result3" ]; then
    echo "  INFO: T3 result = $result3"
fi

assert_contains "T3a: charlie trovato via fallback sed" "$result3" '"charlie@siae.it"'
assert_contains "T3b: diana trovato via fallback sed" "$result3" '"diana@siae.it"'

# Verify still valid JSON array
assert_contains "T3c: inizia con [" "$result3" "["
assert_contains "T3d: finisce con ]" "$result3" "]"

entry_count3=$(printf '%s' "$result3" | grep -o '"[^"]*@[^"]*"' | wc -l | tr -d ' ')
assert "T3e: esattamente 2 entry nel fallback" "$entry_count3" "2"

# ---------------------------------------------------------------
echo ""
echo "=== TEST T_degraded — git<2.14 shim: BOTH %(trailers...) formats return empty → [] ==="

REPO_DEGRADED="$WORK/repo_degraded"
make_repo "$REPO_DEGRADED"
cd "$REPO_DEGRADED"

touch base_d.txt
"$REAL_GIT" add base_d.txt
"$REAL_GIT" commit -m "$(printf 'base\n\nDevForge-Author: eve@siae.it')" >/dev/null 2>&1

BASE_D_SHA=$("$REAL_GIT" rev-parse HEAD)
"$REAL_GIT" update-ref refs/remotes/origin/main "$BASE_D_SHA"

touch c_d.txt
"$REAL_GIT" add c_d.txt
"$REAL_GIT" commit -m "$(printf 'commit degraded\n\nDevForge-Author: eve@siae.it')" >/dev/null 2>&1

# Shim: both %(trailers:key=...,valueonly) and %(trailers) return empty (git<2.14 simulation)
SHIM_DIR_D="$WORK/shims_degraded"
mkdir -p "$SHIM_DIR_D"
cat > "$SHIM_DIR_D/git" <<SHIM_EOF_D
#!/usr/bin/env bash
# Shim simulating git<2.14: both %(trailers:key=...,valueonly) and %(trailers) unsupported.
REAL_GIT_BIN="${REAL_GIT}"
cmdstr="\$*"
if printf '%s' "\$cmdstr" | grep -q 'trailers'; then
    # Both %(trailers:key=...) and %(trailers) return empty (old git behaviour)
    exit 0
fi
exec "\$REAL_GIT_BIN" "\$@"
SHIM_EOF_D
chmod +x "$SHIM_DIR_D/git"

export PATH="$SHIM_DIR_D:$OLD_PATH"
result_degraded=$(cd "$REPO_DEGRADED" && DEVFORGE_DEFAULT_BRANCH=main _devforge_pr_author_emails_json 2>/dev/null)
export PATH="$OLD_PATH"

assert "T_degraded_a: git<2.14 entrambi i formati vuoti → [] senza errore" "$result_degraded" "[]"

# ---------------------------------------------------------------
echo ""
echo "=== TEST T4 — email con doppio apice nel valore → output JSON valido ==="

REPO4="$WORK/repo4"
make_repo "$REPO4"
cd "$REPO4"

touch base4.txt
"$REAL_GIT" add base4.txt
"$REAL_GIT" commit -m "base commit" >/dev/null 2>&1

BASE4_SHA=$("$REAL_GIT" rev-parse HEAD)
"$REAL_GIT" update-ref refs/remotes/origin/main "$BASE4_SHA"

touch c_t4.txt
"$REAL_GIT" add c_t4.txt
# Email with double-quote in value
"$REAL_GIT" commit -m "$(printf 'commit t4\n\nDevForge-Author: test"user@siae.it')" >/dev/null 2>&1

result4=$(cd "$REPO4" && DEVFORGE_DEFAULT_BRANCH=main _devforge_pr_author_emails_json 2>/dev/null)

# Should produce valid JSON: double-quote must be escaped as \"
assert_contains "T4a: JSON valido (apice escaped con backslash)" "$result4" '\"'
# Should start and end with brackets
assert_contains "T4b: inizia con [" "$result4" "["
assert_contains "T4c: finisce con ]" "$result4" "]"
# Validate JSON with python if available
if command -v python3 >/dev/null 2>&1; then
    if python3 -c "import sys,json; json.loads(sys.argv[1])" "$result4" 2>/dev/null; then
        echo "  PASS: T4d: python3 json.loads → JSON valido"
        pass=$((pass + 1))
    else
        echo "  FAIL: T4d: python3 json.loads → JSON NON valido per: $result4"
        fail=$((fail + 1))
    fi
fi

# ---------------------------------------------------------------
echo ""
echo "=== TEST T5 — trailer con valore vuoto → skippato, array invariato ==="

REPO5="$WORK/repo5"
make_repo "$REPO5"
cd "$REPO5"

touch base5.txt
"$REAL_GIT" add base5.txt
"$REAL_GIT" commit -m "base commit" >/dev/null 2>&1

BASE5_SHA=$("$REAL_GIT" rev-parse HEAD)
"$REAL_GIT" update-ref refs/remotes/origin/main "$BASE5_SHA"

touch c_t5a.txt
"$REAL_GIT" add c_t5a.txt
# Commit with a valid trailer AND an empty trailer (DevForge-Author: with no value)
"$REAL_GIT" commit -m "$(printf 'commit t5a\n\nDevForge-Author: frank@siae.it')" >/dev/null 2>&1

touch c_t5b.txt
"$REAL_GIT" add c_t5b.txt
# Commit with empty DevForge-Author trailer value (should be skipped)
"$REAL_GIT" commit -m "$(printf 'commit t5b\n\nDevForge-Author: ')" >/dev/null 2>&1

result5=$(cd "$REPO5" && DEVFORGE_DEFAULT_BRANCH=main _devforge_pr_author_emails_json 2>/dev/null)

# frank should be present; no empty string entry
assert_contains "T5a: frank@siae.it presente" "$result5" '"frank@siae.it"'
# Verify no empty string entry ("" would indicate empty value was included)
assert_not_contains "T5b: nessuna entry vuota (\"\")" "$result5" '""'
# Validate JSON with python if available
if command -v python3 >/dev/null 2>&1; then
    if python3 -c "import sys,json; json.loads(sys.argv[1])" "$result5" 2>/dev/null; then
        echo "  PASS: T5c: python3 json.loads → JSON valido"
        pass=$((pass + 1))
    else
        echo "  FAIL: T5c: python3 json.loads → JSON NON valido per: $result5"
        fail=$((fail + 1))
    fi
fi

# ---------------------------------------------------------------
echo ""
echo "SUMMARY: $pass passed, $fail failed"
exit $fail
