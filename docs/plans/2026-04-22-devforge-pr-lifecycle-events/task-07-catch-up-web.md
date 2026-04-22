# Task 07 — Catch-up polling + pr_merged web

**Stato:** [PENDING]
**Stima:** 12 min
**Dipendenze:** Task 05, Task 06

## Goal

Ad ogni `git push`, scansionare fino a 5 snapshot orfani (ordinati per `opened_ts` crescente). Per ogni snapshot, interrogare `gh pr view <n> --json state,mergedAt,commits`. Se `state == MERGED`, emettere `pr_merged` (merge_method:"web") + `pr_metrics` e cancellare snapshot.

Scenario test: 5 (PR diverso, fixture state=MERGED al secondo push su altro branch → catch-up emette pr_merged web).

## File coinvolti

- `tests/hooks/post-commit-pr-lifecycle.test.sh` (MODIFY)
- `hooks/post-commit-review` (MODIFY: aggiungi blocco catch-up)

## Step 1 — Test RED: scenario 5

Aggiungi dopo lo scenario 4b (prima di `echo "SETUP OK"`):

```bash
# ─── Scenario 5: snapshot orfano con state=MERGED → catch-up pr_merged (web) ───
# Setup: crea snapshot orfano per PR 999 (non attivo sul branch corrente)
OPENED_TS_PAST=$(python3 -c "from datetime import datetime, timedelta, timezone; print((datetime.now(timezone.utc) - timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M:%SZ'))")
cat > "${HOME}/.claude/.devforge-pr-state-999.json" << EOF
{"pr_number":999,"base_branch":"main","opened_ts":"${OPENED_TS_PAST}","commits_at_open":1,"last_review_decision":"REVIEW_REQUIRED"}
EOF

# Fixture specifica per pr_number=999 via shim che matcha su argomento
# Sostituiamo lo shim gh per questo scenario: se argomenti contengono "999" → state=MERGED
cat > "${GH_SHIM_DIR}/gh" << 'GHEOF'
#!/usr/bin/env bash
# Se l'invocazione riguarda PR 999 → fixture merged
# Altrimenti fixture corrente (MERGED per PR attiva non applicabile — nessuna attiva ora)
for arg in "$@"; do
    case "$arg" in
        999)
            echo '{"number":999,"state":"MERGED","mergedAt":"2026-04-22T09:00:00Z","commits":{"totalCount":4}}'
            exit 0
            ;;
    esac
done
# Default: nessuna PR sul branch corrente (stato terminale post-scenario 4)
echo ""
exit 0
GHEOF
chmod +x "${GH_SHIM_DIR}/gh"
unset GH_FIXTURE

# Reset snapshot del test-log per contare solo eventi nuovi dello scenario 5
MERGED_COUNT_BEFORE=$(count_events pr_merged)

invoke_hook "git push origin HEAD"

MERGED_COUNT_AFTER=$(count_events pr_merged)
NEW_MERGED=$(( MERGED_COUNT_AFTER - MERGED_COUNT_BEFORE ))
if [ "$NEW_MERGED" != "1" ]; then
    echo "FAIL scenario 5: nuovi pr_merged = $NEW_MERGED, atteso 1"
    cat "$DEVFORGE_LOG_FILE"
    exit 1
fi
if ! grep -q '"merge_method":"web"' "$DEVFORGE_LOG_FILE"; then
    echo "FAIL scenario 5: nessun pr_merged con merge_method=web"
    grep pr_merged "$DEVFORGE_LOG_FILE"
    exit 1
fi
if [ -f "${HOME}/.claude/.devforge-pr-state-999.json" ]; then
    echo "FAIL scenario 5: snapshot PR 999 non cancellato"
    exit 1
fi
# pr_metrics emesso anche per PR 999 (time_to_merge_sec ~ 30min = 1800s)
if ! grep -q "\"pr_number\":999.*\"time_to_merge_sec\":1[0-9]\{3\}" "$DEVFORGE_LOG_FILE"; then
    echo "FAIL scenario 5: pr_metrics PR 999 mancante o time_to_merge_sec fuori range"
    grep 'pr_metrics' "$DEVFORGE_LOG_FILE"
    exit 1
fi
echo "PASS scenario 5: catch-up emette pr_merged (web) + pr_metrics + cleanup snapshot"
```

## Step 2 — Run test, verifica RED

```bash
bash tests/hooks/post-commit-pr-lifecycle.test.sh
```

**Output atteso:** `FAIL scenario 5: nuovi pr_merged = 0`.

## Step 3 — Implementazione

Nel hook, **dentro** il blocco `if [[ "$TOOL_COMMAND" =~ git[[:space:]]+push ]]` e **dopo** il blocco di detection principale (pr_opened / pr_commit_after_open / pr_review_cycle), **prima** della chiusura `fi` esterna, aggiungi:

