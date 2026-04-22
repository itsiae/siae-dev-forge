# Task 06 — pr_metrics aggregato post-merge

**Stato:** [PENDING]
**Stima:** 8 min
**Dipendenze:** Task 05

## Goal

Subito dopo `pr_merged`, emettere `pr_metrics` con:

- `rework_commits` = count `pr_commit_after_open` per `pr_number`
- `review_cycles` = count `pr_review_cycle` per `pr_number`
- `time_to_merge_sec` = `now_epoch - opened_ts_epoch` (da snapshot, catturato **prima** del cleanup)
- `first_push_to_merge_sec` = alias di `time_to_merge_sec`

Verifica scenario 4 esteso: `pr_metrics` emesso con valori corretti calcolati da scenari 2+3 precedenti.

## File coinvolti

- `tests/hooks/post-commit-pr-lifecycle.test.sh` (MODIFY: estendi scenario 4)
- `hooks/post-commit-review` (MODIFY: completa il commento `# Task 06...`)

## Step 1 — Test RED: estensione scenario 4

Dopo le assertion esistenti dello scenario 4 (prima del `echo "PASS scenario 4..."`), aggiungi:

```bash
# pr_metrics deve essere emesso subito dopo pr_merged
if [ "$(count_events pr_metrics)" != "1" ]; then
    echo "FAIL scenario 4b: pr_metrics count = $(count_events pr_metrics), atteso 1"
    cat "$DEVFORGE_LOG_FILE"
    exit 1
fi
# rework_commits deve essere 1 (1x pr_commit_after_open dallo scenario 2)
# NB: scenari 3 e 6 hanno anche pushato commit, ma in quei scenari ci aspettiamo
# anche pr_commit_after_open → rework_commits potrebbe essere 3 (scenari 2, 3, 6).
# Verifichiamo che rework_commits coincida col count eventi emessi.
EXPECTED_REWORK=$(grep -c '"event":"pr_commit_after_open"' "$DEVFORGE_LOG_FILE" || echo 0)
if ! grep -q "\"rework_commits\":${EXPECTED_REWORK}" "$DEVFORGE_LOG_FILE"; then
    echo "FAIL scenario 4b: rework_commits != ${EXPECTED_REWORK}"
    grep pr_metrics "$DEVFORGE_LOG_FILE"
    exit 1
fi
# review_cycles deve essere 1 (1x pr_review_cycle dallo scenario 3)
if ! grep -q '"review_cycles":1' "$DEVFORGE_LOG_FILE"; then
    echo "FAIL scenario 4b: review_cycles != 1"
    grep pr_metrics "$DEVFORGE_LOG_FILE"
    exit 1
fi
# time_to_merge_sec deve essere presente e >= 0
if ! grep -qE '"time_to_merge_sec":[0-9]+' "$DEVFORGE_LOG_FILE"; then
    echo "FAIL scenario 4b: time_to_merge_sec mancante o non numerico"
    grep pr_metrics "$DEVFORGE_LOG_FILE"
    exit 1
fi
echo "PASS scenario 4b: pr_metrics con rework_commits=${EXPECTED_REWORK}, review_cycles=1"
```

Aggiorna il messaggio `echo "PASS scenario 4..."` esistente in `echo "PASS scenario 4: pr_merged cli + delta=3 + snapshot cancellato"` (resta invariato).

## Step 2 — Run test, verifica RED

```bash
bash tests/hooks/post-commit-pr-lifecycle.test.sh
```

**Output atteso:** `FAIL scenario 4b: pr_metrics count = 0`.

## Step 3 — Implementazione

Nel hook (task 05), sostituisci il commento `# Task 06 aggiungera' pr_metrics qui` con:

```bash
                # pr_metrics: aggregato subito dopo pr_merged
                REWORK_COUNT=$(grep -c "\"event\":\"pr_commit_after_open\".*\"pr_number\":${PR_NUMBER}" "$DEVFORGE_LOG_FILE" 2>/dev/null || echo 0)
                CYCLES_COUNT=$(grep -c "\"event\":\"pr_review_cycle\".*\"pr_number\":${PR_NUMBER}" "$DEVFORGE_LOG_FILE" 2>/dev/null || echo 0)
                TTM_SEC=0
                if [ -f "$SNAPSHOT_FILE" ] && command -v python3 >/dev/null 2>&1; then
                    OPENED_TS=$(grep -o '"opened_ts":"[^"]*"' "$SNAPSHOT_FILE" | sed 's/.*"opened_ts":"//;s/"$//')
                    if [ -n "$OPENED_TS" ]; then
                        TTM_SEC=$(python3 -c "
import sys
from datetime import datetime, timezone
t = datetime.fromisoformat(sys.argv[1].replace('Z','+00:00'))
now = datetime.now(timezone.utc)
print(max(0, int((now - t).total_seconds())))
" "$OPENED_TS" 2>/dev/null || echo 0)
                    fi
                fi
                devforge_log "pr_metrics" "success" \
                    "{\"pr_number\":${PR_NUMBER},\"rework_commits\":${REWORK_COUNT},\"review_cycles\":${CYCLES_COUNT},\"time_to_merge_sec\":${TTM_SEC},\"first_push_to_merge_sec\":${TTM_SEC}}"
```

**IMPORTANTE:** `pr_metrics` deve essere emesso **prima** di `rm -f "$SNAPSHOT_FILE"`, altrimenti `OPENED_TS` non è leggibile. Verifica che il blocco sia prima della riga `rm -f "$SNAPSHOT_FILE"`.

## Step 4 — Run test, verifica GREEN

```bash
bash tests/hooks/post-commit-pr-lifecycle.test.sh
```

Scenario 4 e 4b passano con valori coerenti.

## Step 5 — Commit

```bash
git add hooks/post-commit-review tests/hooks/post-commit-pr-lifecycle.test.sh
git commit -m "feat(hook): emit pr_metrics aggregato dopo pr_merged

rework_commits + review_cycles da count JSONL.
time_to_merge_sec = now - opened_ts da snapshot.

Co-Authored-By: SIAE DevForge"
```

## Definition of Done

- [ ] Scenario 4b passa con `rework_commits`, `review_cycles`, `time_to_merge_sec` popolati.
- [ ] `pr_metrics` emesso prima del cleanup snapshot.
- [ ] Scenari precedenti restano verdi.
- [ ] Commit creato.
