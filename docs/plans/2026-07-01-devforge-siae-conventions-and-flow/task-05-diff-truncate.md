# Task 05 — `lib/diff-truncate.sh`: diff troncato oltre soglia (no hang/loop)

**Cluster:** B diff (REQ-DF-03)
**Dipendenze:** Nessuna (indipendente da Task 04; consumato da Task 06/07).

## Goal

`devforge_diff_or_summary <base> [max_lines]` deve restituire il diff completo di `git diff <base>...HEAD` quando il numero di righe è ≤ soglia (`DEVFORGE_MAX_DIFF_LINES`, default 2000), e quando lo supera deve restituire `--stat` + `--name-only` + i primi N file con una nota esplicita di troncamento — terminando sempre con `return 0` (mai un loop/hang).

## File coinvolti

- `lib/diff-truncate.sh` — **nuovo** (funzione `devforge_diff_or_summary`).
- `tests/lib/diff-truncate.test.sh` — **nuovo** (unit test, repo temporaneo).
- `hooks/ENV_VARS.md` — **modifica**: nuova sezione `## PR Diff Resolution` dopo la sezione `## Release Risk Assessment` (dopo riga 267, fine file) che documenta `DEVFORGE_MAX_DIFF_LINES`.

## Step TDD

### Step 1 — Test fallente (COMPLETO)

Crea `tests/lib/diff-truncate.test.sh`:

```bash
#!/usr/bin/env bash
# tests/lib/diff-truncate.test.sh — unit test per lib/diff-truncate.sh (REQ-DF-03).
# Copre: diff piccolo -> diff completo; diff grande (> soglia) -> stat+name-only+
# nota di troncamento, senza mai bloccarsi (exit sempre 0).
set -eu
PASS=0; FAIL=0
REPO_ROOT="$(git rev-parse --show-toplevel)"
LIB="${REPO_ROOT}/lib/diff-truncate.sh"

if [ ! -f "$LIB" ]; then
    echo "FAIL — $LIB not found"
    exit 1
fi

# shellcheck disable=SC1090
source "$LIB"

_mkrepo() {
    local td; td=$(mktemp -d)
    ( cd "$td"
      git init -q; git config user.email t@t; git config user.name t
      echo seed > seed.txt; git add -A; git commit -qm seed; git branch -m main
      git checkout -qb work ) >/dev/null 2>&1
    echo "$td"
}

echo "=== AC-1: diff piccolo (sotto soglia) -> diff completo, exit 0 ==="
TD=$(_mkrepo)
( cd "$TD" && echo "riga1" > small.txt && git add -A && git commit -qm small ) >/dev/null 2>&1
OUT=$(cd "$TD" && devforge_diff_or_summary "main" 2000); RC=$?
if [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -q '^+riga1$' && ! printf '%s' "$OUT" | grep -q 'diff troncato'; then
    echo PASS; PASS=$((PASS+1))
else
    echo "FAIL — rc=$RC out=<<$OUT>>"; FAIL=$((FAIL+1))
fi
rm -rf "$TD"

echo "=== AC-2: diff grande (sopra soglia bassa di test) -> stat+name-only+nota, exit 0 ==="
TD=$(_mkrepo)
( cd "$TD" && seq 1 50 > big.txt && git add -A && git commit -qm big ) >/dev/null 2>&1
OUT=$(cd "$TD" && devforge_diff_or_summary "main" 10); RC=$?
if [ "$RC" -eq 0 ] \
    && printf '%s' "$OUT" | grep -q 'file changed' \
    && printf '%s' "$OUT" | grep -qx 'big.txt' \
    && printf '%s' "$OUT" | grep -q 'diff troncato oltre 10 righe — richiedi i file mancanti on-demand'; then
    echo PASS; PASS=$((PASS+1))
else
    echo "FAIL — rc=$RC out=<<$OUT>>"; FAIL=$((FAIL+1))
fi
rm -rf "$TD"

echo "=== AC-3: default DEVFORGE_MAX_DIFF_LINES=2000 se max_lines omesso ==="
TD=$(_mkrepo)
( cd "$TD" && echo "riga1" > small2.txt && git add -A && git commit -qm small2 ) >/dev/null 2>&1
OUT=$(cd "$TD" && unset DEVFORGE_MAX_DIFF_LINES; devforge_diff_or_summary "main"); RC=$?
if [ "$RC" -eq 0 ] && ! printf '%s' "$OUT" | grep -q 'diff troncato'; then
    echo PASS; PASS=$((PASS+1))
else
    echo "FAIL — rc=$RC out=<<$OUT>>"; FAIL=$((FAIL+1))
fi
rm -rf "$TD"

echo "=== AC-4: DEVFORGE_MAX_DIFF_LINES da env se max_lines non passato ==="
TD=$(_mkrepo)
( cd "$TD" && seq 1 50 > big2.txt && git add -A && git commit -qm big2 ) >/dev/null 2>&1
OUT=$(cd "$TD" && DEVFORGE_MAX_DIFF_LINES=5 devforge_diff_or_summary "main"); RC=$?
if [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -q 'diff troncato oltre 5 righe'; then
    echo PASS; PASS=$((PASS+1))
else
    echo "FAIL — rc=$RC out=<<$OUT>>"; FAIL=$((FAIL+1))
fi
rm -rf "$TD"

echo "=== AC-5: base inesistente -> non hang, exit 0, nessun output vuoto pericoloso ==="
TD=$(_mkrepo)
OUT=$(cd "$TD" && devforge_diff_or_summary "refs/heads/does-not-exist" 2000 2>/dev/null); RC=$?
[ "$RC" -eq 0 ] && { echo PASS; PASS=$((PASS+1)); } || { echo "FAIL — rc=$RC"; FAIL=$((FAIL+1)); }
rm -rf "$TD"

echo ""; echo "RESULT: PASS=$PASS FAIL=$FAIL"; [ "$FAIL" -eq 0 ]
```

