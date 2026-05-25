#!/usr/bin/env bash
# test_sentinel_handshake.sh — test bash per lib/sentinel-handshake.sh (Task 10).
#
# Verifica i case principali:
#   1. read sentinel valido → exit 0 + key=value su stdout (option_a_target_line=40, ecc.)
#   2. read sentinel mancante → exit 1
#   3. write target=40 → user-choice.json creato (target_line=40, target_branch=30)
#   4. write target=99 (invalid) → exit 1
#   5. (bonus) write target=70 → user-choice.json creato (target_line=70, target_branch=60)
#   6. (bonus) read sentinel malformed → exit 1
#
# Usage: bash skills/code-coverage/scripts/tests/test_sentinel_handshake.sh

set -e
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
HANDSHAKE="$SKILL_DIR/lib/sentinel-handshake.sh"

if [ ! -f "$HANDSHAKE" ]; then
    echo "FATAL: handshake script not found: $HANDSHAKE" >&2
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
        echo "  ✗ $name (output did not contain '$needle')"
        echo "    output was:"
        echo "$haystack" | sed 's/^/      /'
        TESTS_FAILED=$((TESTS_FAILED+1))
    fi
}

assert_json_field() {
    local file="$1"
    local key="$2"
    local expected="$3"
    local name="$4"
    if [ ! -f "$file" ]; then
        echo "  ✗ $name (file missing: $file)"
        TESTS_FAILED=$((TESTS_FAILED+1))
        return
    fi
    local actual
    actual=$(python3 -c "
import json, sys
with open('$file', 'r') as fh:
    data = json.load(fh)
print(data.get('$key', '<MISSING>'))
" 2>/dev/null)
    if [ "$actual" = "$expected" ]; then
        echo "  ✓ $name ($key=$actual)"
        TESTS_PASSED=$((TESTS_PASSED+1))
    else
        echo "  ✗ $name (expected $key=$expected, got $key=$actual)"
        TESTS_FAILED=$((TESTS_FAILED+1))
    fi
}

# Setup workspace temporaneo
TMPDIR="$(mktemp -d -t sentinel-handshake-test.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

setup_repo() {
    local name="$1"
    local repo="$TMPDIR/$name"
    mkdir -p "$repo/.code-coverage"
    echo "$repo"
}

write_valid_sentinel() {
    local repo="$1"
    cat > "$repo/.code-coverage/pending-user-choice.json" <<'EOF'
{
  "type": "forced_choice_coverage_target",
  "schema_version": "1.0",
  "context": {
    "repo": "pae-deposito-musica-be",
    "manifest_root": ".",
    "size_class": "medium",
    "source_level": "17",
    "spring_boot": true,
    "lombok_jdk_mismatch": false,
    "assertj_present": true
  },
  "options": {
    "A": {
      "label": "Coverage 40% — quick win",
      "target_line": 40,
      "target_branch": 30,
      "focus": ["POJO", "utility"],
      "estimated_wallclock_min_p50": 25,
      "estimated_wallclock_min_p90": 50
    },
    "B": {
      "label": "Coverage 70% — full bundle",
      "target_line": 70,
      "target_branch": 60,
      "focus": ["service layer"],
      "estimated_wallclock_min_p50": 98,
      "estimated_wallclock_min_p90": 164
    }
  },
  "default": null,
  "allow_skip": false
}
EOF
}

echo "test_sentinel_handshake.sh"
echo "  HANDSHAKE=$HANDSHAKE"

# ─────────────────────────────────────────────────────────────────────────────
# Case 1: read sentinel valido → exit 0 + struct key=value
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "Case 1: read sentinel valido"
REPO1="$(setup_repo case1)"
write_valid_sentinel "$REPO1"
set +e
STDOUT1="$(bash "$HANDSHAKE" read "$REPO1" 2>/dev/null)"
EXIT1=$?
set -e
assert_exit "$EXIT1" "0" "read valid sentinel → exit 0"
assert_contains "$STDOUT1" "type=forced_choice_coverage_target" "stdout contiene type"
assert_contains "$STDOUT1" "size_class=medium" "stdout contiene size_class"
assert_contains "$STDOUT1" "spring_boot=true" "stdout contiene spring_boot=true (bool)"
assert_contains "$STDOUT1" "option_a_target_line=40" "stdout contiene option_a_target_line=40"
assert_contains "$STDOUT1" "option_a_p50_min=25" "stdout contiene option_a_p50_min=25"
assert_contains "$STDOUT1" "option_a_p90_min=50" "stdout contiene option_a_p90_min=50"
assert_contains "$STDOUT1" "option_b_target_line=70" "stdout contiene option_b_target_line=70"
assert_contains "$STDOUT1" "option_b_p50_min=98" "stdout contiene option_b_p50_min=98"
assert_contains "$STDOUT1" "option_b_p90_min=164" "stdout contiene option_b_p90_min=164"
assert_contains "$STDOUT1" "option_a_label=Coverage 40%" "stdout contiene option_a_label"
assert_contains "$STDOUT1" "option_b_label=Coverage 70%" "stdout contiene option_b_label"

# ─────────────────────────────────────────────────────────────────────────────
# Case 2: read sentinel mancante → exit 1
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "Case 2: read sentinel mancante"
REPO2="$(setup_repo case2)"
# nessun pending-user-choice.json
set +e
bash "$HANDSHAKE" read "$REPO2" >/dev/null 2>&1
EXIT2=$?
set -e
assert_exit "$EXIT2" "1" "read sentinel mancante → exit 1"

# ─────────────────────────────────────────────────────────────────────────────
# Case 3: write target=40 → user-choice.json corretto
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "Case 3: write target=40"
REPO3="$(setup_repo case3)"
write_valid_sentinel "$REPO3"
set +e
bash "$HANDSHAKE" write "$REPO3" 40 >/dev/null 2>&1
EXIT3=$?
set -e
assert_exit "$EXIT3" "0" "write target=40 → exit 0"
USER_CHOICE3="$REPO3/.code-coverage/user-choice.json"
[ -f "$USER_CHOICE3" ] && \
    { echo "  ✓ user-choice.json creato"; TESTS_PASSED=$((TESTS_PASSED+1)); } || \
    { echo "  ✗ user-choice.json non creato"; TESTS_FAILED=$((TESTS_FAILED+1)); }
assert_json_field "$USER_CHOICE3" "target_line" "40" "target_line=40"
assert_json_field "$USER_CHOICE3" "target_branch" "30" "target_branch=30 (fixed rule)"
assert_json_field "$USER_CHOICE3" "size_class" "medium" "size_class=medium"
assert_json_field "$USER_CHOICE3" "estimated_wallclock_min_p50" "25" "p50=25 dal sentinel"
assert_json_field "$USER_CHOICE3" "estimated_wallclock_min_p90" "50" "p90=50 dal sentinel"
assert_json_field "$USER_CHOICE3" "source" "sentinel_handshake" "source=sentinel_handshake"

# ─────────────────────────────────────────────────────────────────────────────
# Case 4: write target=99 (invalid) → exit 1
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "Case 4: write target=99 (invalid)"
REPO4="$(setup_repo case4)"
write_valid_sentinel "$REPO4"
set +e
bash "$HANDSHAKE" write "$REPO4" 99 >/dev/null 2>&1
EXIT4=$?
set -e
assert_exit "$EXIT4" "1" "write target=99 → exit 1"
[ ! -f "$REPO4/.code-coverage/user-choice.json" ] && \
    { echo "  ✓ user-choice.json NON creato per target invalido"; TESTS_PASSED=$((TESTS_PASSED+1)); } || \
    { echo "  ✗ user-choice.json creato erroneamente"; TESTS_FAILED=$((TESTS_FAILED+1)); }

# ─────────────────────────────────────────────────────────────────────────────
# Case 5 (bonus): write target=70 → user-choice.json corretto (branch=60)
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "Case 5 (bonus): write target=70"
REPO5="$(setup_repo case5)"
write_valid_sentinel "$REPO5"
set +e
bash "$HANDSHAKE" write "$REPO5" 70 >/dev/null 2>&1
EXIT5=$?
set -e
assert_exit "$EXIT5" "0" "write target=70 → exit 0"
USER_CHOICE5="$REPO5/.code-coverage/user-choice.json"
assert_json_field "$USER_CHOICE5" "target_line" "70" "target_line=70"
assert_json_field "$USER_CHOICE5" "target_branch" "60" "target_branch=60 (fixed rule)"
assert_json_field "$USER_CHOICE5" "estimated_wallclock_min_p50" "98" "p50=98 da option B"
assert_json_field "$USER_CHOICE5" "estimated_wallclock_min_p90" "164" "p90=164 da option B"

# ─────────────────────────────────────────────────────────────────────────────
# Case 6 (bonus): read sentinel malformed → exit 1
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "Case 6 (bonus): read sentinel malformed"
REPO6="$(setup_repo case6)"
printf '%s' '{not valid json' > "$REPO6/.code-coverage/pending-user-choice.json"
set +e
bash "$HANDSHAKE" read "$REPO6" >/dev/null 2>&1
EXIT6=$?
set -e
assert_exit "$EXIT6" "1" "read malformed sentinel → exit 1"

# ─────────────────────────────────────────────────────────────────────────────
# Case 7 (bonus): subcommand mancante → exit 1
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "Case 7 (bonus): subcommand mancante"
set +e
bash "$HANDSHAKE" >/dev/null 2>&1
EXIT7=$?
set -e
assert_exit "$EXIT7" "1" "no args → exit 1"

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "──────────────────────────────────────────────"
echo "PASSED=$TESTS_PASSED FAILED=$TESTS_FAILED"
echo "──────────────────────────────────────────────"

[ $TESTS_FAILED -eq 0 ]
