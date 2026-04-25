# Task 11 — Implementare hooks/devforge-context (fusione 3 hook, TDD)

**Stato:** [PENDING]
**Execution:** in-session (TDD stretto)
**Dipendenze:** T01 (centralizations, per checkpoint-schema)
**Durata stimata:** 25 min

## Goal

Creare hook `hooks/devforge-context` che fonde le responsabilità di `user-prompt-context` + `devforge-reinject` + `devforge-context-always` con:
- **Budget 2KB per iniezione** (hard cap)
- **Diff-based reinject** (hash stato → skip se invariato)
- **Tier-based tags** (default no-tag, IMPORTANT se gate violato recente, EXTREMELY_IMPORTANT solo se hard-gate attivo)
- **Adaptive interval** (skip se task-skills complete per task corrente)
- Telemetria: `prompt_injection_emitted` evento con `size_bytes` + `tier`

`batch-reset` resta standalone (responsabilità diversa).

## State file nuovo

`~/.claude/.devforge-last-injection-hash` — singolo hash SHA-256 del payload emesso ultimo. Next injection confronta: se stesso hash → output `{}`.

## Tier logic

```
tier = 'none'                  # default
if recent_gate_violation:      # <60s dall'ultimo block
    tier = 'important'
if active_hard_gate:           # verification|tdd|git-workflow missing e richiesto
    tier = 'extreme'
```

## Step TDD

### Step 1 — RED: scrivi test PRIMA

File: `tests/hooks/test_devforge_context.sh`

```bash
#!/usr/bin/env bash
set -eu
cd "$(git rev-parse --show-toplevel)"
PASS=0; FAIL=0
_assert() {
    local name="$1"; local cmd="$2"
    if eval "$cmd" >/dev/null 2>&1; then echo "  PASS  $name"; PASS=$((PASS+1))
    else echo "  FAIL  $name"; FAIL=$((FAIL+1)); fi
}

HOOK=hooks/devforge-context
export HOME=$(mktemp -d); mkdir -p "$HOME/.claude"
trap 'rm -rf "$HOME"' EXIT

_assert "hook exists and executable" "[ -x $HOOK ]"

echo ""
echo "=== Budget: first emission <= 2048 bytes ==="
OUT1=$(echo '{}' | bash $HOOK 2>/dev/null || true)
SIZE1=$(printf '%s' "$OUT1" | wc -c | tr -d ' ')
_assert "first emission <= 2048 bytes (actual=$SIZE1)" "[ $SIZE1 -le 2048 ]"
_assert "first emission non-empty" "[ $SIZE1 -gt 10 ]"

echo ""
echo "=== Diff-based: 2nd emission same state = empty/minimal ==="
OUT2=$(echo '{}' | bash $HOOK 2>/dev/null || true)
SIZE2=$(printf '%s' "$OUT2" | wc -c | tr -d ' ')
_assert "2nd same-state emission <= 20 bytes (actual=$SIZE2)" "[ $SIZE2 -le 20 ]"

echo ""
echo "=== Diff-based: hash changes trigger new emission ==="
# Simulate state change: touch session-skills
echo "siae-tdd" > "$HOME/.claude/.devforge-session-skills"
OUT3=$(echo '{}' | bash $HOOK 2>/dev/null || true)
SIZE3=$(printf '%s' "$OUT3" | wc -c | tr -d ' ')
_assert "state change re-emits (actual=$SIZE3)" "[ $SIZE3 -gt 20 ]"

echo ""
echo "=== Tier policy: default NO EXTREMELY_IMPORTANT ==="
OUT_DEFAULT=$(echo '{}' | bash $HOOK 2>/dev/null || true)
_assert "default output has no EXTREMELY_IMPORTANT tag" \
    "! echo '$OUT_DEFAULT' | grep -q EXTREMELY_IMPORTANT"

echo ""
echo "=== Telemetry: logs prompt_injection_emitted event ==="
export DEVFORGE_LOG_FILE="$HOME/.claude/test-activity.jsonl"
: > "$DEVFORGE_LOG_FILE"
# trigger a new emission (change state)
rm -f "$HOME/.claude/.devforge-session-skills"
echo '{}' | bash $HOOK >/dev/null 2>&1 || true
_assert "prompt_injection_emitted event logged" \
    "grep -q prompt_injection_emitted $DEVFORGE_LOG_FILE"

echo ""
echo "=== JSON output valid ==="
OUT_JSON=$(echo '{}' | bash $HOOK 2>/dev/null || true)
if [ -n "$OUT_JSON" ] && [ "$OUT_JSON" != "{}" ]; then
    echo "$OUT_JSON" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null
    _assert "output is valid JSON" "[ $? -eq 0 ]"
else
    echo "  SKIP  output is minimal, JSON check skipped"
fi

echo ""
echo "Total: $((PASS+FAIL)) — PASS: $PASS — FAIL: $FAIL"
exit $FAIL
```

