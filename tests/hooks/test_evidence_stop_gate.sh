#!/usr/bin/env bash
# test_evidence_stop_gate.sh — ADR-006 + ADR-008 rewrite of stop-gate.
# Covers: 2-block escape removed, DEVFORGE_FORCE_STOP explicit bypass,
# session-scope rollback path.
set -eu
PASS=0; FAIL=0
REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK="${REPO_ROOT}/hooks/stop-gate"

_invoke_with_completion() {
    # Minimal transcript with an assistant message containing a completion claim.
    cat <<JSON
{"messages":[{"role":"user","content":"fai la fix"},{"role":"assistant","content":"fatto, tutto completato"}]}
JSON
}

_run_hook() {
    local tmp_home; tmp_home=$(mktemp -d)
    mkdir -p "$tmp_home/.claude"
    # Provide an empty session-skills so retrospective gate logic has a file.
    printf 'siae-retrospective\n' > "$tmp_home/.claude/.devforge-session-skills"
    _invoke_with_completion | HOME="$tmp_home" env DEVFORGE_USE_SESSION_SCOPE="${1:-0}" DEVFORGE_FORCE_STOP="${2:-0}" SKILLS_SEED="${3:-}" bash -c '
        if [ -n "$SKILLS_SEED" ]; then
            printf "%s\n" "$SKILLS_SEED" > "$HOME/.claude/.devforge-session-skills"
        fi
        bash "'"$HOOK"'" 2>/dev/null
    '
    rm -rf "$tmp_home" >/dev/null 2>&1 || true
}

echo "=== 1. Completion claim + no verification → block ==="
OUT=$(_run_hook 1 0 "siae-retrospective")
if echo "$OUT" | grep -q '"decision": "block"' && echo "$OUT" | grep -q "siae-verification"; then
    echo "  PASS  block emitted"; PASS=$((PASS+1))
else
    echo "  FAIL  expected block, got: $(echo "$OUT" | head -3)"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== 2. Completion claim + siae-verification in session → allow (rollback scope) ==="
OUT=$(_run_hook 1 0 "siae-verification,siae-retrospective")
if ! echo "$OUT" | grep -q '"decision": "block"'; then
    echo "  PASS  allowed"; PASS=$((PASS+1))
else
    echo "  FAIL  unexpected block: $(echo "$OUT" | head -3)"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== 3. DEVFORGE_FORCE_STOP=1 → allow + tracked ==="
OUT=$(_run_hook 1 1 "siae-retrospective")
if ! echo "$OUT" | grep -q '"decision": "block"'; then
    echo "  PASS  force-stop allowed"; PASS=$((PASS+1))
else
    echo "  FAIL  force-stop still blocked"; FAIL=$((FAIL+1))
fi

echo ""
echo "=== 4. No auto-escape after 2 consecutive blocks (ADR-006) ==="
TMPH=$(mktemp -d)
mkdir -p "$TMPH/.claude"
printf 'siae-retrospective\n' > "$TMPH/.claude/.devforge-session-skills"
# Seed a counter at 5 to make sure an old-style escape would trigger
echo "5" > "$TMPH/.claude/.devforge-stop-block-count"
OUT=$(_invoke_with_completion | HOME="$TMPH" env DEVFORGE_USE_SESSION_SCOPE=1 bash "$HOOK" 2>/dev/null || true)
if echo "$OUT" | grep -q '"decision": "block"'; then
    echo "  PASS  still blocked (no auto-escape)"; PASS=$((PASS+1))
else
    echo "  FAIL  auto-escape still present"; FAIL=$((FAIL+1))
fi
rm -rf "$TMPH"

echo ""
echo "Total: $((PASS+FAIL)) — PASS: $PASS — FAIL: $FAIL"
exit $FAIL
