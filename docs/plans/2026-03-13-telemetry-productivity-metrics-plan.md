# Telemetry Productivity Metrics — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.

**Goal:** Arricchire la telemetria DevForge con 6 nuovi event type per misurare produttività
**Architettura:** Nuovi call site a `devforge_log` negli hook esistenti. Nessuna modifica infrastrutturale (S3, Lambda, API GW invariati). Timestamp chaining per calcolare durate skill.
**Stack:** Bash (hook), JSONL (logger.sh)
**SP:** 5
**Design doc:** `docs/plans/2026-03-13-telemetry-productivity-metrics-design.md`

---

## Task 1: `skill_completed` — Timestamp chaining in post-skill + stop-gate [DONE]

**Problema tecnico:** Il hook `post-skill` scatta quando il Skill tool ritorna contenuto,
non quando la skill "finisce". Soluzione: **timestamp chaining** — ogni invocazione skill
chiude la precedente calcolando la durata dal timestamp salvato.

**File coinvolti:**
- Modifica: `hooks/post-skill` (righe 1-33)
- Modifica: `hooks/stop-gate` (righe 1-53)

**Step 1: Scrivi test — verifica che `post-skill` emette `skill_completed` per skill precedente**

Aggiungi in `tests/run-all.sh` dopo la sezione "Hook Validation" (riga 323):

```bash
# Check 5: post-skill emette skill_completed per skill precedente
# Setup: crea file timestamp simulando skill precedente
SKILL_TS_FILE="${HOME}/.claude/.devforge-skill-start"
echo '1710000000000000000|test-skill-prev|2. Design' > "$SKILL_TS_FILE"
TEST_LOG="/tmp/devforge-test-skill-completed.jsonl"
DEVFORGE_LOG_FILE_BAK="${DEVFORGE_LOG_FILE:-}"
export DEVFORGE_LOG_FILE="$TEST_LOG"
rm -f "$TEST_LOG"
skill_completed_output=$(echo '{"skill":"siae-devforge:siae-brainstorming"}' | bash "${PLUGIN_ROOT}/hooks/post-skill" 2>/dev/null; echo "exit:$?")
if echo "$skill_completed_output" | grep -q 'exit:0' && grep -q '"event":"skill_completed"' "$TEST_LOG" 2>/dev/null; then
  echo "  PASS  hooks/post-skill: emette skill_completed per skill precedente"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/post-skill: non emette skill_completed"
  hook_fail=$((hook_fail + 1))
fi
rm -f "$TEST_LOG" "$SKILL_TS_FILE"
[ -n "$DEVFORGE_LOG_FILE_BAK" ] && export DEVFORGE_LOG_FILE="$DEVFORGE_LOG_FILE_BAK" || unset DEVFORGE_LOG_FILE
```

**Step 2: Esegui test e verifica che fallisce**

```bash
cd siae-dev-forge && bash tests/run-all.sh
```
Output atteso: `FAIL  hooks/post-skill: non emette skill_completed`

**Step 3: Implementa timestamp chaining in `hooks/post-skill`**

Sostituisci il contenuto di `hooks/post-skill` con:

