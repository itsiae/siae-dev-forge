# Task 05 — `hooks/post-commit-review` detection `--no-verify`/`-n` → `gate_bypassed`

**Goal:** quando un nuovo commit è rilevato e il comando git commit conteneva `--no-verify`
(o un cluster di flag corti contenente `n`, es. `-nm`), emettere `gate_bypassed`
`mechanism=git_no_verify`. Ignorare `-n` dentro il messaggio del commit. Copre AC5, AC7.

**File coinvolti:**
- Modifica: `hooks/post-commit-review` (dentro il blocco nuovo-commit, dopo riga 86)
- Crea: `tests/hooks/test_post_commit_no_verify.sh`

**Precondizione:** rebase da `main` (overlap con `feat/telemetry-kpi-enrichment`, design §9).
**Ordine:** eseguire Task 05 PRIMA di Task 06 (stesso file).

## Step 1 — Scrivi il test fallente

Crea `tests/hooks/test_post_commit_no_verify.sh`:

```bash
#!/usr/bin/env bash
# Test: hooks/post-commit-review emette gate_bypassed git_no_verify su commit --no-verify/-n
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
HOOK="${PLUGIN_ROOT}/hooks/post-commit-review"
PASS=0; FAIL=0
ok() { if eval "$2"; then echo "  PASS  $1"; PASS=$((PASS+1)); else echo "  FAIL  $1"; FAIL=$((FAIL+1)); fi; }

# Setup: fresh HOME (saved-hash vuoto) + repo con 2 commit (HEAD~1 valido). Esegue il
# hook con un payload Bash che porta il comando da analizzare. Ritorna il path activity.jsonl.
run_with_cmd() {
    local cmd="$1" H R payload
    H="$(mktemp -d)"; mkdir -p "$H/.claude"
    R="$(mktemp -d)"
    ( cd "$R" && git init -q && git config user.email t@t.it && git config user.name t \
      && echo a > a.txt && git add a.txt && git commit -qm init \
      && echo b >> a.txt && git commit -qam second ) >/dev/null 2>&1
    payload=$(python3 -c "import json,sys;print(json.dumps({'tool_input':{'command':sys.argv[1]}}))" "$cmd")
    ( cd "$R" && printf '%s' "$payload" | HOME="$H" bash "$HOOK" >/dev/null 2>&1 || true )
    echo "$H/.claude/devforge-activity.jsonl"
}

has_bypass() { [ -s "$1" ] && grep -q 'gate_bypassed' "$1" && grep -q 'git_no_verify' "$1"; }

# POS 1: --no-verify
A=$(run_with_cmd 'git commit --no-verify -m "msg"')
ok "POS --no-verify emette git_no_verify" "has_bypass '$A'"

# POS 2: -nm (cluster con n)
B=$(run_with_cmd 'git commit -nm "msg"')
ok "POS -nm emette git_no_verify" "has_bypass '$B'"

# NEG: -n dentro il messaggio (deve emettere commit_created ma NON gate_bypassed)
C=$(run_with_cmd 'git commit -m "fix -n test"')
ok "NEG '-n' nel messaggio: commit_created presente" "[ -s '$C' ] && grep -q 'commit_created' '$C'"
ok "NEG '-n' nel messaggio: nessun git_no_verify" "! has_bypass '$C'"

echo ""; echo "PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
```

## Step 2 — Esegui e verifica che fallisce

Run: `bash tests/hooks/test_post_commit_no_verify.sh`
Output atteso: i 2 POS FAIL (`gate_bypassed` non emesso); i 2 NEG PASS → `FAIL=2`, exit 1.

## Step 3 — Implementa il codice minimo

In `hooks/post-commit-review`, dentro il blocco `if [ -n "$CURRENT_HEAD" ] && [ "$CURRENT_HEAD" != "$SAVED_HASH" ]; then` (inizia riga 51), **subito dopo** la `devforge_log "commit_created" ...` (termina riga 86), inserisci:

```bash
    # gate_bypassed (Layer 1): git commit con --no-verify / -n salta i git hook.
    # Strip dei segmenti quotati per non matchare "-n" dentro il messaggio del commit.
    CMD_NOQUOTES=$(printf '%s' "$TOOL_COMMAND" | sed "s/'[^']*'//g; s/\"[^\"]*\"//g")
    if printf '%s' "$CMD_NOQUOTES" | grep -qE 'git[[:space:]]+commit' \
       && printf '%s' "$CMD_NOQUOTES" | grep -qE -- '(--no-verify)|([[:space:]]-[A-Za-z]*n[A-Za-z]*([[:space:]]|$))'; then
        devforge_log "gate_bypassed" "warning" \
            "{\"mechanism\":\"git_no_verify\",\"commit_sha\":\"${CURRENT_HEAD}\"}" 2>/dev/null || true
    fi
```

> Note regex: dopo lo strip dei quoted-segment, `--no-verify` matcha esplicitamente; il
> cluster di flag corti `-[A-Za-z]*n[A-Za-z]*` cattura `-n`, `-nm`, `-vn` (in git commit
> solo `-n`=`--no-verify` contiene 'n'); `--amend`/`-am`/`-m` non matchano (verificato nei test).

## Step 4 — Esegui e verifica che passa

Run: `bash tests/hooks/test_post_commit_no_verify.sh`
Output atteso: `PASS=4 FAIL=0` (exit 0).

Regressione: `bash tests/hooks/test_commit_created_no_regression.sh` → invariato.

## Step 5 — Commit

```bash
git add hooks/post-commit-review tests/hooks/test_post_commit_no_verify.sh
git commit -m "feat(telemetry): post-commit-review rileva --no-verify → gate_bypassed (Layer 1 task-05)"
```

## Criteri di accettazione
- [ ] `git commit --no-verify -m x` e `git commit -nm x` → `gate_bypassed mechanism=git_no_verify`.
- [ ] `git commit -m "fix -n test"` → `commit_created` sì, `gate_bypassed` no (no falso positivo).
- [ ] Emissione best-effort `|| true` (AC7).
- [ ] `test_commit_created_no_regression.sh` non regredisce.
- [ ] `PASS=4 FAIL=0`.
