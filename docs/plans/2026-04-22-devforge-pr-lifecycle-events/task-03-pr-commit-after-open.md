# Task 03 — pr_commit_after_open su push successivi

**Stato:** [PENDING]
**Stima:** 8 min
**Dipendenze:** Task 02

## Goal

Quando esiste già snapshot per il pr_number corrente, ogni `git push` emette `pr_commit_after_open` con `commit_sha` (HEAD attuale) e `commits_since_open` (= `commits.totalCount` corrente - `commits_at_open` salvato in snapshot).

Scenario test: 2 (secondo push → `pr_commit_after_open` emesso, no nuovo `pr_opened`).

## File coinvolti

- `tests/hooks/post-commit-pr-lifecycle.test.sh` (MODIFY)
- `hooks/post-commit-review` (MODIFY: aggiungi branch `else` al blocco snapshot)

## Step 1 — Test RED: scenario 2

In `tests/hooks/post-commit-pr-lifecycle.test.sh`, **prima** dello scenario 7 (serve isolamento — lo scenario 7 riusa lo stesso push), sposta/aggiungi:

Sostituisci lo scenario 7 esistente con questa versione estesa (scenario 2 + 7):

```bash
# ─── Scenario 2: secondo push → pr_commit_after_open, NO altro pr_opened ───
# Nuovo commit nel repo per aggiornare HEAD
cd "$TEST_REPO"
echo "change" >> file.txt
git add file.txt
git commit -q -m "second commit"
NEW_SHA=$(git rev-parse HEAD)

# commits.totalCount passa da 2 → 3 (simula push di un nuovo commit sulla PR)
set_gh_fixture '{"number":213,"baseRefName":"main","changedFiles":3,"commits":{"totalCount":3},"reviewDecision":"REVIEW_REQUIRED","state":"OPEN"}'

invoke_hook "git push origin HEAD"

if [ "$(count_events pr_opened)" != "1" ]; then
    echo "FAIL scenario 2: pr_opened count = $(count_events pr_opened), atteso 1 (dedup)"
    exit 1
fi
if [ "$(count_events pr_commit_after_open)" != "1" ]; then
    echo "FAIL scenario 2: pr_commit_after_open count = $(count_events pr_commit_after_open), atteso 1"
    cat "$DEVFORGE_LOG_FILE"
    exit 1
fi
# Verifica commits_since_open = 3 - 2 = 1
if ! grep -q '"commits_since_open":1' "$DEVFORGE_LOG_FILE"; then
    echo "FAIL scenario 2: commits_since_open != 1"
    grep pr_commit_after_open "$DEVFORGE_LOG_FILE"
    exit 1
fi
echo "PASS scenario 2: pr_commit_after_open con commits_since_open=1"
echo "PASS scenario 7: dedup pr_opened via snapshot (count=1)"
```

Rimuovi lo scenario 7 vecchio (era duplicato dello scenario 2 senza nuovo commit).

## Step 2 — Run test, verifica RED

```bash
bash tests/hooks/post-commit-pr-lifecycle.test.sh
```

**Output atteso:**

```
PASS scenario 1: ...
FAIL scenario 2: pr_commit_after_open count = 0, atteso 1
```

## Step 3 — Implementazione

Nel blocco Task 02, sostituisci il commento `# else: snapshot esiste → NO pr_opened (Task 03 aggiungera' pr_commit_after_open)` con il branch `else` attivo:

```bash
                if [ ! -f "$SNAPSHOT_FILE" ]; then
                    # Primo push con PR → emit pr_opened + crea snapshot
                    devforge_log "pr_opened" "success" \
                        "{\"pr_number\":${PR_NUMBER},\"base_branch\":\"${SAFE_BASE_BRANCH}\",\"files_changed\":${FILES_CHANGED},\"commits_count\":${COMMITS_COUNT}}"

                    OPENED_TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
                    cat > "${SNAPSHOT_FILE}.tmp" << EOF_SNAP
{"pr_number":${PR_NUMBER},"base_branch":"${BASE_BRANCH}","opened_ts":"${OPENED_TS}","commits_at_open":${COMMITS_COUNT},"last_review_decision":"REVIEW_REQUIRED"}
EOF_SNAP
                    mv "${SNAPSHOT_FILE}.tmp" "$SNAPSHOT_FILE"
                else
                    # Snapshot esiste → emit pr_commit_after_open
                    COMMITS_AT_OPEN=$(grep -o '"commits_at_open":[0-9]*' "$SNAPSHOT_FILE" | grep -oE '[0-9]+' | head -1 || echo "0")
                    COMMITS_SINCE_OPEN=$(( COMMITS_COUNT - COMMITS_AT_OPEN ))
                    [ "$COMMITS_SINCE_OPEN" -lt 0 ] && COMMITS_SINCE_OPEN=0
                    CURRENT_COMMIT_SHA=$(git rev-parse HEAD 2>/dev/null || echo "")
                    devforge_log "pr_commit_after_open" "success" \
                        "{\"pr_number\":${PR_NUMBER},\"commit_sha\":\"${CURRENT_COMMIT_SHA}\",\"commits_since_open\":${COMMITS_SINCE_OPEN}}"
                fi
```

## Step 4 — Run test, verifica GREEN

```bash
bash tests/hooks/post-commit-pr-lifecycle.test.sh
```

**Output atteso:**

```
PASS scenario 1: pr_opened 1x + snapshot creato
PASS scenario 2: pr_commit_after_open con commits_since_open=1
PASS scenario 7: dedup pr_opened via snapshot (count=1)
SETUP OK
```

## Step 5 — Commit

```bash
git add hooks/post-commit-review tests/hooks/post-commit-pr-lifecycle.test.sh
git commit -m "feat(hook): emit pr_commit_after_open on push with existing snapshot

commits_since_open = commits.totalCount - commits_at_open (da snapshot).
Include commit_sha corrente come rework signal.

Co-Authored-By: SIAE DevForge"
```

## Definition of Done

- [ ] Scenario 2 passa con `commits_since_open=1`.
- [ ] Scenario 1 e 7 restano verdi.
- [ ] Commit creato.