```bash
#!/usr/bin/env bash
# PostToolUse hook for siae-devforge plugin (intercepts Skill tool invocations)
# Logs skill_invoked events and skill_completed for the PREVIOUS skill via timestamp chaining.

set -euo pipefail

# Determine plugin root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Source activity logger
source "${PLUGIN_ROOT}/lib/logger.sh"

# Timestamp file for skill duration chaining
SKILL_TS_FILE="${HOME}/.claude/.devforge-skill-start"

# Read tool output from stdin (JSON with tool_name and tool_input)
HOOK_INPUT=$(cat)

# Extract skill name from the input
SKILL_NAME=$(echo "$HOOK_INPUT" | grep -o '"skill"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"skill"[[:space:]]*:[[:space:]]*"//;s/"$//' || true)

if [ -z "$SKILL_NAME" ]; then
    SKILL_NAME=$(echo "$HOOK_INPUT" | grep -o '"name"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"name"[[:space:]]*:[[:space:]]*"//;s/"$//' || true)
fi

if [ -n "$SKILL_NAME" ]; then
    # --- Close previous skill (timestamp chaining) ---
    if [ -f "$SKILL_TS_FILE" ]; then
        PREV_DATA=$(cat "$SKILL_TS_FILE")
        PREV_START_NS=$(echo "$PREV_DATA" | cut -d'|' -f1)
        PREV_SKILL=$(echo "$PREV_DATA" | cut -d'|' -f2)
        PREV_PHASE=$(echo "$PREV_DATA" | cut -d'|' -f3)

        if [ -n "$PREV_START_NS" ] && [ "$PREV_START_NS" != "0" ]; then
            devforge_log_timed "skill_completed" "success" "$PREV_START_NS" \
                "{\"skill_name\":\"${PREV_SKILL}\",\"sdlc_phase\":\"${PREV_PHASE}\",\"outcome\":\"success\"}"
        fi
    fi

    # --- Log current skill invocation ---
    SDLC_PHASE=$(devforge_get_sdlc_phase "$SKILL_NAME")
    devforge_log "skill_invoked" "success" "{\"skill_name\":\"${SKILL_NAME}\",\"sdlc_phase\":\"${SDLC_PHASE}\"}"

    # --- Save timestamp for next chaining ---
    CURRENT_NS=$(date +%s%N 2>/dev/null || echo "0")
    echo "${CURRENT_NS}|${SKILL_NAME}|${SDLC_PHASE}" > "$SKILL_TS_FILE"
fi

# Pass through — PostToolUse hooks should not block
echo '{}'
exit 0
```

**Step 4: Esegui test e verifica che passa**

```bash
cd siae-dev-forge && bash tests/run-all.sh
```
Output atteso: `PASS  hooks/post-skill: emette skill_completed per skill precedente`

**Step 5: Aggiungi chiusura ultima skill in `hooks/stop-gate`**

Aggiungi dopo riga 15 (dopo la funzione `escape_for_json`) in `hooks/stop-gate`:

```bash
# --- Close last skill via timestamp chaining (telemetry) ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
if [ -f "${PLUGIN_ROOT}/lib/logger.sh" ]; then
    source "${PLUGIN_ROOT}/lib/logger.sh"
    SKILL_TS_FILE="${HOME}/.claude/.devforge-skill-start"
    if [ -f "$SKILL_TS_FILE" ]; then
        PREV_DATA=$(cat "$SKILL_TS_FILE")
        PREV_START_NS=$(echo "$PREV_DATA" | cut -d'|' -f1)
        PREV_SKILL=$(echo "$PREV_DATA" | cut -d'|' -f2)
        PREV_PHASE=$(echo "$PREV_DATA" | cut -d'|' -f3)
        if [ -n "$PREV_START_NS" ] && [ "$PREV_START_NS" != "0" ]; then
            devforge_log_timed "skill_completed" "success" "$PREV_START_NS" \
                "{\"skill_name\":\"${PREV_SKILL}\",\"sdlc_phase\":\"${PREV_PHASE}\",\"outcome\":\"success\"}"
        fi
        rm -f "$SKILL_TS_FILE"
    fi
fi
```

**Step 6: Commit**

```bash
git add hooks/post-skill hooks/stop-gate tests/run-all.sh
git commit -m "feat(telemetry): add skill_completed event via timestamp chaining

Closes previous skill on next skill_invoked or session stop.
Duration computed from nanosecond timestamps saved between invocations."
```

---

## Task 2: `commit_created` — Metriche git nel post-commit-review [DONE]

**File coinvolti:**
- Modifica: `hooks/post-commit-review` (righe 19-22)

**Step 1: Scrivi test — verifica che `post-commit-review` emette `commit_created`**

Aggiungi in `tests/run-all.sh` nella sezione Hook Validation:

