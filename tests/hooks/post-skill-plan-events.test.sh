#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Setup: sandbox repo temp + design doc fresco
TMP=$(mktemp -d)
export DEVFORGE_LOG_FILE="${TMP}/activity.jsonl"
export DEVFORGE_SESSION_DIR="${TMP}/session"
mkdir -p "${DEVFORGE_SESSION_DIR}"
export DEVFORGE_FORCE_BASH_FALLBACK=1

cd "$TMP"
git init -q
git config user.email "t@t.l"
git config user.name "T"
mkdir -p docs/plans
cat > docs/plans/2026-04-21-test-design.md <<'FM'
---
title: Test design
date: 2026-04-21
status: proposed
---
# Test design
FM

# Simula invocazione siae-brainstorming
HOOK_INPUT='{"tool_name":"Skill","tool_input":{"skill":"siae-devforge:siae-brainstorming","args":""}}'
echo "$HOOK_INPUT" | bash "${PLUGIN_ROOT}/hooks/post-skill" >/dev/null 2>&1 || true

# Assert: plan_created è nel log
if ! grep -q '"event":"plan_created"' "$DEVFORGE_LOG_FILE"; then
    echo "FAIL: plan_created missing after siae-brainstorming"
    cat "$DEVFORGE_LOG_FILE"
    exit 1
fi

# Assert: plan_path nel meta
if ! grep -q '"plan_path":"docs/plans/2026-04-21-test-design.md"' "$DEVFORGE_LOG_FILE"; then
    echo "FAIL: plan_path missing or wrong"
    grep '"event":"plan_created"' "$DEVFORGE_LOG_FILE"
    exit 1
fi

echo "PASS: plan_created emitted"

# Step 2: plan_approved dopo siae-writing-plans con status:approved
sed -i.bak 's/status: proposed/status: approved/' docs/plans/2026-04-21-test-design.md
HOOK_INPUT2='{"tool_name":"Skill","tool_input":{"skill":"siae-devforge:siae-writing-plans","args":""}}'
echo "$HOOK_INPUT2" | bash "${PLUGIN_ROOT}/hooks/post-skill" >/dev/null 2>&1 || true

if ! grep -q '"event":"plan_approved"' "$DEVFORGE_LOG_FILE"; then
    echo "FAIL: plan_approved missing after siae-writing-plans on approved plan"
    exit 1
fi

echo "PASS: plan_approved emitted"

# Step 3: no plan_approved se status=proposed
rm -f "$DEVFORGE_LOG_FILE"
sed -i.bak 's/status: approved/status: proposed/' docs/plans/2026-04-21-test-design.md
echo "$HOOK_INPUT2" | bash "${PLUGIN_ROOT}/hooks/post-skill" >/dev/null 2>&1 || true

if grep -q '"event":"plan_approved"' "$DEVFORGE_LOG_FILE"; then
    echo "FAIL: plan_approved emitted even with status=proposed"
    exit 1
fi

echo "PASS: plan_approved correctly skipped on proposed"

# Step 4: skip se design doc piu' vecchio di PLAN_EVENT_WINDOW_SEC (60s)
rm -f "$DEVFORGE_LOG_FILE"
# Imposta mtime a 3 minuti fa (cross-OS: GNU coreutils -d + BSD -A fallback + touch -t absolute)
STALE_FILE="docs/plans/2026-04-21-test-design.md"
STALED=0
# Order: touch -t (POSIX, most portable) -> BSD touch -A -> GNU touch -d
OLD_TS=$(date -v-3M +%Y%m%d%H%M.%S 2>/dev/null || date -d "3 minutes ago" +%Y%m%d%H%M.%S 2>/dev/null || echo "")
if [ -n "$OLD_TS" ] && touch -t "$OLD_TS" "$STALE_FILE" 2>/dev/null; then
    STALED=1
elif touch -A -0300 "$STALE_FILE" 2>/dev/null; then
    # BSD touch: -A [-][[hh]mm]SS -> indietro 3 minuti = 03 minuti 00 sec
    STALED=1
elif touch -d "3 minutes ago" "$STALE_FILE" 2>/dev/null; then
    STALED=1
fi

# Verify file is actually stale (age > PLAN_EVENT_WINDOW_SEC = 60s)
if [ "$STALED" -eq 1 ]; then
    _mtime=$(stat -f %m "$STALE_FILE" 2>/dev/null || stat -c %Y "$STALE_FILE" 2>/dev/null || echo 0)
    _age=$(( $(date +%s) - _mtime ))
    if [ "$_age" -le 60 ]; then
        STALED=0
    fi
fi

if [ "$STALED" -eq 0 ]; then
    echo "WARN: cannot stale file mtime on this platform, skipping step 4"
else
    HOOK_INPUT3='{"tool_name":"Skill","tool_input":{"skill":"siae-devforge:siae-brainstorming","args":""}}'
    echo "$HOOK_INPUT3" | bash "${PLUGIN_ROOT}/hooks/post-skill" >/dev/null 2>&1 || true

    if grep -q '"event":"plan_created"' "$DEVFORGE_LOG_FILE"; then
        echo "FAIL: plan_created emitted for stale design doc (>60s)"
        cat "$DEVFORGE_LOG_FILE"
        exit 1
    fi
    echo "PASS: plan_created correctly skipped on stale doc"
fi
