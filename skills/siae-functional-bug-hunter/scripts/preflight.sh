#!/usr/bin/env bash
# preflight.sh — phase 0 environment check for functional-bug-hunter.
#
# Read-only. Verifies bash >= 4 (with POSIX fallback path), python3 >= 3.9,
# jq >= 1.6 (or marks Python fallback path), git availability, tree-sitter
# grammars discoverability.
#
# Output: a single JSON object on stdout describing the detected environment.
# Exit code: 0 always (a failed check is reported in the JSON, not via
# exit code; the caller decides how to react per runtime mode).
#
# Usage: scripts/preflight.sh
#
# This script never writes to the target repository and performs no
# outbound network calls.

set -u  # NOTE: no -e: we want soft checks. We capture and report.

shell_version="${BASH_VERSION:-unknown}"
bash_major="${shell_version%%.*}"
if [ -z "$bash_major" ] || ! [ "$bash_major" -ge 4 ] 2>/dev/null; then
  bash_ok=false
  bash_fallback="posix"
else
  bash_ok=true
  bash_fallback="none"
fi

# Python check
if command -v python3 >/dev/null 2>&1; then
  py_ver="$(python3 -c 'import sys; print("{}.{}".format(sys.version_info[0], sys.version_info[1]))' 2>/dev/null || echo "unknown")"
  py_major="${py_ver%%.*}"
  py_minor="${py_ver#*.}"
  if [ "$py_major" = "3" ] && [ "$py_minor" -ge 9 ] 2>/dev/null; then
    py_ok=true
  else
    py_ok=false
  fi
else
  py_ver="missing"
  py_ok=false
fi

# jq check
if command -v jq >/dev/null 2>&1; then
  jq_ver="$(jq --version 2>/dev/null | sed 's/^jq-//')"
  jq_major="${jq_ver%%.*}"
  jq_minor="${jq_ver#*.}"
  jq_minor="${jq_minor%%.*}"
  if [ "$jq_major" = "1" ] && [ "$jq_minor" -ge 6 ] 2>/dev/null; then
    jq_ok=true
    jq_path="full"
  else
    jq_ok=false
    jq_path="python-fallback"
  fi
else
  jq_ver="missing"
  jq_ok=false
  jq_path="python-fallback"
fi

# git check
if command -v git >/dev/null 2>&1; then
  git_ver="$(git --version 2>/dev/null | awk '{print $3}')"
  git_ok=true
else
  git_ver="missing"
  git_ok=false
fi

# tree-sitter check (best effort — grammar packaging varies by environment).
# We probe the npm-style `tree-sitter` CLI and the Python `tree_sitter` module.
ts_cli="missing"
ts_py="missing"
if command -v tree-sitter >/dev/null 2>&1; then
  ts_cli="$(tree-sitter --version 2>/dev/null | head -1)"
fi
if [ "$py_ok" = true ]; then
  if python3 -c 'import tree_sitter' >/dev/null 2>&1; then
    ts_py="present"
  fi
fi
if [ "$ts_cli" = "missing" ] && [ "$ts_py" = "missing" ]; then
  ts_ok=false
  ts_mode="regex-fallback"
else
  ts_ok=true
  ts_mode="tree-sitter"
fi

# Emit JSON. We avoid shelling out to jq here so this script works even
# when jq is missing.
cat <<JSON
{
  "bash": { "version": "${shell_version}", "ok": ${bash_ok}, "fallback": "${bash_fallback}" },
  "python": { "version": "${py_ver}", "ok": ${py_ok} },
  "jq": { "version": "${jq_ver}", "ok": ${jq_ok}, "path": "${jq_path}" },
  "git": { "version": "${git_ver}", "ok": ${git_ok} },
  "tree_sitter": { "cli": "${ts_cli}", "python": "${ts_py}", "ok": ${ts_ok}, "mode": "${ts_mode}" },
  "overall_ok": $([ "$py_ok" = true ] && echo true || echo false)
}
JSON

exit 0
