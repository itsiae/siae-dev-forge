#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# devforge-statusline.sh — Status line for Claude Code
# Reads JSON from stdin + DevForge state files, outputs 2 formatted lines.
#
# State files written by: hooks/session-start, hooks/post-skill,
#   hooks/capture-test-result, hooks/batch-checkpoint
# ============================================================================

# --- 1. ANSI Colors ---
RED='\033[31m'
GREEN='\033[32m'
YELLOW='\033[33m'
RESET='\033[0m'

# --- 2. JSON parsing from stdin (no eval — safe from injection) ---
DEVFORGE_DIR="${HOME}/.claude"
CACHE_FILE="${DEVFORGE_DIR}/.devforge-git-cache"

CTX_USED="0"
QUOTA_5H=""
AGENT_NAME=""

STDIN_JSON=""
if [ ! -t 0 ]; then
  STDIN_JSON="$(cat)"
fi

if [ -n "$STDIN_JSON" ]; then
  if command -v jq >/dev/null 2>&1; then
    CTX_USED="$(printf '%s' "$STDIN_JSON" | jq -r '.context_window.used_percentage // 0' 2>/dev/null)" || CTX_USED="0"
    QUOTA_5H="$(printf '%s' "$STDIN_JSON" | jq -r '.rate_limits.five_hour.used_percentage // empty' 2>/dev/null)" || QUOTA_5H=""
    AGENT_NAME="$(printf '%s' "$STDIN_JSON" | jq -r '.agent.name // empty' 2>/dev/null)" || AGENT_NAME=""
  else
    # Fallback without jq: extract numeric values via tr+sed (macOS compatible)
    CTX_USED="$(printf '%s' "$STDIN_JSON" | tr ',' '\n' | sed -n 's/.*"used_percentage"[[:space:]]*:[[:space:]]*\([0-9.]*\).*/\1/p' | head -1)" || CTX_USED="0"
    [ -z "$CTX_USED" ] && CTX_USED="0"
  fi
fi

# --- 3. Read DevForge state files ---
read_file() {
  local path="$1"
  if [ -f "$path" ]; then
    local content=""
    read -r content < "$path" 2>/dev/null || true
    printf '%s' "$content"
  fi
}

# Skill start: timestamp_ns|skill_name|sdlc_phase (written by hooks/post-skill)
SKILL_START_RAW="$(read_file "${DEVFORGE_DIR}/.devforge-skill-start")"
CURRENT_SKILL=""
SDLC_PHASE=""
if [ -n "$SKILL_START_RAW" ]; then
  CURRENT_SKILL="$(printf '%s' "$SKILL_START_RAW" | cut -d'|' -f2)"
  SDLC_PHASE="$(printf '%s' "$SKILL_START_RAW" | cut -d'|' -f3)"
fi

# TDD state: PHASE|target|test_name|timestamp (written by hooks/capture-test-result)
TDD_RAW="$(read_file "${DEVFORGE_DIR}/.devforge-tdd-state")"
TDD_PHASE=""
if [ -n "$TDD_RAW" ]; then
  TDD_PHASE="$(printf '%s' "$TDD_RAW" | cut -d'|' -f1)"
fi

# Session skills: skill1,skill2,skill3 (written by hooks/post-skill)
SESSION_SKILLS="$(read_file "${DEVFORGE_DIR}/.devforge-session-skills")"

# Session commits (written by hooks/post-commit-review)
SESSION_COMMITS="$(read_file "${DEVFORGE_DIR}/.devforge-session-commits")"
SESSION_COMMITS="${SESSION_COMMITS//[!0-9]/}"
SESSION_COMMITS="${SESSION_COMMITS:-0}"

# Batch counter and checkpoint (written by hooks/batch-checkpoint)
BATCH_COUNTER="$(read_file "${DEVFORGE_DIR}/.devforge-batch-counter")"
BATCH_COUNTER="${BATCH_COUNTER//[!0-9]/}"
BATCH_CHECKPOINT=0
if [ -f "${DEVFORGE_DIR}/.devforge-batch-checkpoint" ]; then
  BATCH_CHECKPOINT=1
fi

# --- 4. Git branch with cache (TTL 5s) ---
get_git_branch() {
  local now
  now="$(date +%s)"
  if [ -f "$CACHE_FILE" ]; then
    local cached_time="" cached_branch=""
    { read -r cached_time; read -r cached_branch; } < "$CACHE_FILE" 2>/dev/null || true
    cached_time="${cached_time//[!0-9]/}"
    cached_time="${cached_time:-0}"
    local age=$(( now - cached_time ))
    if [ "$age" -lt 5 ] && [ -n "$cached_branch" ]; then
      printf '%s' "$cached_branch"
      return
    fi
  fi
  local branch
  branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)" || branch="no-repo"
  [ -z "$branch" ] && branch="no-repo"
  printf '%s\n%s\n' "$now" "$branch" > "$CACHE_FILE" 2>/dev/null || true
  chmod 600 "$CACHE_FILE" 2>/dev/null || true
  printf '%s' "$branch"
}

GIT_BRANCH="$(get_git_branch)"
# Sanitize branch name: keep only safe chars for printf %b
GIT_BRANCH="${GIT_BRANCH//[^a-zA-Z0-9\/_.\-]/}"

# --- 5. Helper functions ---

