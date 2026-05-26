#!/usr/bin/env bash
# test_phase4_gate.sh — test bash per lib/phase4-gate.sh (HARD-WARN consumer gate).
#
# Verifica i 4 case principali:
#   1. env.json mancante → exit 0 (fail-open)
#   2. severity=OK → exit 0, no output
#   3. severity=WARN → exit 0, stderr contiene "WARN"
#   4. severity=HARD-WARN → exit 2, stderr contiene "BLOCKED" + "Suggested fix" + reason
#
# Usage: bash skills/code-coverage/scripts/tests/test_phase4_gate.sh

set -e
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
GATE="$SKILL_DIR/lib/phase4-gate.sh"

if [ ! -f "$GATE" ]; then
    echo "FATAL: gate script not found: $GATE" >&2
    exit 1
fi

TESTS_PASSED=0
TESTS_FAILED=0

assert_exit() {
    local actual="$1"
    local expected="$2"
    local name="$3"
    if [ "$actual" = "$expected" ]; then
        echo "  ✓ $name"
        TESTS_PASSED=$((TESTS_PASSED+1))
    else
        echo "  ✗ $name (expected exit=$expected got exit=$actual)"
        TESTS_FAILED=$((TESTS_FAILED+1))
    fi
}

assert_contains() {
    local haystack="$1"
    local needle="$2"
    local name="$3"
    if echo "$haystack" | grep -q -- "$needle"; then
        echo "  ✓ $name"
        TESTS_PASSED=$((TESTS_PASSED+1))
    else
        echo "  ✗ $name (stderr did not contain '$needle')"
        echo "    stderr was: $haystack"
        TESTS_FAILED=$((TESTS_FAILED+1))
    fi
}

assert_empty() {
    local actual="$1"
    local name="$2"
    if [ -z "$actual" ]; then
        echo "  ✓ $name"
        TESTS_PASSED=$((TESTS_PASSED+1))
    else
        echo "  ✗ $name (expected empty output, got: $actual)"
        TESTS_FAILED=$((TESTS_FAILED+1))
    fi
}

# Setup workspace temporaneo
TMPDIR="$(mktemp -d -t phase4-gate-test.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

setup_repo() {
    local name="$1"
    local repo="$TMPDIR/$name"
    mkdir -p "$repo/.code-coverage"
    echo "$repo"
}

write_env() {
    local repo="$1"
    local content="$2"
    printf '%s' "$content" > "$repo/.code-coverage/env.json"
}

echo "test_phase4_gate.sh"
echo "  GATE=$GATE"

# ─────────────────────────────────────────────────────────────────────────────
# Case 1: env.json mancante → exit 0 (fail-open)
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "Case 1: env.json mancante → fail-open (exit 0)"
REPO1="$(setup_repo case1)"
rm -f "$REPO1/.code-coverage/env.json"  # ensure missing
set +e
STDERR1="$(bash "$GATE" "$REPO1" 2>&1 >/dev/null)"
EXIT1=$?
set -e
assert_exit "$EXIT1" "0" "exit 0 fail-open quando env.json manca"
assert_empty "$STDERR1" "stderr vuoto (silent fail-open)"

# ─────────────────────────────────────────────────────────────────────────────
# Case 2: severity=OK → exit 0, no output
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "Case 2: severity=OK → exit 0, silent"
REPO2="$(setup_repo case2)"
write_env "$REPO2" '{
  "jdk_compat": {
    "severity": "OK",
    "reason": "",
    "suggested_fix": "",
    "jdk_major": 17,
    "lombok_version": "1.18.30",
    "source_level": "17"
  }
}'
set +e
STDERR2="$(bash "$GATE" "$REPO2" 2>&1 >/dev/null)"
EXIT2=$?
set -e
assert_exit "$EXIT2" "0" "exit 0 quando severity=OK"
assert_empty "$STDERR2" "stderr vuoto quando severity=OK"

# ─────────────────────────────────────────────────────────────────────────────
# Case 3: severity=WARN → exit 0, stderr contiene "WARN"
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "Case 3: severity=WARN → exit 0 + warning su stderr"
REPO3="$(setup_repo case3)"
write_env "$REPO3" '{
  "jdk_compat": {
    "severity": "WARN",
    "reason": "JDK runtime non rilevato",
    "suggested_fix": "",
    "jdk_major": null,
    "lombok_version": "1.18.30",
    "source_level": "17"
  }
}'
set +e
STDERR3="$(bash "$GATE" "$REPO3" 2>&1 >/dev/null)"
EXIT3=$?
set -e
assert_exit "$EXIT3" "0" "exit 0 quando severity=WARN"
assert_contains "$STDERR3" "WARN" "stderr contiene token 'WARN'"
assert_contains "$STDERR3" "JDK runtime non rilevato" "stderr contiene reason"

# ─────────────────────────────────────────────────────────────────────────────
# Case 4: severity=HARD-WARN → exit 2, stderr completo
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "Case 4: severity=HARD-WARN → exit 2 + BLOCKED + Suggested fix"
REPO4="$(setup_repo case4)"
write_env "$REPO4" '{
  "jdk_compat": {
    "severity": "HARD-WARN",
    "reason": "Lombok 1.18.16 max_jdk=15, runtime is 25 → TypeTag UNKNOWN / javac internals breaking expected",
    "suggested_fix": "export JAVA_HOME=$(/usr/libexec/java_home -v 15)  # o equivalente Linux/Windows",
    "jdk_major": 25,
    "lombok_version": "1.18.16",
    "source_level": "8"
  }
}'
set +e
STDERR4="$(bash "$GATE" "$REPO4" 2>&1 >/dev/null)"
EXIT4=$?
set -e
assert_exit "$EXIT4" "2" "exit 2 quando severity=HARD-WARN"
assert_contains "$STDERR4" "BLOCKED" "stderr contiene token 'BLOCKED'"
assert_contains "$STDERR4" "Suggested fix" "stderr contiene 'Suggested fix'"
assert_contains "$STDERR4" "Lombok 1.18.16" "stderr contiene reason (Lombok version)"
assert_contains "$STDERR4" "JAVA_HOME" "stderr contiene comando suggested_fix"
assert_contains "$STDERR4" "ignore-jdk-mismatch" "stderr contiene override hint"

# ─────────────────────────────────────────────────────────────────────────────
# Case 5 (bonus): JSON malformato → fail-open (exit 0)
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "Case 5 (bonus): env.json malformato → fail-open"
REPO5="$(setup_repo case5)"
printf '%s' '{this is not valid json' > "$REPO5/.code-coverage/env.json"
set +e
bash "$GATE" "$REPO5" >/dev/null 2>&1
EXIT5=$?
set -e
assert_exit "$EXIT5" "0" "exit 0 fail-open quando env.json malformato"

# ─────────────────────────────────────────────────────────────────────────────
# Case 6 (bonus): sourcing + chiamata diretta della funzione
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "Case 6 (bonus): sourceable + chiamata funzione diretta"
set +e
SOURCED_EXIT=$(bash -c "source '$GATE'; check_jdk_compat_gate '$REPO4' 2>/dev/null; echo \$?")
set -e
assert_exit "$SOURCED_EXIT" "2" "check_jdk_compat_gate da source → exit 2 su HARD-WARN"

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "──────────────────────────────────────────────"
echo "PASSED=$TESTS_PASSED FAILED=$TESTS_FAILED"
echo "──────────────────────────────────────────────"

[ $TESTS_FAILED -eq 0 ]