### Step 2 — Esegui e verifica il FAIL

Comando:

```bash
bash "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge/tests/lib/diff-truncate.test.sh"
```

Output atteso (fallisce perché `lib/diff-truncate.sh` non esiste ancora):

```
FAIL — /Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge/lib/diff-truncate.sh not found
```

(exit code `1`)

### Step 3 — Implementazione minima (COMPLETA)

Crea `lib/diff-truncate.sh`:

```bash
#!/usr/bin/env bash
# diff-truncate.sh — evita hang/loop su diff enormi tra branch (REQ-DF-03).
# Se il diff supera DEVFORGE_MAX_DIFF_LINES righe, emette --stat + --name-only +
# nota di troncamento esplicita invece del diff completo. Non blocca mai (return 0).
# Design: docs/plans/2026-07-01-devforge-siae-conventions-and-flow/design.md

# devforge_diff_or_summary <base> [max_lines]
# $1 = base branch/ref (es. "origin/main", "main", risultato di devforge_resolve_pr_base)
# $2 = soglia righe (default: $DEVFORGE_MAX_DIFF_LINES, o 2000 se non settata)
# Stdout: diff completo (sotto soglia) oppure stat+name-only+nota (sopra soglia).
# Return: sempre 0 (fail-safe, mai hang).
devforge_diff_or_summary() {
    local base="${1:-}"
    local max_lines="${2:-${DEVFORGE_MAX_DIFF_LINES:-2000}}"
    [ -z "$base" ] && { printf 'diff troncato oltre %s righe — richiedi i file mancanti on-demand (base non specificata)\n' "$max_lines"; return 0; }

    local full_diff line_count
    full_diff=$(git diff "${base}...HEAD" 2>/dev/null) || { printf ''; return 0; }
    [ -z "$full_diff" ] && return 0

    line_count=$(printf '%s\n' "$full_diff" | wc -l | tr -d ' ')

    if [ "$line_count" -le "$max_lines" ]; then
        printf '%s\n' "$full_diff"
        return 0
    fi

    git diff --stat "${base}...HEAD" 2>/dev/null
    printf '\n'
    git diff --name-only "${base}...HEAD" 2>/dev/null
    printf '\ndiff troncato oltre %s righe — richiedi i file mancanti on-demand\n' "$max_lines"
    return 0
}
```

### Step 4 — Esegui e verifica il PASS

Comando:

```bash
bash "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge/tests/lib/diff-truncate.test.sh"
```

Output atteso:

