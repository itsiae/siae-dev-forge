#!/usr/bin/env bash
# sync-semgrep-registry.sh — mirror local Semgrep community rulesets
#
# Wave 1 follow-up task-03 (EC-21): mirror community packs in rules/semgrep/vendored/
# per non dipendere da registry online runtime. Idempotente.
#
# Usage: scripts/sync-semgrep-registry.sh
# Env:   VENDOR_DIR (default: rules/semgrep/vendored)
#        LOCK_FILE  (default: rules/semgrep/siae/version.lock)
set -euo pipefail

VENDOR_DIR="${VENDOR_DIR:-rules/semgrep/vendored}"
LOCK_FILE="${LOCK_FILE:-rules/semgrep/siae/version.lock}"
RULESETS=(
  "p/owasp-top-ten"
  "p/javascript"
  "p/typescript"
  "p/jwt"
  "p/xss"
  "p/sql-injection"
)

mkdir -p "$VENDOR_DIR"

require() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required tool: $1" >&2; exit 1; }
}
require semgrep
require curl

# Cross-platform sha256
hash_cmd() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum | awk '{print $1}'
  else
    shasum -a 256 | awk '{print $1}'
  fi
}

# Cross-platform sed -i (BSD vs GNU)
sed_i() {
  if sed --version >/dev/null 2>&1; then
    sed -i "$@"
  else
    sed -i '' "$@"
  fi
}

today=$(date -u +%Y-%m-%d)
if [[ -f "$LOCK_FILE" ]]; then
  sed_i "s/^community_rulesets_last_sync=.*/community_rulesets_last_sync=${today}/" "$LOCK_FILE"
fi

for rs in "${RULESETS[@]}"; do
  fname="${rs/\//-}.yaml"
  out="$VENDOR_DIR/$fname"
  echo "Syncing $rs → $out"
  # Best-effort fetch via semgrep registry HTTP endpoint
  if curl -fsSL "https://semgrep.dev/c/${rs}" -o "$out.tmp" 2>/dev/null; then
    if [[ -s "$out.tmp" ]]; then
      mv "$out.tmp" "$out"
      hash=$(cat "$out" | hash_cmd)
      key="community_rulesets_sha256_${rs/\//-}"
      if [[ -f "$LOCK_FILE" ]]; then
        if grep -q "^${key}=" "$LOCK_FILE"; then
          sed_i "s|^${key}=.*|${key}=${hash}|" "$LOCK_FILE"
        else
          echo "${key}=${hash}" >> "$LOCK_FILE"
        fi
      fi
      echo "  ✓ $rs ($(wc -c < "$out") bytes, sha256=${hash:0:12}...)"
    else
      echo "  ⚠️  $rs: empty response, skipped" >&2
      rm -f "$out.tmp"
    fi
  else
    echo "  ⚠️  $rs: curl failed, skipped" >&2
  fi
done

echo "Sync completato: ${#RULESETS[@]} rulesets in $VENDOR_DIR"
