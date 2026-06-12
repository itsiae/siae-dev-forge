# Task 05 — C4: GC sessioni morte (archivia, unità per-sessione)

**Goal:** Smettere di ri-scansionare in eterno gli outbox di ~967 sessioni morte. `devforge_gc_dead_outboxes` archivia (non cancella) l'intera directory-sessione in `~/.claude/devforge-state-archive/` quando è morta. Invocata 1×/giorno via sentinel.

> **WARN-5 (design):** la GC opera sulla **directory-sessione come unità atomica**, MAI sul singolo batch. Un batch non-acked può avere mtime >GC_DAYS se l'endpoint era irraggiungibile — GCarlo per età-file violerebbe zero-loss. La GC archivia, non droppa.

## File coinvolti

- Modifica: `lib/telemetry-upload.sh` (nuova funzione `devforge_gc_dead_outboxes` + wrapper `devforge_gc_maybe`)
- Modifica: `tests/test_telemetry_flush_storm.sh` (aggiungi test 10-12)

## Step TDD bite-sized

### Step 1 — Scrivi i test fallenti

Aggiungi in `tests/test_telemetry_flush_storm.sh` prima del blocco `Totale:`:

```bash
# Helper: backdate every file under a dir to N seconds ago (portable BSD/GNU)
backdate_dir() {
    local dir="$1" secs_ago="$2"
    local ep=$(( $(date +%s) - secs_ago ))
    local f
    find "$dir" -exec sh -c '
        if touch -d "@'"$ep"'" "$1" 2>/dev/null; then :; else
            touch -t "$(date -r '"$ep"' +%Y%m%d%H%M.%S 2>/dev/null)" "$1" 2>/dev/null || true
        fi
    ' _ {} \; 2>/dev/null
}

# ── Test 10: dead session (mtime > GC_DAYS) archived as a unit ──
echo "Test 10: dead-session outbox archived"
new_env
export DEVFORGE_FLUSH_GC_DAYS=14
export DEVFORGE_SID="sess-CURRENT"
ob=$(seed_outbox "sess-DEAD" 3)
backdate_dir "${HOME}/.claude/devforge-state/sess-DEAD" $(( 15 * 86400 ))
devforge_gc_dead_outboxes
archived=$([ -d "${HOME}/.claude/devforge-state-archive/sess-DEAD" ] && echo "yes" || echo "no")
gone_from_state=$([ -d "${HOME}/.claude/devforge-state/sess-DEAD" ] && echo "no" || echo "yes")
assert_eq "dead session archived" "yes" "$archived"
assert_eq "dead session removed from state" "yes" "$gone_from_state"
unset DEVFORGE_FLUSH_GC_DAYS DEVFORGE_SID
cleanup_env

# ── Test 11: recent session NOT archived ──
echo "Test 11: recent session preserved"
new_env
export DEVFORGE_FLUSH_GC_DAYS=14
export DEVFORGE_SID="sess-CURRENT"
seed_outbox "sess-RECENT" 2 >/dev/null   # fresh mtime
devforge_gc_dead_outboxes
still_there=$([ -d "${HOME}/.claude/devforge-state/sess-RECENT" ] && echo "yes" || echo "no")
assert_eq "recent session NOT archived" "yes" "$still_there"
unset DEVFORGE_FLUSH_GC_DAYS DEVFORGE_SID
cleanup_env

# ── Test 12: current session NEVER archived even if old ──
echo "Test 12: current session never archived"
new_env
export DEVFORGE_FLUSH_GC_DAYS=14
export DEVFORGE_SID="sess-CURRENT"
ob=$(seed_outbox "sess-CURRENT" 1)
backdate_dir "${HOME}/.claude/devforge-state/sess-CURRENT" $(( 30 * 86400 ))
devforge_gc_dead_outboxes
current_safe=$([ -d "${HOME}/.claude/devforge-state/sess-CURRENT" ] && echo "yes" || echo "no")
assert_eq "current session preserved despite age" "yes" "$current_safe"
unset DEVFORGE_FLUSH_GC_DAYS DEVFORGE_SID
cleanup_env
```

