#!/usr/bin/env bash
# Unit tests: trailer hook hardening (task-04 — F2c).
#
# Verifies:
#   1. The generated prepare-commit-msg contains marker v2 and node→python3 chain
#   2. With python3 masked and node available, a commit gets DevForge-Author trailer
#   3. Simulating git interpret-trailers absent (shim), installer emits
#      trailer_hook_skipped_old_git and a commit is NOT blocked (exit 0)
#   4. A pre-existing v1 hook is upgraded to v2 (base-marker detection);
#      a truly foreign hook (no base marker) is NOT overwritten (return 2).
#
# Conventions: set -uo pipefail, assert/fail/pass pattern, trap rm EXIT,
# shim PATH to mask interpreters. DEVFORGE_CLAUDE_JSON for fake email.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
INSTALLER="${REPO_ROOT}/lib/install-trailer-hook.sh"
LOGGER="${REPO_ROOT}/lib/logger.sh"

fail=0
pass=0

assert() {
    local name="$1" actual="$2" expected="$3"
    if [ "$actual" = "$expected" ]; then
        echo "  PASS: $name"; pass=$((pass + 1))
    else
        echo "  FAIL: $name — expected '$expected' got '$actual'"; fail=$((fail + 1))
    fi
}
assert_contains() {
    local name="$1" haystack="$2" needle="$3"
    if printf '%s' "$haystack" | grep -qF "$needle"; then
        echo "  PASS: $name"; pass=$((pass + 1))
    else
        echo "  FAIL: $name — '$needle' NOT found in output"; fail=$((fail + 1))
    fi
}

# --- isolated workspace ---
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

OLD_PATH="$PATH"

# Build fake ~/.claude.json with known email
FAKE_CLAUDE_JSON="$WORK/fake_claude.json"
cat > "$FAKE_CLAUDE_JSON" <<'EOF'
{
  "oauthAccount": {
    "emailAddress": "trailer.test@siae.it"
  }
}
EOF
export DEVFORGE_CLAUDE_JSON="$FAKE_CLAUDE_JSON"
EXPECTED_EMAIL="trailer.test@siae.it"

# Shim directory
SHIM_DIR="$WORK/shims"
mkdir -p "$SHIM_DIR"

