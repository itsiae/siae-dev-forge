#!/usr/bin/env bash
# Test: session-start preserves session-skills on resume|clear|compact,
# resets only on startup or unknown source.
#
# Fixes recurring sub-skill-gate false positives after auto-compact.
set -eu
PASS=0; FAIL=0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$SCRIPT_DIR"

_assert() {
    local name="$1"; local cmd="$2"
    if eval "$cmd" >/dev/null 2>&1; then echo "  PASS  $name"; PASS=$((PASS+1))
    else echo "  FAIL  $name (cmd: $cmd)"; FAIL=$((FAIL+1)); fi
}

# Isolated HOME
export HOME="$(mktemp -d)"
mkdir -p "$HOME/.claude/devforge-state"
trap 'rm -rf "$HOME"' EXIT

HOOK="$SCRIPT_DIR/hooks/session-start"
SKILLS_FILE="$HOME/.claude/.devforge-session-skills"

echo "=== Case 1: source=resume preserves skills ==="
echo "siae-tdd,siae-brainstorming" > "$SKILLS_FILE"
echo '{"source":"resume"}' | bash "$HOOK" >/dev/null 2>&1 || true
_assert "resume preserves skills" \
    "grep -q 'siae-tdd,siae-brainstorming' $SKILLS_FILE"

echo ""
echo "=== Case 2: source=clear preserves skills ==="
echo "siae-git-workflow" > "$SKILLS_FILE"
echo '{"source":"clear"}' | bash "$HOOK" >/dev/null 2>&1 || true
_assert "clear preserves skills" \
    "grep -q 'siae-git-workflow' $SKILLS_FILE"

echo ""
echo "=== Case 3: source=compact preserves skills ==="
echo "siae-verification" > "$SKILLS_FILE"
echo '{"source":"compact"}' | bash "$HOOK" >/dev/null 2>&1 || true
_assert "compact preserves skills" \
    "grep -q 'siae-verification' $SKILLS_FILE"

echo ""
echo "=== Case 4: source=startup resets skills (new session) ==="
echo "siae-tdd" > "$SKILLS_FILE"
echo '{"source":"startup"}' | bash "$HOOK" >/dev/null 2>&1 || true
SIZE=$(wc -c < "$SKILLS_FILE" | tr -d ' ')
_assert "startup resets skills (file empty or near-empty)" \
    "[ $SIZE -le 1 ]"

echo ""
echo "=== Case 5: no source field (unknown) resets (backward-compat) ==="
echo "siae-tdd" > "$SKILLS_FILE"
echo '{}' | bash "$HOOK" >/dev/null 2>&1 || true
SIZE=$(wc -c < "$SKILLS_FILE" | tr -d ' ')
_assert "missing source field resets (safe default)" \
    "[ $SIZE -le 1 ]"

echo ""
echo "Total: $((PASS+FAIL))  PASS: $PASS  FAIL: $FAIL"
exit $FAIL
