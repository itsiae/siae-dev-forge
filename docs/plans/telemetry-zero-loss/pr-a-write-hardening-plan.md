# PR-A — Write-side hardening + Hook flush triggers

**Branch target:** `feat/telemetry-write-hardening` (da derivare da `main`)
**SP-Augmented:** 6
**Riferimento design:** `docs/plans/2026-04-13-telemetry-zero-loss-design.md` §5.1, §5.2
**Status:** in attesa approvazione design, NON iniziare implementazione

## Pre-flight

1. `git status` — verify working tree (oggi 18 file dirty, da gestire prima di branch)
2. `git stash push -m "wip pre-zero-loss-PR-A"` (untracked sopravvivono al checkout, le 2 M `lib/logger.sh` + `tests/analyze-token-usage.py` vanno stashate)
3. `git checkout main && git pull origin main`
4. `git checkout -b feat/telemetry-write-hardening`
5. Verify `git log --oneline main..HEAD` = 0 commits (parto pulito)

## Subtask bite-sized (TDD ciclo per ognuno)

### A1 — Scaffold tests/zero-loss/

```bash
mkdir -p tests/zero-loss/{unit,integration,chaos,replay,acceptance}
touch tests/zero-loss/{unit,integration,chaos,replay,acceptance}/conftest.py
touch tests/zero-loss/manual-checklist.md
touch tests/zero-loss/Makefile
```

