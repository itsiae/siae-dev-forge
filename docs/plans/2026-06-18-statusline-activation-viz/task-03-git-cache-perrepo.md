# Task 03 — #1: cache git per-cwd (fix bug cross-repo)

**Stato:** [PENDING]
**File:** `tests/statusline/test_statusline_git_cache_perrepo.sh` (nuovo), `statusline/devforge-statusline.sh`
**AC coperti:** AC-#1
**Stima:** Umano ~1 · Augmented ~0.5

## Ciclo TDD

### RED — nuovo test

Crea `tests/statusline/test_statusline_git_cache_perrepo.sh`. Verifica che due cwd diversi producano file cache distinti e che il branch in cache di un cwd non contamini l'altro.

```bash
#!/usr/bin/env bash
# Test: cache git keyed per-cwd, nessuna contaminazione cross-repo (#1)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATUSLINE="$(cd "$SCRIPT_DIR/../../statusline" && pwd)/devforge-statusline.sh"
PASS=0; FAIL=0

HOME_SB="$(mktemp -d)"; mkdir -p "$HOME_SB/.claude"

# due repo git fittizi con branch diversi
mk_repo() { # dir branch
  mkdir -p "$1"; ( cd "$1" && git init -q && git checkout -q -b "$2" && git commit -q --allow-empty -m init ) 2>/dev/null
}
R1="$(mktemp -d)/repoA"; mk_repo "$R1" "branch-aaa"
R2="$(mktemp -d)/repoB"; mk_repo "$R2" "branch-bbb"

render() { ( cd "$1" && printf '{}' | HOME="$HOME_SB" bash "$STATUSLINE" 2>/dev/null | head -1 ); }

# Render repoA poi repoB: B non deve mostrare branch-aaa
OUT_A="$(render "$R1")"
OUT_B="$(render "$R2")"
if printf '%s' "$OUT_A" | grep -q "branch-aaa"; then PASS=$((PASS+1)); echo "  PASS  repoA mostra branch-aaa"; else FAIL=$((FAIL+1)); echo "  FAIL  repoA (out: $OUT_A)"; fi
if printf '%s' "$OUT_B" | grep -q "branch-bbb" && ! printf '%s' "$OUT_B" | grep -q "branch-aaa"; then
  PASS=$((PASS+1)); echo "  PASS  repoB mostra branch-bbb senza contaminazione"
else
  FAIL=$((FAIL+1)); echo "  FAIL  repoB contaminato (out: $OUT_B)"
fi

# Due file cache distinti creati
ncache=$(ls "$HOME_SB/.claude"/.devforge-git-cache* 2>/dev/null | wc -l | tr -d ' ')
if [ "$ncache" -ge 2 ]; then PASS=$((PASS+1)); echo "  PASS  cache keyed per-cwd ($ncache file)"; else FAIL=$((FAIL+1)); echo "  FAIL  cache non keyed ($ncache file)"; fi

rm -rf "$HOME_SB" "$(dirname "$R1")" "$(dirname "$R2")"
echo "  TOTALE: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
```

Esegui → DEVE fallire (oggi cache globale, repoB può mostrare branch-aaa entro 5s e c'è 1 solo file cache).

### GREEN — implementa in statusline

Sostituisci la riga 28:
```bash
CACHE_FILE="${DEVFORGE_DIR}/.devforge-git-cache"
```
con una key per-cwd (cksum POSIX):
```bash
# Cache git keyed per-cwd: evita contaminazione cross-repo/sessione (#1)
_cwd_key="$(printf '%s' "$PWD" | cksum 2>/dev/null | tr -dc '0-9' | cut -c1-12)"
_cwd_key="${_cwd_key:-default}"
CACHE_FILE="${DEVFORGE_DIR}/.devforge-git-cache-${_cwd_key}"
unset _cwd_key
```

Riesegui test → PASS=3 FAIL=0.

### REFACTOR
Nessuno. (Nota: i vecchi file `.devforge-git-cache` senza suffisso restano orfani innocui; non vanno puliti in questo task.)

## Criteri di completamento
- [ ] `test_statusline_git_cache_perrepo.sh` PASS=3 FAIL=0
- [ ] due cwd → due file cache distinti
- [ ] nessuna contaminazione cross-repo
