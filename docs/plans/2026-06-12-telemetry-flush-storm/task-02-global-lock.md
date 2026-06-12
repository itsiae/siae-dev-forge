# Task 02 — C1: Lock globale mkdir-based su `devforge_upload_backlog`

**Goal:** Impedire che più flusher concorrenti processino lo stesso backlog. Mutex cross-process via `mkdir` atomico (`~/.claude/.devforge-flush.lock`), con stale-guard a 120s. Sostituisce il flock no-op su macOS.

## File coinvolti

- Modifica: `lib/telemetry-upload.sh` (funzione `devforge_upload_backlog`)
- Modifica: `tests/test_telemetry_flush_storm.sh` (aggiungi test 2-4)

## Step TDD bite-sized

### Step 1 — Scrivi i test fallenti

Aggiungi in `tests/test_telemetry_flush_storm.sh`, PRIMA della riga `echo ""` finale (`Totale:`):

```bash
# ── Test 2: lock held → second invocation returns 0 without processing ──
echo "Test 2: lock blocks concurrent invocation"
new_env
lock="${HOME}/.claude/.devforge-flush.lock"
mkdir -p "$lock"   # simulate a flush already in progress (fresh mtime)
seed_outbox "sess-B" 3 >/dev/null
_devforge_post_batch() { echo "200"; }
devforge_upload_backlog
pending=$(ls "${HOME}/.claude/devforge-state/sess-B/outbox"/batch-*.jsonl 2>/dev/null | wc -l | tr -d ' ')
assert_eq "locked: batches untouched" "3" "$pending"
cleanup_env

# ── Test 3: stale lock (>120s) recovered, flush proceeds ──
echo "Test 3: stale lock recovered"
new_env
lock="${HOME}/.claude/.devforge-flush.lock"
mkdir -p "$lock"
# Backdate lock dir mtime to 121s ago (portable: touch -t needs a timestamp; use -A on BSD / -d on GNU)
old_epoch=$(( $(date +%s) - 121 ))
if touch -d "@${old_epoch}" "$lock" 2>/dev/null; then :; else
    # BSD touch: -t CCYYMMDDhhmm.SS
    touch -t "$(date -r "${old_epoch}" +%Y%m%d%H%M.%S 2>/dev/null)" "$lock" 2>/dev/null || true
fi
seed_outbox "sess-C" 2 >/dev/null
_devforge_post_batch() { echo "200"; }
devforge_upload_backlog
acked=$(ls "${HOME}/.claude/devforge-state/sess-C/outbox/acked"/batch-*.jsonl 2>/dev/null | wc -l | tr -d ' ')
assert_eq "stale lock: flush proceeded" "2" "$acked"
cleanup_env

# ── Test 4: lock released after successful flush ──
echo "Test 4: lock released on exit"
new_env
seed_outbox "sess-D" 1 >/dev/null
_devforge_post_batch() { echo "200"; }
devforge_upload_backlog
lock_present=$([ -d "${HOME}/.claude/.devforge-flush.lock" ] && echo "yes" || echo "no")
assert_eq "lock removed after flush" "no" "$lock_present"
cleanup_env
```

### Step 2 — Esegui e verifica che falliscono

Run: `bash tests/test_telemetry_flush_storm.sh`
Output atteso: Test 2 FAIL (`locked: batches untouched` → attuale 0, manca il lock), Test 3/4 dipendono dall'implementazione. Almeno un FAIL.

### Step 3 — Implementa il lock

In `lib/telemetry-upload.sh`, modifica `devforge_upload_backlog`. Dopo le guardie endpoint esistenti (dopo `[ -d "$state_root" ] || return 0`, riga 139 attuale) e PRIMA del loop `for outbox_dir`, inserisci:

```bash
    # --- C1: global mkdir-based lock (cross-process mutex, replaces no-op flock) ---
    local lock_dir="${HOME}/.claude/.devforge-flush.lock"
    # Stale-lock guard: if lock dir older than 120s, the holder died — reclaim it.
    if [ -d "$lock_dir" ]; then
        local now_s lock_mtime
        now_s=$(date +%s)
        lock_mtime=$(stat -f%m "$lock_dir" 2>/dev/null || stat -c%Y "$lock_dir" 2>/dev/null || echo "$now_s")
        if [ "$((now_s - lock_mtime))" -ge 120 ] 2>/dev/null; then
            rmdir "$lock_dir" 2>/dev/null || rm -rf "$lock_dir" 2>/dev/null
        fi
    fi
    # Acquire: mkdir is atomic. If it fails, another flush is already running → bail.
    mkdir "$lock_dir" 2>/dev/null || return 0
```

Poi avvolgi il loop `for outbox_dir ... done` esistente in un subshell con trap EXIT che rilascia il lock (il subshell eredita `lock_dir`):

```bash
    (
        trap 'rmdir "$lock_dir" 2>/dev/null || rm -rf "$lock_dir" 2>/dev/null' EXIT
        for outbox_dir in "$state_root"/*/outbox "$state_root/.global-outbox"; do
            [ -d "$outbox_dir" ] || continue
            for batch in "$outbox_dir"/batch-*.jsonl; do
                [ -f "$batch" ] || continue
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

> Il subshell + `trap ... EXIT` garantisce il rilascio del lock su QUALSIASI uscita (return, errore, cap-break di Task 3). Più affidabile di `trap RETURN` (che richiede `set -T`).

### Step 4 — Esegui e verifica che passano

Run: `bash tests/test_telemetry_flush_storm.sh`
Output atteso: `PASS: locked: batches untouched`, `PASS: stale lock: flush proceeded`, `PASS: lock removed after flush`. FAIL=0.

### Step 5 — Commit

```
git add lib/telemetry-upload.sh tests/test_telemetry_flush_storm.sh
git commit -m "feat(telemetry): C1 lock globale mkdir-based su upload_backlog (stale-guard 120s)"
```

## Criteri di accettazione

- [ ] Lock acquisito via `mkdir "$lock_dir"`; fallimento → `return 0` immediato (no concorrenza).
- [ ] Stale-guard: lock dir con mtime ≥120s viene rimosso e riacquisito.
- [ ] Lock rilasciato su ogni uscita via subshell `trap ... EXIT`.
- [ ] `stat` portabile macOS (`-f%m`) + Linux (`-c%Y`).
- [ ] Test 2/3/4 PASS, FAIL=0.
