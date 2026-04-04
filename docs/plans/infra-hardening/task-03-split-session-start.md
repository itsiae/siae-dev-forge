# Task 03: Split session-start (D3)

**Deliverable:** D3
**Dipendenze:** Task 01 (DEVFORGE_STATE_DIR)
**File coinvolti:** `hooks/session-start`, nuovo `hooks/session-maintenance`

---

## Step 1 — Leggi session-start e identifica le 6 fasi

```bash
wc -l hooks/session-start
```

Identifica le sezioni: (A) Statusline, (B) MCP setup, (C) Banner, (D) Version check, (E) Context injection, (F) Telemetria.

## Step 2 — Crea `hooks/session-maintenance`

Nuovo file `hooks/session-maintenance`:

```bash
#!/usr/bin/env bash
# session-maintenance — Async post-startup tasks
# ─────────────────────────────────────────────────
# Lanciato in background da session-start.
# Non deve produrre output su stdout (romperebbe il JSON).
# Errori vanno in DEVFORGE_STATE_DIR/devforge-maintenance.log.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Source logger for DEVFORGE_STATE_DIR and logging
source "${PLUGIN_ROOT}/lib/logger.sh"

MAINT_LOG="${DEVFORGE_STATE_DIR}/devforge-maintenance.log"
exec 2>>"$MAINT_LOG"

# ── (A) Statusline install (da session-start:24) ──
bash "${PLUGIN_ROOT}/statusline/install.sh" 2>/dev/null || true

# ── (B) MCP setup (da session-start:27-30) ──
bash "${PLUGIN_ROOT}/hooks/setup-mcp-kibana" 2>/dev/null &
bash "${PLUGIN_ROOT}/hooks/setup-mcp-sport" 2>/dev/null &

# ── (D) Version check + auto-update (da session-start:48-83) ──
PLUGIN_VERSION=$(grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' "${PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | head -1 | sed 's/.*"version"[[:space:]]*:[[:space:]]*"//;s/"$//' || echo "unknown")
if command -v gh >/dev/null 2>&1 && [ "$PLUGIN_VERSION" != "unknown" ] && [ "${DEVFORGE_SKIP_UPDATE:-}" != "1" ]; then
    LATEST_TAG=$(gh release list --repo itsiae/siae-dev-forge --limit 1 --json tagName --jq '.[0].tagName' 2>/dev/null || echo "")
    LATEST_VERSION="${LATEST_TAG#v}"
    if [ -n "$LATEST_VERSION" ] && echo "$LATEST_VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$'; then
        if printf '1.0\n2.0' | sort -V >/dev/null 2>&1; then
            if [ "$PLUGIN_VERSION" != "$LATEST_VERSION" ] && \
               [ "$(printf '%s\n%s' "$PLUGIN_VERSION" "$LATEST_VERSION" | sort -V | tail -1)" = "$LATEST_VERSION" ]; then
                (MARKETPLACE_DIR="${HOME}/.claude/plugins/marketplaces/siae-devforge"; \
                [ -d "$MARKETPLACE_DIR/.git" ] && git -C "$MARKETPLACE_DIR" pull origin main --ff-only >/dev/null 2>&1; \
                rm -rf "${HOME}/.claude/plugins/cache/siae-devforge" 2>/dev/null; \
                claude plugin update "siae-devforge@siae-devforge" >/dev/null 2>&1) &
            fi
        fi
    fi
fi

# ── (F) Telemetria + session state (da session-start:174-228) ──
# Log session start event
START_NS=$(cat "${DEVFORGE_STATE_DIR}/.devforge-session-start-ns" 2>/dev/null || echo "0")
devforge_log_timed "session_start" "success" "$START_NS" "{\"project_dir\":\"$(pwd)\",\"plugin_version\":\"${PLUGIN_VERSION}\"}" 2>/dev/null || true

# Save session start timestamp
echo "$(date +%s%N 2>/dev/null || echo '0')" > "${DEVFORGE_STATE_DIR}/.devforge-session-start-ns"

# Cache resolved user
RESOLVED_USER=$(devforge_get_user)
echo "$RESOLVED_USER" > "${DEVFORGE_STATE_DIR}/.devforge-user"

# PR merge detection (last 24h)
if command -v gh >/dev/null 2>&1 && command -v jq >/dev/null 2>&1; then
    GH_REPO=$(git remote get-url origin 2>/dev/null \
        | sed 's/\.git$//' | grep -oE '[^/:]+/[^/]+$' || echo "")
    if [ -n "$GH_REPO" ]; then
        MERGED_PRS=$(gh pr list --repo "$GH_REPO" --state merged --author "@me" \
            --json number,mergedAt,createdAt,reviews \
            --jq '[.[] | select((.mergedAt | fromdateiso8601) > (now - 86400))]' 2>/dev/null || echo "[]")
        if [ "$MERGED_PRS" != "[]" ] && [ -n "$MERGED_PRS" ]; then
            echo "$MERGED_PRS" | jq -c '.[]' 2>/dev/null | while IFS= read -r pr; do
                PR_NUMBER=$(echo "$pr" | jq -r '.number' 2>/dev/null || echo "0")
                devforge_log "pr_merged" "success" "{\"pr_number\":${PR_NUMBER}}" 2>/dev/null || true
            done
        fi
    fi
fi

# Session lock
SESSION_LOCK_FILE="${DEVFORGE_STATE_DIR}/.devforge-session-lock"
CURRENT_PID=$$
if [ -f "$SESSION_LOCK_FILE" ]; then
    OLD_PID=$(cat "$SESSION_LOCK_FILE" 2>/dev/null || echo "0")
    if kill -0 "$OLD_PID" 2>/dev/null && [ "$OLD_PID" != "$CURRENT_PID" ]; then
        devforge_log "session_start" "warning" "{\"reason\":\"concurrent_session_detected\",\"old_pid\":${OLD_PID},\"new_pid\":${CURRENT_PID}}" 2>/dev/null || true
    fi
fi
echo "$CURRENT_PID" > "$SESSION_LOCK_FILE"

wait  # attendi MCP setup background
```