context_bar() {
  local pct="${1:-0}"
  local pct_int="${pct%%.*}"
  pct_int="${pct_int//[!0-9]/}"
  pct_int="${pct_int:-0}"

  local filled=$(( pct_int / 10 ))
  local empty=$(( 10 - filled ))

  local color="$GREEN"
  if [ "$pct_int" -ge 90 ]; then
    color="$RED"
  elif [ "$pct_int" -ge 70 ]; then
    color="$YELLOW"
  fi

  local bar=""
  local i
  for (( i=0; i<filled; i++ )); do bar="${bar}█"; done
  for (( i=0; i<empty; i++ )); do bar="${bar}░"; done

  printf '%b%s %s%%%b' "$color" "$bar" "$pct_int" "$RESET"
}

tdd_badge() {
  local phase="$1"
  case "$phase" in
    RED)      printf 'TDD: %b🔴 RED%b'      "$RED"    "$RESET" ;;
    GREEN)    printf 'TDD: %b🟢 GREEN%b'    "$GREEN"  "$RESET" ;;
    REFACTOR) printf 'TDD: %b🔧 REFACTOR%b' "$YELLOW" "$RESET" ;;
    INIT)     printf 'TDD: ⏳ INIT' ;;
    *)        return ;;
  esac
}

skill_check() {
  local skill="$1"
  local skills_csv="$2"
  if printf '%s' "$skills_csv" | grep -qF "$skill" 2>/dev/null; then
    printf '✅'
  else
    printf '⬜'
  fi
}

has_skill() {
  printf '%s' "$SESSION_SKILLS" | grep -qF "$1" 2>/dev/null
}

# --- 6. Compose line 1 — Operational status ---
LINE1="🔨 DevForge"

if [ -n "$SDLC_PHASE" ] && [ "$SDLC_PHASE" != "idle" ] && [ "$SDLC_PHASE" != "unknown" ]; then
  LINE1="${LINE1} [${SDLC_PHASE}]"
fi

if [ -n "$AGENT_NAME" ]; then
  LINE1="${LINE1} (${AGENT_NAME})"
fi

LINE1="${LINE1} | ${GIT_BRANCH}"

if [ -n "$TDD_PHASE" ]; then
  TDD_STR="$(tdd_badge "$TDD_PHASE")"
  if [ -n "$TDD_STR" ]; then
    LINE1="${LINE1} | ${TDD_STR}"
  fi
fi

# --- 7. Compose line 2 — Awareness + warnings ---
# Use string concatenation instead of arrays (bash 3.2 + set -u safe)
WARN_STR=""

CTX_INT="${CTX_USED%%.*}"
CTX_INT="${CTX_INT//[!0-9]/}"
CTX_INT="${CTX_INT:-0}"

if [ "$CTX_INT" -ge 80 ]; then
  WARN_STR="$(printf '%b⚠️ Context alto — nuova sessione%b' "$YELLOW" "$RESET")"
fi

if [ "$BATCH_CHECKPOINT" -eq 1 ]; then
  WARN_STR="${WARN_STR:+$WARN_STR }$(printf '%b⏸️ Batch completo — serve report%b' "$YELLOW" "$RESET")"
fi

if [ "$SESSION_COMMITS" -gt 0 ]; then
  if ! has_skill "siae-verification"; then
    WARN_STR="${WARN_STR:+$WARN_STR }$(printf '%b⚠️ Verification non invocata%b' "$YELLOW" "$RESET")"
  fi
fi

if [ -n "$SDLC_PHASE" ] && printf '%s' "$SDLC_PHASE" | grep -qiE "implement|testing" 2>/dev/null; then
  if ! has_skill "siae-brainstorming"; then
    WARN_STR="${WARN_STR:+$WARN_STR }$(printf '%b⚠️ Brainstorming saltato%b' "$YELLOW" "$RESET")"
  fi
fi

# Skill checklist
BRAIN_CHK="$(skill_check 'brainstorming' "$SESSION_SKILLS")"
TDD_CHK="$(skill_check 'tdd' "$SESSION_SKILLS")"
VERIF_CHK="$(skill_check 'verification' "$SESSION_SKILLS")"

LINE2="${BRAIN_CHK}brain ${TDD_CHK}tdd ${VERIF_CHK}verif"

# Batch progress
if [ -n "$BATCH_COUNTER" ] && [ "$BATCH_COUNTER" -gt 0 ] 2>/dev/null; then
  LINE2="${LINE2} | Task ${BATCH_COUNTER}/3"
fi

# Context bar
CTX_BAR="$(context_bar "$CTX_USED")"
LINE2="${LINE2} | Ctx: ${CTX_BAR}"

# Quota 5h
if [ -n "$QUOTA_5H" ]; then
  QUOTA_INT="${QUOTA_5H%%.*}"
  QUOTA_INT="${QUOTA_INT//[!0-9]/}"
  QUOTA_INT="${QUOTA_INT:-0}"
  QUOTA_COLOR="$GREEN"
  if [ "$QUOTA_INT" -ge 90 ]; then
    QUOTA_COLOR="$RED"
  elif [ "$QUOTA_INT" -ge 70 ]; then
    QUOTA_COLOR="$YELLOW"
  fi
  LINE2="${LINE2} | 5h: ${QUOTA_COLOR}${QUOTA_INT}%${RESET}"
fi

# Prepend warnings
if [ -n "$WARN_STR" ]; then
  LINE2="${WARN_STR} | ${LINE2}"
fi

# --- 8. Output ---
printf '%b\n' "$LINE1"
printf '%b\n' "$LINE2"
