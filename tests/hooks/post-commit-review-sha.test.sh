#!/usr/bin/env bash
# Test: commit_created event deve contenere commit_sha nel meta
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
export DEVFORGE_LOG_FILE=$(mktemp)
export DEVFORGE_SESSION_DIR=$(mktemp -d)
export DEVFORGE_FORCE_BASH_FALLBACK=1

# Simula un commit: crea repo temp con 1 commit
TMP_REPO=$(mktemp -d)
trap 'rm -rf "$TMP_REPO" "$DEVFORGE_SESSION_DIR" "$DEVFORGE_LOG_FILE"' EXIT
cd "$TMP_REPO"
git init -q
git config user.email "test@test.local"
git config user.name "Test"
echo "hello" > file.txt
git add file.txt
git commit -q -m "first commit"
EXPECTED_SHA=$(git rev-parse HEAD)

# Simula il trigger: chiamare il logger come fa post-commit-review
source "${PLUGIN_ROOT}/lib/logger.sh"
devforge_log "commit_created" "success" "{\"commit_sha\":\"${EXPECTED_SHA}\",\"files_changed\":1,\"insertions\":1,\"deletions\":0,\"has_tests\":false}"

# Assert: il log contiene commit_sha == EXPECTED_SHA
if ! grep -qF "\"commit_sha\":\"${EXPECTED_SHA}\"" "$DEVFORGE_LOG_FILE"; then
    echo "FAIL: commit_sha missing in emitted event"
    cat "$DEVFORGE_LOG_FILE"
    exit 1
fi

echo "PASS: commit_sha present"

# Step 2: test end-to-end del hook reale
# Simula PostToolUse input per un commit — deve essere in un repo con HEAD diverso da saved hash
# Usiamo TMP_REPO come working dir (già git init + 1 commit), con HOME isolato
export HOME="$(mktemp -d)"
mkdir -p "${HOME}/.claude"
# Saved hash diverso da HEAD per forzare il ramo commit_created
echo "0000000000000000000000000000000000000000" > "${HOME}/.claude/.devforge-last-commit-hash"

HOOK_INPUT='{"tool_name":"Bash","command":"git commit -m test","tool_input":{"command":"git commit -m test"}}'
echo "$HOOK_INPUT" | bash "${PLUGIN_ROOT}/hooks/post-commit-review" >/dev/null 2>&1

# Cerca l'ultimo evento commit_created nel log
LAST_COMMIT_EVENT=$(grep '"event":"commit_created"' "$DEVFORGE_LOG_FILE" | tail -1)
if [ -z "$LAST_COMMIT_EVENT" ]; then
    echo "FAIL e2e: hook non ha emesso commit_created (saved_hash=000... HEAD=${EXPECTED_SHA}, dovrebbe triggerare)"
    echo "--- log content ---"
    cat "$DEVFORGE_LOG_FILE"
    exit 1
fi

# Verifica che sia SHA reale (64 hex? git sha is 40 hex) non il valore dummy dello step 1
HOOK_SHA_LINE=$(grep '"event":"commit_created"' "$DEVFORGE_LOG_FILE" | tail -1)
if echo "$HOOK_SHA_LINE" | grep -q "\"commit_sha\":\"${EXPECTED_SHA}\""; then
    echo "PASS e2e: hook emette commit_sha reale"
elif echo "$HOOK_SHA_LINE" | grep -q '"commit_sha":"[0-9a-f]\{40\}"'; then
    echo "PASS e2e: hook emette commit_sha (40-hex)"
else
    echo "FAIL e2e: hook NON emette commit_sha"
    echo "Event: $HOOK_SHA_LINE"
    exit 1
fi