Dopo aver creato `session-maintenance`, rimuovere da `session-start` le righe 23-30 (statusline, MCP), 48-83 (version check), 174-229 (telemetria, user, PR merge, lock). Mantenere solo: shebang, set, PLUGIN_ROOT, source logger, banner (righe 32-46), context injection (righe 85-172), e in coda il lancio async.

## Step 3 — Riduci session-start

`hooks/session-start` mantiene solo:
- Shebang + set -euo pipefail
- Source logger.sh
- (C) Banner stderr
- (E) Context injection (skill catalog, using-devforge, branching check)
- Output JSON `additional_context`
- Lancio async: `bash "${PLUGIN_ROOT}/hooks/session-maintenance" &`

Target: ~60 righe.

## Step 4 — Rendi session-maintenance eseguibile

```bash
chmod +x hooks/session-maintenance
```

## Step 5 — Test

```bash
# Verifica che session-start produce JSON valido velocemente
time (echo '{}' | bash hooks/session-start 2>/dev/null | python3 -m json.tool > /dev/null)
```
Output atteso: JSON valido, tempo <1s.

```bash
# Verifica che session-maintenance non crasha
bash hooks/session-maintenance 2>&1 && echo "OK" || echo "FAIL"
```
Output atteso: OK (o errori non-fatali loggati in maintenance.log).

## Step 6 — Commit

```bash
git add hooks/session-start hooks/session-maintenance
git commit -m "refactor(hooks): split session-start into bootstrap + async maintenance

- session-start now only does banner + context injection (<1s)
- session-maintenance handles statusline, MCP, version check, telemetry
- Maintenance runs in background, errors go to devforge-maintenance.log

Co-Authored-By: SIAE DevForge"
```