```bash
# Check 6: post-commit-review emette commit_created su git commit
TEST_LOG="/tmp/devforge-test-commit-created.jsonl"
DEVFORGE_LOG_FILE_BAK="${DEVFORGE_LOG_FILE:-}"
export DEVFORGE_LOG_FILE="$TEST_LOG"
rm -f "$TEST_LOG"
# Mock: simula un git commit command (il hook legge il comando dal JSON input)
commit_output=$(echo '{"command":"git commit -m test"}' | bash "${PLUGIN_ROOT}/hooks/post-commit-review" 2>/dev/null; echo "exit:$?")
if echo "$commit_output" | grep -q 'exit:0' && grep -q '"event":"commit_created"' "$TEST_LOG" 2>/dev/null; then
  echo "  PASS  hooks/post-commit-review: emette commit_created su git commit"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/post-commit-review: non emette commit_created"
  hook_fail=$((hook_fail + 1))
fi
rm -f "$TEST_LOG"
[ -n "$DEVFORGE_LOG_FILE_BAK" ] && export DEVFORGE_LOG_FILE="$DEVFORGE_LOG_FILE_BAK" || unset DEVFORGE_LOG_FILE
```

**Step 2: Esegui test e verifica che fallisce**

```bash
cd siae-dev-forge && bash tests/run-all.sh
```
Output atteso: `FAIL  hooks/post-commit-review: non emette commit_created`

**Step 3: Implementa `commit_created` in `hooks/post-commit-review`**

Sostituisci il blocco git commit (righe 19-22) con:

```bash
# Emit commit_created event with git stats (non-blocking, background)
if [[ "$TOOL_COMMAND" =~ git[[:space:]]+commit ]]; then
    source "${PLUGIN_ROOT}/lib/telemetry-upload.sh" 2>/dev/null || true
    devforge_upload_logs &

    # Collect git diff stats for the commit just created
    source "${PLUGIN_ROOT}/lib/logger.sh" 2>/dev/null || true
    DIFF_STAT=$(git diff --stat HEAD~1 HEAD 2>/dev/null || echo "")
    FILES_CHANGED=$(echo "$DIFF_STAT" | tail -1 | grep -oE '[0-9]+ file' | grep -oE '[0-9]+' || echo "0")
    INSERTIONS=$(echo "$DIFF_STAT" | tail -1 | grep -oE '[0-9]+ insertion' | grep -oE '[0-9]+' || echo "0")
    DELETIONS=$(echo "$DIFF_STAT" | tail -1 | grep -oE '[0-9]+ deletion' | grep -oE '[0-9]+' || echo "0")

    # Detect if commit includes test files
    CHANGED_FILES=$(git diff --name-only HEAD~1 HEAD 2>/dev/null || echo "")
    HAS_TESTS="false"
    if echo "$CHANGED_FILES" | grep -qE '(Test\.|_test\.|\.test\.|\.spec\.|/test/|/tests/)'; then
        HAS_TESTS="true"
    fi

    devforge_log "commit_created" "success" \
        "{\"files_changed\":${FILES_CHANGED:-0},\"insertions\":${INSERTIONS:-0},\"deletions\":${DELETIONS:-0},\"has_tests\":${HAS_TESTS}}"

    # Track commits in session counter
    SESSION_COMMITS_FILE="${HOME}/.claude/.devforge-session-commits"
    CURRENT_COMMITS=$(cat "$SESSION_COMMITS_FILE" 2>/dev/null || echo "0")
    echo $((CURRENT_COMMITS + 1)) > "$SESSION_COMMITS_FILE"
fi
```

**Step 4: Esegui test e verifica che passa**

```bash
cd siae-dev-forge && bash tests/run-all.sh
```
Output atteso: `PASS  hooks/post-commit-review: emette commit_created su git commit`

**Step 5: Commit**

```bash
git add hooks/post-commit-review tests/run-all.sh
git commit -m "feat(telemetry): add commit_created event with git stats

Logs files_changed, insertions, deletions, has_tests on every git commit.
Tracks session commit counter for session_end aggregation."
```

---

## Task 3: `pr_opened` — Detection PR dopo push in post-commit-review [DONE]

