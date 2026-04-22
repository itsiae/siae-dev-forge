# Task 04 — pr_review_cycle su CHANGES_REQUESTED

**Stato:** [PENDING]
**Stima:** 10 min
**Dipendenze:** Task 02

## Goal

Emettere `pr_review_cycle` quando `reviewDecision` dalla fixture passa a `CHANGES_REQUESTED` ed è **diverso** da `last_review_decision` nello snapshot. `cycle_num` = count esistenti per pr_number + 1.

Aggiornare `last_review_decision` nello snapshot dopo emit, per evitare doppio emit (scenario 6).

Scenari test: 3 (prima transizione a CHANGES_REQUESTED) e 6 (secondo push con stessa decisione → no doppio emit).

## File coinvolti

- `tests/hooks/post-commit-pr-lifecycle.test.sh` (MODIFY)
- `hooks/post-commit-review` (MODIFY)

## Step 1 — Test RED: scenari 3 + 6

Aggiungi dopo lo scenario 2 (prima di `echo "SETUP OK"`):

```bash
# ─── Scenario 3: reviewDecision → CHANGES_REQUESTED → pr_review_cycle cycle_num=1 ───
cd "$TEST_REPO"
echo "fix" >> file.txt
git add file.txt
git commit -q -m "fix review"

set_gh_fixture '{"number":213,"baseRefName":"main","changedFiles":3,"commits":{"totalCount":4},"reviewDecision":"CHANGES_REQUESTED","state":"OPEN"}'

invoke_hook "git push origin HEAD"

if [ "$(count_events pr_review_cycle)" != "1" ]; then
    echo "FAIL scenario 3: pr_review_cycle count = $(count_events pr_review_cycle), atteso 1"
    cat "$DEVFORGE_LOG_FILE"
    exit 1
fi
if ! grep -q '"cycle_num":1' "$DEVFORGE_LOG_FILE"; then
    echo "FAIL scenario 3: cycle_num != 1"
    grep pr_review_cycle "$DEVFORGE_LOG_FILE"
    exit 1
fi
echo "PASS scenario 3: pr_review_cycle cycle_num=1"

# ─── Scenario 6: push successivo con stessa CHANGES_REQUESTED → no doppio emit ───
cd "$TEST_REPO"
echo "fix2" >> file.txt
git add file.txt
git commit -q -m "another fix"

# Stessa fixture con reviewDecision invariata
set_gh_fixture '{"number":213,"baseRefName":"main","changedFiles":3,"commits":{"totalCount":5},"reviewDecision":"CHANGES_REQUESTED","state":"OPEN"}'

invoke_hook "git push origin HEAD"

if [ "$(count_events pr_review_cycle)" != "1" ]; then
    echo "FAIL scenario 6: pr_review_cycle count = $(count_events pr_review_cycle), atteso 1 (no doppio emit)"
    exit 1
fi
echo "PASS scenario 6: pr_review_cycle dedup (no doppio emit con stessa decisione)"
```

## Step 2 — Run test, verifica RED

```bash
bash tests/hooks/post-commit-pr-lifecycle.test.sh
```

**Output atteso:** `FAIL scenario 3: pr_review_cycle count = 0`.

## Step 3 — Implementazione

Nel hook, **dopo** il blocco `if/else` snapshot (pr_opened / pr_commit_after_open) e **dentro** il blocco `if [ "${PR_NUMBER:-0}" -gt 0 ]`, aggiungi:

```bash
                # pr_review_cycle: emetti se reviewDecision == CHANGES_REQUESTED
                # AND != last_review_decision nello snapshot
                REVIEW_DECISION=$(echo "$PR_JSON" | grep -o '"reviewDecision":"[^"]*"' | sed 's/.*"reviewDecision":"//;s/"$//' || echo "")
                if [ "$REVIEW_DECISION" = "CHANGES_REQUESTED" ] && [ -f "$SNAPSHOT_FILE" ]; then
                    LAST_DECISION=$(grep -o '"last_review_decision":"[^"]*"' "$SNAPSHOT_FILE" | sed 's/.*"last_review_decision":"//;s/"$//' || echo "")
                    if [ "$LAST_DECISION" != "CHANGES_REQUESTED" ]; then
                        PREV_CYCLES=$(grep -c "\"event\":\"pr_review_cycle\".*\"pr_number\":${PR_NUMBER}" "$DEVFORGE_LOG_FILE" 2>/dev/null || echo 0)
                        CYCLE_NUM=$(( PREV_CYCLES + 1 ))
                        devforge_log "pr_review_cycle" "success" \
                            "{\"pr_number\":${PR_NUMBER},\"cycle_num\":${CYCLE_NUM},\"trigger\":\"changes_requested\"}"

                        # Update snapshot con nuova last_review_decision
                        python3 - "$SNAPSHOT_FILE" "$REVIEW_DECISION" << 'PYEOF' || true
import json, sys
p, new_dec = sys.argv[1], sys.argv[2]
with open(p) as f: d = json.load(f)
d["last_review_decision"] = new_dec
with open(p + ".tmp", "w") as f: json.dump(d, f)
import os; os.replace(p + ".tmp", p)
PYEOF
                    fi
                fi
```

## Step 4 — Run test, verifica GREEN

```bash
bash tests/hooks/post-commit-pr-lifecycle.test.sh
```

Tutti gli scenari 1,2,3,6,7 devono passare.

## Step 5 — Commit

```bash
git add hooks/post-commit-review tests/hooks/post-commit-pr-lifecycle.test.sh
git commit -m "feat(hook): emit pr_review_cycle on CHANGES_REQUESTED transition

cycle_num incrementale per pr_number (count prior + 1).
Dedup via last_review_decision in snapshot — no doppio emit su stessa decisione.

Co-Authored-By: SIAE DevForge"
```

## Definition of Done

- [ ] Scenario 3 passa con `cycle_num=1`.
- [ ] Scenario 6 passa (no doppio emit).
- [ ] Scenari precedenti 1,2,7 restano verdi.
- [ ] `last_review_decision` aggiornato nello snapshot.
- [ ] Commit creato.
