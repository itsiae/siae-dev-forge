# Task 08 — CRLF guard su tutte le letture cursore (Capability C)

**AC:** AC8 · **File:** `lib/logger.sh`, `lib/telemetry-upload.sh`, `tests/zero-loss/unit/test_logger_crlf_cursor.sh`

## Problema (HIGH-12)

Su Windows Git Bash con `core.autocrlf`, i file cursore possono contenere `\r`. Un
`cursor=$(cat cursor_file)` → `"2097152\r"` → `$((cursor + 1))` → *invalid arithmetic operator*
sotto `set -e` → abort. Va normalizzato ogni read numerico di cursore/stato.

## RED — test che fallisce

Crea `tests/zero-loss/unit/test_logger_crlf_cursor.sh`:
- Scrivi un cursore con CRLF: `printf '2097152\r\n' > "$outbox/.cursor-activity.jsonl"`.
- Esegui `devforge_create_batch` (telemetry-upload.sh) in subshell con `set -euo pipefail` →
  nessun abort, batch creato correttamente dal byte 2097153.
- Stesso per `devforge_batch_global` e `_devforge_check_rotation` (cursore con CRLF).
- Atteso PRE-fix: FAIL (abort aritmetico) sui punti non ancora normalizzati.

## GREEN — implementazione

Aggiungi `| tr -d '\r'` a OGNI lettura cursore/stato numerico. Punti noti:
- `lib/telemetry-upload.sh`: `devforge_create_batch` (`cursor=$(cat "$cursor_file" ...)`, r.53);
  `devforge_batch_global` (già normalizzato in task-07); `_devforge_maybe_remove_archived` (r.86);
  `devforge_gc_maybe`/stale-lock mtime reads se applicabile.
- `lib/logger.sh`: `_devforge_check_rotation` (`cursor=$(cat "$cursor_file" ...)`, r.288);
  `devforge_next_seq` (già in task-01); `_devforge_rotate_inline` (già in task-05).

Pattern uniforme:
```bash
cursor=$(cat "$cursor_file" 2>/dev/null | tr -d '\r' || echo "0")
```

## REFACTOR

Grep finale `grep -n 'cat .*cursor' lib/*.sh` per garantire copertura totale; nessun read cursore
senza `tr -d '\r'`.

## Verifica / Done

- `bash tests/zero-loss/unit/test_logger_crlf_cursor.sh` PASS.
- No-regression suite verde. Marca `[DONE]`.
