# Task 3 — session_conflict event type + cleanup skill-start

**Stato:** [DONE]
**File coinvolti:** `hooks/session-start` (MODIFICA)
**AC coperti:** AC-3, AC-4

---

## Step 1 — Cambia event type per sessione concorrente

**File:** `hooks/session-start`
**Linea 226:**

Da:
```bash
        devforge_log "session_start" "warning" "{\"reason\":\"concurrent_session_detected\",\"old_pid\":${OLD_PID},\"new_pid\":${CURRENT_PID}}"
```

A:
```bash
        devforge_log "session_conflict" "warning" "{\"reason\":\"concurrent_session_detected\",\"old_pid\":${OLD_PID},\"new_pid\":${CURRENT_PID}}"
```

Cambio di una sola parola: `"session_start"` → `"session_conflict"`.

## Step 2 — Aggiungi cleanup skill-start

**File:** `hooks/session-start`
**Punto di innesto:** dopo linea 245 (`rm -f "${HOME}/.claude/.devforge-retro-reminded" 2>/dev/null`), prima del blocco "Cleanup stale sentinel files" (linea 247).

Aggiungi:
```bash
rm -f "${HOME}/.claude/.devforge-skill-start"
```

## Step 3 — Verifica session_conflict

```bash
grep "session_conflict" ~/.claude/devforge-activity.jsonl | tail -1 | python3 -m json.tool
```

Output atteso: evento con `"event": "session_conflict"` (non `session_start`).

Se non ci sono sessioni concorrenti attive, verifica che il nuovo event type non rompe il log:
```bash
grep "session_start" ~/.claude/devforge-activity.jsonl | tail -1 | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); assert d['status']=='success', f'Expected success, got {d[\"status\"]}'"
```

Output atteso: nessun errore (i `session_start` legittimi hanno status `success`, non più `warning`).

## Step 4 — Verifica cleanup skill-start

```bash
# Crea un file stale simulato
echo "stale|stale-skill|unknown" > ~/.claude/.devforge-skill-start

# Esegui session-start
bash hooks/session-start

# Verifica che il file è stato rimosso
ls -la ~/.claude/.devforge-skill-start 2>&1
```

Output atteso: `No such file or directory`.