### Step 2 — Esegui e verifica che falliscono

Run: `bash tests/test_telemetry_flush_storm.sh`
Output atteso: Test 10 FAIL — `devforge_gc_dead_outboxes: command not found` o nessun archiviamento.

### Step 3 — Implementa la GC

In `lib/telemetry-upload.sh`, aggiungi DOPO `devforge_pending_count` (fine file):

```bash
# devforge_gc_dead_outboxes — archive (never delete) outboxes of dead sessions.
# Atomic unit = the session directory (WARN-5): never GC a single batch by file age.
# A session is eligible iff: (a) not the current $DEVFORGE_SID, AND
# (b) the newest mtime anywhere under its outbox is older than DEVFORGE_FLUSH_GC_DAYS.
devforge_gc_dead_outboxes() {
    local state_root="${HOME}/.claude/devforge-state"
    [ -d "$state_root" ] || return 0
    local archive_root="${HOME}/.claude/devforge-state-archive"
    local gc_days="${DEVFORGE_FLUSH_GC_DAYS:-14}"
    local current_sid="${DEVFORGE_SID:-}"
    local now_s threshold
    now_s=$(date +%s)
    threshold=$((gc_days * 86400))

    local sess_dir sid newest mtime f
    for sess_dir in "$state_root"/*/; do
        [ -d "${sess_dir}outbox" ] || continue
        sid=$(basename "$sess_dir")
        [ "$sid" = "$current_sid" ] && continue   # never GC current session
        # Newest mtime anywhere under the outbox (batches, acked, failed, cursors).
        newest=0
        for f in $(find "${sess_dir}outbox" -type f 2>/dev/null); do
            mtime=$(stat -f%m "$f" 2>/dev/null || stat -c%Y "$f" 2>/dev/null || echo 0)
            [ "$mtime" -gt "$newest" ] 2>/dev/null && newest=$mtime
        done
        [ "$newest" -eq 0 ] && continue   # empty outbox, leave for next pass
        if [ "$((now_s - newest))" -ge "$threshold" ] 2>/dev/null; then
            mkdir -p "$archive_root" 2>/dev/null
            mv "$sess_dir" "${archive_root}/" 2>/dev/null || true
        fi
    done
}

# devforge_gc_maybe — run GC at most once per day via a sentinel.
devforge_gc_maybe() {
    local sentinel="${HOME}/.claude/.devforge-last-gc"
    local now_s last
    now_s=$(date +%s)
    last=$(cat "$sentinel" 2>/dev/null || echo "0")
    if [ "$last" -gt 0 ] 2>/dev/null && [ "$((now_s - last))" -lt 86400 ] 2>/dev/null; then
        return 0
    fi
    echo "$now_s" > "$sentinel"
    devforge_gc_dead_outboxes 2>/dev/null || true
}
```

### Step 4 — Esegui e verifica che passano

Run: `bash tests/test_telemetry_flush_storm.sh`
Output atteso: Test 10/11/12 PASS. FAIL=0.

### Step 5 — Commit

```
git add lib/telemetry-upload.sh tests/test_telemetry_flush_storm.sh
git commit -m "feat(telemetry): C4 GC sessioni morte per-sessione (archivia, sentinel 1x/giorno)"
```

## Criteri di accettazione

- [ ] `devforge_gc_dead_outboxes` archivia l'intera dir-sessione (mai singoli batch).
- [ ] Eleggibile solo se non-corrente AND newest-mtime > GC_DAYS (default 14).
- [ ] Sessione corrente (`$DEVFORGE_SID`) MAI archiviata anche se vecchia.
- [ ] Sessione recente NON archiviata.
- [ ] `mv` verso archive, nessun `rm` (zero-loss).
- [ ] `devforge_gc_maybe` esegue al più 1×/giorno via sentinel `.devforge-last-gc`.
- [ ] Test 10/11/12 PASS, FAIL=0.