**File coinvolti:**
- Modifica: `hooks/post-commit-review` (dopo il blocco git commit, prima del check gh pr create)

**Step 1: Scrivi test — verifica che pr_opened viene skippato senza `gh`**

Aggiungi in `tests/run-all.sh` nella sezione Hook Validation:

```bash
# Check 7: post-commit-review gestisce pr_opened gracefully senza gh
TEST_LOG="/tmp/devforge-test-pr-opened.jsonl"
DEVFORGE_LOG_FILE_BAK="${DEVFORGE_LOG_FILE:-}"
export DEVFORGE_LOG_FILE="$TEST_LOG"
rm -f "$TEST_LOG"
# Simula git push (il hook proverà gh pr view, che fallirà — deve essere graceful)
pr_output=$(echo '{"command":"git push origin feature/test"}' | PATH="/usr/bin:/bin" bash "${PLUGIN_ROOT}/hooks/post-commit-review" 2>/dev/null; echo "exit:$?")
if echo "$pr_output" | grep -q 'exit:0'; then
  echo "  PASS  hooks/post-commit-review: gestisce pr_opened senza gh (exit 0)"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/post-commit-review: crash su pr_opened senza gh"
  hook_fail=$((hook_fail + 1))
fi
rm -f "$TEST_LOG"
[ -n "$DEVFORGE_LOG_FILE_BAK" ] && export DEVFORGE_LOG_FILE="$DEVFORGE_LOG_FILE_BAK" || unset DEVFORGE_LOG_FILE
```

**Step 2: Esegui test e verifica che passa (graceful skip è il comportamento atteso)**

```bash
cd siae-dev-forge && bash tests/run-all.sh
```
Output atteso: `PASS  hooks/post-commit-review: gestisce pr_opened senza gh (exit 0)`

Nota: questo test verifica la resilienza. Il test funzionale richiede `gh` CLI autenticato.

**Step 3: Implementa `pr_opened` in `hooks/post-commit-review`**

Aggiungi dopo il blocco `git commit` e PRIMA del check `gh pr create / git push` (riga 25),
inserisci la detection pr_opened per git push:

```bash
# Emit pr_opened event after push if a PR exists (requires gh CLI)
if [[ "$TOOL_COMMAND" =~ git[[:space:]]+push ]]; then
    source "${PLUGIN_ROOT}/lib/logger.sh" 2>/dev/null || true
    if command -v gh >/dev/null 2>&1; then
        PR_JSON=$(gh pr view --json number,baseRefName,changedFiles,commits 2>/dev/null || echo "")
        if [ -n "$PR_JSON" ]; then
            PR_NUMBER=$(echo "$PR_JSON" | grep -o '"number":[0-9]*' | grep -oE '[0-9]+' || echo "0")
            BASE_BRANCH=$(echo "$PR_JSON" | grep -o '"baseRefName":"[^"]*"' | sed 's/.*"baseRefName":"//;s/"$//' || echo "unknown")
            FILES_CHANGED=$(echo "$PR_JSON" | grep -o '"changedFiles":[0-9]*' | grep -oE '[0-9]+' || echo "0")
            COMMITS_COUNT=$(echo "$PR_JSON" | grep -o '"totalCount":[0-9]*' | grep -oE '[0-9]+' || echo "0")
            devforge_log "pr_opened" "success" \
                "{\"pr_number\":${PR_NUMBER},\"base_branch\":\"${BASE_BRANCH}\",\"files_changed\":${FILES_CHANGED},\"commits_count\":${COMMITS_COUNT}}"
        fi
    fi
fi
```

**Step 4: Esegui test e verifica che passa**

```bash
cd siae-dev-forge && bash tests/run-all.sh
```
Output atteso: tutti i test PASS (incluso il graceful skip senza gh)

**Step 5: Commit**

```bash
git add hooks/post-commit-review tests/run-all.sh
git commit -m "feat(telemetry): add pr_opened event after git push

Detects open PR via gh CLI after push. Gracefully skips if gh not available."
```

---

## Task 4: `pr_merged` — Detection PR merge recenti in session-start [DONE]

