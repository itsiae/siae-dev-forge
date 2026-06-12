# Task 03 — C2: Cap per invocazione (oldest-first)

**Goal:** Limitare a `DEVFORGE_FLUSH_MAX_BATCHES` (default 100) il numero di batch processati per chiamata di `devforge_upload_backlog`, processandoli oldest-first. Drain incrementale del backlog invece di storm unico (13k curl seriali).

## File coinvolti

- Modifica: `lib/telemetry-upload.sh` (corpo subshell di `devforge_upload_backlog`)
- Modifica: `tests/test_telemetry_flush_storm.sh` (aggiungi test 5-6)

## Step TDD bite-sized

### Step 1 — Scrivi i test fallenti

Aggiungi in `tests/test_telemetry_flush_storm.sh` prima del blocco `Totale:`:

```bash
# ── Test 5: cap limits batches processed per invocation ──
echo "Test 5: cap caps processed batches"
new_env
export DEVFORGE_FLUSH_MAX_BATCHES=3
seed_outbox "sess-E" 10 >/dev/null
_devforge_post_batch() { echo "200"; }
devforge_upload_backlog
acked=$(ls "${HOME}/.claude/devforge-state/sess-E/outbox/acked"/batch-*.jsonl 2>/dev/null | wc -l | tr -d ' ')
remaining=$(ls "${HOME}/.claude/devforge-state/sess-E/outbox"/batch-*.jsonl 2>/dev/null | wc -l | tr -d ' ')
assert_eq "cap: exactly 3 acked" "3" "$acked"
assert_eq "cap: 7 remaining" "7" "$remaining"
unset DEVFORGE_FLUSH_MAX_BATCHES
cleanup_env

# ── Test 6: oldest-first ordering (lowest epoch in filename acked first) ──
echo "Test 6: oldest-first drain"
new_env
export DEVFORGE_FLUSH_MAX_BATCHES=1
ob="${HOME}/.claude/devforge-state/sess-F/outbox"
mkdir -p "$ob"
printf '{"old":1}\n' > "${ob}/batch-0000000001-pid.jsonl"
printf '{"new":1}\n' > "${ob}/batch-0000000009-pid.jsonl"
_devforge_post_batch() { echo "200"; }
devforge_upload_backlog
# The oldest (epoch ...001) must be the one acked
oldest_acked=$([ -f "${ob}/acked/batch-0000000001-pid.jsonl" ] && echo "yes" || echo "no")
assert_eq "oldest batch acked first" "yes" "$oldest_acked"
unset DEVFORGE_FLUSH_MAX_BATCHES
cleanup_env
```

### Step 2 — Esegui e verifica che falliscono

Run: `bash tests/test_telemetry_flush_storm.sh`
Output atteso: Test 5 FAIL (`cap: exactly 3 acked` → attuale 10, nessun cap), Test 6 dipende dall'ordering.

### Step 3 — Implementa il cap

In `lib/telemetry-upload.sh`, dentro `devforge_upload_backlog`, prima del subshell aggiungi la lettura del cap:

```bash
    local max_batches="${DEVFORGE_FLUSH_MAX_BATCHES:-100}"
```

Poi modifica il corpo del subshell per contare e fermarsi al cap. Sostituisci il subshell di Task 2 con:

```bash
    (
        trap 'rmdir "$lock_dir" 2>/dev/null || rm -rf "$lock_dir" 2>/dev/null' EXIT
        local processed=0
        for outbox_dir in "$state_root"/*/outbox "$state_root/.global-outbox"; do
            [ -d "$outbox_dir" ] || continue
            # Oldest-first: batch names embed epoch_ns; lexicographic sort = chronological.
            local batch
            for batch in $(ls -1 "$outbox_dir"/batch-*.jsonl 2>/dev/null | sort); do
                [ -f "$batch" ] || continue
                [ "$processed" -ge "$max_batches" ] 2>/dev/null && exit 0
                processed=$((processed + 1))
                local response
                response=$(_devforge_post_batch "$batch")
                if [ "$response" = "200" ] || [ "$response" = "201" ]; then
                    mkdir -p "${outbox_dir}/acked" 2>/dev/null
                    mv "$batch" "${outbox_dir}/acked/" 2>/dev/null || true
                fi
            done
        done
    )
```

> Cambiamenti vs Task 2: (a) `ls -1 ... | sort` forza l'ordine oldest-first esplicito (il glob è già ordinato ma `sort` lo rende robusto a locale/glob settings); (b) contatore `processed` con `exit 0` dal subshell al raggiungimento del cap — il `trap EXIT` rilascia comunque il lock.

### Step 4 — Esegui e verifica che passano

Run: `bash tests/test_telemetry_flush_storm.sh`
Output atteso: `PASS: cap: exactly 3 acked`, `PASS: cap: 7 remaining`, `PASS: oldest batch acked first`. FAIL=0.

### Step 5 — Commit

```
git add lib/telemetry-upload.sh tests/test_telemetry_flush_storm.sh
git commit -m "feat(telemetry): C2 cap per invocazione oldest-first (DEVFORGE_FLUSH_MAX_BATCHES=100)"
```

## Criteri di accettazione

- [ ] `DEVFORGE_FLUSH_MAX_BATCHES` (default 100) limita i batch processati per chiamata.
- [ ] Processing oldest-first via `ls -1 | sort` (epoch_ns nel nome).
- [ ] Cap raggiunto → `exit 0` dal subshell, lock rilasciato dal trap.
- [ ] Test 5/6 PASS, FAIL=0; test precedenti ancora verdi.
