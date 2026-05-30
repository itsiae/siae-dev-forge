#!/usr/bin/env bash
# DevForge — verify all subagents default to Sonnet 4.6
#
# Background: until v1.72.1 all DevForge agents used `model: inherit`, meaning
# the subagent ran on whatever model the parent session was using (e.g. Opus 4.7).
# Starting v1.73.0 we pin agents to `model: sonnet` for cost + eval-baseline
# consistency. Users who want to override can pass `Agent({model: "opus"})`
# explicitly in their tool call.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
AGENTS_DIR="${REPO_ROOT}/agents"

PASS=0
FAIL=0
FAIL_DETAILS=""

assert() {
    local desc="$1" cmd="$2"
    if eval "$cmd"; then
        PASS=$((PASS + 1))
        printf "  [PASS] %s\n" "$desc"
    else
        FAIL=$((FAIL + 1))
        FAIL_DETAILS="${FAIL_DETAILS}\n  [FAIL] ${desc}"
    fi
}

# 1. Each agent file declares model: sonnet
EXPECTED_AGENTS=(
    "code-reviewer"
    "doc-generator"
    "mcp-impact-analyst"
    "qa-investigator"
    "spec-reviewer"
)

for agent in "${EXPECTED_AGENTS[@]}"; do
    file="${AGENTS_DIR}/${agent}.md"
    assert "agents/${agent}.md exists" "[ -f '$file' ]"
    assert "agents/${agent}.md has 'model: sonnet'" \
        "grep -qE '^model: sonnet$' '$file'"
done

# 2. No residual 'model: inherit' across all agents
if grep -lE '^model: inherit$' "${AGENTS_DIR}"/*.md 2>/dev/null; then
    FAIL=$((FAIL + 1))
    FAIL_DETAILS="${FAIL_DETAILS}\n  [FAIL] residual 'model: inherit' found in agents/"
else
    PASS=$((PASS + 1))
    printf "  [PASS] zero residual 'model: inherit' in agents/\n"
fi

# 3. No other model values that could shadow sonnet (haiku, opus, claude-* pinning)
SHADOW_VALUES=$(grep -hE '^model:' "${AGENTS_DIR}"/*.md 2>/dev/null | sort -u | grep -vE '^model: sonnet$' || true)
if [ -n "$SHADOW_VALUES" ]; then
    FAIL=$((FAIL + 1))
    FAIL_DETAILS="${FAIL_DETAILS}\n  [FAIL] unexpected model values in agents/: ${SHADOW_VALUES}"
else
    PASS=$((PASS + 1))
    printf "  [PASS] only 'model: sonnet' appears across all agents\n"
fi

# 4. Frontmatter format integrity: model field is in YAML block (between --- lines)
for agent in "${EXPECTED_AGENTS[@]}"; do
    file="${AGENTS_DIR}/${agent}.md"
    # Extract content between first two '---' lines (frontmatter)
    frontmatter=$(awk '/^---$/{c++; next} c==1{print} c==2{exit}' "$file")
    if echo "$frontmatter" | grep -qE '^model: sonnet$'; then
        PASS=$((PASS + 1))
        printf "  [PASS] %s — 'model: sonnet' is inside YAML frontmatter\n" "$agent"
    else
        FAIL=$((FAIL + 1))
        FAIL_DETAILS="${FAIL_DETAILS}\n  [FAIL] ${agent} — 'model: sonnet' is OUTSIDE the YAML frontmatter block"
    fi
done

# 5. Count check: exactly 5 agents
ACTUAL_COUNT=$(find "${AGENTS_DIR}" -maxdepth 1 -name '*.md' -type f | wc -l | tr -d '[:space:]')
assert "exactly 5 agents in agents/ (got $ACTUAL_COUNT)" "[ '$ACTUAL_COUNT' -eq 5 ]"

echo
echo "================================"
echo "agent_model_sonnet.test.sh — Risultati"
echo "  PASS: $PASS"
echo "  FAIL: $FAIL"
[ -n "$FAIL_DETAILS" ] && echo -e "Failures:$FAIL_DETAILS"
echo "================================"

[ "$FAIL" -eq 0 ] || exit 1
exit 0
