#!/usr/bin/env bash
# Test: PR lifecycle events (pr_opened idempotente, pr_commit_after_open,
# pr_review_cycle, pr_merged, pr_metrics)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Isolated HOME per non inquinare stato reale
TEST_HOME=$(mktemp -d)
TEST_REPO=$(mktemp -d)
TEST_LOG=$(mktemp)
GH_SHIM_DIR=$(mktemp -d)

trap 'rm -rf "$TEST_HOME" "$TEST_REPO" "$TEST_LOG" "$GH_SHIM_DIR"' EXIT

export HOME="$TEST_HOME"
export DEVFORGE_LOG_FILE="$TEST_LOG"
export DEVFORGE_SESSION_DIR=$(mktemp -d)
export DEVFORGE_FORCE_BASH_FALLBACK=1
mkdir -p "${HOME}/.claude"

# Setup repo di test con 1 commit iniziale
cd "$TEST_REPO"
git init -q
git config user.email "test@test.local"
git config user.name "Test"
echo "hello" > file.txt
git add file.txt
git commit -q -m "first commit"
INITIAL_SHA=$(git rev-parse HEAD)
echo "$INITIAL_SHA" > "${HOME}/.claude/.devforge-last-commit-hash"

# Shim gh: scrive response JSON a stdout basandosi su $GH_FIXTURE
cat > "${GH_SHIM_DIR}/gh" << 'GHEOF'
#!/usr/bin/env bash
# Restituisce il contenuto di $GH_FIXTURE (se set) o JSON vuoto.
if [ -n "${GH_FIXTURE:-}" ] && [ -f "$GH_FIXTURE" ]; then
    cat "$GH_FIXTURE"
else
    echo ""
fi
exit 0
GHEOF
chmod +x "${GH_SHIM_DIR}/gh"
export PATH="${GH_SHIM_DIR}:${PATH}"

# Helper: invoca il hook con un TOOL_COMMAND simulato
invoke_hook() {
    local cmd="$1"
    local hook_input
    hook_input=$(python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","command":sys.argv[1],"tool_input":{"command":sys.argv[1]}}))' "$cmd")
    echo "$hook_input" | bash "${PLUGIN_ROOT}/hooks/post-commit-review" >/dev/null 2>&1 || true
}

# Helper: setta fixture gh per la prossima invocazione
set_gh_fixture() {
    GH_FIXTURE=$(mktemp)
    echo "$1" > "$GH_FIXTURE"
    export GH_FIXTURE
}

# Helper: conta eventi per nome nel log
count_events() {
    local event_name="$1"
    grep -c "\"event\":\"${event_name}\"" "$DEVFORGE_LOG_FILE" 2>/dev/null || echo 0
}

# ─── Scenario 1: primo push con PR → pr_opened + snapshot ───
set_gh_fixture '{"number":213,"baseRefName":"main","changedFiles":3,"commits":{"totalCount":2},"reviewDecision":"REVIEW_REQUIRED","state":"OPEN"}'

invoke_hook "git push origin HEAD"

if [ "$(count_events pr_opened)" != "1" ]; then
    echo "FAIL scenario 1: pr_opened count = $(count_events pr_opened), atteso 1"
    cat "$DEVFORGE_LOG_FILE"
    exit 1
fi
if [ ! -f "${HOME}/.claude/.devforge-pr-state-213.json" ]; then
    echo "FAIL scenario 1: snapshot file non creato"
    exit 1
fi
echo "PASS scenario 1: pr_opened 1x + snapshot creato"

# ─── Scenario 2: secondo push → pr_commit_after_open, NO altro pr_opened ───
cd "$TEST_REPO"
echo "change" >> file.txt
git add file.txt
git commit -q -m "second commit"
NEW_SHA=$(git rev-parse HEAD)

# commits.totalCount passa da 2 → 3
set_gh_fixture '{"number":213,"baseRefName":"main","changedFiles":3,"commits":{"totalCount":3},"reviewDecision":"REVIEW_REQUIRED","state":"OPEN"}'

invoke_hook "git push origin HEAD"

if [ "$(count_events pr_opened)" != "1" ]; then
    echo "FAIL scenario 2: pr_opened count = $(count_events pr_opened), atteso 1 (dedup)"
    exit 1
fi
if [ "$(count_events pr_commit_after_open)" != "1" ]; then
    echo "FAIL scenario 2: pr_commit_after_open count = $(count_events pr_commit_after_open), atteso 1"
    cat "$DEVFORGE_LOG_FILE"
    exit 1
fi
if ! grep -q '"commits_since_open":1' "$DEVFORGE_LOG_FILE"; then
    echo "FAIL scenario 2: commits_since_open != 1"
    grep pr_commit_after_open "$DEVFORGE_LOG_FILE"
    exit 1
fi
echo "PASS scenario 2: pr_commit_after_open con commits_since_open=1"
echo "PASS scenario 7: dedup pr_opened via snapshot (count=1)"

# ─── Scenario 3: reviewDecision → CHANGES_REQUESTED → pr_review_cycle cycle_num=1 ───
cd "$TEST_REPO"
echo "fix" >> file.txt
git add file.txt
git commit -q -m "fix review"

set_gh_fixture '{"number":213,"baseRefName":"main","changedFiles":3,"commits":{"totalCount":4},"reviewDecision":"CHANGES_REQUESTED","state":"OPEN"}'

invoke_hook "git push origin HEAD"

if [ "$(count_events pr_review_cycle)" != "1" ]; then
    echo "FAIL scenario 3: pr_review_cycle count = $(count_events pr_review_cycle), atteso 1"
    cat "$DEVFORGE_LOG_FILE"
    exit 1
fi
if ! grep -q '"cycle_num":1' "$DEVFORGE_LOG_FILE"; then
    echo "FAIL scenario 3: cycle_num != 1"
    grep pr_review_cycle "$DEVFORGE_LOG_FILE"
    exit 1
fi
echo "PASS scenario 3: pr_review_cycle cycle_num=1"

# ─── Scenario 6: push successivo con stessa CHANGES_REQUESTED → no doppio emit ───
cd "$TEST_REPO"
echo "fix2" >> file.txt
git add file.txt
git commit -q -m "another fix"

set_gh_fixture '{"number":213,"baseRefName":"main","changedFiles":3,"commits":{"totalCount":5},"reviewDecision":"CHANGES_REQUESTED","state":"OPEN"}'

invoke_hook "git push origin HEAD"

if [ "$(count_events pr_review_cycle)" != "1" ]; then
    echo "FAIL scenario 6: pr_review_cycle count = $(count_events pr_review_cycle), atteso 1 (no doppio emit)"
    exit 1
fi
echo "PASS scenario 6: pr_review_cycle dedup (no doppio emit)"

echo "SETUP OK"
exit 0
