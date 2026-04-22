# Task 02 — pr_opened idempotente via snapshot

**Stato:** [PENDING]
**Stima:** 10 min
**Dipendenze:** Task 01

## Goal

Rendere `pr_opened` idempotente: emesso esattamente 1x per pr_number. Criterio di dedup: **assenza snapshot file** `$HOME/.claude/.devforge-pr-state-<n>.json`.

Scenari test coperti: 1 (primo push crea snapshot + emette pr_opened) e 7 (push con snapshot esistente NON ri-emette pr_opened).

## File coinvolti

- `tests/hooks/post-commit-pr-lifecycle.test.sh` (MODIFY: aggiungi scenari)
- `hooks/post-commit-review` (MODIFY: sostituisci blocco righe 85-103)

## Step 1 — Test RED: scenario 1 (primo push)

In `tests/hooks/post-commit-pr-lifecycle.test.sh`, **prima** di `echo "SETUP OK"`, aggiungi:

```bash
# ─── Scenario 1: primo push con PR → pr_opened + snapshot ───
set_gh_fixture '{"number":213,"baseRefName":"main","changedFiles":3,"commits":{"totalCount":2},"reviewDecision":"REVIEW_REQUIRED","state":"OPEN"}'

invoke_hook "git push origin HEAD"

if [ "$(count_events pr_opened)" != "1" ]; then
    echo "FAIL scenario 1: pr_opened count = $(count_events pr_opened), atteso 1"
    cat "$DEVFORGE_LOG_FILE"
    exit 1
fi
if [ ! -f "${HOME}/.claude/.devforge-pr-state-213.json" ]; then
    echo "FAIL scenario 1: snapshot file non creato"
    exit 1
fi
echo "PASS scenario 1: pr_opened 1x + snapshot creato"

# ─── Scenario 7: secondo push, snapshot esiste → NON ri-emette pr_opened ───
# (stessa PR, stessa fixture)
invoke_hook "git push origin HEAD"

if [ "$(count_events pr_opened)" != "1" ]; then
    echo "FAIL scenario 7: pr_opened count = $(count_events pr_opened), atteso 1 (dedup)"
    exit 1
fi
echo "PASS scenario 7: dedup pr_opened via snapshot"
```

## Step 2 — Run test, verifica RED

```bash
bash tests/hooks/post-commit-pr-lifecycle.test.sh
```

**Output atteso (fallimento atteso):**

```
FAIL scenario 1: ...
```

Oppure passa ma lo snapshot non esiste (hook attuale non crea snapshot).

## Step 3 — Implementazione in `hooks/post-commit-review`

**Sostituisci** il blocco esistente alle righe 85-103 (`# Emit pr_opened event after push...`) con:

```bash
# Emit PR lifecycle events on git push (idempotente via snapshot file)
if [[ "$TOOL_COMMAND" =~ git[[:space:]]+push ]]; then
    source "${PLUGIN_ROOT}/lib/logger.sh" 2>/dev/null || true
    devforge_init_session 2>/dev/null || true
    if command -v gh >/dev/null 2>&1; then
        PR_JSON=$(timeout 3 gh pr view --json number,baseRefName,changedFiles,commits,reviewDecision,state 2>/dev/null || echo "")
        if [ -n "$PR_JSON" ]; then
            PR_NUMBER=$(echo "$PR_JSON" | grep -o '"number":[0-9]*' | grep -oE '[0-9]+' | head -1 || echo "0")
            if [ "${PR_NUMBER:-0}" -gt 0 ]; then
                BASE_BRANCH=$(echo "$PR_JSON" | grep -o '"baseRefName":"[^"]*"' | sed 's/.*"baseRefName":"//;s/"$//' || echo "unknown")
                FILES_CHANGED=$(echo "$PR_JSON" | grep -o '"changedFiles":[0-9]*' | grep -oE '[0-9]+' | head -1 || echo "0")
                COMMITS_COUNT=$(echo "$PR_JSON" | grep -o '"totalCount":[0-9]*' | grep -oE '[0-9]+' | head -1 || echo "0")
                SAFE_BASE_BRANCH=$(devforge_sanitize_json_str "$BASE_BRANCH")

                SNAPSHOT_FILE="${HOME}/.claude/.devforge-pr-state-${PR_NUMBER}.json"

                if [ ! -f "$SNAPSHOT_FILE" ]; then
                    # Primo push con PR → emit pr_opened + crea snapshot
                    devforge_log "pr_opened" "success" \
                        "{\"pr_number\":${PR_NUMBER},\"base_branch\":\"${SAFE_BASE_BRANCH}\",\"files_changed\":${FILES_CHANGED},\"commits_count\":${COMMITS_COUNT}}"

                    OPENED_TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
                    cat > "${SNAPSHOT_FILE}.tmp" << EOF_SNAP
{"pr_number":${PR_NUMBER},"base_branch":"${BASE_BRANCH}","opened_ts":"${OPENED_TS}","commits_at_open":${COMMITS_COUNT},"last_review_decision":"REVIEW_REQUIRED"}
EOF_SNAP
                    mv "${SNAPSHOT_FILE}.tmp" "$SNAPSHOT_FILE"
                fi
                # else: snapshot esiste → NO pr_opened (Task 03 aggiungera' pr_commit_after_open)
                SHOULD_UPLOAD=1
            fi
        fi
    fi
fi
```

## Step 4 — Run test, verifica GREEN

```bash
bash tests/hooks/post-commit-pr-lifecycle.test.sh
```

**Output atteso:**

```
PASS scenario 1: pr_opened 1x + snapshot creato
PASS scenario 7: dedup pr_opened via snapshot
SETUP OK
```

## Step 5 — Verifica test esistenti non rotti

```bash
bash tests/hooks/post-commit-review-sha.test.sh
bash tests/hooks/post-skill-plan-events.test.sh
```

Entrambi devono restare verdi.

## Step 6 — Commit

```bash
git add hooks/post-commit-review tests/hooks/post-commit-pr-lifecycle.test.sh
git commit -m "feat(hook): pr_opened idempotente via snapshot file

Source of truth: \$HOME/.claude/.devforge-pr-state-<n>.json.
Primo push con PR crea snapshot + emette pr_opened.
Push successivi con snapshot esistente saltano pr_opened (dedup).

Co-Authored-By: SIAE DevForge"
```

## Definition of Done

- [ ] Scenari 1 e 7 passano.
- [ ] `post-commit-review-sha.test.sh` e `post-skill-plan-events.test.sh` restano verdi.
- [ ] Snapshot file creato al primo push con PR.
- [ ] Commit creato.
