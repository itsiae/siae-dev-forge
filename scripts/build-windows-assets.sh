#!/usr/bin/env bash
# Scarica asset upstream x64, calcola SHA256, popola SHA256SUMS.
# Usage: scripts/build-windows-assets.sh <output-dir>
set -euo pipefail

OUT="${1:-dist/windows-assets}"
mkdir -p "$OUT"

GIT_VERSION="2.46.0"
PYTHON_TAG="20240415"
PYTHON_FULL_VERSION="3.12.3"
JQ_VERSION="1.7.1"

download_verify() {
    local url="$1" out="$2"
    echo "-> $url"
    curl -sfL -o "$out" "$url" || { echo "Download $url failed"; exit 1; }
}

# Git installer (per direct-download path)
download_verify \
  "https://github.com/git-for-windows/git/releases/download/v${GIT_VERSION}.windows.1/Git-${GIT_VERSION}-64-bit.exe" \
  "$OUT/Git-${GIT_VERSION}-64-bit.exe"

# PortableGit SFX (per fallback embedded)
download_verify \
  "https://github.com/git-for-windows/git/releases/download/v${GIT_VERSION}.windows.1/PortableGit-${GIT_VERSION}-64-bit.7z.exe" \
  "$OUT/PortableGit-x64.7z.exe"

# Python Standalone (indygreg)
download_verify \
  "https://github.com/indygreg/python-build-standalone/releases/download/${PYTHON_TAG}/cpython-${PYTHON_FULL_VERSION}+${PYTHON_TAG}-x86_64-pc-windows-msvc-shared-install_only.tar.gz" \
  "$OUT/python-standalone-x64.tar.gz"

# jq binary (official)
download_verify \
  "https://github.com/jqlang/jq/releases/download/jq-${JQ_VERSION}/jq-windows-amd64.exe" \
  "$OUT/jq-win64.exe"

# Genera SHA256SUMS
(cd "$OUT" && sha256sum *.exe *.tar.gz > SHA256SUMS)
cat "$OUT/SHA256SUMS"

echo "Asset pronti in $OUT"
