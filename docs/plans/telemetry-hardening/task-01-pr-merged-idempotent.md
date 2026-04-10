# Task 1 — pr_merged idempotente

**Stato:** [DONE]
**File coinvolti:** `hooks/session-start` (MODIFICA)
**AC coperti:** AC-1, AC-5

---

## Step 1 — Aggiungi seen-file e dedup logic

**File:** `hooks/session-start`
**Punto di innesto:** dentro il loop `while IFS= read -r pr; do` (linea 196), prima della chiamata `devforge_log "pr_merged"` (linea 212).

**Sostituisci** il blocco linee 196-216 (dal `while` al `done`) con:

```bash
        SEEN_FILE="${HOME}/.claude/.devforge-seen-pr-merges"
        touch "$SEEN_FILE"
        echo "$MERGED_PRS" | jq -c '.[]' 2>/dev/null | while IFS= read -r pr; do
                PR_NUMBER=$(echo "$pr" | jq -r '.number' 2>/dev/null || echo "0")
                CREATED_AT=$(echo "$pr" | jq -r '.createdAt' 2>/dev/null || echo "")
                MERGED_AT=$(echo "$pr" | jq -r '.mergedAt' 2>/dev/null || echo "")
                REVIEWERS_COUNT=$(echo "$pr" | jq '[.reviews[]? | .author.login] | unique | length' 2>/dev/null || echo "0")

                # Idempotency: skip if already logged
                if grep -qF "${GH_REPO}#${PR_NUMBER}" "$SEEN_FILE" 2>/dev/null; then
                    continue
                fi

                REVIEW_CYCLE_HOURS="0"
                if [ -n "$CREATED_AT" ] && [ -n "$MERGED_AT" ]; then
                    CREATED_EPOCH=$(date -jf "%Y-%m-%dT%H:%M:%SZ" "$CREATED_AT" +%s 2>/dev/null || date -d "$CREATED_AT" +%s 2>/dev/null || echo "0")
                    MERGED_EPOCH=$(date -jf "%Y-%m-%dT%H:%M:%SZ" "$MERGED_AT" +%s 2>/dev/null || date -d "$MERGED_AT" +%s 2>/dev/null || echo "0")
                    if [ "$CREATED_EPOCH" != "0" ] && [ "$MERGED_EPOCH" != "0" ]; then
                        DELTA_SECONDS=$((MERGED_EPOCH - CREATED_EPOCH))
                        REVIEW_CYCLE_HOURS=$(echo "scale=1; $DELTA_SECONDS / 3600" | bc 2>/dev/null || echo "0")
                    fi
                fi

                devforge_log "pr_merged" "success" \
                    "{\"pr_number\":${PR_NUMBER},\"review_cycle_hours\":${REVIEW_CYCLE_HOURS},\"reviewers_count\":${REVIEWERS_COUNT}}"

                # Mark as seen + keep file bounded
                echo "${GH_REPO}#${PR_NUMBER}" >> "$SEEN_FILE"
                tail -200 "$SEEN_FILE" > "${SEEN_FILE}.tmp" && mv "${SEEN_FILE}.tmp" "$SEEN_FILE"
            done
```

## Step 2 — Verifica

Simula due sessioni consecutive:

```bash
# Prima sessione — logga le PR
bash hooks/session-start
grep "pr_merged" ~/.claude/devforge-activity.jsonl | wc -l

# Seconda sessione — non dovrebbe riloggare
bash hooks/session-start
grep "pr_merged" ~/.claude/devforge-activity.jsonl | wc -l
```

Output atteso: il count non aumenta alla seconda sessione.

Verifica che il file seen sia bounded:
```bash
wc -l ~/.claude/.devforge-seen-pr-merges
```
Output atteso: <= 200 righe.
