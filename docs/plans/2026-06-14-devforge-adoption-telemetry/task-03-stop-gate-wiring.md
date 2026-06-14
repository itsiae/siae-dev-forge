# Task 03 — Wiring `devforge_emit_task_adoption` in `hooks/stop-gate`

**Goal:** invocare `devforge_emit_task_adoption` dentro `_devforge_emit_session_end`
(`hooks/stop-gate`), subito dopo l'emissione di `session_end`, best-effort e non-bloccante.
Copre AC1 (path end-to-end), AC7 (non-bloccante).

**File coinvolti:**
- Modifica: `hooks/stop-gate` (dentro `_devforge_emit_session_end`, dopo riga 99)
- Crea: `tests/hooks/test_stop_gate_task_adoption_wiring.sh`

**Dipendenza:** Task 02 (`lib/adoption-emit.sh`).

## Step 1 — Scrivi il test fallente

Crea `tests/hooks/test_stop_gate_task_adoption_wiring.sh`:

```bash
#!/usr/bin/env bash
# Test: hooks/stop-gate wira devforge_emit_task_adoption in _devforge_emit_session_end
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="${PLUGIN_ROOT}/hooks/stop-gate"
PASS=0; FAIL=0
ok() { if eval "$2"; then echo "  PASS  $1"; PASS=$((PASS+1)); else echo "  FAIL  $1"; FAIL=$((FAIL+1)); fi; }

# Strutturale: il wiring è presente dentro la funzione, con guard best-effort.
ok "source adoption-emit.sh presente" "grep -q 'adoption-emit.sh' '$HOOK'"
ok "chiamata devforge_emit_task_adoption presente" "grep -q 'devforge_emit_task_adoption' '$HOOK'"
ok "chiamata con guard best-effort (|| true)" \
   "grep -E 'devforge_emit_task_adoption[[:space:]]*2>/dev/null[[:space:]]*\\|\\|[[:space:]]*true' '$HOOK' >/dev/null"

# Smoke: stop-gate con stdin vuoto (path _devforge_emit_session_end) non crasha.
TMPHOME="$(mktemp -d)"
OUT=$(printf '' | HOME="$TMPHOME" bash "$HOOK" 2>/dev/null; echo "exit:$?")
ok "smoke: stdin vuoto exit 0" "echo '$OUT' | grep -q 'exit:0'"

echo ""; echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
```

## Step 2 — Esegui e verifica che fallisce

Run: `bash tests/hooks/test_stop_gate_task_adoption_wiring.sh`
Output atteso: i 3 check strutturali FAIL (wiring assente), smoke PASS → `FAIL=3`, exit 1.

## Step 3 — Implementa il codice minimo

In `hooks/stop-gate`, dentro `_devforge_emit_session_end()`, **subito dopo** il blocco che
emette `session_end` (la `devforge_log_timed "session_end" ...` che termina a riga 99) e
**prima** del commento `# PR #3 ADR-009: 3-line recap` (riga 101), inserisci:

```bash
    # task_adoption (Layer 1, design 2026-06-14) — best-effort, non blocca lo Stop.
    if [ -f "${PLUGIN_ROOT}/lib/adoption-emit.sh" ]; then
        # shellcheck disable=SC1091
        . "${PLUGIN_ROOT}/lib/adoption-emit.sh" 2>/dev/null || true
        devforge_emit_task_adoption 2>/dev/null || true
    fi
```

> Nota: `PLUGIN_ROOT` è già definito in `hooks/stop-gate` (usato per `token-collector.py` e
> `adoption-analyzer.py`). `devforge_log`/`devforge_compute_task_id` sono già in scope (lo
> stop-gate sorgenta `lib/logger.sh` e `lib/task-id.sh`). L'`. adoption-emit.sh` aggiunge solo
> la nuova funzione.

## Step 4 — Esegui e verifica che passa

Run: `bash tests/hooks/test_stop_gate_task_adoption_wiring.sh`
Output atteso: `PASS=4 FAIL=0` (exit 0).

Regressione stop-gate esistente:
Run: `bash tests/hooks/test_evidence_stop_gate.sh`
Output atteso: invariato rispetto a prima della modifica (nessuna nuova FAIL).

## Step 5 — Commit

```bash
git add hooks/stop-gate tests/hooks/test_stop_gate_task_adoption_wiring.sh
git commit -m "feat(telemetry): stop-gate emette task_adoption a session_end (Layer 1 task-03)"
```

## Criteri di accettazione
- [ ] `_devforge_emit_session_end` sorgenta `adoption-emit.sh` e chiama
      `devforge_emit_task_adoption` con guard `2>/dev/null || true`.
- [ ] stop-gate con stdin vuoto non crasha (exit 0) (AC7).
- [ ] `tests/hooks/test_evidence_stop_gate.sh` non regredisce.
- [ ] 4 PASS / 0 FAIL.
