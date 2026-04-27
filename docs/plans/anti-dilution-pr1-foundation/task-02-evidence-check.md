# Task 02 — Implementare lib/evidence-check.sh (TDD)

**Stato:** [PENDING]
**Execution:** in-session (TDD stretto)
**Dipendenze:** nessuna
**Durata stimata:** 15-20 min

## Goal

Implementare `lib/evidence-check.sh` con la funzione `devforge_skill_validated(skill_name, task_id)` che verifica il predicato `validates_via` di una skill. Usata dai gate in PR #2 per sostituire il check `grep -qF SKILL SESSION_SKILLS_FILE`.

In PR #1 la funzione è **implementata e testata** ma NON ancora chiamata dai gate (cutover in PR #2 dual-write phase).

## Predicati da implementare (5 MVP per PR #1)

| Skill | Predicate ID | Check |
|---|---|---|
| siae-tdd | `tdd_red_green_observed` | `~/.claude/.devforge-tdd-state` contiene `GREEN\|` o `REFACTOR\|` (transitioned da RED) |
| siae-brainstorming | `design_doc_produced` | Almeno 1 file `docs/plans/*-design.md` con mtime > session_start_ns |
| siae-git-workflow | `conventional_commit_made` | `git log -1 --format=%s` match regex `^(feat\|fix\|chore\|docs\|refactor\|test\|style\|perf\|build\|ci)(\(.+\))?!?:` |
| siae-verification | `verification_run_passed` | Almeno 1 evento `verification_run` con exit=0 in `$DEVFORGE_LOG_FILE` per la sessione corrente |
| siae-blind-review | `blind_review_completed` | Almeno 1 evento `blind_review_verdict` in `$DEVFORGE_LOG_FILE` per la sessione corrente |

## API

```bash
# Source this file from hooks or tests
source lib/evidence-check.sh

# Check if skill is validated (not just invoked)
# $1 = skill name (senza prefisso "siae-devforge:")
# $2 = task_id (opzionale in PR #1; in PR #2 diventerà required)
# Returns: 0 if validated, 1 if not
devforge_skill_validated "siae-tdd" "$TASK_ID"
```

## Step TDD

### Step 1 — RED: scrivi i test PRIMA

File: `tests/lib/test_evidence_check.sh`

Test da includere (5 predicati × positive+negative = 10 test minimi):

