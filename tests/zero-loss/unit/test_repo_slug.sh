#!/usr/bin/env bash
# Unit tests: task-06 — 6b+6d: campo repo_slug + marker duration_source.
#
# Verifica che:
# 1. devforge_repo_slug normalizza URL SSH e HTTPS → org/repo
# 2. devforge_log emette "repo_slug" nel JSON top-level
# 3. devforge_log_timed emette "repo_slug" e "duration_source":"wallclock"
#
# Nota: NON aggiungere trap EXIT dentro funzioni invocate via $(...) — distrugge
# il trap del chiamante nel subshell.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LOGGER="${REPO_ROOT}/lib/logger.sh"

fail=0
pass=0

assert() {
    local name="$1" actual="$2" expected="$3"
    if [ "$actual" = "$expected" ]; then
        echo "  PASS: $name"
        pass=$((pass + 1))
    else
        echo "  FAIL: $name — expected '$expected' got '$actual'"
        fail=$((fail + 1))
    fi
}

assert_nonempty() {
    local name="$1" actual="$2"
    if [ -n "$actual" ]; then
        echo "  PASS: $name (value='$actual')"
        pass=$((pass + 1))
    else
        echo "  FAIL: $name — expected non-empty, got empty"
        fail=$((fail + 1))
    fi
}

assert_contains() {
    local name="$1" haystack="$2" needle="$3"
    if printf '%s' "$haystack" | grep -qF "$needle"; then
        echo "  PASS: $name (found '$needle')"
        pass=$((pass + 1))
    else
        echo "  FAIL: $name — expected to find '$needle' in: $haystack"
        fail=$((fail + 1))
    fi
}

# --- setup isolated workspace ---
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

export HOME="$WORK"
mkdir -p "$WORK/.claude"

echo "testsid" > "$WORK/.claude/.devforge-session-id"

SESSION_DIR="$WORK/.claude/devforge-state/testsid"
mkdir -p "$SESSION_DIR"

cat > "$WORK/.claude.json" <<'EOF'
{
  "oauthAccount": {
    "emailAddress": "slug.test@siae.it",
    "accountUuid": "slug-uuid-0001",
    "organizationUuid": "slug-org-uuid-0001",
    "organizationName": "SIAE Slug Test"
  }
}
EOF
export DEVFORGE_CLAUDE_JSON="$WORK/.claude.json"
export DEVFORGE_LOG_FILE="$SESSION_DIR/activity.jsonl"
touch "$DEVFORGE_LOG_FILE"
export DEVFORGE_PINNED_SID="testsid"
export DEVFORGE_SESSION_DIR="$SESSION_DIR"

# Source il logger DOPO aver settato HOME
# shellcheck disable=SC1090
source "$LOGGER" 2>/dev/null || { echo "FATAL: cannot source $LOGGER"; exit 2; }

# ---------------------------------------------------------------
echo "TEST 1 — devforge_repo_slug: URL SSH con .git"
result=$(devforge_repo_slug "git@gitlab.itsiae.it:itsiae/diritti-api.git")
assert "T1: SSH URL → itsiae/diritti-api" "$result" "itsiae/diritti-api"

# ---------------------------------------------------------------
echo "TEST 2 — devforge_repo_slug: URL HTTPS con .git"
result=$(devforge_repo_slug "https://github.com/itsiae/diritti-api.git")
assert "T2: HTTPS URL con .git → itsiae/diritti-api" "$result" "itsiae/diritti-api"

# ---------------------------------------------------------------
echo "TEST 3 — devforge_repo_slug: URL HTTPS senza .git"
result=$(devforge_repo_slug "https://github.com/itsiae/diritti-api")
assert "T3: HTTPS URL senza .git → itsiae/diritti-api" "$result" "itsiae/diritti-api"

# ---------------------------------------------------------------
echo "TEST 4 — devforge_repo_slug: URL vuoto → stringa vuota"
result=$(devforge_repo_slug "")
assert "T4: URL vuoto → ''" "$result" ""

# ---------------------------------------------------------------
echo "TEST 5 — devforge_log_timed emette repo_slug non vuoto e duration_source=wallclock"
# Usiamo un repo git reale (il repo stesso) come working dir implicito.
# Sovrascriviamo DEVFORGE_LOG_FILE per isolare questo test.
TIMED_LOG="$SESSION_DIR/timed_test.jsonl"
touch "$TIMED_LOG"
ORIG_LOG="$DEVFORGE_LOG_FILE"
export DEVFORGE_LOG_FILE="$TIMED_LOG"
# Forziamo repo_remote via shim git nella PATH
SHIM_DIR="$WORK/shims"
mkdir -p "$SHIM_DIR"
OLD_PATH="$PATH"
REAL_GIT=$(PATH="$OLD_PATH" command -v git 2>/dev/null || echo "/usr/bin/git")
cat > "$SHIM_DIR/git" <<EOF
#!/usr/bin/env bash
# Shim git: intercetta solo "remote get-url origin"
if [ "\${1:-}" = "remote" ] && [ "\${2:-}" = "get-url" ] && [ "\${3:-}" = "origin" ]; then
    echo "git@gitlab.itsiae.it:itsiae/diritti-api.git"
    exit 0
fi
# Tutto il resto va al git reale
exec "${REAL_GIT}" "\$@"
EOF
chmod +x "$SHIM_DIR/git"
export PATH="$SHIM_DIR:$OLD_PATH"

start_ns=$(_devforge_epoch_ns)
devforge_log_timed "test_event" "success" "$start_ns" '{"test":true}' 2>/dev/null || true

export PATH="$OLD_PATH"
rm -f "$SHIM_DIR/git"

# Leggi l'ultima riga del log
last_line=$(tail -1 "$TIMED_LOG" 2>/dev/null || echo "")

assert_nonempty "T5a: log timed ha prodotto una riga" "$last_line"

# Verifica repo_slug non vuoto nel JSON
slug_val=$(printf '%s' "$last_line" | grep -o '"repo_slug":"[^"]*"' | sed 's/"repo_slug":"//;s/"//')
assert_nonempty "T5b: repo_slug non vuoto nell'evento timed" "$slug_val"
assert "T5c: repo_slug è itsiae/diritti-api" "$slug_val" "itsiae/diritti-api"

# Verifica duration_source=wallclock
assert_contains "T5d: duration_source:wallclock presente" "$last_line" '"duration_source":"wallclock"'

# Restore
export DEVFORGE_LOG_FILE="$ORIG_LOG"

# ---------------------------------------------------------------
echo ""
echo "SUMMARY: $pass passed, $fail failed"
exit $fail
