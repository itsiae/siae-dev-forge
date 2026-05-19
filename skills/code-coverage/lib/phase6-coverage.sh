#!/usr/bin/env bash
# phase6-coverage.sh — Coverage run + parse per Phase 6 di /code-coverage.
#
# Risolve framework→cov_cmd via select_command.py, esegue il coverage command
# in modo hardened (NO eval, NO jq), normalizza il report via parse_coverage.py.
#
# G9 (drop jq): parsing JSON via `python3 -c "import json,sys; ..."` (jq optional).
# G11 (eval hardening): esecuzione comando via `bash -c "$COV_CMD"` con cd controllato
#   verso $REPO/$MANIFEST_ROOT (monorepo-safe), NO eval.
#
# Uso:
#   bash skills/code-coverage/lib/phase6-coverage.sh <repo_path>

set -e
set -o pipefail

REPO="${1:?usage: phase6-coverage.sh <repo_path>}"

if [ ! -d "$REPO" ]; then
  echo "ERROR: repo path not found: $REPO" >&2
  exit 1
fi

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# --- Risolve cov_cmd / report_path / format via select_command.py ---
SEL=$(python3 "$SKILL_DIR/scripts/select_command.py" "$REPO")

# Parse JSON con python3 (no jq dependency — G9).
parse_field() {
  local field="$1"
  printf '%s' "$SEL" | python3 -c "
import json, sys
data = json.load(sys.stdin)
val = data.get('${field}', '')
print(val if val is not None else '')
"
}

COV_CMD=$(parse_field "cov_cmd")
REPORT_PATH=$(parse_field "report_path")
FORMAT=$(parse_field "format")
SELECT_ERR=$(parse_field "error")
MANIFEST_ROOT=$(parse_field "manifest_root")

if [ -n "$SELECT_ERR" ]; then
  echo "ERROR: $SELECT_ERR" >&2
  exit 1
fi

if [ -z "$COV_CMD" ]; then
  echo "ERROR: select_command.py returned empty cov_cmd" >&2
  exit 1
fi

# --- Esegui coverage command in modo hardened (G11: NO eval) ---
TARGET_DIR="$REPO"
if [ -n "$MANIFEST_ROOT" ] && [ "$MANIFEST_ROOT" != "." ]; then
  TARGET_DIR="$REPO/$MANIFEST_ROOT"
fi

if [ ! -d "$TARGET_DIR" ]; then
  echo "ERROR: target dir not found: $TARGET_DIR" >&2
  exit 1
fi

mkdir -p "$REPO/.code-coverage"

# Sub-shell isolata, no eval, redirect su tee per stdout.log.
( cd "$TARGET_DIR" && bash -c "$COV_CMD" ) 2>&1 \
  | tee "$REPO/.code-coverage/coverage-stdout.log"

COV_EXIT=${PIPESTATUS[0]}
if [ "$COV_EXIT" -ne 0 ]; then
  # Test runner crash (OOM, classpath, compile error). NON entrare in Phase 7
  # repair loop su sintomo sbagliato. Block 4 + END.
  echo "ERROR: coverage command failed with exit=$COV_EXIT" >&2
  echo "See .code-coverage/coverage-stdout.log for details" >&2
  exit "$COV_EXIT"
fi

# --- Parse report normalizzato → coverage-report.json ---
REPORT_FULL_PATH="$TARGET_DIR/$REPORT_PATH"
if [ ! -e "$REPORT_FULL_PATH" ]; then
  echo "ERROR: coverage report not produced at $REPORT_FULL_PATH" >&2
  exit 1
fi

python3 "$SKILL_DIR/scripts/parse_coverage.py" "$FORMAT" "$REPORT_FULL_PATH" \
  > "$REPO/.code-coverage/coverage-report.json"

echo "[phase6] coverage parsed → .code-coverage/coverage-report.json (format=$FORMAT)"
