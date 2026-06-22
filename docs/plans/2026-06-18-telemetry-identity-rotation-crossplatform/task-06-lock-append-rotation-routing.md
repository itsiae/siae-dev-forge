# Task 06 — `_devforge_lock_append` 4-arg + cursor-aware rotation + routing (Capability B)

**AC:** AC3, AC4, AC6, AC9 · **File:** `lib/logger.sh`, `tests/zero-loss/unit/test_logger_rotation_crosstier.sh`

## Obiettivo

Cablare `_devforge_rotate_inline` (task-05) dentro il lockdir di `_devforge_lock_append`, estendere
la firma a 4 argomenti (BLOCK-5) e fare il routing `outbox_dir` in `_devforge_atomic_append` (GAP-B).
Risultato: rotazione effettiva su tier node/perl/bash (Windows) con parità a python3.

## RED — test che fallisce

Estendi `test_logger_rotation_crosstier.sh` (matrice interpreti):
- Per ogni profilo {python3, node-only, perl-only, bash-only}: 60 append da ~100B con
  `DEVFORGE_ROTATE_BYTES=2048` → `archived_files >= 1` (oggi node/perl/bash danno 0 → FAIL).
- Dopo rotazione: il file fresco riparte da cursor 0 (cursore live assente o azzerato), nessuna
  riga persa (totale righe global+archivi == 60).
- Cap 50MB: con `DEVFORGE_LOG_FILE` + più archivi e un cursore consumato, `_devforge_check_rotation`
  droppa l'archivio consumato anche su node-only.
- Atteso PRE-fix: FAIL su tier non-python3.

## GREEN — implementazione

1. Firma esplicita:
```bash
# $1=file  $2=line(con \n)  $3=rotate_bytes(default 0)  $4=outbox_dir(default "")
_devforge_lock_append() {
    local file="$1" line="$2" rotate_bytes="${3:-0}" outbox_dir="${4:-}"
    ...
```
2. Dentro il lockdir, **prima** dell'append node/perl/bash, chiama:
```bash
    _devforge_rotate_inline "$file" "$rotate_bytes" "$outbox_dir"
```
   (subito dopo `# Lock acquired.`).
3. In `_devforge_atomic_append`, dopo aver determinato `rotate_bytes`, calcola `outbox_dir` e
   passa entrambi:
```bash
    local outbox_dir=""
    if [ "$target_file" = "${DEVFORGE_LOG_FILE:-}" ]; then
        outbox_dir="${HOME}/.claude/devforge-state/.global-outbox"
    elif [ -n "${DEVFORGE_SESSION_DIR:-}" ]; then
        outbox_dir="${DEVFORGE_SESSION_DIR}/outbox"
    fi
    # BLOCK-3: se SESSION_DIR è vuoto, outbox_dir resta "" → cursor-move disabilitato
    # (mai produrre il path assoluto "/outbox"). La rotazione avviene comunque (senza cursor-move).
    _devforge_lock_append "$target_file" "${line}"$'\n' "$rotate_bytes" "$outbox_dir"
```
   (sostituisce la chiamata a 2 arg a logger.sh:97).

## REFACTOR

Verifica che il path python3 (atomic_write.py) resti invariato e che il fallback python3-fail
passi ora `rotate_bytes`/`outbox_dir` corretti. Commento ADR-6.

## Verifica / Done

- `bash tests/zero-loss/unit/test_logger_rotation_crosstier.sh` PASS su tutti i tier.
- No-regression: `test_logger_perl_fsync.sh`, `test_logger_uses_atomic_write.sh` verdi
  (la firma estesa è retro-compatibile: 3°/4° arg opzionali). Marca `[DONE]`.
