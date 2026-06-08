# Task 05 — top-level `auth_email`/`auth_account_uuid`/`repo_remote` in ogni evento

**Stato:** [PENDING]
**File:** `lib/logger.sh` (`devforge_log` ~455-516 e `devforge_log_timed` ~520-586)
**Dipende da:** Task 04 (env pinnate)
**Obiettivo:** ogni evento emesso porta i 3 campi top-level. `repo_remote` calcolato per-evento
(`git remote get-url origin`); auth letti dalle env pinnate (no re-read del JSON 141KB).

## RED — Test (`tests/hooks/test_log_toplevel_attribution.sh`)
```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
FAIL=0
export DEVFORGE_FORCE_BASH_FALLBACK=1

assert_json_field() { # file, jq-ish field via python, expected
    python3 -c "import json,sys; print(json.loads(open(sys.argv[1]).read().strip().splitlines()[-1]).get(sys.argv[2],'MISSING'))" "$1" "$2"
}

# Repo con origin + env auth pinnate
TMP_REPO=$(mktemp -d); cd "$TMP_REPO"; git init -q
git config user.email "t@t.local"; git config user.name "T"
git remote add origin "https://github.com/itsiae/sport-demo.git"
echo x > f; git add f; git commit -q -m c
source "${PLUGIN_ROOT}/lib/logger.sh"
export DEVFORGE_LOG_FILE=$(mktemp); export DEVFORGE_SESSION_DIR=$(mktemp -d)
export DEVFORGE_AUTH_EMAIL="carmen.lasala@siae.it"; export DEVFORGE_AUTH_ACCOUNT_UUID="abc-123"

devforge_log "commit_created" "success" "{\"commit_sha\":\"deadbeef\"}"
[ "$(assert_json_field "$DEVFORGE_LOG_FILE" auth_email)" = "carmen.lasala@siae.it" ] || { echo "FAIL: auth_email top-level"; FAIL=1; }
[ "$(assert_json_field "$DEVFORGE_LOG_FILE" auth_account_uuid)" = "abc-123" ] || { echo "FAIL: auth_account_uuid top-level"; FAIL=1; }
[ "$(assert_json_field "$DEVFORGE_LOG_FILE" repo_remote)" = "https://github.com/itsiae/sport-demo.git" ] || { echo "FAIL: repo_remote"; FAIL=1; }
# commit_sha resta nel meta
grep -qF '"commit_sha":"deadbeef"' "$DEVFORGE_LOG_FILE" || { echo "FAIL: commit_sha nel meta"; FAIL=1; }

# devforge_log_timed: stessi 3 campi + JSON valido
START=$(_devforge_epoch_ns)
devforge_log_timed "skill_completed" "success" "$START" "{}"
[ "$(assert_json_field "$DEVFORGE_LOG_FILE" repo_remote)" = "https://github.com/itsiae/sport-demo.git" ] || { echo "FAIL: repo_remote timed"; FAIL=1; }
[ "$(assert_json_field "$DEVFORGE_LOG_FILE" auth_email)" = "carmen.lasala@siae.it" ] || { echo "FAIL: auth_email timed"; FAIL=1; }
python3 -c "import json; [json.loads(l) for l in open('$DEVFORGE_LOG_FILE') if l.strip()]" || { echo "FAIL: JSONL non valido"; FAIL=1; }

# No-regression: campi identita' esistenti invariati
for k in user user_raw user_source actor_canonical; do
    grep -qF "\"$k\":" "$DEVFORGE_LOG_FILE" || { echo "FAIL: regressione, manca $k"; FAIL=1; }
done

# Repo senza origin → repo_remote vuoto, no crash
TMP_REPO2=$(mktemp -d); cd "$TMP_REPO2"; git init -q
git config user.email "t@t.local"; git config user.name "T"; echo y > g; git add g; git commit -q -m c2
export DEVFORGE_LOG_FILE=$(mktemp)
devforge_log "test_run_result" "success" "{}"
[ "$(assert_json_field "$DEVFORGE_LOG_FILE" repo_remote)" = "" ] || { echo "FAIL: repo_remote non vuoto senza origin"; FAIL=1; }

[ "$FAIL" = "0" ] && echo "PASS test_log_toplevel_attribution" || exit 1
```

