# Task 05 — pr_merged via gh pr merge (CLI)

**Stato:** [PENDING]
**Stima:** 8 min
**Dipendenze:** Task 02

## Goal

Quando `TOOL_COMMAND` contiene `gh pr merge`, emettere `pr_merged` con `merge_method:"cli"`, `total_commits`, `delta_from_open`. Cancellare lo snapshot file.

Scenario test: 4 (gh pr merge CLI → pr_merged + snapshot cancellato).

`pr_metrics` sarà aggiunto in Task 06 subito dopo questo evento.

## File coinvolti

- `tests/hooks/post-commit-pr-lifecycle.test.sh` (MODIFY)
- `hooks/post-commit-review` (MODIFY)

## Step 1 — Test RED: scenario 4

Aggiungi dopo lo scenario 6 (prima di `echo "SETUP OK"`):

```bash
# ─── Scenario 4: gh pr merge CLI → pr_merged (cli) + snapshot cancellato ───
# A questo punto commits.totalCount è 5 (da scenario 6), commits_at_open era 2
set_gh_fixture '{"number":213,"baseRefName":"main","changedFiles":3,"commits":{"totalCount":5},"reviewDecision":"APPROVED","state":"OPEN"}'

invoke_hook "gh pr merge 213 --squash"

if [ "$(count_events pr_merged)" != "1" ]; then
    echo "FAIL scenario 4: pr_merged count = $(count_events pr_merged), atteso 1"
    cat "$DEVFORGE_LOG_FILE"
    exit 1
fi
if ! grep -q '"merge_method":"cli"' "$DEVFORGE_LOG_FILE"; then
    echo "FAIL scenario 4: merge_method != cli"
    grep pr_merged "$DEVFORGE_LOG_FILE"
    exit 1
fi
# delta_from_open = total_commits (5) - commits_at_open (2) = 3
if ! grep -q '"delta_from_open":3' "$DEVFORGE_LOG_FILE"; then
    echo "FAIL scenario 4: delta_from_open != 3"
    grep pr_merged "$DEVFORGE_LOG_FILE"
    exit 1
fi
if [ -f "${HOME}/.claude/.devforge-pr-state-213.json" ]; then
    echo "FAIL scenario 4: snapshot non cancellato dopo merge"
    exit 1
fi
echo "PASS scenario 4: pr_merged cli + delta=3 + snapshot cancellato"
```

## Step 2 — Run test, verifica RED

```bash
bash tests/hooks/post-commit-pr-lifecycle.test.sh
```

**Output atteso:** `FAIL scenario 4: pr_merged count = 0`.

## Step 3 — Implementazione

Nel hook, **dopo** il blocco `if [[ "$TOOL_COMMAND" =~ git[[:space:]]+push ]]` e **prima** del blocco esistente `if [[ ! "$TOOL_COMMAND" =~ gh[[:space:]]+pr[[:space:]]+create ]]`, aggiungi:

```bash
# Emit pr_merged on gh pr merge CLI invocation
if [[ "$TOOL_COMMAND" =~ gh[[:space:]]+pr[[:space:]]+merge ]]; then
    source "${PLUGIN_ROOT}/lib/logger.sh" 2>/dev/null || true
    devforge_init_session 2>/dev/null || true
    if command -v gh >/dev/null 2>&1; then
        PR_JSON=$(timeout 3 gh pr view --json number,commits 2>/dev/null || echo "")
        if [ -n "$PR_JSON" ]; then
            PR_NUMBER=$(echo "$PR_JSON" | grep -o '"number":[0-9]*' | grep -oE '[0-9]+' | head -1 || echo "0")
            TOTAL_COMMITS=$(echo "$PR_JSON" | grep -o '"totalCount":[0-9]*' | grep -oE '[0-9]+' | head -1 || echo "0")
            if [ "${PR_NUMBER:-0}" -gt 0 ]; then
                SNAPSHOT_FILE="${HOME}/.claude/.devforge-pr-state-${PR_NUMBER}.json"
                COMMITS_AT_OPEN=0
                if [ -f "$SNAPSHOT_FILE" ]; then
                    COMMITS_AT_OPEN=$(grep -o '"commits_at_open":[0-9]*' "$SNAPSHOT_FILE" | grep -oE '[0-9]+' | head -1 || echo "0")
                fi
                DELTA=$(( TOTAL_COMMITS - COMMITS_AT_OPEN ))
                [ "$DELTA" -lt 0 ] && DELTA=0

                devforge_log "pr_merged" "success" \
                    "{\"pr_number\":${PR_NUMBER},\"merge_method\":\"cli\",\"total_commits\":${TOTAL_COMMITS},\"delta_from_open\":${DELTA}}"

                # Task 06 aggiungera' pr_metrics qui

                # Cleanup snapshot
                rm -f "$SNAPSHOT_FILE"
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

Scenario 4 passa, scenari precedenti restano verdi.

## Step 5 — Commit

```bash
git add hooks/post-commit-review tests/hooks/post-commit-pr-lifecycle.test.sh
git commit -m "feat(hook): emit pr_merged on gh pr merge CLI

merge_method=cli, delta_from_open = total_commits - commits_at_open.
Cleanup snapshot file dopo emit.

Co-Authored-By: SIAE DevForge"
```

## Definition of Done

- [ ] Scenario 4 passa con `merge_method=cli`, `delta_from_open=3`.
- [ ] Snapshot file cancellato dopo emit.
- [ ] Scenari precedenti restano verdi.
- [ ] Commit creato.