**File coinvolti:**
- Modifica: `hooks/session-start` (dopo riga 81, prima di `exit 0`)

**Step 1: Scrivi test — verifica che session-start non crasha con detection pr_merged**

Aggiungi in `tests/run-all.sh` nella sezione Hook Validation:

```bash
# Check 8: session-start gestisce pr_merged detection senza crash
session_output=$(bash "${PLUGIN_ROOT}/hooks/session-start" 2>/dev/null; echo "exit:$?")
if echo "$session_output" | grep -q 'exit:0'; then
  echo "  PASS  hooks/session-start: gestisce pr_merged detection (exit 0)"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/session-start: crash su pr_merged detection"
  hook_fail=$((hook_fail + 1))
fi
```

**Step 2: Esegui test e verifica che passa (baseline — nessuna regressione)**

```bash
cd siae-dev-forge && bash tests/run-all.sh
```
Output atteso: `PASS  hooks/session-start: gestisce pr_merged detection (exit 0)`

**Step 3: Implementa `pr_merged` in `hooks/session-start`**

Aggiungi dopo riga 81 (dopo `devforge_log_timed "session_start"`) e prima di `exit 0`:

```bash
# --- Detect recently merged PRs (last 24h) for productivity metrics ---
if command -v gh >/dev/null 2>&1; then
    MERGED_PRS=$(gh pr list --state merged --author "$(devforge_get_user)" \
        --json number,mergedAt,createdAt,reviews \
        --jq '[.[] | select((.mergedAt | fromdateiso8601) > (now - 86400))]' 2>/dev/null || echo "[]")

    if [ "$MERGED_PRS" != "[]" ] && [ -n "$MERGED_PRS" ]; then
        # Log each merged PR
        echo "$MERGED_PRS" | jq -c '.[]' 2>/dev/null | while IFS= read -r pr; do
            PR_NUMBER=$(echo "$pr" | jq -r '.number' 2>/dev/null || echo "0")
            CREATED_AT=$(echo "$pr" | jq -r '.createdAt' 2>/dev/null || echo "")
            MERGED_AT=$(echo "$pr" | jq -r '.mergedAt' 2>/dev/null || echo "")
            REVIEWERS_COUNT=$(echo "$pr" | jq '[.reviews[]? | .author.login] | unique | length' 2>/dev/null || echo "0")

            # Compute review cycle hours (created → merged)
            REVIEW_CYCLE_HOURS="0"
            if [ -n "$CREATED_AT" ] && [ -n "$MERGED_AT" ]; then
                CREATED_EPOCH=$(date -jf "%Y-%m-%dT%H:%M:%SZ" "$CREATED_AT" +%s 2>/dev/null || date -d "$CREATED_AT" +%s 2>/dev/null || echo "0")
                MERGED_EPOCH=$(date -jf "%Y-%m-%dT%H:%M:%SZ" "$MERGED_AT" +%s 2>/dev/null || date -d "$MERGED_AT" +%s 2>/dev/null || echo "0")
                if [ "$CREATED_EPOCH" != "0" ] && [ "$MERGED_EPOCH" != "0" ]; then
                    DELTA_SECONDS=$((MERGED_EPOCH - CREATED_EPOCH))
                    # Bash integer division: multiply by 10 first for 1 decimal
                    REVIEW_CYCLE_HOURS=$(echo "scale=1; $DELTA_SECONDS / 3600" | bc 2>/dev/null || echo "0")
                fi
            fi

            devforge_log "pr_merged" "success" \
                "{\"pr_number\":${PR_NUMBER},\"review_cycle_hours\":${REVIEW_CYCLE_HOURS},\"reviewers_count\":${REVIEWERS_COUNT}}"
        done
    fi
fi

# --- Initialize session counters ---
echo "0" > "${HOME}/.claude/.devforge-session-commits"
echo "" > "${HOME}/.claude/.devforge-session-skills"
```

**Step 4: Esegui test e verifica che passa**