## GREEN — Implementazione (`lib/logger.sh`)

### Passo 1 — calcolo variabili (in ENTRAMBE le funzioni)
In `devforge_log` dopo `project_canonical=$(basename "$repo_root")` (~riga 481) e in
`devforge_log_timed` nel punto analogo (~riga 552), aggiungere:
```bash
    local repo_remote auth_email_v auth_uuid_v safe_repo_remote safe_auth_email safe_auth_uuid
    repo_remote=$(git remote get-url origin 2>/dev/null || echo "")
    auth_email_v="${DEVFORGE_AUTH_EMAIL:-}"
    auth_uuid_v="${DEVFORGE_AUTH_ACCOUNT_UUID:-}"
    safe_repo_remote=$(devforge_sanitize_json_str "$repo_remote")
    safe_auth_email=$(devforge_sanitize_json_str "$auth_email_v")
    safe_auth_uuid=$(devforge_sanitize_json_str "$auth_uuid_v")
```

### Passo 2 — printf COMPLETO post-modifica (copiare verbatim, NON interpretare)
I 3 campi vanno **dopo `project_canonical` e prima di `ts`**. Allineamento format↔args verificato.

**`devforge_log` (sostituisce il printf righe ~501-503):**
```bash
    json_line=$(printf '{"event_id":"%s","schema_version":2,"session_seq":%s,"hook_name":"%s","actor_canonical":"%s","repo_root":"%s","project_canonical":"%s","repo_remote":"%s","auth_email":"%s","auth_account_uuid":"%s","ts":"%s","user":"%s","user_raw":"%s","user_source":"%s","sid":"%s","branch":"%s","jira_id":%s,"project":"%s","event":"%s","status":"%s","meta":%s}' \
        "$event_id" "$seq" "$hook_name" "$safe_user" "$safe_repo_root" "$safe_project_canonical" \
        "$safe_repo_remote" "$safe_auth_email" "$safe_auth_uuid" \
        "$ts" "$safe_user" "$safe_user_raw" "$safe_user_source" "$safe_sid" "$safe_branch" "$jira_json" "$safe_project" "$safe_event" "$safe_status" "$meta")
```

**`devforge_log_timed` (sostituisce il printf righe ~571-573):** identico ma con
`"duration_ms":%d` dopo `"status":"%s"` e `"$duration_ms"` prima di `"$meta"`:
```bash
    json_line=$(printf '{"event_id":"%s","schema_version":2,"session_seq":%s,"hook_name":"%s","actor_canonical":"%s","repo_root":"%s","project_canonical":"%s","repo_remote":"%s","auth_email":"%s","auth_account_uuid":"%s","ts":"%s","user":"%s","user_raw":"%s","user_source":"%s","sid":"%s","branch":"%s","jira_id":%s,"project":"%s","event":"%s","status":"%s","duration_ms":%d,"meta":%s}' \
        "$event_id" "$seq" "$hook_name" "$safe_user" "$safe_repo_root" "$safe_project_canonical" \
        "$safe_repo_remote" "$safe_auth_email" "$safe_auth_uuid" \
        "$ts" "$safe_user" "$safe_user_raw" "$safe_user_source" "$safe_sid" "$safe_branch" "$jira_json" "$safe_project" "$safe_event" "$safe_status" "$duration_ms" "$meta")
```

**Attenzione:** `duration_ms` resta tra `status` e `meta` (NON spostarlo). I 3 nuovi campi
si inseriscono tra `project_canonical` e `ts` in ENTRAMBE le funzioni — questa è la sola posizione corretta.

## Verifica
```bash
bash tests/hooks/test_log_toplevel_attribution.sh
```

## Accettazione
- [ ] `auth_email`, `auth_account_uuid`, `repo_remote` top-level in eventi da entrambe le funzioni.
- [ ] `commit_sha` resta nel meta di commit_created.
- [ ] Repo senza origin → `repo_remote` = "", nessun crash.
- [ ] JSONL valido; `user`/`user_raw`/`user_source`/`actor_canonical` invariati.