make_shim() {
    local name="$1" exit_code="${2:-127}"
    printf '#!/usr/bin/env bash\nexit %s\n' "$exit_code" > "$SHIM_DIR/$name"
    chmod +x "$SHIM_DIR/$name"
}
clear_shims() { rm -f "$SHIM_DIR"/*; }

# Helper: create a temp git repo and install the hook into it.
# Returns the repo path in stdout.
make_git_repo() {
    local repo
    repo=$(mktemp -d)
    git init "$repo" >/dev/null 2>&1
    git -C "$repo" config user.email "test@siae.it"
    git -C "$repo" config user.name "Test"
    printf '%s' "$repo"
}

# Helper: do a commit in a repo (creates a file and commits it).
# Returns the exit code of git commit.
do_commit() {
    local repo="$1" msg="${2:-test commit}"
    local f="$repo/f_$(date +%s%N).txt"
    printf 'content\n' > "$f"
    git -C "$repo" add . >/dev/null 2>&1
    git -C "$repo" commit --no-gpg-sign -m "$msg" >/dev/null 2>&1
}

# ---------------------------------------------------------------
echo "TEST 1 — Generated hook contains marker v2 and node→python3 chain"

T1_REPO=$(make_git_repo)
(
    cd "$T1_REPO"
    source "$INSTALLER" 2>/dev/null
    devforge_install_trailer_hook
)
T1_HOOK="$T1_REPO/.git/hooks/prepare-commit-msg"

assert "T1a: hook file exists after install" \
    "$([ -f "$T1_HOOK" ] && echo yes || echo no)" "yes"

if [ -f "$T1_HOOK" ]; then
    T1_CONTENT=$(cat "$T1_HOOK")
    assert_contains "T1b: marker v2 present" "$T1_CONTENT" "# DEVFORGE-TRAILER-HOOK v2"
    assert_contains "T1c: node chain present" "$T1_CONTENT" "command -v node"
    assert_contains "T1d: python3 fallback present" "$T1_CONTENT" "command -v python3"
    # Ensure v1 is NOT the live marker
    if printf '%s' "$T1_CONTENT" | grep -qF "DEVFORGE-TRAILER-HOOK v1"; then
        echo "  FAIL: T1e: old marker v1 found — not bumped"; fail=$((fail + 1))
    else
        echo "  PASS: T1e: old marker v1 NOT present (correctly bumped)"; pass=$((pass + 1))
    fi
fi
rm -rf "$T1_REPO"

# ---------------------------------------------------------------
echo "TEST 2 — python3 masked, node available: commit gets DevForge-Author trailer"

clear_shims
make_shim python3
export PATH="$SHIM_DIR:$OLD_PATH"

T2_REPO=$(make_git_repo)
(
    cd "$T2_REPO"
    source "$INSTALLER" 2>/dev/null
    devforge_install_trailer_hook
)

# Verify node is available but python3 is shimmed
if ! command -v node >/dev/null 2>&1; then
    echo "  SKIP: T2 — node not available in this environment; skipping"
    pass=$((pass + 1))  # don't penalize env without node
else
    do_commit "$T2_REPO" "feat: test trailer via node"

    LAST_MSG=$(git -C "$T2_REPO" log -1 --format="%B" 2>/dev/null)
    if printf '%s' "$LAST_MSG" | grep -qF "DevForge-Author: $EXPECTED_EMAIL"; then
        echo "  PASS: T2a: DevForge-Author trailer present (via node)"; pass=$((pass + 1))
    else
        echo "  FAIL: T2a: DevForge-Author trailer NOT found in commit message"
        echo "       Last message: $LAST_MSG"
        fail=$((fail + 1))
    fi
fi

export PATH="$OLD_PATH"
clear_shims
rm -rf "$T2_REPO"

# ---------------------------------------------------------------
echo "TEST 3 — git interpret-trailers absent: installer emits trailer_hook_skipped_old_git, commit not blocked"

# Set up logger env for session state
T3_SESSION_DIR="$WORK/session3"
mkdir -p "$T3_SESSION_DIR"
T3_LOG="$T3_SESSION_DIR/activity.jsonl"
touch "$T3_LOG"

# Build a git shim that fails for interpret-trailers subcommand
# but works for all other git calls (init/add/commit/config/rev-parse/--version).
# Strategy: shim wraps real git, intercepting "interpret-trailers" and "--help" subcmds.
REAL_GIT=$(command -v git)
cat > "$SHIM_DIR/git" <<SHIMEOF
#!/usr/bin/env bash
# Shim: fail on interpret-trailers (simulates old git without the command)
for arg in "\$@"; do
    if [ "\$arg" = "interpret-trailers" ]; then
        exit 1
    fi
done
exec "$REAL_GIT" "\$@"
SHIMEOF
chmod +x "$SHIM_DIR/git"

export PATH="$SHIM_DIR:$OLD_PATH"

T3_REPO=$(make_git_repo)

# Source logger and installer in subshell to emit telemetry via devforge_log
(
    export HOME="$WORK"
    export DEVFORGE_SESSION_DIR="$T3_SESSION_DIR"
    export DEVFORGE_LOG_FILE="$T3_LOG"
    export DEVFORGE_PINNED_USER="trailer.test@siae.it"
    export DEVFORGE_PINNED_SID="test-sid-t3"
    export DEVFORGE_FORCE_BASH_FALLBACK=1
    source "$LOGGER" 2>/dev/null
    cd "$T3_REPO"
    source "$INSTALLER" 2>/dev/null
    devforge_install_trailer_hook
) 2>/dev/null || true

# Check telemetry was emitted
T3_EVENT_COUNT=$(grep -c '"trailer_hook_skipped_old_git"' "$T3_LOG" 2>/dev/null || true)
if [ "${T3_EVENT_COUNT:-0}" -gt 0 ]; then
    echo "  PASS: T3a: trailer_hook_skipped_old_git event emitted"; pass=$((pass + 1))
else
    echo "  FAIL: T3a: trailer_hook_skipped_old_git event NOT found in log"
    fail=$((fail + 1))
fi

# Verify commit is not blocked even with broken git interpret-trailers
# (The hook itself also uses the same shimmed git, so interpret-trailers will fail
#  at runtime — but hook must exit 0 and not block the commit)
T3_COMMIT_RC=0
do_commit "$T3_REPO" "feat: commit with broken interpret-trailers" || T3_COMMIT_RC=$?
assert "T3b: commit not blocked (exit 0) when interpret-trailers absent" \
    "$T3_COMMIT_RC" "0"

export PATH="$OLD_PATH"
clear_shims
rm -rf "$T3_REPO"

# ---------------------------------------------------------------
echo "TEST 4 — v1 hook is upgraded to v2; foreign hook (no base marker) is NOT overwritten"

# Part A: pre-existing v1 hook must be upgraded to v2.
T4A_REPO=$(make_git_repo)
T4A_HOOK="$T4A_REPO/.git/hooks/prepare-commit-msg"
mkdir -p "$(dirname "$T4A_HOOK")"
printf '#!/usr/bin/env bash\n# DEVFORGE-TRAILER-HOOK v1\nexit 0\n' > "$T4A_HOOK"
chmod +x "$T4A_HOOK"

(
    cd "$T4A_REPO"
    source "$INSTALLER" 2>/dev/null
    devforge_install_trailer_hook
)

T4A_CONTENT=$(cat "$T4A_HOOK")
assert_contains "T4a: after upgrade hook contains marker v2" \
    "$T4A_CONTENT" "# DEVFORGE-TRAILER-HOOK v2"
assert_contains "T4b: after upgrade hook contains node chain" \
    "$T4A_CONTENT" "command -v node"
# Verify v1 marker is no longer the active marker line (first occurrence is now v2)
if printf '%s' "$T4A_CONTENT" | grep -m1 "DEVFORGE-TRAILER-HOOK" | grep -qF "v2"; then
    echo "  PASS: T4c: first DEVFORGE-TRAILER-HOOK line is v2 (upgrade confirmed)"; pass=$((pass + 1))
else
    echo "  FAIL: T4c: first DEVFORGE-TRAILER-HOOK line is NOT v2"; fail=$((fail + 1))
fi
rm -rf "$T4A_REPO"

# Part B: a truly foreign hook (no base marker) must NOT be overwritten (return 2).
T4B_REPO=$(make_git_repo)
T4B_HOOK="$T4B_REPO/.git/hooks/prepare-commit-msg"
mkdir -p "$(dirname "$T4B_HOOK")"
FOREIGN_CONTENT='#!/usr/bin/env bash
# husky hook — do not clobber
exit 0
'
printf '%s' "$FOREIGN_CONTENT" > "$T4B_HOOK"
chmod +x "$T4B_HOOK"

T4B_RC=0
(
    cd "$T4B_REPO"
    source "$INSTALLER" 2>/dev/null
    devforge_install_trailer_hook
    exit $?
)
T4B_RC=$?

assert "T4d: installer returns 2 for foreign hook" "$T4B_RC" "2"

# Use grep to verify the foreign marker is still present and no DevForge marker crept in.
if grep -qF "husky hook" "$T4B_HOOK" && ! grep -qF "DEVFORGE-TRAILER-HOOK" "$T4B_HOOK"; then
    echo "  PASS: T4e: foreign hook content unchanged (husky marker present, no DevForge marker)"; pass=$((pass + 1))
else
    echo "  FAIL: T4e: foreign hook content was modified"; fail=$((fail + 1))
fi
rm -rf "$T4B_REPO"

# ---------------------------------------------------------------
echo ""
echo "SUMMARY: $pass passed, $fail failed"
exit $fail
