#!/usr/bin/env bash
# wordcount.sh — count prose words in a Markdown file,
# excluding YAML frontmatter (top-of-file `---` block) and fenced code
# blocks (``` … ```).
#
# Used by Quality Bar #1: SKILL.md prose body must be in [1500, 2500].
#
# Usage: tools/wordcount.sh <path-to-markdown>
# Output (stdout): single integer (prose word count).
# Exit code: 0 on success, non-zero on missing input.

set -eu

if [ "$#" -lt 1 ]; then
  echo "usage: $0 <markdown-file>" >&2
  exit 2
fi

if [ ! -f "$1" ]; then
  echo "file not found: $1" >&2
  exit 2
fi

awk '
  BEGIN { in_fm=0; in_code=0; fm_seen=0; w=0 }
  /^---$/ {
    if (fm_seen==0) { in_fm=1; fm_seen=1; next }
    else if (in_fm==1) { in_fm=0; next }
  }
  /^```/ { in_code = !in_code; next }
  in_fm==1 { next }
  in_code==1 { next }
  {
    n = split($0, arr, /[[:space:]]+/)
    for (i=1; i<=n; i++) {
      if (arr[i] != "") w++
    }
  }
  END { print w }
' "$1"
