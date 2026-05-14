#!/usr/bin/env bash
# Test: scripts/devforge-install-runners.sh
#
# Covers --help, --check, --dry-run, --stack validation, idempotence and
# default-stack behavior. External tools are mocked via PATH manipulation
# using fake stub scripts placed in a tmpdir.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTALLER="$REPO_ROOT/scripts/devforge-install-runners.sh"

PASS=0
FAIL=0

fail() {
    echo "FAIL: $1"
    FAIL=$((FAIL+1))
}
pass() {
    echo "PASS: $1"
    PASS=$((PASS+1))
}

if [[ ! -x "$INSTALLER" ]]; then
    echo "FAIL: setup — installer script not found or not executable at $INSTALLER"
    exit 1
fi

# --- Test 1: --help exits 0 and prints usage ---
OUT=$(bash "$INSTALLER" --help 2>&1) && RC=0 || RC=$?
if [[ "$RC" -eq 0 ]] && echo "$OUT" | grep -qi 'usage'; then
    pass "test1 — --help exits 0 and prints usage"
else
    fail "test1 — --help exit=$RC, output missing 'usage'"
fi

# --- Test 2: --check exits 0 even with empty PATH (nothing installed) ---
TMP_EMPTY=$(mktemp -d)
# Provide minimal core utils so the script itself runs (uname, tput, etc.).
# We rebuild a clean PATH that still has /bin and /usr/bin for core utils
# but skip /usr/local and brew bins so user tools register as MISSING.
SAFE_PATH="/usr/bin:/bin"
OUT=$(PATH="$SAFE_PATH" bash "$INSTALLER" --check 2>&1) && RC=0 || RC=$?
if [[ "$RC" -eq 0 ]] && echo "$OUT" | grep -qE 'MISSING|INSTALLED'; then
    pass "test2 — --check exits 0 and reports tool status"
else
    fail "test2 — --check exit=$RC (expected 0 with status report)"
    echo "--- output ---"
    echo "$OUT" | head -20
    echo "--------------"
fi
rm -rf "$TMP_EMPTY"

# --- Test 3: --dry-run --stack python prints pip3 install but does not execute ---
TMP_SENTINEL=$(mktemp -d)
SENTINEL="$TMP_SENTINEL/pip3-ran"
mkdir -p "$TMP_SENTINEL/bin"
cat > "$TMP_SENTINEL/bin/pip3" << EOF
#!/usr/bin/env bash
# Stub pip3 — would mutate system if invoked
echo "MUTATION" > "$SENTINEL"
exit 0
EOF
chmod +x "$TMP_SENTINEL/bin/pip3"
OUT=$(PATH="$TMP_SENTINEL/bin:/usr/bin:/bin" bash "$INSTALLER" --dry-run --stack python 2>&1) && RC=0 || RC=$?
if [[ "$RC" -eq 0 ]] && echo "$OUT" | grep -q 'pip3 install' && [[ ! -f "$SENTINEL" ]]; then
    pass "test3 — --dry-run --stack python prints pip3 install without executing"
else
    fail "test3 — exit=$RC; pip3 install printed=$(echo "$OUT" | grep -c 'pip3 install' || true); sentinel exists=$([[ -f "$SENTINEL" ]] && echo yes || echo no)"
    echo "--- output ---"
    echo "$OUT" | head -20
    echo "--------------"
fi
rm -rf "$TMP_SENTINEL"

# --- Test 4: --stack invalid exits non-zero with error ---
OUT=$(bash "$INSTALLER" --stack bogus 2>&1) && RC=0 || RC=$?
if [[ "$RC" -ne 0 ]] && echo "$OUT" | grep -qiE 'invalid|unknown|error'; then
    pass "test4 — --stack invalid exits non-zero with error"
else
    fail "test4 — exit=$RC; expected non-zero with error message"
fi

# --- Test 5: idempotence — fake bandit in PATH causes SKIP for bandit ---
TMP_FAKE=$(mktemp -d)
mkdir -p "$TMP_FAKE/bin"
cat > "$TMP_FAKE/bin/bandit" << 'EOF'
#!/usr/bin/env bash
echo "bandit 1.7.5 (stub)"
exit 0
EOF
chmod +x "$TMP_FAKE/bin/bandit"
OUT=$(PATH="$TMP_FAKE/bin:/usr/bin:/bin" bash "$INSTALLER" --check --stack python 2>&1) && RC=0 || RC=$?
# Expect a line showing bandit as INSTALLED (since `command -v bandit` succeeds)
if [[ "$RC" -eq 0 ]] && echo "$OUT" | grep -qE 'bandit.*INSTALLED|INSTALLED.*bandit'; then
    pass "test5 — fake bandit detected as INSTALLED (idempotence/skip logic verified)"
else
    fail "test5 — exit=$RC; bandit not reported as INSTALLED"
    echo "--- output ---"
    echo "$OUT" | head -30
    echo "--------------"
fi

# Also verify --dry-run with the same fake bandit reports SKIP
OUT=$(PATH="$TMP_FAKE/bin:/usr/bin:/bin" bash "$INSTALLER" --dry-run --stack python 2>&1) && RC=0 || RC=$?
if [[ "$RC" -eq 0 ]] && echo "$OUT" | grep -qE 'SKIP.*bandit|bandit.*already installed'; then
    pass "test5b — fake bandit reports SKIP under --dry-run"
else
    fail "test5b — exit=$RC; SKIP message for bandit missing"
    echo "--- output ---"
    echo "$OUT" | head -30
    echo "--------------"
fi
rm -rf "$TMP_FAKE"

# --- Test 6: default stack is 'all' (report mentions multiple stacks) ---
OUT=$(PATH="/usr/bin:/bin" bash "$INSTALLER" --check 2>&1) && RC=0 || RC=$?
# Expect coverage of cross-stack + python + java + aws sections at minimum
HITS=0
for kw in cross python java aws android; do
    if echo "$OUT" | grep -qi "$kw"; then
        HITS=$((HITS+1))
    fi
done
if [[ "$RC" -eq 0 ]] && [[ "$HITS" -ge 3 ]]; then
    pass "test6 — default stack 'all' covers multiple stacks (hits=$HITS)"
else
    fail "test6 — exit=$RC; hits=$HITS (expected >=3)"
    echo "--- output ---"
    echo "$OUT" | head -40
    echo "--------------"
fi

# --- Summary ---
echo ""
echo "Risultato: ${PASS} PASS, ${FAIL} FAIL"
if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
exit 0
