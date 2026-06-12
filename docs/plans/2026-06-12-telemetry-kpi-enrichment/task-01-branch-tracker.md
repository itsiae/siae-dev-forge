# Task 01 — `hooks/branch-tracker` (evento branch_created)

**Stato:** [PENDING]
**Dipendenze:** nessuna
**File:** `hooks/branch-tracker` (nuovo), `hooks/hooks.json` (modifica), `tests/hooks/test_branch_tracker.sh` (nuovo)
**Metodo:** TDD — test PRIMA, poi impl.

## Obiettivo

Emettere l'evento telemetria `branch_created` quando l'utente crea un branch
(`git checkout -b` / `git switch -c`), con `base_branch` corretto, senza falsi positivi.

## Step 1 — Test (`tests/hooks/test_branch_tracker.sh`)

Stile `tests/hooks/*.test.sh` (mktemp HOME + repo git fixture). Il branch-tracker legge
da stdin il JSON dell'hook con `tool_input.command`. Il test invoca lo script con un payload
JSON e un repo git reale, poi verifica gli eventi nel log `~/.claude/devforge-activity.jsonl`.

```bash
#!/usr/bin/env bash
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TEST_TMP=$(mktemp -d); trap 'rm -rf "$TEST_TMP"' EXIT
export HOME="$TEST_TMP"; mkdir -p "$HOME/.claude"
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"
PASS=0; FAIL=0
ok(){ echo "  PASS: $1"; PASS=$((PASS+1)); }
ko(){ echo "  FAIL: $1 ($2)"; FAIL=$((FAIL+1)); }

# repo fixture
REPO="$TEST_TMP/repo"; mkdir -p "$REPO"; cd "$REPO"
git init -q && git config user.email t@t && git config user.name t
git commit -q --allow-empty -m init && git branch -m main

LOG="$HOME/.claude/devforge-activity.jsonl"
run_hook(){ # $1=command  → invoca branch-tracker con payload JSON
  : > "$LOG"
  printf '{"tool_input":{"command":"%s"},"cwd":"%s"}' "$1" "$REPO" \
    | bash "$PLUGIN_ROOT/hooks/branch-tracker" >/dev/null 2>&1 || true
}
ev_count(){ grep -c "\"event\":\"branch_created\"" "$LOG" 2>/dev/null || true; }
ev_base(){ grep -o '"base_branch":"[^"]*"' "$LOG" | head -1 | sed 's/.*"base_branch":"//;s/"$//'; }

# T1 — checkout -b da main → evento, base_branch=main
git checkout -q -b feature/x
run_hook "git checkout -b feature/x"
{ [ "$(ev_count)" = "1" ] && [ "$(ev_base)" = "main" ]; } && ok "T1 checkout -b base=main" || ko "T1" "count=$(ev_count) base=$(ev_base)"

# T2 — switch -c → evento, base = branch precedente (feature/x)
git switch -q -c feature/y
run_hook "git switch -c feature/y"
{ [ "$(ev_count)" = "1" ] && [ "$(ev_base)" = "feature/x" ]; } && ok "T2 switch -c base=feature/x" || ko "T2" "count=$(ev_count) base=$(ev_base)"

# T3 — comando non-branch (checkout di branch esistente) → nessun evento
git checkout -q main
run_hook "git checkout main"
{ [ "$(ev_count)" = "0" ]; } && ok "T3 checkout existing: no evento" || ko "T3" "count=$(ev_count)"

# T3b — checkout -b FALLITO (branch gia' esiste): HEAD non cambia → no evento
git checkout -q main
run_hook "git checkout -b feature/x"   # feature/x esiste gia', HEAD resta main
{ [ "$(ev_count)" = "0" ]; } && ok "T3b checkout -b fallito: no evento" || ko "T3b" "count=$(ev_count)"

# T3c — detached HEAD → checkout -b feature/d: evento, base_branch=""
FIRST=$(git rev-parse HEAD); git checkout -q "$FIRST"   # detached
git checkout -q -b feature/d
run_hook "git checkout -b feature/d"
{ [ "$(ev_count)" = "1" ] && [ -z "$(ev_base)" ]; } && ok "T3c detached: base vuoto" || ko "T3c" "count=$(ev_count) base='$(ev_base)'"

# T3d — flag intermedio: git checkout -q -b feature/q → EVENTO emesso (caso comune tool/script)
git checkout -q main; git checkout -q -b feature/q
run_hook "git checkout -q -b feature/q"
{ [ "$(ev_count)" = "1" ] && [ "$(ev_base)" = "main" ]; } && ok "T3d checkout -q -b: evento emesso" || ko "T3d" "count=$(ev_count) base=$(ev_base)"

# T4 — evento ha branch/repo_remote top-level (da devforge_log), non duplicati nel meta
git checkout -q main; git checkout -q -b feature/z
run_hook "git checkout -b feature/z"
line=$(grep '"event":"branch_created"' "$LOG" | head -1)
has_top=$(echo "$line" | grep -o '"branch":"feature/z"' | head -1)
meta_dup=$(echo "$line" | sed 's/.*"meta"://' | grep -o '"branch":' | head -1)
{ [ -n "$has_top" ] && [ -z "$meta_dup" ]; } && ok "T4 branch top-level, no dup meta" || ko "T4" "top='$has_top' metadup='$meta_dup'"

echo "branch-tracker: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
```

