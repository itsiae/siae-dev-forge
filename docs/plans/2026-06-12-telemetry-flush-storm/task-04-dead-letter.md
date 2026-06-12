# Task 04 — C3: Dead-letter dopo K tentativi → `failed/`

**Goal:** Un batch che riceve non-200 ripetuti viene spostato in `outbox/failed/` dopo `DEVFORGE_FLUSH_MAX_TRIES` (default 5) tentativi, invece di essere ritentato in eterno. **Zero-loss**: isolato, non cancellato. **Dipende da Task 2 (C1)** — race-safe solo sotto lock.

> **PREREQUISITO HARD (WARN-3):** Task 2 deve essere `[DONE]`. Senza il lock C1, due flusher concorrenti possono leggere lo stesso contatore `.tries-*` e fare race sul `mv`. NON implementare C3 senza C1.

## File coinvolti

- Modifica: `lib/telemetry-upload.sh` (ramo non-200 nel subshell di `devforge_upload_backlog`)
- Modifica: `tests/test_telemetry_flush_storm.sh` (aggiungi test 7-9)

## Step TDD bite-sized

### Step 1 — Scrivi i test fallenti

Aggiungi in `tests/test_telemetry_flush_storm.sh` prima del blocco `Totale:`:

```bash
# ── Test 7: non-200 increments tries, batch stays until K reached ──
echo "Test 7: tries counter increments, no premature failed/"
new_env
export DEVFORGE_FLUSH_MAX_TRIES=5
ob=$(seed_outbox "sess-G" 1)
_devforge_post_batch() { echo "500"; }
devforge_upload_backlog   # try 1
devforge_upload_backlog   # try 2
still_pending=$(ls "$ob"/batch-*.jsonl 2>/dev/null | wc -l | tr -d ' ')
no_failed=$([ -d "$ob/failed" ] && ls "$ob/failed"/batch-*.jsonl 2>/dev/null | wc -l | tr -d ' ' || echo 0)
assert_eq "after 2 non-200: still pending" "1" "$still_pending"
assert_eq "after 2 non-200: failed/ empty" "0" "$no_failed"
unset DEVFORGE_FLUSH_MAX_TRIES
cleanup_env

# ── Test 8: after K non-200, batch moves to failed/ and is not retried ──
echo "Test 8: dead-letter after K tries"
new_env
export DEVFORGE_FLUSH_MAX_TRIES=3
ob=$(seed_outbox "sess-H" 1)
_devforge_post_batch() { echo "500"; }
devforge_upload_backlog; devforge_upload_backlog; devforge_upload_backlog   # 3 tries
in_failed=$(ls "$ob/failed"/batch-*.jsonl 2>/dev/null | wc -l | tr -d ' ')
in_outbox=$(ls "$ob"/batch-*.jsonl 2>/dev/null | wc -l | tr -d ' ')
assert_eq "batch in failed/ after K" "1" "$in_failed"
assert_eq "batch no longer in outbox" "0" "$in_outbox"
# Not retried: a 4th call must not touch failed/ count
devforge_upload_backlog
still_failed=$(ls "$ob/failed"/batch-*.jsonl 2>/dev/null | wc -l | tr -d ' ')
assert_eq "failed batch not retried" "1" "$still_failed"
unset DEVFORGE_FLUSH_MAX_TRIES
cleanup_env

# ── Test 9: success resets/removes the tries sidecar ──
echo "Test 9: 200 clears tries sidecar"
new_env
ob=$(seed_outbox "sess-I" 1)
batch_name=$(basename "$(ls "$ob"/batch-*.jsonl)")
_devforge_post_batch() { echo "500"; }
devforge_upload_backlog   # creates .tries-<name>
tries_after_fail=$([ -f "${ob}/.tries-${batch_name}" ] && echo "yes" || echo "no")
assert_eq "tries sidecar created on fail" "yes" "$tries_after_fail"
_devforge_post_batch() { echo "200"; }
devforge_upload_backlog   # success → ack + remove sidecar
sidecar_gone=$([ -f "${ob}/.tries-${batch_name}" ] && echo "no" || echo "yes")
assert_eq "tries sidecar removed on success" "yes" "$sidecar_gone"
cleanup_env
```

### Step 2 — Esegui e verifica che falliscono

Run: `bash tests/test_telemetry_flush_storm.sh`
Output atteso: Test 8 FAIL (`batch in failed/ after K` → attuale 0, nessun dead-letter); il batch resta in outbox in eterno.

### Step 3 — Implementa il dead-letter

In `lib/telemetry-upload.sh`, dentro `devforge_upload_backlog`, leggi il max_tries vicino a `max_batches`:

```bash
    local max_tries="${DEVFORGE_FLUSH_MAX_TRIES:-5}"
```

Poi nel subshell, sostituisci il blocco `if [ "$response" = "200" ]...` con la versione che gestisce sia il successo (rimuove sidecar) sia il fallimento (incrementa, dead-letter a K):

```bash
                if [ "$response" = "200" ] || [ "$response" = "201" ]; then
                    mkdir -p "${outbox_dir}/acked" 2>/dev/null
                    mv "$batch" "${outbox_dir}/acked/" 2>/dev/null || true
                    rm -f "${outbox_dir}/.tries-$(basename "$batch")" 2>/dev/null
                else
                    # Non-200 (incl. "000" transport fail, 4xx, 5xx): count the attempt.
                    local tries_file tries
                    tries_file="${outbox_dir}/.tries-$(basename "$batch")"
                    tries=$(cat "$tries_file" 2>/dev/null || echo "0")
                    tries=$((tries + 1))
                    echo "$tries" > "$tries_file"
                    if [ "$tries" -ge "$max_tries" ] 2>/dev/null; then
                        # Dead-letter: isolate, never delete (zero-loss).
                        mkdir -p "${outbox_dir}/failed" 2>/dev/null
                        mv "$batch" "${outbox_dir}/failed/" 2>/dev/null || true
                        rm -f "$tries_file" 2>/dev/null
                    fi
                fi
```

> Safe sotto lock C1: un solo flusher legge/scrive `.tries-*` e fa il `mv`. I 4xx persistenti finiscono comunque in `failed/` dopo K — sono non recuperabili così come sono, ma restano su disco per ispezione/reinvio manuale.

### Step 4 — Esegui e verifica che passano

Run: `bash tests/test_telemetry_flush_storm.sh`
Output atteso: Test 7/8/9 tutti PASS. FAIL=0.

### Step 5 — Commit

```
git add lib/telemetry-upload.sh tests/test_telemetry_flush_storm.sh
git commit -m "feat(telemetry): C3 dead-letter dopo K tentativi -> failed/ (zero-loss, sotto lock C1)"
```

## Criteri di accettazione

- [ ] Non-200 incrementa `.tries-<batch>`; batch resta in outbox finché tries < K.
- [ ] A `tries >= DEVFORGE_FLUSH_MAX_TRIES` (default 5) → batch in `outbox/failed/`, sidecar rimosso.
- [ ] Batch in `failed/` NON più ritentato dalle invocazioni successive.
- [ ] 200/201 rimuove il sidecar `.tries-<batch>`.
- [ ] Nessun `rm` del batch — solo `mv` in `failed/` (zero-loss).
- [ ] Test 7/8/9 PASS, FAIL=0.
