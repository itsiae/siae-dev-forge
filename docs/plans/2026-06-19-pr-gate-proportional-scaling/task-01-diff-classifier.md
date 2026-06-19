# Task 01 — `lib/diff-risk-classifier.sh` (NUOVO)

**Goal:** Funzione `devforge_classify_diff_risk` che stampa `low` | `code` classificando
il diff vs base branch per estensione/path, rename-aware, fail-safe `code`.

**File:** crea `lib/diff-risk-classifier.sh` + `tests/hooks/test_diff_risk_classifier.sh`.
**Copre AC:** AC-1..6, AC-11..14.

---

## Step 1 — Test fallente

Crea `tests/hooks/test_diff_risk_classifier.sh`. Usa repo git temporaneo reale:

```bash
#!/usr/bin/env bash
# test_diff_risk_classifier.sh — classificazione rischio diff per gate PR scaling.
set -eu
PASS=0; FAIL=0
REPO_ROOT="$(git rev-parse --show-toplevel)"
LIB="${REPO_ROOT}/lib/diff-risk-classifier.sh"

# Crea un repo git temp con base 'main' e un branch con i file passati come $@.
# $1 = nome caso ; resto = "op:path" dove op = add|rename:OLD>NEW
_mkrepo() {
    local td; td=$(mktemp -d)
    ( cd "$td"
      git init -q; git config user.email t@t; git config user.name t
      echo seed > seed.txt; git add -A; git commit -qm seed; git branch -m main
      git checkout -qb work ) >/dev/null 2>&1
    echo "$td"
}
_run() {  # $1=repodir → stampa risk
    ( cd "$1" && source "$LIB" && devforge_classify_diff_risk "main" )
}

echo "=== AC-1: solo .md → low ==="
TD=$(_mkrepo); ( cd "$TD" && echo x > a.md && git add -A && git commit -qm m ) >/dev/null 2>&1
[ "$(_run "$TD")" = "low" ] && { echo PASS; PASS=$((PASS+1)); } || { echo FAIL; FAIL=$((FAIL+1)); }
rm -rf "$TD"

echo "=== AC-2: solo .claude-plugin/plugin.json → low ==="
TD=$(_mkrepo); ( cd "$TD" && mkdir -p .claude-plugin && echo '{}' > .claude-plugin/plugin.json && git add -A && git commit -qm m ) >/dev/null 2>&1
[ "$(_run "$TD")" = "low" ] && { echo PASS; PASS=$((PASS+1)); } || { echo FAIL; FAIL=$((FAIL+1)); }
rm -rf "$TD"

echo "=== AC-3: hooks/foo misto a .md → code ==="
TD=$(_mkrepo); ( cd "$TD" && echo x > a.md && mkdir -p hooks && echo y > hooks/foo && git add -A && git commit -qm m ) >/dev/null 2>&1
[ "$(_run "$TD")" = "code" ] && { echo PASS; PASS=$((PASS+1)); } || { echo FAIL; FAIL=$((FAIL+1)); }
rm -rf "$TD"

echo "=== AC-4: hooks.json → code ==="
TD=$(_mkrepo); ( cd "$TD" && mkdir -p hooks && echo '{}' > hooks/hooks.json && git add -A && git commit -qm m ) >/dev/null 2>&1
[ "$(_run "$TD")" = "code" ] && { echo PASS; PASS=$((PASS+1)); } || { echo FAIL; FAIL=$((FAIL+1)); }
rm -rf "$TD"

echo "=== AC-5: diff vuoto → code ==="
TD=$(_mkrepo)  # work == main, nessun commit
[ "$(_run "$TD")" = "code" ] && { echo PASS; PASS=$((PASS+1)); } || { echo FAIL; FAIL=$((FAIL+1)); }
rm -rf "$TD"

echo "=== AC-6: .py/.sh → code ==="
TD=$(_mkrepo); ( cd "$TD" && echo x > a.py && git add -A && git commit -qm m ) >/dev/null 2>&1
[ "$(_run "$TD")" = "code" ] && { echo PASS; PASS=$((PASS+1)); } || { echo FAIL; FAIL=$((FAIL+1)); }
rm -rf "$TD"

echo "=== AC-11: rename hooks/x.sh → docs/x.md → code (sorgente non-allowlist) ==="
TD=$(_mkrepo)
( cd "$TD" && git checkout -q main && mkdir -p hooks && echo s > hooks/x.sh && git add -A && git commit -qm base && git checkout -q work && git merge -q main && mkdir -p docs && git mv hooks/x.sh docs/x.md && git commit -qm ren ) >/dev/null 2>&1
[ "$(_run "$TD")" = "code" ] && { echo PASS; PASS=$((PASS+1)); } || { echo FAIL; FAIL=$((FAIL+1)); }
rm -rf "$TD"

echo "=== AC-12: docs/runme senza estensione → code ==="
TD=$(_mkrepo); ( cd "$TD" && mkdir -p docs && echo x > docs/runme && git add -A && git commit -qm m ) >/dev/null 2>&1
[ "$(_run "$TD")" = "code" ] && { echo PASS; PASS=$((PASS+1)); } || { echo FAIL; FAIL=$((FAIL+1)); }
rm -rf "$TD"

echo "=== AC-13: base branch arg alternativo usato ==="
TD=$(_mkrepo); ( cd "$TD" && git branch alt main && echo x > a.md && git add -A && git commit -qm m ) >/dev/null 2>&1
[ "$( ( cd "$TD" && source "$LIB" && devforge_classify_diff_risk "alt" ) )" = "low" ] && { echo PASS; PASS=$((PASS+1)); } || { echo FAIL; FAIL=$((FAIL+1)); }
rm -rf "$TD"

echo "=== AC-14: .claude-plugin/evil.json → code (non-manifest) ==="
TD=$(_mkrepo); ( cd "$TD" && mkdir -p .claude-plugin && echo '{}' > .claude-plugin/evil.json && git add -A && git commit -qm m ) >/dev/null 2>&1
[ "$(_run "$TD")" = "code" ] && { echo PASS; PASS=$((PASS+1)); } || { echo FAIL; FAIL=$((FAIL+1)); }
rm -rf "$TD"

echo ""; echo "RESULT: PASS=$PASS FAIL=$FAIL"; [ "$FAIL" -eq 0 ]
```

