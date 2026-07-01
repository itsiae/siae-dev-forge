#!/usr/bin/env bash
# test_file_taxonomy_trivial.sh — unit tests for devforge_change_is_trivial (REQ-DF-04)
# Covers: trivial = estensione non-IaC AND lines_changed <= soglia AND
# path non-sensibile (hooks/, lib/*gate*, lib/review_evidence/).
set -eu
PASS=0; FAIL=0
REPO_ROOT="$(git rev-parse --show-toplevel)"
LIB_FILE="${REPO_ROOT}/lib/file-taxonomy.sh"

if [ ! -f "$LIB_FILE" ]; then
    echo "FAIL — $LIB_FILE not found"
    exit 1
fi

# shellcheck disable=SC1090
source "$LIB_FILE"

_expect_trivial() {
    local name="$1" path="$2" lines="$3"
    if devforge_change_is_trivial "$path" "$lines"; then
        echo "  PASS  $name — $path ($lines lines)"; PASS=$((PASS+1))
    else
        echo "  FAIL  $name — $path ($lines lines) should be TRIVIAL"; FAIL=$((FAIL+1))
    fi
}

_expect_not_trivial() {
    local name="$1" path="$2" lines="$3"
    if devforge_change_is_trivial "$path" "$lines"; then
        echo "  FAIL  $name — $path ($lines lines) should NOT be trivial"; FAIL=$((FAIL+1))
    else
        echo "  PASS  $name — $path ($lines lines)"; PASS=$((PASS+1))
    fi
}

echo "=== 1. Trivial: small change, non-IaC, non-sensitive path ==="
_expect_trivial "small markdown"  "README.md" 5
_expect_trivial "small python"    "app/handler.py" 5
_expect_trivial "at threshold"    "app/handler.py" 15

echo ""
echo "=== 2. NOT trivial: sensitive path (hooks/) ==="
_expect_not_trivial "hooks pr-gate"  "hooks/pr-gate" 5
_expect_not_trivial "hooks any file" "hooks/session-start" 3

echo ""
echo "=== 3. NOT trivial: sensitive path (lib/*gate*) ==="
_expect_not_trivial "lib gate file"  "lib/tdd-gate-helpers.sh" 5
_expect_not_trivial "lib gate dir"   "lib/gate/foo.sh" 5

echo ""
echo "=== 4. NOT trivial: sensitive path (lib/review_evidence/) ==="
_expect_not_trivial "review_evidence" "lib/review_evidence/_sarif.py" 5

echo ""
echo "=== 5. NOT trivial: IaC extension regardless of size ==="
_expect_not_trivial "tf 1 line"   "terraform/main.tf" 1
_expect_not_trivial "hcl 1 line"  "terragrunt.hcl" 1

echo ""
echo "=== 6. NOT trivial: over the line threshold ==="
_expect_not_trivial "40 lines python" "app/handler.py" 40
_expect_not_trivial "16 lines just over" "app/handler.py" 16

echo ""
echo "=== 7. Configurable threshold via DEVFORGE_BRAINSTORM_TRIVIAL_MAX_LINES ==="
(
    export DEVFORGE_BRAINSTORM_TRIVIAL_MAX_LINES=5
    if devforge_change_is_trivial "app/handler.py" 10; then
        echo "  FAIL  10 lines should NOT be trivial with threshold=5"
        exit 1
    else
        echo "  PASS  10 lines correctly NOT trivial with threshold=5"
    fi
) && PASS=$((PASS+1)) || FAIL=$((FAIL+1))

echo ""
echo "Total: $((PASS+FAIL)) — PASS: $PASS — FAIL: $FAIL"
exit $FAIL
