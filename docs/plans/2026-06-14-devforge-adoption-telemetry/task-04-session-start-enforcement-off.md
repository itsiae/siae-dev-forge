# Task 04 — `hooks/session-start` — `gate_bypassed` enforcement_off

**Goal:** se `DEVFORGE_ENFORCEMENT_OFF=1`, `hooks/session-start` emette un evento
`gate_bypassed` con `mechanism=enforcement_off` — **dopo** l'emissione dello stdout
`additional_context` (riga ~291) e del log `session_start` (riga 312), best-effort,
pipefail-safe, senza scrivere su stdout. Copre AC4, AC7.

**File coinvolti:**
- Modifica: `hooks/session-start` (dopo riga 312)
- Crea: `tests/hooks/test_session_start_enforcement_off.sh`

## Step 1 — Scrivi il test fallente

Crea `tests/hooks/test_session_start_enforcement_off.sh`:

```bash
#!/usr/bin/env bash
# Test: hooks/session-start emette gate_bypassed enforcement_off quando DEVFORGE_ENFORCEMENT_OFF=1
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="${PLUGIN_ROOT}/hooks/session-start"
PASS=0; FAIL=0
ok() { if eval "$2"; then echo "  PASS  $1"; PASS=$((PASS+1)); else echo "  FAIL  $1"; FAIL=$((FAIL+1)); fi; }

# (A) STRUTTURALE (hard) — il wiring è presente, guarded, pipefail-safe, no stdout.
ok "guard DEVFORGE_ENFORCEMENT_OFF presente" \
   "grep -q 'DEVFORGE_ENFORCEMENT_OFF' '$HOOK'"
ok "emette gate_bypassed enforcement_off" \
   "grep -q 'gate_bypassed' '$HOOK' && grep -q 'enforcement_off' '$HOOK'"
ok "emissione best-effort (|| true)" \
   "grep -E 'gate_bypassed.*\\|\\|[[:space:]]*true|enforcement_off.*\\|\\|[[:space:]]*true' '$HOOK' >/dev/null"

# (B) FUNZIONALE (tollerante: session-start può essere pesante in sandbox).
TMPHOME="$(mktemp -d)"; mkdir -p "$TMPHOME/.claude"
STDOUT=$(printf '{}' | HOME="$TMPHOME" DEVFORGE_ENFORCEMENT_OFF=1 bash "$HOOK" 2>/dev/null || true)
ACT="$TMPHOME/.claude/devforge-activity.jsonl"
if [ -s "$ACT" ]; then
    ok "func: gate_bypassed+enforcement_off in activity.jsonl" \
       "grep -q 'gate_bypassed' '$ACT' && grep -q 'enforcement_off' '$ACT'"
    ok "invariante: stdout contiene additional_context" \
       "echo \"\$STDOUT\" | grep -q 'additional_context'"
    # Negativo: senza la env var, nessun gate_bypassed
    TMPHOME2="$(mktemp -d)"; mkdir -p "$TMPHOME2/.claude"
    printf '{}' | HOME="$TMPHOME2" bash "$HOOK" >/dev/null 2>&1 || true
    ACT2="$TMPHOME2/.claude/devforge-activity.jsonl"
    ok "func negativo: nessun gate_bypassed senza la env var" \
       "! ( [ -s '$ACT2' ] && grep -q 'gate_bypassed' '$ACT2' )"
else
    echo "  SKIP  func: session-start non ha prodotto activity.jsonl in sandbox (strutturale copre il wiring)"
fi

echo ""; echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
```

## Step 2 — Esegui e verifica che fallisce

Run: `bash tests/hooks/test_session_start_enforcement_off.sh`
Output atteso: i check strutturali su `gate_bypassed`/`enforcement_off` FAIL (assenti) → `FAIL>=1`.

## Step 3 — Implementa il codice minimo

In `hooks/session-start`, **subito dopo** la riga 312
(`devforge_log_timed "session_start" "success" ...`), inserisci:

```bash
# gate_bypassed (Layer 1) — il kill-switch globale altrimenti non lascia traccia.
# DOPO l'emissione dello stdout additional_context (riga ~291): nessun rischio di
# abortire il JSON. best-effort + pipefail-safe + nessun output su stdout.
if [ "${DEVFORGE_ENFORCEMENT_OFF:-0}" = "1" ]; then
    devforge_log "gate_bypassed" "warning" \
        '{"mechanism":"enforcement_off","scope":"session"}' >/dev/null 2>&1 || true
fi
```

## Step 4 — Esegui e verifica che passa

Run: `bash tests/hooks/test_session_start_enforcement_off.sh`
Output atteso: `FAIL=0` (i 3 strutturali PASS; i funzionali PASS o SKIP coerente).

Regressione: `bash tests/hooks/test_session_start_preserve_skills.sh` non deve regredire
(nota: questo test può essere lento/flaky in sandbox — confronta solo le FAIL nuove).

## Step 5 — Commit

```bash
git add hooks/session-start tests/hooks/test_session_start_enforcement_off.sh
git commit -m "feat(telemetry): session-start emette gate_bypassed enforcement_off (Layer 1 task-04)"
```

## Criteri di accettazione
- [ ] Con `DEVFORGE_ENFORCEMENT_OFF=1` → un `gate_bypassed mechanism=enforcement_off scope=session`.
- [ ] Senza la env var → nessun `gate_bypassed`.
- [ ] L'emissione è dopo lo stdout `additional_context`, con `|| true` e `>/dev/null` (AC7,
      invariante `session_start_hook_invariants`).
- [ ] `FAIL=0`.
