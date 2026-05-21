#!/usr/bin/env bash
# check_pluggability.sh — Quality Bar #4
#
# Verifies that the references/stacks/ directory is pluggable: every
# `<id>.md` (except INDEX.md) contains all 10 required sections, AND
# every Tier-1 stack listed in INDEX.md has a corresponding file.
#
# Usage: tools/check_pluggability.sh [path-to-skill-root]
# Default path: the parent directory of this script's parent.
#
# Output: lines prefixed with PASS / FAIL describing each check.
# Exit code: 0 if all checks pass, 1 otherwise.

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_ROOT="${1:-$(cd "$SCRIPT_DIR/.." && pwd)}"
STACKS_DIR="$SKILL_ROOT/references/stacks"
INDEX_FILE="$STACKS_DIR/INDEX.md"

fail=0

if [ ! -d "$STACKS_DIR" ]; then
  echo "FAIL: stacks directory not found: $STACKS_DIR"
  exit 1
fi
if [ ! -f "$INDEX_FILE" ]; then
  echo "FAIL: INDEX.md not found: $INDEX_FILE"
  exit 1
fi

REQUIRED_SECTIONS=(
  "## Stack id"
  "## Manifest fingerprints"
  "## Analysis-unit granularity"
  "## Parser"
  "## Entry-point kinds detected"
  "## Inputs typing"
  "## Side-effect detection"
  "## Cross-stack bridge hints"
  "## Bug-patterns row pointer"
  "## Empty-input branch"
)

# Walk every <id>.md (excluding INDEX.md itself) and check the 10 sections.
for f in "$STACKS_DIR"/*.md; do
  base="$(basename "$f")"
  if [ "$base" = "INDEX.md" ]; then
    continue
  fi
  missing=()
  for sec in "${REQUIRED_SECTIONS[@]}"; do
    if ! grep -Fq "$sec" "$f"; then
      missing+=("$sec")
    fi
  done
  if [ "${#missing[@]}" -gt 0 ]; then
    echo "FAIL: $base missing sections: ${missing[*]}"
    fail=1
  else
    echo "PASS: $base (10/10 sections)"
  fi
done

# Cross-check: every <id>.md in stacks/ is referenced by INDEX.md.
for f in "$STACKS_DIR"/*.md; do
  base="$(basename "$f")"
  if [ "$base" = "INDEX.md" ]; then
    continue
  fi
  if ! grep -Fq "($base)" "$INDEX_FILE"; then
    echo "FAIL: $base not referenced by INDEX.md"
    fail=1
  fi
done

# Cross-check: every reference in INDEX.md points to an existing file.
# We parse markdown link syntax: [label](filename).
REFS=$(grep -Eo '\([a-z0-9_-]+\.md\)' "$INDEX_FILE" | tr -d '()' | sort -u)
for r in $REFS; do
  if [ ! -f "$STACKS_DIR/$r" ]; then
    echo "FAIL: INDEX.md references missing file: $r"
    fail=1
  fi
done

if [ "$fail" -eq 0 ]; then
  echo "PASS check_pluggability: all stacks/ files conform to the 10-section template"
  exit 0
else
  echo "FAIL check_pluggability: see lines above"
  exit 1
fi