```bash
    # ─── Catch-up: scansiona snapshot orfani per merge via UI web ───
    # Max 5 snapshot per push, ordinati per opened_ts crescente
    if command -v gh >/dev/null 2>&1; then
        CATCH_UP_COUNT=0
        CURRENT_PR_NUMBER="${PR_NUMBER:-0}"
        # Ordina snapshot per mtime (proxy di opened_ts — scrittura iniziale)
        for snapshot in $(ls -1tr "${HOME}/.claude/".devforge-pr-state-*.json 2>/dev/null | head -5); do
            [ "$CATCH_UP_COUNT" -ge 5 ] && break
            [ ! -f "$snapshot" ] && continue
            ORPHAN_PR=$(grep -o '"pr_number":[0-9]*' "$snapshot" | grep -oE '[0-9]+' | head -1 || echo "0")
            # Skip PR corrente (già processata sopra)
            if [ "$ORPHAN_PR" = "$CURRENT_PR_NUMBER" ]; then
                continue
            fi
            [ "${ORPHAN_PR:-0}" -eq 0 ] && continue

            ORPHAN_JSON=$(timeout 3 gh pr view "$ORPHAN_PR" --json state,mergedAt,commits 2>/dev/null || echo "")
            [ -z "$ORPHAN_JSON" ] && continue

            ORPHAN_STATE=$(echo "$ORPHAN_JSON" | grep -o '"state":"[^"]*"' | sed 's/.*"state":"//;s/"$//' || echo "")
            if [ "$ORPHAN_STATE" = "MERGED" ] || [ "$ORPHAN_STATE" = "CLOSED" ]; then
                ORPHAN_TOTAL=$(echo "$ORPHAN_JSON" | grep -o '"totalCount":[0-9]*' | grep -oE '[0-9]+' | head -1 || echo "0")
                ORPHAN_COMMITS_AT_OPEN=$(grep -o '"commits_at_open":[0-9]*' "$snapshot" | grep -oE '[0-9]+' | head -1 || echo "0")
                ORPHAN_DELTA=$(( ORPHAN_TOTAL - ORPHAN_COMMITS_AT_OPEN ))
                [ "$ORPHAN_DELTA" -lt 0 ] && ORPHAN_DELTA=0

                MERGE_METHOD="web"
                [ "$ORPHAN_STATE" = "CLOSED" ] && MERGE_METHOD="closed"

                devforge_log "pr_merged" "success" \
                    "{\"pr_number\":${ORPHAN_PR},\"merge_method\":\"${MERGE_METHOD}\",\"total_commits\":${ORPHAN_TOTAL},\"delta_from_open\":${ORPHAN_DELTA}}"

                # pr_metrics per orphan
                ORPHAN_REWORK=$(grep -c "\"event\":\"pr_commit_after_open\".*\"pr_number\":${ORPHAN_PR}" "$DEVFORGE_LOG_FILE" 2>/dev/null || echo 0)
                ORPHAN_CYCLES=$(grep -c "\"event\":\"pr_review_cycle\".*\"pr_number\":${ORPHAN_PR}" "$DEVFORGE_LOG_FILE" 2>/dev/null || echo 0)
                ORPHAN_OPENED_TS=$(grep -o '"opened_ts":"[^"]*"' "$snapshot" | sed 's/.*"opened_ts":"//;s/"$//')
                ORPHAN_TTM=0
                if [ -n "$ORPHAN_OPENED_TS" ] && command -v python3 >/dev/null 2>&1; then
                    ORPHAN_TTM=$(python3 -c "
import sys
from datetime import datetime, timezone
t = datetime.fromisoformat(sys.argv[1].replace('Z','+00:00'))
now = datetime.now(timezone.utc)
print(max(0, int((now - t).total_seconds())))
" "$ORPHAN_OPENED_TS" 2>/dev/null || echo 0)
                fi
                devforge_log "pr_metrics" "success" \
                    "{\"pr_number\":${ORPHAN_PR},\"rework_commits\":${ORPHAN_REWORK},\"review_cycles\":${ORPHAN_CYCLES},\"time_to_merge_sec\":${ORPHAN_TTM},\"first_push_to_merge_sec\":${ORPHAN_TTM}}"

                rm -f "$snapshot"
                CATCH_UP_COUNT=$(( CATCH_UP_COUNT + 1 ))
                SHOULD_UPLOAD=1
            fi
        done
    fi
```

**NB:** posiziona il blocco dentro il medesimo `if [[ "$TOOL_COMMAND" =~ git[[:space:]]+push ]]` che già esiste da Task 02, in modo che sia eseguito anche quando non c'è PR attiva sul branch corrente (push su altro branch).

## Step 4 — Run test, verifica GREEN

```bash
bash tests/hooks/post-commit-pr-lifecycle.test.sh
```

Tutti i 7 scenari devono passare:

```
PASS scenario 1: pr_opened 1x + snapshot creato
PASS scenario 2: pr_commit_after_open con commits_since_open=1
PASS scenario 7: dedup pr_opened via snapshot (count=1)
PASS scenario 3: pr_review_cycle cycle_num=1
PASS scenario 6: pr_review_cycle dedup (no doppio emit con stessa decisione)
PASS scenario 4: pr_merged cli + delta=3 + snapshot cancellato
PASS scenario 4b: pr_metrics con rework_commits=X, review_cycles=1
PASS scenario 5: catch-up emette pr_merged (web) + pr_metrics + cleanup snapshot
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
git commit -m "feat(hook): catch-up polling per pr_merged via UI web

Scansiona fino a 5 snapshot orfani per push (ls -1tr = oldest first).
gh pr view <n> → state MERGED/CLOSED → pr_merged + pr_metrics + cleanup.
Copre merge fatti da UI web senza gh pr merge locale.

Co-Authored-By: SIAE DevForge"
```

## Definition of Done

- [ ] Scenario 5 passa: `pr_merged` (merge_method=web) + `pr_metrics` + snapshot 999 cancellato.
- [ ] Tutti i 7 scenari passano.
- [ ] Test esistenti (`post-commit-review-sha`, `post-skill-plan-events`) restano verdi.
- [ ] Cap 5 snapshot rispettato (loop `head -5`).
- [ ] Commit creato.
