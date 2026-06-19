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

# Initialize session context for token/telemetry reads
PLUGIN_ROOT_INIT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." 2>/dev/null && pwd)"
if [ -f "${PLUGIN_ROOT_INIT}/lib/logger.sh" ]; then
    source "${PLUGIN_ROOT_INIT}/lib/logger.sh" 2>/dev/null || true
    devforge_init_session 2>/dev/null || true
fi

# Cache git keyed per-cwd: evita contaminazione cross-repo/sessione (#1)
# cksum (POSIX) → CRC+byte-count; tr+cut danno una key numerica (≤12 cifre, lunghezza
# variabile ma deterministica per cwd). Cache best-effort: una collisione (prob. trascurabile)
# si auto-sana al refresh TTL 5s. Fallback "default" se cksum manca.
_cwd_key="$(printf '%s' "$PWD" | cksum 2>/dev/null | tr -dc '0-9' | cut -c1-12)"
_cwd_key="${_cwd_key:-default}"
CACHE_FILE="${DEVFORGE_DIR}/.devforge-git-cache-${_cwd_key}"
unset _cwd_key

CTX_USED="0"
QUOTA_5H=""
AGENT_NAME=""

STDIN_JSON=""
if [ ! -t 0 ]; then
  # `[ ! -t 0 ]` returns true even when stdin is open but has no data
  # (e.g. Claude Code opens the status line command with stdin connected
  # but does not write to it). In that case, `cat` blocks indefinitely
  # waiting for EOF. Fix: use `read -t` with timeout — exits immediately
  # when no data arrives within the timeout window.
  #
  # Assumption: JSON is written atomically (single line or rapid burst).
  # A line arriving after the timeout is silently dropped; this is
  # acceptable since Claude Code emits compact single-line JSON.
  #
  # Bash 3.2 (macOS default, GPLv2) does not support decimal read timeouts
  # — only integers are valid. Bash 4.0+ supports decimals for lower latency.
  # Note: 2>/dev/null intentionally suppresses "invalid timeout specification"
  # warnings emitted by bash 3.2 when a decimal value is attempted.
  _bash_major="${BASH_VERSINFO[0]}"
  if [ "${_bash_major}" -ge 4 ] 2>/dev/null; then
    _read_timeout="0.3"
  else
    _read_timeout="1"
  fi
  _stdin_buf=""
  if IFS= read -r -t "${_read_timeout}" _stdin_buf 2>/dev/null; then
    STDIN_JSON="$_stdin_buf"
    while IFS= read -r -t "${_read_timeout}" _stdin_buf 2>/dev/null; do
      STDIN_JSON="${STDIN_JSON}"$'\n'"${_stdin_buf}"
    done
  fi
  unset _stdin_buf _read_timeout _bash_major
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

# Token stats from session dir
SESSION_TOKENS=""
SESSION_COST=""
if [ -n "$DEVFORGE_SESSION_DIR" ] && [ -f "${DEVFORGE_SESSION_DIR}/token-stats.json" ] && command -v python3 >/dev/null 2>&1; then
    TDATA=$(python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
t=d.get('total',0)
c=d.get('cost_eur',0)
tok=f'{t/1e6:.1f}M' if t>=1e6 else f'{t/1e3:.0f}K' if t>=1e3 else str(t)
print(f'{tok}\t{c:.2f}')
" "${DEVFORGE_SESSION_DIR}/token-stats.json" 2>/dev/null) || true
    if [ -n "$TDATA" ]; then
        SESSION_TOKENS="$(printf '%s' "$TDATA" | cut -f1)"
        SESSION_COST="$(printf '%s' "$TDATA" | cut -f2)"
    fi
fi

# Telemetry status
TELEMETRY_STATUS=""
PLUGIN_ROOT_SL="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." 2>/dev/null && pwd)"
if [ -f "${PLUGIN_ROOT_SL}/lib/telemetry-upload.sh" ]; then
    source "${PLUGIN_ROOT_SL}/lib/telemetry-upload.sh" 2>/dev/null || true
    PENDING=$(devforge_pending_count 2>/dev/null || echo "0")
    if [ "$PENDING" -gt 0 ] 2>/dev/null; then
        TELEMETRY_STATUS="pending:${PENDING}"
    fi
