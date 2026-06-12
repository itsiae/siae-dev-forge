# Task 01 — Refactor: estrai `_devforge_post_batch`

**Goal:** Estrarre la chiamata curl di upload in una funzione `_devforge_post_batch <file>` che fa `echo` dell'HTTP code, così i test possono iniettare risposte senza rete reale. Comportamento runtime invariato.

## File coinvolti

- Modifica: `lib/telemetry-upload.sh` (funzione `devforge_upload_backlog`, righe 144-158 attuali)
- Crea: `tests/test_telemetry_flush_storm.sh` (nuovo file di test dedicato)

## Step TDD bite-sized

### Step 1 — Scrivi il test fallente

Crea `tests/test_telemetry_flush_storm.sh` con questo contenuto completo:

```bash
#!/usr/bin/env bash
# Tests for telemetry flush storm fix (design 2026-06-12).
# Strategy: override _devforge_post_batch to inject HTTP codes, no real network.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

PASS=0
FAIL=0
assert_eq() {
    local name="$1" expected="$2" actual="$3"
    if [ "$expected" = "$actual" ]; then echo "  PASS: $name"; PASS=$((PASS+1));
    else echo "  FAIL: $name"; echo "    expected: '$expected'"; echo "    actual:   '$actual'"; FAIL=$((FAIL+1)); fi
}

# Fresh HOME + state per test
new_env() {
    TEST_TMP=$(mktemp -d)
    export HOME="$TEST_TMP"
    mkdir -p "${TEST_TMP}/.claude/devforge-state"
    export DEVFORGE_TELEMETRY_ENDPOINT="https://mock.invalid/v1/logs"
    export DEVFORGE_TELEMETRY_KEY="test-key"
}
cleanup_env() { rm -rf "$TEST_TMP"; }

# Seed an outbox with N batch files for a fake session
seed_outbox() {
    local sid="$1" n="$2"
    local ob="${HOME}/.claude/devforge-state/${sid}/outbox"
    mkdir -p "$ob"
    local i
    for i in $(seq 1 "$n"); do
        printf '{"e":%d}\n' "$i" > "${ob}/batch-000000000${i}-pid.jsonl"
    done
    echo "$ob"
}

source "${PLUGIN_ROOT}/lib/telemetry-upload.sh"

# ── Test 1: _devforge_post_batch is a defined function ──
echo "Test 1: _devforge_post_batch exists and is overridable"
new_env
_devforge_post_batch() { echo "200"; }   # override
seed_outbox "sess-A" 2 >/dev/null
devforge_upload_backlog
acked=$(ls "${HOME}/.claude/devforge-state/sess-A/outbox/acked"/batch-*.jsonl 2>/dev/null | wc -l | tr -d ' ')
assert_eq "all batches acked on 200" "2" "$acked"
cleanup_env

echo ""
echo "Totale: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
```

### Step 2 — Esegui e verifica che fallisce

Run: `bash tests/test_telemetry_flush_storm.sh`
Output atteso: `FAIL: all batches acked on 200` — perché `_devforge_post_batch` non esiste ancora, l'override non viene usato da `devforge_upload_backlog` (che chiama `curl` direttamente verso `mock.invalid` → non-200 → nessun ack).

### Step 3 — Implementa il refactor

In `lib/telemetry-upload.sh`, aggiungi la funzione PRIMA di `devforge_upload_backlog` (dopo la riga 130, prima del commento `# devforge_upload_backlog`):

```bash
# _devforge_post_batch <batch_file> — POST one batch, echo HTTP code.
# Extracted for testability: tests override this to inject codes without network.
# Returns "000" on curl transport failure (timeout/DNS/connection).
_devforge_post_batch() {
    local batch="$1"
    curl -s -o /dev/null -w "%{http_code}" \
        -X POST "$DEVFORGE_TELEMETRY_ENDPOINT" \
        -H "x-api-key: $DEVFORGE_TELEMETRY_KEY" \
        -H "Content-Type: application/jsonl" \
        --data-binary "@${batch}" \
        --max-time 10 2>/dev/null || echo "000"
}
```

Poi sostituisci nel loop di `devforge_upload_backlog` il blocco curl (righe 146-152 attuali):

```bash
            local response
            response=$(curl -s -o /dev/null -w "%{http_code}" \
                -X POST "$DEVFORGE_TELEMETRY_ENDPOINT" \
                -H "x-api-key: $DEVFORGE_TELEMETRY_KEY" \
                -H "Content-Type: application/jsonl" \
                --data-binary "@${batch}" \
                --max-time 10 2>/dev/null) || continue
```

con:

```bash
            local response
            response=$(_devforge_post_batch "$batch")
```

> Nota: rimuovi il `|| continue` — ora `_devforge_post_batch` ritorna sempre un codice ("000" su failure), quindi il ramo non-200 va eseguito (necessario per il contatore tentativi di Task 4). Il comportamento su 200/201 resta identico.

### Step 4 — Esegui e verifica che passa

Run: `bash tests/test_telemetry_flush_storm.sh`
Output atteso: `PASS: all batches acked on 200` · `Totale: PASS=1 FAIL=0`

### Step 5 — Commit

```
git add lib/telemetry-upload.sh tests/test_telemetry_flush_storm.sh
git commit -m "refactor(telemetry): estrai _devforge_post_batch per injection nei test"
```

## Criteri di accettazione

- [ ] `_devforge_post_batch` definita in `lib/telemetry-upload.sh`, ritorna HTTP code o "000".
- [ ] `devforge_upload_backlog` chiama `_devforge_post_batch` invece di curl inline.
- [ ] Rimosso il `|| continue` sul curl (il ramo non-200 ora è raggiungibile).
- [ ] `bash tests/test_telemetry_flush_storm.sh` → PASS=1 FAIL=0.
- [ ] Comportamento runtime su 200/201 invariato (batch → `acked/`).
