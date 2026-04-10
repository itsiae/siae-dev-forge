# Task 10 — Enrich session_end + commit_created con token stats

**Stato:** [PENDING]
**File coinvolti:** `hooks/stop-gate` (MODIFICA), `hooks/post-commit-review` (MODIFICA)
**AC coperti:** AC-14, AC-15
**Fase:** PR3
**Dipende da:** Task 7, 8

---

## Step 1 — Stop-gate: arricchisci session_end

Nel blocco telemetria di `hooks/stop-gate`, prima di `devforge_log_timed "session_end"`:

```bash
    # Token stats for session_end enrichment
    TOKEN_TOTAL=0
    TOKEN_OUTPUT=0
    TOKEN_COST_EUR="0"
    if [ -n "$DEVFORGE_SESSION_DIR" ] && [ -f "${DEVFORGE_SESSION_DIR}/token-stats.json" ]; then
        TDATA=$(python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
print(f'{d.get(\"total\",0)}\t{d.get(\"output\",0)}\t{d.get(\"cost_eur\",0)}')
" "${DEVFORGE_SESSION_DIR}/token-stats.json" 2>/dev/null) || true
        if [ -n "$TDATA" ]; then
            TOKEN_TOTAL=$(printf '%s' "$TDATA" | cut -f1)
            TOKEN_OUTPUT=$(printf '%s' "$TDATA" | cut -f2)
            TOKEN_COST_EUR=$(printf '%s' "$TDATA" | cut -f3)
        fi
    fi
```

Modifica la meta di `session_end`:
```bash
    devforge_log_timed "session_end" "success" "$SESSION_START_NS" \
        "{\"skills_used_count\":${SKILLS_USED_COUNT},\"commits_count\":${COMMITS_COUNT},\"total_tokens\":${TOKEN_TOTAL},\"output_tokens\":${TOKEN_OUTPUT},\"cost_estimate_eur\":${TOKEN_COST_EUR}}"
```

## Step 2 — Post-commit-review: arricchisci commit_created

Nel blocco commit detection, dopo `python3 token-collector.py update`:

Leggi token stats e calcola delta rispetto all'ultimo commit (stessa logica già definita nel piano token-counter, Task 5).

## Step 3 — Verifica

```bash
bash -n hooks/stop-gate
bash -n hooks/post-commit-review
```
Output atteso: nessun errore.
