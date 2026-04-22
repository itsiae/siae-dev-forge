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

echo "SETUP OK"
exit 0