## Step 2 — Esegui (RED)
Run: `bash tests/hooks/test_diff_risk_classifier.sh`
Atteso: FAIL su tutti (lib inesistente → `source` fallisce / funzione assente).

## Step 3 — Implementa `lib/diff-risk-classifier.sh`

```bash
#!/usr/bin/env bash
# diff-risk-classifier.sh — classifica il rischio di un diff per lo scaling dei gate PR.
# Output: 'low' (solo doc/manifest) | 'code' (qualsiasi altro / dubbio). Fail-safe: code.
# Design: docs/plans/2026-06-19-pr-gate-proportional-scaling-design.md

# True se il path è low-risk: estensione documentale OR manifest plugin esatto.
_devforge_path_is_lowrisk() {
    case "$1" in
        *.md|*.txt|*.rst|*.pdf|*.png|*.jpg|*.jpeg|*.svg) return 0 ;;
        .claude-plugin/plugin.json|.claude-plugin/marketplace.json) return 0 ;;
        *) return 1 ;;
    esac
}

# Stampa 'low' | 'code'. $1 = base branch (default origin/main).
devforge_classify_diff_risk() {
    local base="${1:-origin/main}"
    local status
    status=$(git diff --name-status "${base}...HEAD" 2>/dev/null) || { printf 'code'; return 0; }
    [ -z "$status" ] && { printf 'code'; return 0; }   # diff vuoto = nessun motivo di scalare
    local line op p1 p2
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        op=$(printf '%s' "$line" | cut -f1)
        case "$op" in
            R*)  # rename: cut -f2 = OLD, cut -f3 = NEW — entrambi devono essere low-risk
                p1=$(printf '%s' "$line" | cut -f2)
                p2=$(printf '%s' "$line" | cut -f3)
                _devforge_path_is_lowrisk "$p1" || { printf 'code'; return 0; }
                _devforge_path_is_lowrisk "$p2" || { printf 'code'; return 0; }
                ;;
            *)
                p1=$(printf '%s' "$line" | cut -f2)
                _devforge_path_is_lowrisk "$p1" || { printf 'code'; return 0; }
                ;;
        esac
    done <<EOF
$status
EOF
    printf 'low'
}
```

## Step 4 — Esegui (GREEN)
Run: `bash tests/hooks/test_diff_risk_classifier.sh`
Atteso: `RESULT: PASS=10 FAIL=0`. Inoltre `bash -n lib/diff-risk-classifier.sh` → OK.

## Step 5 — Commit
```bash
git add lib/diff-risk-classifier.sh tests/hooks/test_diff_risk_classifier.sh
git commit -m "feat(lib): diff-risk-classifier per scaling gate PR (task-01)"
```

## Criteri di accettazione
- [ ] `devforge_classify_diff_risk` stampa esattamente `low`|`code`, mai vuoto.
- [ ] `low` solo se TUTTI i path sono allowlist (estensione doc o 2 manifest esatti).
- [ ] Rename con src/dst fuori allowlist → `code` (AC-11).
- [ ] git fail / diff vuoto → `code` (AC-5).
- [ ] `test_diff_risk_classifier.sh` → PASS=10 FAIL=0.
