# Task 06 — `hooks/post-commit-review` — `task_id` join-key su commit_created/pr_*

**Goal:** aggiungere `meta.task_id` (via `devforge_compute_task_id`) agli eventi
`commit_created`, `pr_opened`, `pr_merged`, `pr_metrics` per abilitare la join precisa
*adesione↔outcome* a valle. Vuoto fuori scope (`itsiae/*`). Copre AC6.

**File coinvolti:**
- Modifica: `hooks/post-commit-review` (source task-id.sh + 4 meta JSON)
- Crea: `tests/hooks/test_post_commit_task_id.sh`

**Ordine:** eseguire DOPO Task 05 (stesso file). Precondizione: rebase da `main` (design §9).

## Step 1 — Scrivi il test fallente

Crea `tests/hooks/test_post_commit_task_id.sh`:

```bash
#!/usr/bin/env bash
# Test: hooks/post-commit-review aggiunge meta.task_id a commit_created (e pr_* strutturale)
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="${PLUGIN_ROOT}/hooks/post-commit-review"
PASS=0; FAIL=0
ok() { if eval "$2"; then echo "  PASS  $1"; PASS=$((PASS+1)); else echo "  FAIL  $1"; FAIL=$((FAIL+1)); fi; }

# Esegue il hook in un repo con remote dato; ritorna il valore meta.task_id dell'evento
# commit_created (stringa vuota se assente).
task_id_of_commit_created() {
    local remote="$1" H R payload act
    H="$(mktemp -d)"; mkdir -p "$H/.claude"
    R="$(mktemp -d)"
    ( cd "$R" && git init -q && git config user.email t@t.it && git config user.name t \
      && git remote add origin "$remote" \
      && echo a > a.txt && git add a.txt && git commit -qm init \
      && echo b >> a.txt && git commit -qam second ) >/dev/null 2>&1
    payload=$(python3 -c "import json;print(json.dumps({'tool_input':{'command':'git commit -m x'}}))")
    ( cd "$R" && printf '%s' "$payload" | HOME="$H" bash "$HOOK" >/dev/null 2>&1 || true )
    act="$H/.claude/devforge-activity.jsonl"
    python3 - "$act" <<'PY'
import json,sys
try:
    for ln in open(sys.argv[1]):
        e=json.loads(ln)
        if e.get("event")=="commit_created":
            print((e.get("meta") or {}).get("task_id",""))
            break
except Exception:
    print("")
PY
}

# In-scope itsiae → task_id non vuoto (12 hex)
TID_IN=$(task_id_of_commit_created "https://github.com/itsiae/test-repo.git")
ok "in-scope: commit_created.meta.task_id non vuoto" "[ -n '$TID_IN' ]"
ok "in-scope: task_id è 12-hex" "printf '%s' '$TID_IN' | grep -qE '^[0-9a-f]{12}\$'"

# Fuori scope (remote non-itsiae) → task_id vuoto
TID_OUT=$(task_id_of_commit_created "https://github.com/other/test-repo.git")
ok "fuori scope: task_id vuoto" "[ -z '$TID_OUT' ]"

# Strutturale: pr_opened / pr_merged / pr_metrics includono task_id nel meta
ok "pr_opened meta include task_id" "grep -A2 'pr_opened' '$HOOK' | grep -q 'task_id'"
ok "pr_merged meta include task_id" "grep -A2 'pr_merged' '$HOOK' | grep -q 'task_id'"
ok "pr_metrics meta include task_id" "grep -A2 'pr_metrics' '$HOOK' | grep -q 'task_id'"

echo ""; echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
```

## Step 2 — Esegui e verifica che fallisce

Run: `bash tests/hooks/test_post_commit_task_id.sh`
Output atteso: in-scope task_id vuoto (manca il campo) e strutturali pr_* FAIL → `FAIL>=4`.

## Step 3 — Implementa il codice minimo

**(a)** In `hooks/post-commit-review`, **dopo** la definizione di `PLUGIN_ROOT` (riga 21),
prima del source di net-timeout.sh, aggiungi:

```bash
# task_id join-key (Layer 1): correlazione adesione↔outcome a valle. Vuoto fuori itsiae/*.
source "${PLUGIN_ROOT}/lib/task-id.sh" 2>/dev/null || true
TASK_ID=""
if command -v devforge_compute_task_id >/dev/null 2>&1; then
    TASK_ID=$(devforge_compute_task_id 2>/dev/null || echo "")
fi
```

**(b)** Aggiungi `,"task_id":"${TASK_ID}"` come ultimo campo del `meta` JSON. Ci sono
**6 punti di emissione** (commit_created ×1, pr_opened ×1, pr_merged ×2, pr_metrics ×2):
sostituisci la riga del meta JSON con la versione riscritta indicata (è l'unica riga da
toccare in ciascun punto, la `devforge_log` resta invariata sopra).

**B1 — `commit_created` (riga 86).** Sostituisci:
```bash
        "{\"commit_sha\":\"${CURRENT_HEAD}\",\"files_changed\":${FILES_CHANGED:-0},\"insertions\":${INSERTIONS:-0},\"deletions\":${DELETIONS:-0},\"has_tests\":${HAS_TESTS},\"tests_files_changed\":${TESTS_FILES_COUNT}${TOKEN_META}}"
```
con:
```bash
        "{\"commit_sha\":\"${CURRENT_HEAD}\",\"files_changed\":${FILES_CHANGED:-0},\"insertions\":${INSERTIONS:-0},\"deletions\":${DELETIONS:-0},\"has_tests\":${HAS_TESTS},\"tests_files_changed\":${TESTS_FILES_COUNT}${TOKEN_META},\"task_id\":\"${TASK_ID}\"}"
```