```bash
#!/usr/bin/env bash
# tests/lib/test_evidence_check.sh
set -eu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$SCRIPT_DIR/lib/evidence-check.sh"

PASS=0
FAIL=0
assert() {
    local name="$1"; local expected="$2"; local actual="$3"
    if [ "$expected" = "$actual" ]; then
        echo "  PASS  $name"
        PASS=$((PASS+1))
    else
        echo "  FAIL  $name (expected=$expected actual=$actual)"
        FAIL=$((FAIL+1))
    fi
}

# Setup isolated state
export HOME="$(mktemp -d)"
mkdir -p "$HOME/.claude"
trap 'rm -rf "$HOME"' EXIT

# --- siae-tdd positive ---
echo "GREEN|foo.py|test_bar|$(date +%s)" > "$HOME/.claude/.devforge-tdd-state"
devforge_skill_validated "siae-tdd" "dummy-task" && R=0 || R=1
assert "tdd_red_green_observed: GREEN state returns 0" "0" "$R"

# --- siae-tdd negative (INIT state) ---
echo "INIT|pending|awaiting|$(date +%s)" > "$HOME/.claude/.devforge-tdd-state"
devforge_skill_validated "siae-tdd" "dummy-task" && R=0 || R=1
assert "tdd_red_green_observed: INIT state returns 1" "1" "$R"

# --- siae-tdd negative (no state file) ---
rm -f "$HOME/.claude/.devforge-tdd-state"
devforge_skill_validated "siae-tdd" "dummy-task" && R=0 || R=1
assert "tdd_red_green_observed: missing state returns 1" "1" "$R"

# --- siae-brainstorming positive ---
export DEVFORGE_SESSION_START_S=$(($(date +%s) - 3600))  # 1h ago
mkdir -p docs/plans
touch docs/plans/2026-04-25-test-design.md  # mtime = now
devforge_skill_validated "siae-brainstorming" "dummy-task" && R=0 || R=1
assert "design_doc_produced: fresh design doc returns 0" "0" "$R"

# --- siae-brainstorming negative (old file) ---
# Set mtime to before session_start_s
touch -t 202001010000 docs/plans/2026-04-25-test-design.md
devforge_skill_validated "siae-brainstorming" "dummy-task" && R=0 || R=1
assert "design_doc_produced: stale file returns 1" "1" "$R"
rm -rf docs/plans

# --- siae-git-workflow positive ---
TMP_REPO="$(mktemp -d)"
git -C "$TMP_REPO" init -q
git -C "$TMP_REPO" commit --allow-empty -m "feat(x): y" -q
(cd "$TMP_REPO" && devforge_skill_validated "siae-git-workflow" "dummy-task") && R=0 || R=1
assert "conventional_commit_made: feat(x): y returns 0" "0" "$R"

# --- siae-git-workflow negative ---
git -C "$TMP_REPO" commit --allow-empty -m "updated stuff" -q
(cd "$TMP_REPO" && devforge_skill_validated "siae-git-workflow" "dummy-task") && R=0 || R=1
assert "conventional_commit_made: non-conventional returns 1" "1" "$R"
rm -rf "$TMP_REPO"

# --- siae-verification positive ---
export DEVFORGE_LOG_FILE="$HOME/.claude/devforge-activity.jsonl"
export DEVFORGE_SESSION_ID="test-session-123"
cat > "$DEVFORGE_LOG_FILE" <<EOF
{"sid":"test-session-123","event":"verification_run","meta":{"exit":0}}
EOF
devforge_skill_validated "siae-verification" "dummy-task" && R=0 || R=1
assert "verification_run_passed: exit=0 event returns 0" "0" "$R"

# --- siae-verification negative (no event) ---
echo '{"sid":"test-session-123","event":"other"}' > "$DEVFORGE_LOG_FILE"
devforge_skill_validated "siae-verification" "dummy-task" && R=0 || R=1
assert "verification_run_passed: no event returns 1" "1" "$R"

# --- siae-blind-review positive ---
cat > "$DEVFORGE_LOG_FILE" <<EOF
{"sid":"test-session-123","event":"blind_review_verdict","meta":{"verdict":"APPROVED"}}
EOF
devforge_skill_validated "siae-blind-review" "dummy-task" && R=0 || R=1
assert "blind_review_completed: verdict event returns 0" "0" "$R"

echo ""
echo "Total: $((PASS+FAIL))  PASS: $PASS  FAIL: $FAIL"
exit $FAIL
```

Run: `bash tests/lib/test_evidence_check.sh`
Output atteso (RED): tutti FAIL perché `lib/evidence-check.sh` non esiste ancora → script fallisce al source.

### Step 2 — Verifica RED

```bash
bash tests/lib/test_evidence_check.sh 2>&1 | head -5
```
Output atteso: `evidence-check.sh: No such file or directory` o simile.

### Step 3 — GREEN: implementa lib/evidence-check.sh

File: `lib/evidence-check.sh`