```
=== AC-1: diff piccolo (sotto soglia) -> diff completo, exit 0 ===
PASS
=== AC-2: diff grande (sopra soglia bassa di test) -> stat+name-only+nota, exit 0 ===
PASS
=== AC-3: default DEVFORGE_MAX_DIFF_LINES=2000 se max_lines omesso ===
PASS
=== AC-4: DEVFORGE_MAX_DIFF_LINES da env se max_lines non passato ===
PASS
=== AC-5: base inesistente -> non hang, exit 0, nessun output vuoto pericoloso ===
PASS

RESULT: PASS=5 FAIL=0
```

Poi aggiungi la documentazione in `hooks/ENV_VARS.md`. Leggi prima le ultime righe per confermare il punto di inserzione:

```bash
tail -10 "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge/hooks/ENV_VARS.md"
```

Output atteso (stato pre-modifica, fine file):

```
### Trigger automatico

Hook `pr-release-gate` (PostToolUse Bash, 30s timeout) si attiva su:
- `gh pr create --base main` AND
- branch corrente `release/**`

Posta scorecard come PR comment con idempotency marker `<!-- release-risk:<diff-hash> -->`.
```

Poi appendi in coda al file (dopo l'ultima riga sopra) la nuova sezione:

```markdown

## PR Diff Resolution

| Env var | Default | Description |
|---|---|---|
| `DEVFORGE_MAX_DIFF_LINES` | `2000` | Soglia righe oltre la quale `lib/diff-truncate.sh` (`devforge_diff_or_summary`) smette di emettere il diff completo e passa a `--stat` + `--name-only` + nota di troncamento esplicita. Evita hang/loop su diff enormi nei gate PR (REQ-DF-03). Consumata da `lib/pr-base-resolver.sh` + i siti che oggi calcolano `git diff origin/main...HEAD` inline. |
```

Verifica finale:

```bash
tail -8 "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge/hooks/ENV_VARS.md"
```

Output atteso:

```
## PR Diff Resolution

| Env var | Default | Description |
|---|---|---|
| `DEVFORGE_MAX_DIFF_LINES` | `2000` | Soglia righe oltre la quale `lib/diff-truncate.sh` (`devforge_diff_or_summary`) smette di emettere il diff completo e passa a `--stat` + `--name-only` + nota di troncamento esplicita. Evita hang/loop su diff enormi nei gate PR (REQ-DF-03). Consumata da `lib/pr-base-resolver.sh` + i siti che oggi calcolano `git diff origin/main...HEAD` inline. |
```

### Step 5 — Commit

```bash
git add lib/diff-truncate.sh tests/lib/diff-truncate.test.sh hooks/ENV_VARS.md
git commit -m "feat(diff): aggiungi devforge_diff_or_summary con troncamento oltre soglia (REQ-DF-03)"
```

## Criteri di accettazione

- [ ] `lib/diff-truncate.sh` espone `devforge_diff_or_summary(base, [max_lines])`, sourceable senza side-effect (nessun `set -e`/`exit` a livello top, coerente con `lib/diff-risk-classifier.sh`).
- [ ] AC3 (design REQ-DF-03): diff sotto soglia → output = diff completo di `git diff <base>...HEAD`.
- [ ] AC3: diff sopra soglia → output = `git diff --stat` + `git diff --name-only` + nota esplicita `"diff troncato oltre <N> righe — richiedi i file mancanti on-demand"`, **e la funzione ritorna 0** (mai hang/loop, mai un exit non-zero che blocchi il chiamante).
- [ ] Soglia configurabile via secondo argomento posizionale o via `DEVFORGE_MAX_DIFF_LINES` (default `2000`) se l'argomento è omesso.
- [ ] Base inesistente/errore git → nessun hang, `return 0` (fail-safe, coerente con `diff-risk-classifier.sh` che fail-safe a `'code'`).
- [ ] `DEVFORGE_MAX_DIFF_LINES` documentata in `hooks/ENV_VARS.md` (nuova sezione `## PR Diff Resolution`), stile tabella coerente con le sezioni esistenti (es. `## Release Risk Assessment`).
- [ ] `tests/lib/diff-truncate.test.sh` verde (5/5 PASS) eseguito standalone con `bash tests/lib/diff-truncate.test.sh`.
- [ ] Nessuna regressione: `lib/diff-risk-classifier.sh` e i suoi test restano invariati (Task 05 non lo tocca).
