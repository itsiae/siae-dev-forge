# Task 2 — JSON escaping (11 call in 6 hook)

**Stato:** [DONE]
**File coinvolti:** `hooks/pre-commit`, `hooks/pr-gate`, `hooks/sub-skill-gate`, `hooks/tdd-gate`, `hooks/session-start`, `hooks/user-prompt-context` (MODIFICA)
**AC coperti:** AC-2

---

Il pattern è identico per tutte le 11 call: aggiungere `SAFE_VAR=$(devforge_sanitize_json_str "$VAR")` prima della chiamata `devforge_log`, e usare `${SAFE_VAR}` nel JSON. La funzione `devforge_sanitize_json_str` è già disponibile in `lib/logger.sh` (linea 93), già sourcato in tutti gli hook.

## Step 1 — Fix `hooks/pre-commit` (3 call)

**Linea 70** — sanitizza `TOOL_COMMAND`:
```bash
# PRIMA
devforge_log "pre_commit" "blocked" "{\"command\":\"${TOOL_COMMAND}\",\"skill_missing\":\"siae-git-workflow\"}"
# DOPO
SAFE_TOOL_COMMAND=$(devforge_sanitize_json_str "$TOOL_COMMAND")
devforge_log "pre_commit" "blocked" "{\"command\":\"${SAFE_TOOL_COMMAND}\",\"skill_missing\":\"siae-git-workflow\"}"
```

**Linea 104** — sanitizza `CURRENT_BRANCH`:
```bash
# PRIMA
devforge_log "coverage_gate" "blocked" "{\"coverage\":${COVERAGE_PCT},\"threshold\":${THRESHOLD},\"branch\":\"${CURRENT_BRANCH}\"}"
# DOPO
SAFE_BRANCH=$(devforge_sanitize_json_str "$CURRENT_BRANCH")
devforge_log "coverage_gate" "blocked" "{\"coverage\":${COVERAGE_PCT},\"threshold\":${THRESHOLD},\"branch\":\"${SAFE_BRANCH}\"}"
```

**Linea 178** — sanitizza `TOOL_COMMAND`:
```bash
# PRIMA
devforge_log "quality_gate" "success" "{\"check_name\":\"pre_commit_activated\",\"command\":\"${TOOL_COMMAND}\"}"
# DOPO
SAFE_TOOL_COMMAND=$(devforge_sanitize_json_str "$TOOL_COMMAND")
devforge_log "quality_gate" "success" "{\"check_name\":\"pre_commit_activated\",\"command\":\"${SAFE_TOOL_COMMAND}\"}"
```

## Step 2 — Fix `hooks/pr-gate` (1 call)

**Linea 30** — sanitizza `TOOL_COMMAND`:
```bash
# DOPO
SAFE_TOOL_COMMAND=$(devforge_sanitize_json_str "$TOOL_COMMAND")
devforge_log "pr_gate" "success" "{\"check\":\"pr_security_activated\",\"command\":\"${SAFE_TOOL_COMMAND}\"}"
```

## Step 3 — Fix `hooks/sub-skill-gate` (1 call)

**Linea 90** — sanitizza `SKILL_NAME` e `MISSING_PREREQS`:
```bash
# DOPO
SAFE_SKILL=$(devforge_sanitize_json_str "$SKILL_NAME")
SAFE_PREREQS=$(devforge_sanitize_json_str "$MISSING_PREREQS")
devforge_log "sub_skill_gate" "blocked" "{\"skill\":\"${SAFE_SKILL}\",\"missing_prereqs\":\"${SAFE_PREREQS}\"}"
```

## Step 4 — Fix `hooks/tdd-gate` (2 call)

**Linea 80** — sanitizza `FILE_PATH`:
```bash
# DOPO
SAFE_FILE_PATH=$(devforge_sanitize_json_str "$FILE_PATH")
devforge_log "tdd_gate" "blocked" "{\"file_path\":\"${SAFE_FILE_PATH}\",\"phase\":\"INIT\",\"violation\":\"prod_code_before_test\"}"
```

**Linea 100** — sanitizza `FILE_PATH`:
```bash
# DOPO
SAFE_FILE_PATH=$(devforge_sanitize_json_str "$FILE_PATH")
devforge_log "tdd_gate" "blocked" "{\"file_path\":\"${SAFE_FILE_PATH}\",\"skill_missing\":\"siae-tdd\"}"
```

## Step 5 — Fix `hooks/session-start` (2 call)

**Linea 175** — sanitizza `$(pwd)` e `PLUGIN_VERSION`:
```bash
# DOPO
SAFE_PROJECT_DIR=$(devforge_sanitize_json_str "$(pwd)")
SAFE_PLUGIN_VERSION=$(devforge_sanitize_json_str "$PLUGIN_VERSION")
devforge_log_timed "session_start" "success" "$START_NS" "{\"project_dir\":\"${SAFE_PROJECT_DIR}\",\"plugin_version\":\"${SAFE_PLUGIN_VERSION}\"}"
```

**Linea 254** — sanitizza `${sentinel}`:
```bash
# DOPO
SAFE_SENTINEL=$(devforge_sanitize_json_str "$sentinel")
devforge_log "session_start_cleanup" "info" "{\"file\":\"${SAFE_SENTINEL}\",\"age_hours\":$(( (NOW - MTIME) / 3600 ))}"
```

## Step 6 — Fix `hooks/user-prompt-context` (2 call)

**Linea 54** — sanitizza `mode_name`:
```bash
# DOPO
SAFE_MODE=$(devforge_sanitize_json_str "$mode_name")
devforge_log "user_prompt_context" "warning" "{\"mode\":\"${SAFE_MODE}\",\"reason\":\"stale_sentinel\",\"age_hours\":$((age / 3600))}"
```

**Linea 63** — sanitizza `mode_name`:
```bash
# DOPO
SAFE_MODE=$(devforge_sanitize_json_str "$mode_name")
devforge_log "user_prompt_context" "warning" "{\"mode\":\"${SAFE_MODE}\",\"reason\":\"empty_sentinel\"}"
```

## Step 7 — Verifica

Per ogni hook modificato, verifica che il JSONL prodotto sia JSON valido:

```bash
tail -20 ~/.claude/devforge-activity.jsonl | while IFS= read -r line; do
    echo "$line" | python3 -c "import json,sys; json.loads(sys.stdin.read())" 2>&1 || echo "INVALID: $line"
done
```

Output atteso: nessuna riga "INVALID".