```bash
#!/usr/bin/env bash
# evidence-check.sh — Verify skill meaningful-use via validates_via predicate
# ─────────────────────────────────────────────────────────────────
# Part of: PR #1 anti-dilution (ADR-002 Evidence Contract)
# Used by: gate hooks in PR #2 (dual-write cutover)
# ─────────────────────────────────────────────────────────────────

# devforge_skill_validated SKILL_NAME [TASK_ID]
# Returns 0 if skill's validates_via predicate is satisfied, 1 otherwise.
devforge_skill_validated() {
    local skill="${1:?skill name required}"
    local task_id="${2:-}"  # unused in PR #1, reserved for PR #2

    case "$skill" in
        siae-tdd)
            _devforge_check_tdd_red_green
            ;;
        siae-brainstorming)
            _devforge_check_design_doc_produced
            ;;
        siae-git-workflow)
            _devforge_check_conventional_commit
            ;;
        siae-verification)
            _devforge_check_verification_run_passed
            ;;
        siae-blind-review)
            _devforge_check_blind_review_completed
            ;;
        *)
            # Unknown skill: not validatable in PR #1. Default: not validated.
            return 1
            ;;
    esac
}

_devforge_check_tdd_red_green() {
    local state_file="${HOME}/.claude/.devforge-tdd-state"
    [ -f "$state_file" ] || return 1
    local phase
    phase="$(cut -d'|' -f1 < "$state_file")"
    case "$phase" in
        GREEN|REFACTOR) return 0 ;;
        *) return 1 ;;
    esac
}

_devforge_check_design_doc_produced() {
    local session_start="${DEVFORGE_SESSION_START_S:-0}"
    [ -d docs/plans ] || return 1
    local latest
    latest=$(ls -1t docs/plans/*-design.md 2>/dev/null | head -1)
    [ -n "$latest" ] && [ -f "$latest" ] || return 1
    local mtime
    mtime=$(stat -f %m "$latest" 2>/dev/null || stat -c %Y "$latest" 2>/dev/null || echo 0)
    [ "$mtime" -ge "$session_start" ]
}

_devforge_check_conventional_commit() {
    # Must be inside a git repo
    git rev-parse --git-dir >/dev/null 2>&1 || return 1
    local msg
    msg=$(git log -1 --format=%s 2>/dev/null) || return 1
    [ -n "$msg" ] || return 1
    # Conventional Commits regex (permissive, accepts ! for breaking changes)
    echo "$msg" | grep -qE '^(feat|fix|chore|docs|refactor|test|style|perf|build|ci|revert)(\([^)]+\))?!?:'
}

_devforge_check_verification_run_passed() {
    local log_file="${DEVFORGE_LOG_FILE:-}"
    [ -n "$log_file" ] && [ -f "$log_file" ] || return 1
    local sid="${DEVFORGE_SESSION_ID:-}"
    if [ -n "$sid" ]; then
        grep -E "\"sid\":\"$sid\"" "$log_file" 2>/dev/null | \
            grep -E '"event":"verification_run"' | \
            grep -qE '"exit":0' || return 1
    else
        grep -E '"event":"verification_run"' "$log_file" 2>/dev/null | \
            grep -qE '"exit":0' || return 1
    fi
    return 0
}

_devforge_check_blind_review_completed() {
    local log_file="${DEVFORGE_LOG_FILE:-}"
    [ -n "$log_file" ] && [ -f "$log_file" ] || return 1
    local sid="${DEVFORGE_SESSION_ID:-}"
    if [ -n "$sid" ]; then
        grep -E "\"sid\":\"$sid\"" "$log_file" 2>/dev/null | \
            grep -qE '"event":"blind_review_verdict"' || return 1
    else
        grep -qE '"event":"blind_review_verdict"' "$log_file" 2>/dev/null || return 1
    fi
    return 0
}
```

### Step 4 — Verifica GREEN

```bash
chmod +x lib/evidence-check.sh tests/lib/test_evidence_check.sh
bash tests/lib/test_evidence_check.sh
```
Output atteso: `Total: 10  PASS: 10  FAIL: 0` (exit 0).

### Step 5 — Commit

```bash
git add lib/evidence-check.sh tests/lib/test_evidence_check.sh
git commit -m "feat(lib): add evidence-check.sh with 5 skill validators (TDD)

Part of PR #1 anti-dilution (ADR-002 Evidence Contract).
Implements devforge_skill_validated(skill, task_id) with 5 predicates:
- tdd_red_green_observed
- design_doc_produced
- conventional_commit_made
- verification_run_passed
- blind_review_completed

Function implemented and unit-tested. Integration in gate hooks deferred to PR #2."
```

## Acceptance

- [ ] `tests/lib/test_evidence_check.sh` scritto PRIMA di `lib/evidence-check.sh`
- [ ] Test esegue e fallisce inizialmente (RED)
- [ ] `lib/evidence-check.sh` implementato
- [ ] Test passa (GREEN): `Total: 10 PASS: 10 FAIL: 0`
- [ ] Commit conventional `feat(lib):`
- [ ] Nessuna modifica ai gate hook (cutover in PR #2)