```bash
cd siae-dev-forge && bash tests/run-all.sh
```
Output atteso: `PASS  hooks/session-start: gestisce pr_merged detection (exit 0)`

**Step 5: Commit**

```bash
git add hooks/session-start tests/run-all.sh
git commit -m "feat(telemetry): add pr_merged detection at session start

Checks for PRs merged in last 24h via gh CLI. Computes review_cycle_hours.
Initializes session counters for commits and skills tracking."
```

---

## Task 5: `session_end` — Metriche sessione nel stop-gate [DONE]

**File coinvolti:**
- Modifica: `hooks/stop-gate` (dopo il blocco skill_completed aggiunto in Task 1, prima della detection completion keywords)
- Modifica: `hooks/post-skill` (aggiungere tracking skill names per sessione)

**Step 1: Scrivi test — verifica che stop-gate emette session_end**

Aggiungi in `tests/run-all.sh` nella sezione Hook Validation:

```bash
# Check 9: stop-gate emette session_end con counters
TEST_LOG="/tmp/devforge-test-session-end.jsonl"
DEVFORGE_LOG_FILE_BAK="${DEVFORGE_LOG_FILE:-}"
export DEVFORGE_LOG_FILE="$TEST_LOG"
rm -f "$TEST_LOG"
# Setup session counters
echo "3" > "${HOME}/.claude/.devforge-session-commits"
echo "siae-brainstorming,siae-tdd" > "${HOME}/.claude/.devforge-session-skills"
# Setup session start timestamp
echo "$(date +%s%N 2>/dev/null || echo 0)" > "${HOME}/.claude/.devforge-session-start-ns"
# Simula stop con messaggio che contiene "fatto"
stop_input='{"messages":[{"role":"assistant","content":"tutto fatto"}]}'
stop_output=$(echo "$stop_input" | bash "${PLUGIN_ROOT}/hooks/stop-gate" 2>/dev/null; echo "exit:$?")
if echo "$stop_output" | grep -q 'exit:0' && grep -q '"event":"session_end"' "$TEST_LOG" 2>/dev/null; then
  echo "  PASS  hooks/stop-gate: emette session_end con counters"
  hook_ok=$((hook_ok + 1))
else
  echo "  FAIL  hooks/stop-gate: non emette session_end"
  hook_fail=$((hook_fail + 1))
fi
rm -f "$TEST_LOG" "${HOME}/.claude/.devforge-session-commits" "${HOME}/.claude/.devforge-session-skills" "${HOME}/.claude/.devforge-session-start-ns"
[ -n "$DEVFORGE_LOG_FILE_BAK" ] && export DEVFORGE_LOG_FILE="$DEVFORGE_LOG_FILE_BAK" || unset DEVFORGE_LOG_FILE
```

**Step 2: Esegui test e verifica che fallisce**

```bash
cd siae-dev-forge && bash tests/run-all.sh
```
Output atteso: `FAIL  hooks/stop-gate: non emette session_end`

**Step 3: Salva timestamp di inizio sessione in `hooks/session-start`**

Aggiungi dopo riga 12 (`START_NS=...`) in `hooks/session-start`:

```bash
# Persist session start timestamp for session_end duration calculation
echo "$START_NS" > "${HOME}/.claude/.devforge-session-start-ns"
```

**Step 4: Aggiungi tracking skill name in `hooks/post-skill`**

Aggiungi dopo il salvataggio timestamp (dopo `echo "${CURRENT_NS}|..."`) nel post-skill:

```bash
    # Track skill names for session_end aggregation
    SESSION_SKILLS_FILE="${HOME}/.claude/.devforge-session-skills"
    EXISTING_SKILLS=$(cat "$SESSION_SKILLS_FILE" 2>/dev/null || echo "")
    if [ -z "$EXISTING_SKILLS" ]; then
        echo "$SKILL_NAME" > "$SESSION_SKILLS_FILE"
    elif ! echo "$EXISTING_SKILLS" | grep -qF "$SKILL_NAME"; then
        echo "${EXISTING_SKILLS},${SKILL_NAME}" > "$SESSION_SKILLS_FILE"
    fi
```

