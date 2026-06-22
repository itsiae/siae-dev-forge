# Task 07 — Drain archivi globali in `devforge_batch_global` (Capability B)

**AC:** AC10 · **File:** `lib/telemetry-upload.sh`, `tests/zero-loss/unit/test_batch_global_archives.sh`

## Problema (BLOCK-1 / GAP-A)

Ora che la rotazione (task-06) ruota anche il file **globale** (`~/.claude/devforge-activity.jsonl`),
`devforge_batch_global` (telemetry-upload.sh:100) NON scansiona gli archivi globali
(`devforge-activity-*.archived.jsonl`) → righe stranded. Va reso simmetrico a
`devforge_create_batch` (per-basename cursor).

## RED — test che fallisce

Crea `tests/zero-loss/unit/test_batch_global_archives.sh`:
- Setup: `~/.claude/devforge-activity.jsonl` (live) + `devforge-activity-<ts>.archived.jsonl`
  (con 3 righe), nessun cursore archivio.
- Chiama `devforge_batch_global`.
- Asserisci: viene creato un batch in `.global-outbox` che include le righe dell'archivio;
  cursore per-basename `.cursor-devforge-activity-<ts>.archived.jsonl` scritto = size;
  l'archivio consumato viene rimosso (cleanup).
- Migrazione: se esiste il vecchio `.cursor-global`, viene rinominato in
  `.cursor-devforge-activity.jsonl` (offset preservato).
- Atteso PRE-fix: FAIL (archivi ignorati).

## GREEN — implementazione

Rifattorizza `devforge_batch_global` per iterare su archivi + live con cursore per-basename:

```bash
devforge_batch_global() {
    local global_file="${DEVFORGE_LOG_FILE:-${HOME}/.claude/devforge-activity.jsonl}"
    local dir base state_root outbox
    dir=$(dirname "$global_file"); base=$(basename "$global_file" .jsonl)
    state_root="${HOME}/.claude/devforge-state"; outbox="${state_root}/.global-outbox"
    mkdir -p "${outbox}/acked" 2>/dev/null || return 0

    # Migrazione one-shot dal vecchio cursore fisso .cursor-global.
    if [ -f "${outbox}/.cursor-global" ] && [ ! -f "${outbox}/.cursor-${base}.jsonl" ]; then
        mv "${outbox}/.cursor-global" "${outbox}/.cursor-${base}.jsonl" 2>/dev/null || true
    fi

    # Archivi (vecchio→nuovo) poi live.
    local files f bn cur_f cur sz batch epoch
    files=$(ls -1 "${dir}/${base}"-*.archived.jsonl 2>/dev/null | sort) || files=""
    [ -f "$global_file" ] && [ -s "$global_file" ] && files="${files}
${global_file}"
    for f in $files; do
        [ -f "$f" ] && [ -s "$f" ] || { _devforge_maybe_remove_archived_global "$f" "$outbox" "$base"; continue; }
        bn=$(basename "$f"); cur_f="${outbox}/.cursor-${bn}"
        cur=$(cat "$cur_f" 2>/dev/null | tr -d '\r' || echo "0")
        sz=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f" 2>/dev/null || echo "0")
        if [ "$sz" -gt "$cur" ] 2>/dev/null; then
            epoch=$(command -v _devforge_epoch_ns >/dev/null 2>&1 && _devforge_epoch_ns || date +%s)
            batch="${outbox}/batch-${epoch}-$$-${bn%.jsonl}.jsonl"
            tail -c +"$((cur + 1))" "$f" > "$batch" 2>/dev/null || { rm -f "$batch"; continue; }
            if [ -s "$batch" ]; then echo "$sz" > "$cur_f"; else rm -f "$batch"; fi
        fi
        _devforge_maybe_remove_archived_global "$f" "$outbox" "$base"
    done
}

# Cleanup archivio globale consumato (cursor>=size). Mai tocca il file live.
_devforge_maybe_remove_archived_global() {
    local f="$1" outbox="$2" base="$3" bn cur sz
    bn=$(basename "$f")
    case "$bn" in "${base}"-*.archived.jsonl) ;; *) return 0 ;; esac
    cur=$(cat "${outbox}/.cursor-${bn}" 2>/dev/null | tr -d '\r' || echo "0")
    sz=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f" 2>/dev/null || echo "0")
    if [ "$cur" -ge "$sz" ] 2>/dev/null && [ "$sz" -gt 0 ] 2>/dev/null; then rm -f "$f" "${outbox}/.cursor-${bn}"; fi
}
```

## REFACTOR

**Decisione prescritta** (BLOCK-4): **mantenere `_devforge_maybe_remove_archived_global` come
funzione separata**, NON unificare con `_devforge_maybe_remove_archived` (sessione). Motivo:
unificare richiederebbe modificare la firma della funzione di sessione (codice in produzione su tutti
gli OS) introducendo rischio di regressione sproporzionato al guadagno. Le due funzioni differiscono
per prefisso base (`activity` vs `devforge-activity`) e namespace cursore (`outbox` vs
`.global-outbox`). Documenta inline il perché della duplicazione intenzionale (commento + ADR-7).

## Verifica / Done

- `bash tests/zero-loss/unit/test_batch_global_archives.sh` PASS.
- No-regression: `test_telemetry_flush_storm.sh` verde (drain/gc esistenti). Marca `[DONE]`.