**B2 — `pr_opened` (riga 121).** Sostituisci:
```bash
                        "{\"pr_number\":${PR_NUMBER},\"base_branch\":\"${SAFE_BASE_BRANCH}\",\"files_changed\":${FILES_CHANGED},\"commits_count\":${COMMITS_COUNT}}"
```
con:
```bash
                        "{\"pr_number\":${PR_NUMBER},\"base_branch\":\"${SAFE_BASE_BRANCH}\",\"files_changed\":${FILES_CHANGED},\"commits_count\":${COMMITS_COUNT},\"task_id\":\"${TASK_ID}\"}"
```

**B3 — `pr_merged` occorrenza #1 (riga 184, orphan catch-up).** Sostituisci:
```bash
                    "{\"pr_number\":${ORPHAN_PR},\"merge_method\":\"${MERGE_METHOD}\",\"total_commits\":${ORPHAN_TOTAL},\"delta_from_open\":${ORPHAN_DELTA},\"session_tokens_cumulative\":$(devforge_session_token_total)}"
```
con:
```bash
                    "{\"pr_number\":${ORPHAN_PR},\"merge_method\":\"${MERGE_METHOD}\",\"total_commits\":${ORPHAN_TOTAL},\"delta_from_open\":${ORPHAN_DELTA},\"session_tokens_cumulative\":$(devforge_session_token_total),\"task_id\":\"${TASK_ID}\"}"
```

**B4 — `pr_metrics` occorrenza #1 (riga 202, orphan catch-up).** Sostituisci:
```bash
                    "{\"pr_number\":${ORPHAN_PR},\"rework_commits\":${ORPHAN_REWORK},\"review_cycles\":${ORPHAN_CYCLES},\"time_to_merge_sec\":${ORPHAN_TTM},\"first_push_to_merge_sec\":${ORPHAN_TTM}}"
```
con:
```bash
                    "{\"pr_number\":${ORPHAN_PR},\"rework_commits\":${ORPHAN_REWORK},\"review_cycles\":${ORPHAN_CYCLES},\"time_to_merge_sec\":${ORPHAN_TTM},\"first_push_to_merge_sec\":${ORPHAN_TTM},\"task_id\":\"${TASK_ID}\"}"
```

**B5 — `pr_merged` occorrenza #2 (riga 231, gh pr merge CLI).** Sostituisci:
```bash
                    "{\"pr_number\":${PR_NUMBER},\"merge_method\":\"cli\",\"total_commits\":${TOTAL_COMMITS},\"delta_from_open\":${DELTA},\"session_tokens_cumulative\":$(devforge_session_token_total)}"
```
con:
```bash
                    "{\"pr_number\":${PR_NUMBER},\"merge_method\":\"cli\",\"total_commits\":${TOTAL_COMMITS},\"delta_from_open\":${DELTA},\"session_tokens_cumulative\":$(devforge_session_token_total),\"task_id\":\"${TASK_ID}\"}"
```

**B6 — `pr_metrics` occorrenza #2 (riga 252, gh pr merge CLI).** Sostituisci:
```bash
                    "{\"pr_number\":${PR_NUMBER},\"rework_commits\":${REWORK_COUNT},\"review_cycles\":${CYCLES_COUNT},\"time_to_merge_sec\":${TTM_SEC},\"first_push_to_merge_sec\":${TTM_SEC}}"
```
con:
```bash
                    "{\"pr_number\":${PR_NUMBER},\"rework_commits\":${REWORK_COUNT},\"review_cycles\":${CYCLES_COUNT},\"time_to_merge_sec\":${TTM_SEC},\"first_push_to_merge_sec\":${TTM_SEC},\"task_id\":\"${TASK_ID}\"}"
```

> Append-safe: `${TOKEN_META}` è "" o inizia con `,` → `,"task_id"` resta JSON valido. La
> `}` finale di ogni meta è l'ultimo carattere della stringa (dopo `$(...)` o `${...}`), quindi
> `,\"task_id\":\"${TASK_ID}\"` va inserito prima di quella `}`.

## Step 4 — Esegui e verifica che passa

Run: `bash tests/hooks/test_post_commit_task_id.sh`
Output atteso: `PASS=6 FAIL=0` (exit 0).

Regressione: `bash tests/hooks/test_commit_created_no_regression.sh` e
`bash tests/hooks/post-commit-pr-lifecycle.test.sh` → invariati (verifica che il meta resti
JSON valido).

## Step 5 — Commit

```bash
git add hooks/post-commit-review tests/hooks/test_post_commit_task_id.sh
git commit -m "feat(telemetry): task_id join-key su commit_created/pr_* (Layer 1 task-06)"
```

## Criteri di accettazione
- [ ] `commit_created.meta.task_id` è un 12-hex su repo `itsiae/*`, vuoto fuori scope (AC6).
- [ ] `pr_opened`/`pr_merged`/`pr_metrics` includono `task_id` nel meta.
- [ ] Meta resta JSON valido (test no-regression + lifecycle invariati).
- [ ] `PASS=6 FAIL=0`.