**Step 5: Implementa `session_end` in `hooks/stop-gate`**

Aggiungi dopo il blocco skill_completed (Task 1) e PRIMA della lettura stdin (`INPUT=$(cat)`):

```bash
# --- Emit session_end event with aggregated counters ---
if [ -f "${PLUGIN_ROOT}/lib/logger.sh" ]; then
    # source already done above for skill_completed
    SESSION_START_NS_FILE="${HOME}/.claude/.devforge-session-start-ns"
    SESSION_COMMITS_FILE="${HOME}/.claude/.devforge-session-commits"
    SESSION_SKILLS_FILE="${HOME}/.claude/.devforge-session-skills"

    SESSION_START_NS=$(cat "$SESSION_START_NS_FILE" 2>/dev/null || echo "0")
    COMMITS_COUNT=$(cat "$SESSION_COMMITS_FILE" 2>/dev/null || echo "0")
    SKILLS_LIST=$(cat "$SESSION_SKILLS_FILE" 2>/dev/null || echo "")

    # Count distinct skills
    if [ -n "$SKILLS_LIST" ]; then
        SKILLS_USED_COUNT=$(echo "$SKILLS_LIST" | tr ',' '\n' | sort -u | wc -l | tr -d ' ')
    else
        SKILLS_USED_COUNT=0
    fi

    devforge_log_timed "session_end" "success" "$SESSION_START_NS" \
        "{\"skills_used_count\":${SKILLS_USED_COUNT},\"commits_count\":${COMMITS_COUNT}}"

    # Cleanup session files
    rm -f "$SESSION_START_NS_FILE" "$SESSION_COMMITS_FILE" "$SESSION_SKILLS_FILE"
fi
```

