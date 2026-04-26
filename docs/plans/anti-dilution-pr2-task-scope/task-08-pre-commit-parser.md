---
task: 08
title: pre-commit parser rewrite + coverage-force-run (ADR-006 + ADR-008)
size: M
blocks: [13]
depends: [02]
---

# Task 8 — pre-commit parser + coverage-force-run

Rimuove regex substring (linea 69 `hooks/pre-commit`). Parser primo-token
deterministico. Aggiunge coverage-force-run.

## Change summary

### 1. Parser primo-token (ADR-006)

**Attuale** (problematico):

```bash
if [[ "$TOOL_COMMAND" =~ git[[:space:]]+commit ]]; then
```

Falsi positivi: `git log --oneline | grep commit`, `echo "git commit"`,
`python run_git_commit_analyzer.py`, `git-commit-msg-hook.sh`.

**Nuovo** (token-aware):

```bash
# Tokenize first command in the pipeline (strip leading env vars + sudo)
_first_token() {
    local cmd="$1"
    # Strip leading VAR=value assignments
    cmd=$(echo "$cmd" | sed -E 's/^([[:space:]]*[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]+)+//')
    # Strip leading sudo / env wrappers
    cmd=$(echo "$cmd" | sed -E 's/^(sudo|env|exec|nice|time|timeout)([[:space:]]+[^[:space:]]+)*[[:space:]]+//')
    # First word
    echo "$cmd" | awk '{print $1; exit}'
}

_second_token() {
    local cmd="$1"
    cmd=$(echo "$cmd" | sed -E 's/^([[:space:]]*[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]+)+//')
    cmd=$(echo "$cmd" | sed -E 's/^(sudo|env|exec|nice|time|timeout)([[:space:]]+[^[:space:]]+)*[[:space:]]+//')
    echo "$cmd" | awk '{print $2; exit}'
}

FIRST=$(_first_token "$TOOL_COMMAND")
SECOND=$(_second_token "$TOOL_COMMAND")

if [ "$FIRST" = "git" ] && [ "$SECOND" = "commit" ]; then
    # ... gate logic
elif [ "$FIRST" = "git" ] && { [ "$SECOND" = "checkout" ] || [ "$SECOND" = "switch" ]; }; then
    # Detect -b/-c flag via token scan on remaining args
    # ...
fi
```

Per comandi pipeline (`git log | grep`): il nostro interesse è solo sul
primo segmento before `|`. Se `TOOL_COMMAND` contiene `|`, split sul primo:

```bash
PRIMARY_CMD="${TOOL_COMMAND%%|*}"
FIRST=$(_first_token "$PRIMARY_CMD")
```

### 2. coverage-force-run (ADR-008)

**Logica**: se diff staged contiene file di test (`*.spec.ts`, `*Test.java`,
`test_*.py`) ma `.devforge-last-coverage` è stale (>1800s) o assente,
emit block richiedendo coverage fresh run.

```bash
# Dentro branch "git commit":
STAGED_TESTS=$(git diff --cached --name-only | grep -E '\.(spec|test)\.|Test\.java$|test_.*\.py$|_test\.go$' || true)
if [ -n "$STAGED_TESTS" ]; then
    COVERAGE_AGE=9999
    if [ -f "$COVERAGE_FILE" ]; then
        COVERAGE_TS=$(cut -d'|' -f2 "$COVERAGE_FILE" 2>/dev/null || echo 0)
        NOW_S=$(date +%s)
        COVERAGE_AGE=$(( NOW_S - ${COVERAGE_TS:-0} ))
    fi
    if [ "$COVERAGE_AGE" -gt 1800 ]; then
        cat <<COV_FORCE_EOF
{
  "decision": "block",
  "reason": "DevForge Coverage Force-Run — BLOCCATO. Stai committando file di test ma coverage data stale ($COVERAGE_AGE s). Esegui i test con coverage (mvn test, npm test, pytest --cov) prima del commit. Questo evita che coverage-gate passi solo perché i test non sono stati eseguiti."
}
COV_FORCE_EOF
        exit 0
    fi
fi
```

### 3. Task-scoped check

Integrazione `lib/task-id.sh` + `lib/evidence-check.sh`:

```bash
TASK_ID=$(devforge_compute_task_id)
if [ -n "$TASK_ID" ] && [ "${DEVFORGE_USE_SESSION_SCOPE:-0}" != "1" ]; then
    # Task-scoped
    if ! devforge_task_skill_validated "$TASK_ID" siae-git-workflow; then
        # Block (stesso messaggio)
    fi
else
    # Legacy session-scoped (rollback path)
    if ! echo "$SESSION_SKILLS" | grep -qF "siae-git-workflow"; then
        # Block
    fi
fi
```

## Acceptance

- [ ] Token parser `_first_token` + `_second_token` (centralizzare in `lib/cmd-parser.sh`)
- [ ] Replace regex substring con token check
- [ ] coverage-force-run: block se staged test + coverage stale
- [ ] Task-scoped integration + rollback env var
- [ ] Test `tests/hooks/test_pre_commit_parser.sh`:
  - [ ] `git commit -m "..."` → gate attivo
  - [ ] `git log | grep commit` → gate skip (correct)
  - [ ] `echo "git commit"` → gate skip
  - [ ] `sudo git commit` → gate attivo
  - [ ] `FOO=bar git commit` → gate attivo
  - [ ] `python run_git_commit.py` → gate skip
  - [ ] pipeline `git commit ... && git push` → gate attivo (primary è git commit)
- [ ] Test `tests/hooks/test_coverage_force_run.sh`:
  - [ ] staged test + stale coverage → block
  - [ ] staged test + fresh coverage → allow
  - [ ] no staged test + stale coverage → allow (no force)
- [ ] Zero regression 51/51 test PR #1

## Out of scope

- Coverage collector (come popola `.devforge-last-coverage`) → deferred PR #3