fi

# Batch counter and checkpoint (written by hooks/batch-checkpoint)
BATCH_COUNTER="$(read_file "${DEVFORGE_DIR}/.devforge-batch-counter")"
BATCH_COUNTER="${BATCH_COUNTER//[!0-9]/}"
BATCH_CHECKPOINT=0
if [ -f "${DEVFORGE_DIR}/.devforge-batch-checkpoint" ]; then
  BATCH_CHECKPOINT=1
fi

# Plugin update flag (scritto da hooks/session-start su cambio versione)
PLUGIN_UPDATED_VER=""
if [ -n "${DEVFORGE_SESSION_DIR:-}" ] && [ -f "${DEVFORGE_SESSION_DIR}/.plugin-updated" ]; then
  read -r PLUGIN_UPDATED_VER < "${DEVFORGE_SESSION_DIR}/.plugin-updated" 2>/dev/null || true
fi
# Sanitize per printf %b (rimuove backslash e caratteri non-versione)
PLUGIN_UPDATED_VER="${PLUGIN_UPDATED_VER//[^0-9a-zA-Z.-]/}"

# Versione plugin per il label (A/B): semver da basename PLUGIN_ROOT_SL, altrimenti dev-mode
PLUGIN_LABEL_VER=""
PLUGIN_IS_DEV=0
_pv="$(basename "$PLUGIN_ROOT_SL" 2>/dev/null)"
if printf '%s' "$_pv" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
  PLUGIN_LABEL_VER="$_pv"
else
  PLUGIN_IS_DEV=1
fi
unset _pv

# Salute telemetria (C): sentinel scritto da logger.sh quando il path fsync degrada a bash
TELEMETRY_DOT=""
if [ -f "${DEVFORGE_DIR}/.devforge-no-fsync-warned" ]; then
  TELEMETRY_DOT="🟡"
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
if [ -n "$PLUGIN_LABEL_VER" ]; then
  LINE1="${LINE1} v${PLUGIN_LABEL_VER}"
elif [ "$PLUGIN_IS_DEV" -eq 1 ]; then
  LINE1="${LINE1} (dev)"
fi
if [ -n "$TELEMETRY_DOT" ]; then
  LINE1="${LINE1} ${TELEMETRY_DOT}"
fi

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

if [ -n "$SESSION_TOKENS" ]; then
    LINE1="${LINE1} | ${SESSION_TOKENS} tok"
    if [ -n "$SESSION_COST" ] && [ "$SESSION_COST" != "0.00" ]; then
        LINE1="${LINE1} ~${SESSION_COST}€"
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

# python3 assente: token-stats e telemetria zero-loss degradano silenziosamente.
# Rilevazione live (non via marker): resta visibile finché Python non è installato.
if ! command -v python3 >/dev/null 2>&1; then
  WARN_STR="${WARN_STR:+$WARN_STR }$(printf '%b🐍 python3 assente — installalo per token/telemetria%b' "$YELLOW" "$RESET")"
fi

# Notifica aggiornamento plugin (verde): persiste per tutta la sessione post-update.
if [ -n "$PLUGIN_UPDATED_VER" ]; then
  WARN_STR="${WARN_STR:+$WARN_STR }$(printf '%b🆙 DevForge aggiornato a v%s%b' "$GREEN" "$PLUGIN_UPDATED_VER" "$RESET")"
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

if [ -n "$TELEMETRY_STATUS" ]; then
    LINE2="${LINE2} | ${YELLOW}telem=${TELEMETRY_STATUS}${RESET}"
fi

# Prepend warnings
if [ -n "$WARN_STR" ]; then
  LINE2="${WARN_STR} | ${LINE2}"
fi

# --- 8. Output ---
printf '%b\n' "$LINE1"
printf '%b\n' "$LINE2"