**Nota importante:** il blocco `session_end` deve eseguire SEMPRE (non solo quando c'è un completion claim).
Riorganizza stop-gate: la sezione telemetria (skill_completed + session_end) va PRIMA della
lettura stdin e del check completion keywords. La sezione verification reminder resta invariata.

**Step 6: Esegui test e verifica che passa**

```bash
cd siae-dev-forge && bash tests/run-all.sh
```
Output atteso: `PASS  hooks/stop-gate: emette session_end con counters`

**Step 7: Commit**

```bash
git add hooks/stop-gate hooks/session-start hooks/post-skill tests/run-all.sh
git commit -m "feat(telemetry): add session_end event with duration and counters

Emits session_end on Stop hook with total duration_ms, skills_used_count,
and commits_count. Session counters tracked across hooks via temp files."
```

---

## Task 6: Test `has_tests` detection + schema JSONL validation [DONE]

**File coinvolti:**
- Modifica: `tests/run-all.sh`

**Step 1: Scrivi test per `has_tests` regex pattern**

Aggiungi una nuova sezione in `tests/run-all.sh` prima del Report Finale:

```bash
# --- Telemetry Event Validation ---
echo ""
echo "=== Telemetry Event Validation ==="
echo ""

telemetry_ok=0
telemetry_fail=0

# Test has_tests detection regex
HAS_TESTS_PATTERN='(Test\.|_test\.|\.test\.|\.spec\.|/test/|/tests/)'

# Positive cases
for test_file in "UserServiceTest.java" "test_validator.py" "app.test.ts" "login.spec.ts" "src/test/MyTest.java" "tests/test_main.py"; do
  if echo "$test_file" | grep -qE "$HAS_TESTS_PATTERN"; then
    echo "  PASS  has_tests: riconosce '$test_file'"
    telemetry_ok=$((telemetry_ok + 1))
  else
    echo "  FAIL  has_tests: non riconosce '$test_file'"
    telemetry_fail=$((telemetry_fail + 1))
  fi
done

# Negative cases (should NOT match)
for src_file in "UserService.java" "validator.py" "app.ts" "login.vue" "README.md"; do
  if echo "$src_file" | grep -qE "$HAS_TESTS_PATTERN"; then
    echo "  FAIL  has_tests: falso positivo su '$src_file'"
    telemetry_fail=$((telemetry_fail + 1))
  else
    echo "  PASS  has_tests: correttamente ignora '$src_file'"
    telemetry_ok=$((telemetry_ok + 1))
  fi
done

# Test JSONL schema: verify all event types produce valid JSON
echo ""
echo "  --- JSONL Schema Validation ---"
SCHEMA_LOG="/tmp/devforge-test-schema.jsonl"
rm -f "$SCHEMA_LOG"
export DEVFORGE_LOG_FILE="$SCHEMA_LOG"

source "${PLUGIN_ROOT}/lib/logger.sh"

# Generate sample events
devforge_log "skill_invoked" "success" '{"skill_name":"test","sdlc_phase":"5. Testing"}'
devforge_log "skill_completed" "success" '{"skill_name":"test","sdlc_phase":"5. Testing","outcome":"success"}'
devforge_log "commit_created" "success" '{"files_changed":3,"insertions":42,"deletions":7,"has_tests":true}'
devforge_log "pr_opened" "success" '{"pr_number":1,"base_branch":"main","files_changed":5,"commits_count":2}'
devforge_log "pr_merged" "success" '{"pr_number":1,"review_cycle_hours":4.5,"reviewers_count":2}'
devforge_log_timed "session_end" "success" "$(date +%s%N)" '{"skills_used_count":3,"commits_count":2}'

# Validate each line is valid JSON
TOTAL_LINES=$(wc -l < "$SCHEMA_LOG" | tr -d ' ')
VALID_LINES=0
if command -v jq >/dev/null 2>&1; then
    while IFS= read -r line; do
        if echo "$line" | jq . >/dev/null 2>&1; then
            VALID_LINES=$((VALID_LINES + 1))
        fi
    done < "$SCHEMA_LOG"

    if [ "$VALID_LINES" -eq "$TOTAL_LINES" ]; then
        echo "  PASS  JSONL schema: ${VALID_LINES}/${TOTAL_LINES} linee JSON valide"
        telemetry_ok=$((telemetry_ok + 1))
    else
        echo "  FAIL  JSONL schema: ${VALID_LINES}/${TOTAL_LINES} linee JSON valide"
        telemetry_fail=$((telemetry_fail + 1))
    fi
else
    echo "  SKIP  JSONL schema: jq non disponibile"
    TOTAL_SKIP=$((TOTAL_SKIP + 1))
fi

rm -f "$SCHEMA_LOG"
unset DEVFORGE_LOG_FILE

echo ""
echo "  Telemetry check: ${telemetry_ok} OK | ${telemetry_fail} FAIL"
TOTAL_PASS=$((TOTAL_PASS + telemetry_ok))
TOTAL_FAIL=$((TOTAL_FAIL + telemetry_fail))
```

**Step 2: Esegui test e verifica che passa**

```bash
cd siae-dev-forge && bash tests/run-all.sh
```
Output atteso: tutti i test has_tests e schema JSONL PASS

**Step 3: Commit**

```bash
git add tests/run-all.sh
git commit -m "test(telemetry): add has_tests regex and JSONL schema validation

Validates test file detection pattern for Java/Python/TypeScript.
Verifies all 6 new event types produce valid JSONL output."
```

---

## Riepilogo Dipendenze

```
Task 1 (skill_completed) ← indipendente
Task 2 (commit_created)  ← indipendente
Task 3 (pr_opened)       ← indipendente (stesso file di Task 2, merge manuale)
Task 4 (pr_merged)       ← indipendente
Task 5 (session_end)     ← dipende da Task 1 (stop-gate) + Task 2 (session counter) + Task 4 (session counter init)
Task 6 (test validation) ← dipende da Task 1-5 (testa il risultato finale)
```

**Ordine di esecuzione consigliato:** Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6

**Parallelizzabili:** Task 1 + Task 2 + Task 4 (file diversi, nessuna dipendenza)
**Sequenziali:** Task 3 dopo Task 2 (stesso file), Task 5 dopo Task 1+2+4, Task 6 alla fine