Esegui: `bash tests/hooks/test_branch_tracker.sh` → RED (hook non esiste).

## Step 2 — Implementazione (`hooks/branch-tracker`)

```bash
#!/usr/bin/env bash
# PostToolUse Bash: emette branch_created su git checkout -b / git switch -c.
# Additivo, best-effort, mai bloccante.
set -uo pipefail
export DEVFORGE_CURRENT_HOOK="branch-tracker"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${PLUGIN_ROOT}/lib/cmd-parser.sh" 2>/dev/null || exit 0

INPUT=$(cat 2>/dev/null || echo "")
CMD=$(printf '%s' "$INPUT" | python3 -c 'import json,sys;
try: print(json.load(sys.stdin).get("tool_input",{}).get("command",""))
except Exception: print("")' 2>/dev/null || echo "")
[ -z "$CMD" ] && exit 0

# Fase 1: detect git checkout/switch (2-token, compound-safe via cmd-parser)
if devforge_cmd_has_subcommand "$CMD" git checkout \
   || devforge_cmd_has_subcommand "$CMD" git switch; then
    :
else
    exit 0
fi

# Fase 2: estrai nome target dopo flag di creazione (-b|-c|--branch), tollerando
# flag intermedi (es. 'git checkout -q -b feature/x'). Niente flag → niente branch creato.
TARGET=$(printf '%s' "$CMD" | sed -nE 's/.*[[:space:]](-b|-c|--branch)[[:space:]]+([^[:space:]]+).*/\2/p' | head -1)
[ -z "$TARGET" ] && exit 0

# Guard: il branch deve essere stato EFFETTIVAMENTE creato (HEAD == target).
# Esclude i falsi positivi: comando fallito (branch gia' esistente → HEAD invariato),
# o un '-b' spurio in un comando che non ha creato quel branch.
CUR=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
[ "$CUR" = "$TARGET" ] || exit 0

BASE_BRANCH=$(git rev-parse --abbrev-ref @{-1} 2>/dev/null || echo "")

source "${PLUGIN_ROOT}/lib/logger.sh" 2>/dev/null || exit 0
devforge_init_session 2>/dev/null || true
SAFE_BASE=$(devforge_sanitize_json_str "$BASE_BRANCH")
devforge_log "branch_created" "success" "{\"base_branch\":\"${SAFE_BASE}\"}" 2>/dev/null || true
exit 0
```

NB: `branch`, `repo_root`, `repo_remote` sono iniettati top-level da `devforge_log`
(`lib/logger.sh:553`) — NON metterli nel meta.

## Step 3 — Entry in `hooks/hooks.json`

Nel matcher PostToolUse `"Bash"` (riga ~168), aggiungere come PRIMO hook della lista
(prima di `post-commit-review`) un nuovo command:

```json
{
  "type": "command",
  "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" branch-tracker",
  "timeout": 5
}
```

Verifica con `python3 -c 'import json;json.load(open("hooks/hooks.json"))'` che il JSON resti valido.

Esegui di nuovo `bash tests/hooks/test_branch_tracker.sh` → GREEN.

## Criteri di accettazione

- [ ] Test RED prima, GREEN dopo (T1,T2,T3,T3b,T3c,T3d,T4).
- [ ] `chmod +x hooks/branch-tracker`.
- [ ] Detection 2-token (compound-safe) + estrazione TARGET flag-tollerante (`-b`/`-c`/`--branch`): cattura `git checkout -q -b` (T3d).
- [ ] Guard HEAD==TARGET esclude falsi positivi (`git checkout main` → T3; comando fallito → T3b).
- [ ] `hooks.json` JSON valido, branch-tracker nel matcher PostToolUse Bash.
- [ ] Limite noto (design ADR-1): solo `git worktree add` può non passare da PostToolUse — accettato.
