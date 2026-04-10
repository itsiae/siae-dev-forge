# Task 1 — Logger refactor: state per-sessione + identity pinning

**Stato:** [PENDING]
**File coinvolti:** `lib/logger.sh` (MODIFICA)
**AC coperti:** AC-1, AC-2, AC-3, AC-8
**Fase:** PR2

---

## Contesto

Oggi `lib/logger.sh` scrive in `~/.claude/devforge-activity.jsonl` (globale) e ricalcola user/sid ad ogni evento. Dopo questo task, scrive nella dir di sessione con dual write al globale.

## Step 1 — Aggiungi variabili di sessione pinnate

Dopo la riga `DEVFORGE_SID_FILE="${HOME}/.claude/.devforge-session-id"` (linea 6), aggiungi:

```bash
# Session state directory (set by session-start, used by all hooks)
DEVFORGE_SESSION_DIR=""
DEVFORGE_PINNED_USER=""
DEVFORGE_PINNED_SID=""

# Initialize session context from state dir
devforge_init_session() {
    local sid=$(devforge_get_sid)
    DEVFORGE_SESSION_DIR="${HOME}/.claude/devforge-state/${sid}"
    DEVFORGE_PINNED_SID="$sid"
    
    # Read pinned user from session dir
    if [ -f "${DEVFORGE_SESSION_DIR}/user.json" ] && command -v python3 >/dev/null 2>&1; then
        DEVFORGE_PINNED_USER=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('raw',''))" "${DEVFORGE_SESSION_DIR}/user.json" 2>/dev/null || echo "")
    fi
    [ -z "$DEVFORGE_PINNED_USER" ] && DEVFORGE_PINNED_USER=$(devforge_get_user)
    
    export DEVFORGE_SESSION_DIR DEVFORGE_PINNED_USER DEVFORGE_PINNED_SID
}
```

## Step 2 — Modifica devforge_log per dual write

Modifica la funzione `devforge_log` (linea 106) per scrivere in entrambi i file:

Alla fine della funzione (dopo il `printf` su `$DEVFORGE_LOG_FILE`), aggiungi:

```bash
    # Dual write: also append to session-specific activity log
    if [ -n "$DEVFORGE_SESSION_DIR" ] && [ -d "$DEVFORGE_SESSION_DIR" ]; then
        printf '{"ts":"%s","user":"%s","sid":"%s","branch":"%s","jira_id":%s,"project":"%s","event":"%s","status":"%s","meta":%s}\n' \
            "$ts" "$user" "$sid" "$branch" "$jira_json" "$project" "$event" "$status" "$meta" >> "${DEVFORGE_SESSION_DIR}/activity.jsonl" || true
    fi
```

## Step 3 — Modifica devforge_get_user per usare pinned identity

Modifica `devforge_get_user` (linea 61) per preferire l'identità pinnata:

```bash
devforge_get_user() {
    # Prefer pinned identity (set by session-start)
    if [ -n "$DEVFORGE_PINNED_USER" ]; then
        echo "$DEVFORGE_PINNED_USER"
        return
    fi
    # Fallback to dynamic resolution
    local user
    user=$(git config user.email 2>/dev/null)
    [ -z "$user" ] && user=$(git config --global user.email 2>/dev/null)
    [ -z "$user" ] && [ -f "${HOME}/.claude/.devforge-user" ] && user=$(cat "${HOME}/.claude/.devforge-user" 2>/dev/null)
    [ -z "$user" ] && user="${USER:-$(whoami 2>/dev/null || echo "unknown")}"
    echo "$user"
}
```

Stessa modifica per `devforge_get_sid` (linea 75): preferire `DEVFORGE_PINNED_SID`.

## Step 4 — Aggiungi devforge_next_seq

Aggiungi la funzione per il contatore atomico:

```bash
# Atomic session sequence counter (for event_id generation)
devforge_next_seq() {
    local seq_file="${DEVFORGE_SESSION_DIR}/seq"
    if [ -z "$DEVFORGE_SESSION_DIR" ] || [ ! -d "$DEVFORGE_SESSION_DIR" ]; then
        echo "0"
        return
    fi
    if command -v flock >/dev/null 2>&1; then
        (
            flock -n 9 || { echo "0"; return; }
            local current=$(cat "$seq_file" 2>/dev/null || echo "0")
            local next=$((current + 1))
            echo "$next" > "$seq_file"
            echo "$next"
        ) 9>"${seq_file}.lock"
    else
        # Fallback without flock (acceptable for single-thread hook usage)
        local current=$(cat "$seq_file" 2>/dev/null || echo "0")
        local next=$((current + 1))
        echo "$next" > "$seq_file"
        echo "$next"
    fi
}
```

## Step 5 — Verifica

```bash
bash -n lib/logger.sh
```
Output atteso: nessun errore.

Test funzionale (dopo che session-start crea la dir):
```bash
source lib/logger.sh
devforge_init_session
devforge_log "test_event" "success" '{"test":true}'
cat "${DEVFORGE_SESSION_DIR}/activity.jsonl" | python3 -m json.tool
```
Output atteso: evento JSON valido nella dir di sessione.
