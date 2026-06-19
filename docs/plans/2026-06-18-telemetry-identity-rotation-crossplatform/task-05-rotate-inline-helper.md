# Task 05 — `_devforge_rotate_inline` helper (Capability B)

**AC:** AC3, AC9 · **File:** `lib/logger.sh`, `tests/zero-loss/unit/test_logger_rotation_crosstier.sh`

## Obiettivo

Helper bash che ruota un file di log se supera soglia, con parità a `atomic_write.py._rotate_if_needed`
+ **cursor-move** (BLOCK-2). Portabile, dentro-lock (chiamata da task-06).

## RED — test che fallisce

Crea `tests/zero-loss/unit/test_logger_rotation_crosstier.sh` (parte helper):
- `_devforge_rotate_inline "$f" 2048 "$outbox"` su file > 2KB → crea `${base}-<ts>.archived.jsonl`,
  `$f` non esiste più.
- File < soglia → no-op (nessun archivio).
- File inesistente → no-op, nessun abort.
- Collisione: pre-crea l'archivio col ts corrente → la funzione usa suffisso `-1`.
- Cursor-move: se `${outbox}/.cursor-$(basename $f)` esiste con valore `123`, dopo rotazione
  esiste `${outbox}/.cursor-${archived_basename}` con `123` e il cursore live è rimosso.
- Atteso PRE-fix: FAIL (funzione inesistente).

## GREEN — implementazione

```bash
# Ruota $file in archivio se size > rotate_bytes. Parità atomic_write.py + cursor-move.
# $1=file  $2=rotate_bytes  $3=outbox_dir (opzionale, per cursor-move)
_devforge_rotate_inline() {
    local file="$1" rotate_bytes="$2" outbox="${3:-}"
    [ "${rotate_bytes:-0}" -gt 0 ] 2>/dev/null || return 0
    local size; size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0)
    [ "${size:-0}" -gt "$rotate_bytes" ] 2>/dev/null || return 0
    local dir base ts archived i
    dir=$(dirname "$file"); base=$(basename "$file" .jsonl)
    ts=$(date +%s 2>/dev/null || echo 0)
    archived="${dir}/${base}-${ts}.archived.jsonl"
    if [ -e "$archived" ]; then
        for i in $(seq 1 999); do
            if [ ! -e "${dir}/${base}-${ts}-${i}.archived.jsonl" ]; then
                archived="${dir}/${base}-${ts}-${i}.archived.jsonl"; break
            fi
        done
    fi
    if ! mv "$file" "$archived" 2>/dev/null; then
        # C-21: rename fallito (permessi/iCloud lock/già ruotato). NON è perdita (la riga verrà
        # comunque scritta dall'append). Segnala telemetry_degraded UNA volta per non rumoreggiare.
        local _rs="${HOME}/.claude/.devforge-rotate-failed-warned"
        if [ ! -f "$_rs" ] && [ -e "$file" ]; then
            touch "$_rs" 2>/dev/null || true
            local _ts; _ts=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z" 2>/dev/null || echo "1970-01-01T00:00:00.000Z")
            printf '{"event":"telemetry_degraded","status":"warning","meta":{"reason":"rotation_failed"},"ts":"%s"}\n' \
                "$_ts" >> "${DEVFORGE_LOG_FILE:-${HOME}/.claude/devforge-activity.jsonl}" 2>/dev/null || true
        fi
        return 0   # già ruotato da altri o fallito → esci pulito, mai abort
    fi
    # cursor-move: l'archivio riprende dall'offset live → zero dup/perdita
    if [ -n "$outbox" ]; then
        local live_cur="${outbox}/.cursor-$(basename "$file")"
        local arch_cur="${outbox}/.cursor-$(basename "$archived")"
        [ -f "$live_cur" ] && mv "$live_cur" "$arch_cur" 2>/dev/null || true
    fi
    return 0
}
```

## REFACTOR

Commento di parità con `atomic_write.py:58-82` + nota ADR-6 (cursor-move supera python3).

## Verifica / Done

- `bash tests/zero-loss/unit/test_logger_rotation_crosstier.sh` PASS (parte helper).
- No-regression suite verde. Marca `[DONE]`.