Run pre-implementation:
```bash
bash tests/hooks/test_devforge_context.sh
```
Output atteso: hook non esiste → "hook exists and executable" FAIL → script non prosegue o tutti FAIL.

### Step 2 — GREEN: implementa hooks/devforge-context

File: `hooks/devforge-context`

Esporto scheletro essenziale (l'implementer dettaglia):

```bash
#!/usr/bin/env bash
# devforge-context — unified context injection with budget + diff-based dedup
# ─────────────────────────────────────────────────────────────────
# Replaces: user-prompt-context + devforge-reinject + devforge-context-always
# batch-reset remains separate (different responsibility).
# ─────────────────────────────────────────────────────────────────

set -euo pipefail
export DEVFORGE_CURRENT_HOOK="devforge-context"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${PLUGIN_ROOT}/lib/logger.sh" 2>/dev/null || true
devforge_init_session 2>/dev/null || true

STATE_DIR="${HOME}/.claude"
HASH_FILE="${STATE_DIR}/.devforge-last-injection-hash"
MAX_BYTES=2048

# Compute state hash: skills invoked + branch + gate violations + tdd phase
compute_state_hash() {
    local skills branch tdd_phase gate_violation
    skills=$(cat "${STATE_DIR}/.devforge-session-skills" 2>/dev/null || echo "")
    branch=$(git branch --show-current 2>/dev/null || echo "detached")
    tdd_phase=$(cut -d'|' -f1 < "${STATE_DIR}/.devforge-tdd-state" 2>/dev/null || echo "")
    # Recent block (<60s): check stop-block-count mtime
    gate_violation=0
    if [ -f "${STATE_DIR}/.devforge-stop-block-count" ]; then
        local mtime now
        mtime=$(stat -f%m "${STATE_DIR}/.devforge-stop-block-count" 2>/dev/null || stat -c%Y "${STATE_DIR}/.devforge-stop-block-count" 2>/dev/null || echo 0)
        now=$(date +%s)
        [ $((now - mtime)) -lt 60 ] && gate_violation=1
    fi
    printf '%s|%s|%s|%s' "$skills" "$branch" "$tdd_phase" "$gate_violation" | shasum | cut -d' ' -f1
}

CURRENT_HASH=$(compute_state_hash)
LAST_HASH=$(cat "$HASH_FILE" 2>/dev/null || echo "")

# Diff-based: skip if state unchanged
if [ "$CURRENT_HASH" = "$LAST_HASH" ]; then
    exit 0
fi

# Determine tier
TIER="none"
TAG_OPEN=""
TAG_CLOSE=""
if [ -f "${STATE_DIR}/.devforge-stop-block-count" ]; then
    local mtime now
    mtime=$(stat -f%m "${STATE_DIR}/.devforge-stop-block-count" 2>/dev/null || stat -c%Y "${STATE_DIR}/.devforge-stop-block-count" 2>/dev/null || echo 0)
    now=$(date +%s)
    if [ $((now - mtime)) -lt 60 ]; then
        TIER="important"
        TAG_OPEN="<IMPORTANT>"
        TAG_CLOSE="</IMPORTANT>"
    fi
fi
# Tier 'extreme' riserved for active hard-gate; in PR #1 we don't escalate here.

# Build compact payload (max $MAX_BYTES bytes)
PAYLOAD=""
# 1. Git state (1 line)
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    GIT_BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")
    GIT_LAST=$(git log --oneline -1 2>/dev/null || echo "")
    PAYLOAD="${PAYLOAD}Git: branch=${GIT_BRANCH} | ${GIT_LAST}\n"
fi
# 2. Session stats (1 line)
SKILLS_COUNT=$(cat "${STATE_DIR}/.devforge-session-skills" 2>/dev/null | tr ',' '\n' | grep -c . || echo 0)
COMMITS_COUNT=$(cat "${STATE_DIR}/.devforge-session-commits" 2>/dev/null || echo 0)
PAYLOAD="${PAYLOAD}Session: skills=${SKILLS_COUNT} | commits=${COMMITS_COUNT}\n"
# 3. Backbone 1-liner (compact)
PAYLOAD="${PAYLOAD}Backbone: brainstorm→plan→tdd→verification. If 1% applicable, invoke skill.\n"

# Trim to budget
PAYLOAD=$(printf '%.*s' "$MAX_BYTES" "$PAYLOAD")

# Escape for JSON
escape_for_json() {
    local s="$1"
    s="${s//\\/\\\\}"; s="${s//\"/\\\"}"; s="${s//$'\n'/\\n}"
    printf '%s' "$s"
}
PAYLOAD_ESCAPED=$(escape_for_json "$PAYLOAD")

# Final context with optional tier tag
if [ -n "$TAG_OPEN" ]; then
    CONTEXT="${TAG_OPEN}\\n[DevForge Context]\\n${PAYLOAD_ESCAPED}${TAG_CLOSE}"
else
    CONTEXT="[DevForge Context]\\n${PAYLOAD_ESCAPED}"
fi

# Telemetry
SIZE=$(printf '%s' "$CONTEXT" | wc -c | tr -d ' ')
devforge_log "prompt_injection_emitted" "success" "{\"size_bytes\":${SIZE},\"tier\":\"${TIER}\"}" 2>/dev/null || true

# Store hash
echo "$CURRENT_HASH" > "${HASH_FILE}.tmp" && mv "${HASH_FILE}.tmp" "$HASH_FILE"

cat <<EOF
{
  "additional_context": "${CONTEXT}",
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "${CONTEXT}"
  }
}
EOF
exit 0
```

### Step 3 — Verifica GREEN

```bash
chmod +x hooks/devforge-context
bash tests/hooks/test_devforge_context.sh
```
Output atteso: `Total: ~8 — PASS: 8 — FAIL: 0`.

### Step 4 — Run full regression

```bash
bash tests/compression-regression/assert_injection_reduction.sh
```
Output atteso: tutti PASS (ora hook esiste e rispetta budget).

### Step 5 — Commit

```bash
git add hooks/devforge-context tests/hooks/test_devforge_context.sh
git commit -m "feat(hooks): add devforge-context with budget + diff-based dedup (TDD)

Part of PR #1 anti-dilution (ADR-004 Prompt Injection Budget).
Replaces functionally: user-prompt-context + devforge-reinject + devforge-context-always.
- Max 2KB per emission
- Diff-based: skip if state hash unchanged
- Tier-based tags (none default, IMPORTANT if gate violation <60s)
- Telemetry: prompt_injection_emitted event with size_bytes + tier

batch-reset remains standalone (separate responsibility).
Hook registration in hooks.json: T12."
```

## Acceptance

- [ ] `tests/hooks/test_devforge_context.sh` scritto prima dell'hook (RED)
- [ ] `hooks/devforge-context` implementato e passa tutti i test (GREEN)
- [ ] Prima emissione ≤2KB
- [ ] Seconda emissione stesso stato ≤20 bytes (dedup)
- [ ] Default output senza EXTREMELY_IMPORTANT tag
- [ ] Evento `prompt_injection_emitted` presente nel log
- [ ] `assert_injection_reduction.sh` tutto PASS
- [ ] Commit `feat(hooks):`
