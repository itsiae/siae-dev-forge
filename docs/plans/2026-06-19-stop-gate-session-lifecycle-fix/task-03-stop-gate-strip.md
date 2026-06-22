# Task 03 — Strip `hooks/stop-gate` (rimuovi rm + emit, solo gate)

**Goal:** `hooks/stop-gate` smette di emettere `session_end` e di cancellare lo stato di
sessione; resta solo la logica di gate (retrospective + verification) + flush zero-loss.

**File coinvolti:**
- Modifica: `hooks/stop-gate`
- Creazione: `tests/hooks/test_stop_gate_no_state_wipe.sh`

**Copre AC:** AC-1, AC-2, AC-3, AC-4. **Ordine commit:** dopo Task 02.

---

## Step TDD

### Step 1 — Scrivi il test fallente

Crea `tests/hooks/test_stop_gate_no_state_wipe.sh`:

```bash
#!/usr/bin/env bash
# test_stop_gate_no_state_wipe.sh — Stop non deve cancellare lo stato di sessione.
set -eu
PASS=0; FAIL=0
REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK="${REPO_ROOT}/hooks/stop-gate"

# transcript SENZA keyword di completamento
_no_completion() {
    cat <<'JSON'
{"messages":[{"role":"user","content":"continua"},{"role":"assistant","content":"sto lavorando sul punto successivo"}]}
JSON
}

_seed() {  # ritorna HOME temp con ledger popolato
    local th; th=$(mktemp -d); mkdir -p "$th/.claude"
    printf 'siae-git-workflow\n' > "$th/.claude/.devforge-session-skills"
    printf '2\n' > "$th/.claude/.devforge-session-commits"
    printf '1000000000\n' > "$th/.claude/.devforge-session-start-ns"
    echo "$th"
}

echo "=== AC-1: Stop no-completion NON cancella session-skills ==="
TH=$(_seed)
_no_completion | HOME="$TH" bash "$HOOK" >/dev/null 2>&1 || true
if [ -f "$TH/.claude/.devforge-session-skills" ] \
   && grep -qF 'siae-git-workflow' "$TH/.claude/.devforge-session-skills"; then
    echo "  PASS  session-skills preservato"; PASS=$((PASS+1))
else
    echo "  FAIL  session-skills cancellato (bug primario)"; FAIL=$((FAIL+1))
fi
rm -rf "$TH"

echo "=== AC-2: Stop stdin vuoto NON cancella commits/start-ns ==="
TH=$(_seed)
printf '' | HOME="$TH" bash "$HOOK" >/dev/null 2>&1 || true
if [ -f "$TH/.claude/.devforge-session-commits" ] \
   && [ -f "$TH/.claude/.devforge-session-start-ns" ]; then
    echo "  PASS  commits/start-ns preservati"; PASS=$((PASS+1))
else
    echo "  FAIL  commits/start-ns cancellati"; FAIL=$((FAIL+1))
fi
rm -rf "$TH"

echo "=== AC-3: completion + no verification → block (no-regression) ==="
TH=$(_seed); printf 'siae-retrospective\n' > "$TH/.claude/.devforge-session-skills"
OUT=$(printf '{"messages":[{"role":"assistant","content":"fatto, completato"}]}' \
    | HOME="$TH" env DEVFORGE_USE_SESSION_SCOPE=1 bash "$HOOK" 2>/dev/null || true)
if echo "$OUT" | grep -q '"decision": "block"' && echo "$OUT" | grep -q 'siae-verification'; then
    echo "  PASS  block emesso"; PASS=$((PASS+1))
else
    echo "  FAIL  atteso block: $(echo "$OUT" | head -2)"; FAIL=$((FAIL+1))
fi
rm -rf "$TH"

echo "=== AC-4: completion + verification → allow (no-regression) ==="
TH=$(_seed); printf 'siae-verification,siae-retrospective\n' > "$TH/.claude/.devforge-session-skills"
OUT=$(printf '{"messages":[{"role":"assistant","content":"fatto, completato"}]}' \
    | HOME="$TH" env DEVFORGE_USE_SESSION_SCOPE=1 bash "$HOOK" 2>/dev/null || true)
if ! echo "$OUT" | grep -q '"decision": "block"'; then
    echo "  PASS  allow"; PASS=$((PASS+1))
else
    echo "  FAIL  block inatteso: $(echo "$OUT" | head -2)"; FAIL=$((FAIL+1))
fi
rm -rf "$TH"

echo ""
echo "RESULT: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
```

### Step 2 — Esegui e verifica che fallisce

Run: `bash tests/hooks/test_stop_gate_no_state_wipe.sh`
Output atteso: AC-1 e AC-2 → FAIL (lo `stop-gate` attuale cancella i file via
`_devforge_emit_session_end`). AC-3/AC-4 → già PASS (gate invariato).

### Step 3 — Modifica `hooks/stop-gate`

1. **Rimuovi l'intero corpo di `_devforge_emit_session_end`** (righe ~48-130): la
   funzione e la sua logica di emissione migrano in `hooks/session-end` (Task 01).
   Elimina anche la definizione della funzione e la variabile `SESSION_END_GUARD`
   se non più usata altrove nel file.
2. **Sostituisci le 3 chiamate** a `_devforge_emit_session_end` con `exit 0`:
   - `stop-gate:134` (ramo stdin vuoto): `_devforge_emit_session_end` → `exit 0`
   - `stop-gate:184` (ramo no-completion): `_devforge_emit_session_end` → `exit 0`
   - `stop-gate:246` (ramo verification OK): rimuovi le 2 righe `rm -f` retro/block-count
     (sono cleanup innocui, opzionali da mantenere) + `_devforge_emit_session_end` → `exit 0`
3. **Aggiorna il commento `stop-gate:188`**:
   ```bash
   # Completion claim detected — SKILLS_LIST letta in-memory; lo stato di sessione
   # NON viene piu' toccato qui (session_end migrato a hooks/session-end).
   ```
4. **Conserva intatti**: flush opportunistico iniziale (`stop-gate:27`), lettura counter
   (`stop-gate:31-44`), retrospective gate (`stop-gate:193-204`), verification gate
   (`stop-gate:206-265`).

### Step 4 — Esegui e verifica che passa

Run: `bash tests/hooks/test_stop_gate_no_state_wipe.sh`
Output atteso: `RESULT: PASS=4 FAIL=0`

Run (no-regression sul test esistente): `bash tests/hooks/test_evidence_stop_gate.sh`
Output atteso: tutti PASS (la logica di gate è invariata).

### Step 5 — Commit

```bash
git add hooks/stop-gate tests/hooks/test_stop_gate_no_state_wipe.sh
git commit -m "fix(stop-gate): Stop non cancella piu' lo stato di sessione, solo gate (task-03)"
```

---

## Criteri di accettazione

- [ ] `_devforge_emit_session_end` rimossa da `stop-gate`; nessuna chiamata residua
      (`grep -n _devforge_emit_session_end hooks/stop-gate` → vuoto).
- [ ] Stop su transcript no-completion preserva `.devforge-session-skills` (AC-1).
- [ ] Stop su stdin vuoto preserva `.devforge-session-commits`/`-start-ns` (AC-2).
- [ ] Retrospective + verification gate invariati: AC-3 block, AC-4 allow.
- [ ] `tests/hooks/test_evidence_stop_gate.sh` resta verde (no-regression).
- [ ] `tests/hooks/test_stop_gate_no_state_wipe.sh` → `PASS=4 FAIL=0`.
- [ ] Commento `stop-gate:188` aggiornato (non più "file was cleaned").