**Files attesi:**
- `tests/zero-loss/conftest.py` — fixtures comuni (tmp_session_dir, mock_s3, ecc.)
- `tests/zero-loss/Makefile` — target `test-unit`, `test-integration`, `test-chaos`, `test-acceptance`
- `tests/zero-loss/manual-checklist.md` — checklist per Mac/Win OS restart manuale (edge #10)

**Commit:** `chore(tests): scaffold tests/zero-loss/ structure`

### A2 — Test atomic_write_python (RED prima)

**File:** `tests/zero-loss/unit/test_atomic_write.py`

Test list (RED — devono fallire perché `atomic_write.py` non esiste ancora):

```python
def test_concurrent_threads_no_truncation()  # edge #1
def test_fsync_on_write()                    # edge durability
def test_handles_size_decrease()             # edge #13 truncate
def test_case_sensitive_event_id()           # edge #16
def test_utf8_roundtrip_emoji_accents()      # edge #17
def test_lock_shared_with_bash()             # BLOCK-2 unified lock test
def test_kill_during_write_no_partial()      # edge #2
```

Comando: `pytest tests/zero-loss/unit/test_atomic_write.py -x` → **deve fallire** (ImportError)

**Commit:** `test(zero-loss): RED tests for atomic_write Python utility`

### A3 — GREEN: implementa `lib/atomic_write.py`

Cross-OS lock+fsync wrapper. Schema:

```python
"""Cross-OS atomic append for activity.jsonl with shared bash lock.
Lock file path SAME as bash devforge_with_lock: ${DEVFORGE_SESSION_DIR}/.activity.lock
"""
import os, sys, json
from pathlib import Path

if sys.platform == 'win32':
    import msvcrt
    def _lock(fd):    msvcrt.locking(fd.fileno(), msvcrt.LK_LOCK, 1)
    def _unlock(fd):  msvcrt.locking(fd.fileno(), msvcrt.LK_UNLCK, 1)
else:
    import fcntl
    def _lock(fd):    fcntl.flock(fd.fileno(), fcntl.LOCK_EX)
    def _unlock(fd):  fcntl.flock(fd.fileno(), fcntl.LOCK_UN)

def atomic_append(activity_path: Path, line: str, lock_path: Path = None) -> None:
    """Append line + fsync, holding shared lock with bash devforge_with_lock."""
    lock_path = lock_path or activity_path.parent / '.activity.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, 'w') as lockfd:
        _lock(lockfd)
        try:
            with open(activity_path, 'a', encoding='utf-8') as f:
                if not line.endswith('\n'):
                    line += '\n'
                f.write(line)
                f.flush()
                os.fsync(f.fileno())
        finally:
            _unlock(lockfd)
```

Comando: `pytest tests/zero-loss/unit/test_atomic_write.py -x` → **deve passare**

**Commit:** `feat(telemetry): atomic_append cross-OS with shared bash lock`

### A4 — Test rotation (RED)

**File:** `tests/zero-loss/unit/test_rotation.py`

```python
def test_rotates_at_5mb()                    # edge #12
def test_batcher_reads_archived_in_order()   # batcher continuity
def test_cap_50mb_drops_oldest()             # quota
def test_local_quota_exceeded_event_emitted()
```

**Commit:** `test(zero-loss): RED tests for activity rotation`

### A5 — GREEN: rotation in `lib/logger.sh`

Modifica `devforge_append_jsonl` (logger.sh) per fare rotation pre-append:

```bash
_devforge_check_rotation() {
    local activity="$1"
    local size
    size=$(stat -f%z "$activity" 2>/dev/null || stat -c%s "$activity" 2>/dev/null || echo "0")
    if [ "$size" -gt 5242880 ]; then  # 5MB
        local ts
        ts=$(date +%s)
        mv "$activity" "${activity%.jsonl}-${ts}.archived.jsonl"
        : > "$activity"
    fi
}
```

Modifica `devforge_create_batch` (telemetry-upload.sh) per leggere anche `activity-*.archived.jsonl`.

**Commit:** `feat(telemetry): activity.jsonl rotation at 5MB + batcher reads archived`

### A6 — Disk space gate (RED+GREEN)

Test:
```python
def test_aborts_below_100mb()  # edge #3
def test_emits_local_disk_full_event_on_recovery()
```

Implementazione in `lib/logger.sh` `devforge_log`:
```bash
_devforge_disk_gate() {
    local free_kb
    free_kb=$(df -k "${DEVFORGE_SESSION_DIR:-$HOME/.claude}" | tail -1 | awk '{print $4}')
    if [ "$free_kb" -lt 102400 ]; then  # <100MB
        # queue evento per recovery
        echo "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "${HOME}/.claude/.devforge-disk-full-events.tmp"
        return 1  # skip write
    fi
    return 0
}
```

**Commit:** `feat(telemetry): disk space gate (<100MB free skips write + recovery event)`

### A7 — Clock skew NTP (RED+GREEN)

Test:
```python
def test_detects_skew_above_3600s()         # edge #7
def test_fallback_when_ntp_unreachable()    # edge #18
```

Implementazione in `hooks/session-start`:
```bash
# Dopo session creation, prima di emit session_start
if command -v curl >/dev/null 2>&1; then
    NTP_DATE=$(curl -sf -m 2 https://time.cloudflare.com/ -I 2>/dev/null | grep -i "^date:" | sed 's/^[Dd]ate: //')
    if [ -n "$NTP_DATE" ]; then
        NTP_EPOCH=$(date -j -f "%a, %d %b %Y %H:%M:%S %Z" "$NTP_DATE" +%s 2>/dev/null || \
                    date -d "$NTP_DATE" +%s 2>/dev/null || echo "0")
        LOCAL_EPOCH=$(date -u +%s)
        SKEW=$((LOCAL_EPOCH - NTP_EPOCH))
        SKEW_ABS=${SKEW#-}
        if [ "$SKEW_ABS" -gt 3600 ]; then
            echo '{"force_received_at":true,"clock_skew_sec":'"$SKEW"'}' \
              > "${DEVFORGE_SESSION_DIR}/clock-skew.json"
            devforge_log "clock_skew_detected" "warning" \
              "{\"skew_sec\":$SKEW,\"ntp_source\":\"time.cloudflare.com\"}"
        fi
    fi
fi
```

**Commit:** `feat(telemetry): NTP clock skew detection at session-start`

### A8 — UTF-8 escape verification (test only)

`escape_for_json` esiste già in `logger.sh:143-151`. Solo aggiungere test:
```python
def test_utf8_roundtrip_emoji_accents()  # già nel test_atomic_write.py
def test_escape_for_json_handles_quotes_backslashes()
```

**Commit:** `test(telemetry): UTF-8 escape coverage`

### A9 — Hook flush triggers (BLOCK-1 fix)

Nuovo file `hooks/devforge-flusher`:
```bash
#!/usr/bin/env bash
# PostToolUse flush con cooldown 60s
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LAST_FLUSH="${HOME}/.claude/.devforge-last-flush"
NOW=$(date +%s)
LAST=$(cat "$LAST_FLUSH" 2>/dev/null || echo 0)
[ $((NOW - LAST)) -lt 60 ] && exit 0
echo "$NOW" > "$LAST_FLUSH"
source "${PLUGIN_ROOT}/lib/telemetry-upload.sh" 2>/dev/null || exit 0
devforge_upload_logs 2>/dev/null &
exit 0
```

Modifica `hooks.json` (in `infra/hooks-config/hooks.json`):
```jsonc
"PostToolUse": [
  // entries esistenti
  {
    "matcher": "*",
    "hooks": [{"type": "command",
               "command": "bash hooks/devforge-flusher",
               "async": true}]
  }
]
```

Modifica `hooks/stop-gate`: spostare `devforge_upload_logs` da background async a sync, prima dei gate.

Modifica `hooks/devforge-context-always`: aggiungere flush opportunistico se pending > 0.

**Commit:** `feat(telemetry): hook flush triggers (PostToolUse cooldown + Stop sync + UserPromptSubmit opportunistic)`

### A10 — Test integration (PR-A scope)

**File:** `tests/zero-loss/integration/test_write_hardening_e2e.py`

```python
def test_50_concurrent_writes_no_loss()
def test_kill_during_write_recovers()  # edge #2 + #10
def test_rotation_during_active_session()
```

Setup: docker-compose con LocalStack opzionale (per PR-A non necessario, PR-B sì).

**Commit:** `test(zero-loss): integration tests for write hardening`

### A11 — Windows smoke (CI only, locale opzionale)

**File:** `.github/workflows/zero-loss-ci.yml` (nuovo, parziale per PR-A)

Job `windows-smoke` che esegue `tests/zero-loss/unit/test_atomic_write.py` su Windows runner.

**Commit:** `ci(zero-loss): GitHub Actions workflow with windows-smoke job`

## Pre-PR Checklist (siae-finishing-branch)

- [ ] Tutti i test passano: `make -C tests/zero-loss test-unit`
- [ ] Coverage zero-loss/ ≥ 90%
- [ ] Branching strategy check: PR verso `main` da branch `feat/telemetry-write-hardening` → OK
- [ ] siae-blind-review: review cieca con solo design doc, vedere se trova gap
- [ ] siae-verification: prima di marcare done, evidenza esplicita
- [ ] siae-git-workflow: commit messaggi conventional commits
- [ ] PR description usa template

## Post-merge

- [ ] Verifica zero parse errors in v2 nuovi (7gg post-merge)
- [ ] Verifica che hook flush triggers sparino correttamente (CloudWatch/local logs)
- [ ] Pronto per PR-B (transport-side)

## Risk register

| Risk | Mitigation |
|---|---|
| Race condition lib/logger.sh modificato concorrente | Lock file shared con Python verificato in test A2 |
| Windows test fails (msvcrt edge) | windows-smoke job in CI dal day-one, fix immediato |
| Rotation breaks ongoing batch | test A4 copre, batch usa file lista snapshot pre-rotation |
| Disk gate troppo aggressivo | soglia 100MB conservativa; emit recovery event per non perdere il fatto |
| NTP HTTPS bloccato da firewall | test A7 fallback, NTP è opzionale (non blocca session-start) |

---

**Status:** scratch plan. Sarà committato come parte del primo commit di PR-A.
**Next step quando design approvato:** `siae-writing-plans` per espansione bite-sized di ogni subtask + handoff a `siae-tdd` per ciclo RED-GREEN-REFACTOR.
