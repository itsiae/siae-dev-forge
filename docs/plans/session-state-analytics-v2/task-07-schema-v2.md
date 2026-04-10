# Task 7 — Logger schema v2: event_id + canonical fields

**Stato:** [PENDING]
**File coinvolti:** `lib/logger.sh` (MODIFICA)
**AC coperti:** AC-9, AC-10
**Fase:** PR3
**Dipende da:** Task 1 (PR2)

---

## Step 1 — Aggiungi campi schema v2 a devforge_log

Modifica la funzione `devforge_log` per includere i nuovi campi.

Prima del `printf` finale, calcola i nuovi campi:

```bash
    local seq=$(devforge_next_seq)
    local event_id="${sid}-${seq}"
    local hook_name="${DEVFORGE_CURRENT_HOOK:-unknown}"
    local repo_root
    repo_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
    local project_canonical
    project_canonical=$(basename "$repo_root")
    local actor_canonical="$user"
```

Modifica il `printf` per includere i campi v2 (mantenendo i vecchi per backward compat):

```bash
    printf '{"event_id":"%s","schema_version":2,"session_seq":%d,"hook_name":"%s","actor_canonical":"%s","actor_raw":"%s","repo_root":"%s","project_canonical":"%s","ts":"%s","user":"%s","sid":"%s","branch":"%s","jira_id":%s,"project":"%s","event":"%s","status":"%s","meta":%s}\n' \
        "$event_id" "$seq" "$hook_name" "$actor_canonical" "$user" "$repo_root" "$project_canonical" \
        "$ts" "$user" "$sid" "$branch" "$jira_json" "$project" "$event" "$status" "$meta"
```

**Nota:** `user` e `project` restano per backward compat. `actor_canonical` e `project_canonical` sono i nuovi nomi.

## Step 2 — Stessa modifica per devforge_log_timed

Applica lo stesso pattern a `devforge_log_timed` (aggiunge event_id, schema_version, etc.).

## Step 3 — Aggiungi DEVFORGE_CURRENT_HOOK a ogni hook

Ogni hook che chiama `devforge_log` deve settare:

```bash
export DEVFORGE_CURRENT_HOOK="<nome-hook>"
```

All'inizio di ogni hook, subito dopo `set -euo pipefail`:
- `hooks/session-start`: `export DEVFORGE_CURRENT_HOOK="session-start"`
- `hooks/stop-gate`: `export DEVFORGE_CURRENT_HOOK="stop-gate"`
- `hooks/post-commit-review`: `export DEVFORGE_CURRENT_HOOK="post-commit-review"`
- `hooks/post-skill`: `export DEVFORGE_CURRENT_HOOK="post-skill"`
- `hooks/pre-commit`: `export DEVFORGE_CURRENT_HOOK="pre-commit"`
- `hooks/pr-gate`: `export DEVFORGE_CURRENT_HOOK="pr-gate"`
- `hooks/sub-skill-gate`: `export DEVFORGE_CURRENT_HOOK="sub-skill-gate"`
- `hooks/tdd-gate`: `export DEVFORGE_CURRENT_HOOK="tdd-gate"`
- `hooks/user-prompt-context`: `export DEVFORGE_CURRENT_HOOK="user-prompt-context"`
- `hooks/batch-checkpoint`: `export DEVFORGE_CURRENT_HOOK="batch-checkpoint"`
- `hooks/batch-reset`: `export DEVFORGE_CURRENT_HOOK="batch-reset"`

## Step 4 — Verifica

```bash
bash -n lib/logger.sh
# Test: verifica che un evento ha schema_version e event_id
source lib/logger.sh
devforge_init_session
devforge_log "test" "success" '{"check":"schema_v2"}'
tail -1 "${DEVFORGE_SESSION_DIR}/activity.jsonl" | python3 -c "
import json,sys
d=json.loads(sys.stdin.read())
assert d['schema_version'] == 2, f'Expected schema_version 2, got {d.get(\"schema_version\")}'
assert 'event_id' in d, 'Missing event_id'
print('PASS: schema v2 fields present')
"
```
Output atteso: `PASS: schema v2 fields present`
