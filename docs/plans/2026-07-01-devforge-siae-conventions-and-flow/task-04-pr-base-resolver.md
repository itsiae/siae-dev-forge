# Task 04 — `lib/pr-base-resolver.sh` + unit test

**Cluster:** B diff (REQ-DF-03)
**Dipendenze:** nessuna (primo task del cluster B; Task 06/07 dipendono da questo)

## Goal

`lib/pr-base-resolver.sh` espone `devforge_resolve_pr_base()` che, invocata dentro un repo git, stampa su stdout il nome del branch base corretto seguendo la precedenza: (1) PR esistente per il branch corrente via `gh pr view --json baseRefName`; (2) merge-base distance voting su `origin/release/*` + `origin/sviluppo`; (3) `git symbolic-ref refs/remotes/origin/HEAD`; (4) letterale `main`.

## File coinvolti

- `lib/pr-base-resolver.sh` — **nuovo**.
- `tests/lib/test_pr_base_resolver.sh` — **nuovo**.
- `tests/run-all.sh` — **modifica** (aggiungere invocazione test, in coda al blocco `test_net_timeout.sh` a `:1171-1178`, pattern identico a quel blocco).

## Step TDD

### Step 1 — Scrivi il test fallente (COMPLETO)

Scrivi `tests/lib/test_pr_base_resolver.sh`:

```bash
#!/usr/bin/env bash
# test_pr_base_resolver.sh — unit tests for lib/pr-base-resolver.sh (REQ-DF-03)
# ─────────────────────────────────────────────────────────────────
# Covers: precedenza (1) gh pr view esistente, (2) merge-base distance
# voting su origin/release/* + origin/sviluppo, (3) symbolic-ref
# origin/HEAD, (4) fallback letterale 'main'.
# Ogni scenario usa un repo git temporaneo isolato (fixture), mai il
# repo DevForge stesso, per non dipendere dallo stato reale di origin.
# ─────────────────────────────────────────────────────────────────
set -uo pipefail
PASS=0; FAIL=0
ok(){ echo "  PASS: $1"; PASS=$((PASS+1)); }
ko(){ echo "  FAIL: $1 ($2)"; FAIL=$((FAIL+1)); }

REPO_ROOT="$(git rev-parse --show-toplevel)"
LIB_FILE="${REPO_ROOT}/lib/pr-base-resolver.sh"

if [ ! -f "$LIB_FILE" ]; then
    echo "FAIL — $LIB_FILE not found"
    exit 1
fi

# shellcheck disable=SC1090
source "$LIB_FILE"

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

# _mk_bare_remote <name> — crea un bare repo che farà da "origin" per i clone locali.
_mk_bare_remote() {
    local remote_dir="$WORKDIR/$1.git"
    git init --bare -q "$remote_dir"
    printf '%s' "$remote_dir"
}

# _mk_clone <clone_name> <remote_dir> — clona il remote e configura identity locale.
_mk_clone() {
    local clone_dir="$WORKDIR/$1"
    git clone -q "$2" "$clone_dir"
    git -C "$clone_dir" config user.email "test@example.com"
    git -C "$clone_dir" config user.name "Test"
    printf '%s' "$clone_dir"
}

# _commit <clone_dir> <msg> — commit vuoto con messaggio dato.
_commit() {
    git -C "$1" commit -q --allow-empty -m "$2"
}

# ── Scenario 1: branch derivato da main, nessuna PR aperta, nessun
#    origin/release/* o origin/sviluppo → precedenza (3) symbolic-ref
#    (se impostato su main in questo fixture) altrimenti (4) letterale main.
REMOTE1=$(_mk_bare_remote "remote1")
CLONE1=$(_mk_clone "clone1" "$REMOTE1")
_commit "$CLONE1" "chore: init main"
git -C "$CLONE1" push -q -u origin main
git -C "$CLONE1" checkout -q -b feature/scenario-main
_commit "$CLONE1" "feat: lavoro su feature/scenario-main"
git -C "$REMOTE1" symbolic-ref HEAD refs/heads/main
RESULT=$(cd "$CLONE1" && devforge_resolve_pr_base 2>/dev/null)
[ "$RESULT" = "main" ] && ok "Scenario1 branch-off-main risolve main" \
    || ko "Scenario1 branch-off-main risolve main" "got '$RESULT'"

# ── Scenario 2: branch derivato da un 'sviluppo' locale/remoto (nessun
#    release/*, nessuna PR) → merge-base distance voting sceglie sviluppo.
REMOTE2=$(_mk_bare_remote "remote2")
CLONE2=$(_mk_clone "clone2" "$REMOTE2")
_commit "$CLONE2" "chore: init main"
git -C "$CLONE2" push -q -u origin main
git -C "$CLONE2" checkout -q -b sviluppo
_commit "$CLONE2" "chore: init sviluppo"
git -C "$CLONE2" push -q -u origin sviluppo
git -C "$CLONE2" checkout -q -b feature/scenario-sviluppo
_commit "$CLONE2" "feat: lavoro su feature/scenario-sviluppo"
RESULT=$(cd "$CLONE2" && devforge_resolve_pr_base 2>/dev/null)
[ "$RESULT" = "sviluppo" ] && ok "Scenario2 branch-off-sviluppo risolve sviluppo" \
    || ko "Scenario2 branch-off-sviluppo risolve sviluppo" "got '$RESULT'"

# ── Scenario 3: branch derivato da 'release/x' (candidato con distanza
#    minore rispetto a sviluppo) → merge-base distance voting sceglie release/x.
REMOTE3=$(_mk_bare_remote "remote3")
CLONE3=$(_mk_clone "clone3" "$REMOTE3")
_commit "$CLONE3" "chore: init main"
git -C "$CLONE3" push -q -u origin main
git -C "$CLONE3" checkout -q -b sviluppo
_commit "$CLONE3" "chore: init sviluppo"
git -C "$CLONE3" push -q -u origin sviluppo
git -C "$CLONE3" checkout -q -b release/2026-07-01
_commit "$CLONE3" "chore: init release/2026-07-01"
git -C "$CLONE3" push -q -u origin release/2026-07-01
git -C "$CLONE3" checkout -q -b fix/scenario-release
_commit "$CLONE3" "fix: lavoro su fix/scenario-release"
RESULT=$(cd "$CLONE3" && devforge_resolve_pr_base 2>/dev/null)
[ "$RESULT" = "release/2026-07-01" ] && ok "Scenario3 branch-off-release risolve release/2026-07-01" \
    || ko "Scenario3 branch-off-release risolve release/2026-07-01" "got '$RESULT'"

# ── Scenario 4: gh disponibile e simulato per ritornare una PR esistente
#    con baseRefName='sviluppo' → precedenza (1) vince su tutto il resto,
#    anche se il merge-base voting suggerirebbe un candidato diverso.
REMOTE4=$(_mk_bare_remote "remote4")
CLONE4=$(_mk_clone "clone4" "$REMOTE4")
_commit "$CLONE4" "chore: init main"
git -C "$CLONE4" push -q -u origin main
git -C "$CLONE4" checkout -q -b feature/scenario-pr-exists
_commit "$CLONE4" "feat: lavoro su feature/scenario-pr-exists"
FAKE_GH_DIR="$WORKDIR/fakebin"
mkdir -p "$FAKE_GH_DIR"
cat > "$FAKE_GH_DIR/gh" <<'FAKEGH'
#!/usr/bin/env bash
if [ "$1" = "pr" ] && [ "$2" = "view" ]; then
    echo "sviluppo"
    exit 0
fi
exit 1
FAKEGH
chmod +x "$FAKE_GH_DIR/gh"
RESULT=$(cd "$CLONE4" && PATH="$FAKE_GH_DIR:$PATH" devforge_resolve_pr_base 2>/dev/null)
[ "$RESULT" = "sviluppo" ] && ok "Scenario4 PR esistente vince su merge-base voting" \
    || ko "Scenario4 PR esistente vince su merge-base voting" "got '$RESULT'"

echo "pr-base-resolver: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
```

Rendi il file eseguibile: `chmod +x tests/lib/test_pr_base_resolver.sh`.

### Step 2 — Esegui e verifica il FAIL

Comando:

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && bash tests/lib/test_pr_base_resolver.sh
```

Output atteso (il file `lib/pr-base-resolver.sh` non esiste ancora):

```
FAIL — /Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge/lib/pr-base-resolver.sh not found
```

Con exit code `1`.

### Step 3 — Implementa il codice minimo (COMPLETO)

Crea `lib/pr-base-resolver.sh`:

```bash
#!/usr/bin/env bash
# pr-base-resolver.sh — risolve il branch base corretto per una PR/diff.
# Precedenza: (1) PR esistente per il branch corrente (gh pr view); (2)
# merge-base distance voting su origin/release/* + origin/sviluppo; (3)
# git symbolic-ref refs/remotes/origin/HEAD; (4) letterale 'main'.
# Design: docs/plans/2026-07-01-devforge-siae-conventions-and-flow/design.md (REQ-DF-03)
# Algoritmo (2) da: skills/siae-finishing-branch/reference/finishing-branch-checklist.md:75-83

# _devforge_pr_base_from_gh — stampa baseRefName se una PR esiste per HEAD, altrimenti niente.
# Fail-safe: qualsiasi errore (gh assente, non autenticato, nessuna PR) → stdout vuoto.
_devforge_pr_base_from_gh() {
    command -v gh >/dev/null 2>&1 || return 1
    local base
    base=$(gh pr view --json baseRefName -q .baseRefName 2>/dev/null) || return 1
    [ -n "$base" ] || return 1
    printf '%s' "$base"
}

# _devforge_pr_base_from_voting — merge-base distance voting su
# origin/release/* + origin/sviluppo. Il candidato con distanza minore
# (git rev-list --count) vince. Stampa niente se nessun candidato esiste.
_devforge_pr_base_from_voting() {
    local candidates candidate merge_base distance
    local best_name="" best_distance=""
    candidates=$(git branch -r --list 'origin/release/*' --list 'origin/sviluppo' 2>/dev/null \
        | sed 's/^[[:space:]]*//' | sed 's#^origin/##')
    [ -n "$candidates" ] || return 1
    while IFS= read -r candidate; do
        [ -z "$candidate" ] && continue
        merge_base=$(git merge-base HEAD "origin/${candidate}" 2>/dev/null) || continue
        distance=$(git rev-list --count "${merge_base}..HEAD" 2>/dev/null) || continue
        if [ -z "$best_distance" ] || [ "$distance" -lt "$best_distance" ]; then
            best_distance="$distance"
            best_name="$candidate"
        fi
    done <<EOF
$candidates
EOF
    [ -n "$best_name" ] || return 1
    printf '%s' "$best_name"
}

# _devforge_pr_base_from_symbolic_ref — HEAD simbolico di origin (default branch remoto).
_devforge_pr_base_from_symbolic_ref() {
    local ref
    ref=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null) || return 1
    [ -n "$ref" ] || return 1
    printf '%s' "${ref#refs/remotes/origin/}"
}

# devforge_resolve_pr_base — stampa su stdout il branch base risolto.
# Non fallisce mai: l'ultimo fallback è il letterale 'main'.
devforge_resolve_pr_base() {
    local result
    result=$(_devforge_pr_base_from_gh) && [ -n "$result" ] && { printf '%s\n' "$result"; return 0; }
    result=$(_devforge_pr_base_from_voting) && [ -n "$result" ] && { printf '%s\n' "$result"; return 0; }
    result=$(_devforge_pr_base_from_symbolic_ref) && [ -n "$result" ] && { printf '%s\n' "$result"; return 0; }
    printf '%s\n' "main"
}
```

Rendi il file eseguibile: `chmod +x lib/pr-base-resolver.sh`.

Nota: il test consuma l'output con `$(... 2>/dev/null)` quindi il trailing newline di `printf '%s\n'` viene rimosso automaticamente da command substitution — coerente con l'uso in altri helper `lib/*.sh` (es. `devforge_classify_diff_risk` in `lib/diff-risk-classifier.sh:41` usa `printf '%s'` senza newline; qui usiamo `\n` per compatibilità con uso diretto `echo "$(devforge_resolve_pr_base)"` nei siti chiamanti, entrambi gli stili sono equivalenti sotto `$(...)`).

### Step 4 — Esegui e verifica il PASS

Comando:

```bash
cd "/Users/detomasi/Library/Mobile Documents/com~apple~CloudDocs/siae-dev-forge" && bash tests/lib/test_pr_base_resolver.sh
```

Output atteso:

```
  PASS: Scenario1 branch-off-main risolve main
  PASS: Scenario2 branch-off-sviluppo risolve sviluppo
  PASS: Scenario3 branch-off-release risolve release/2026-07-01
  PASS: Scenario4 PR esistente vince su merge-base voting
pr-base-resolver: PASS=4 FAIL=0
```

Con exit code `0`.

Poi aggiungi in `tests/run-all.sh` (subito dopo il blocco `test_net_timeout.sh`, righe `1171-1178` nello stato attuale del file — verificare il numero riga esatto al momento dell'edit perché precedenti task del piano possono averlo spostato) il blocco gemello:

```bash
# Test pr-base-resolver: precedenza gh pr view > merge-base voting > symbolic-ref > main
if bash "${PLUGIN_ROOT}/tests/lib/test_pr_base_resolver.sh" >/dev/null 2>&1; then
  echo "  PASS  pr-base-resolver: precedenza gh pr view / voting / symbolic-ref / main"
  telfunc_ok=$((telfunc_ok + 1))
else
  echo "  FAIL  pr-base-resolver: risoluzione branch base rotta"
  telfunc_fail=$((telfunc_fail + 1))
fi
```

Verifica che la variabile contatore usata nel blocco copiato (`telfunc_ok`/`telfunc_fail`) sia effettivamente quella in scope in quel punto del file leggendo il contesto circostante prima di incollare — se il nome differisce, usa quello reale del blocco `test_net_timeout.sh` adiacente.

### Step 5 — Commit

```
git add lib/pr-base-resolver.sh tests/lib/test_pr_base_resolver.sh tests/run-all.sh
git commit -m "feat(lib): aggiungi pr-base-resolver con precedenza gh/voting/symbolic-ref/main

Nuovo lib/pr-base-resolver.sh — devforge_resolve_pr_base() risolve il
branch base corretto per diff/PR: (1) gh pr view se una PR esiste per
il branch corrente, (2) merge-base distance voting su origin/release/*
+ origin/sviluppo (algoritmo da finishing-branch-checklist.md), (3)
git symbolic-ref origin/HEAD, (4) letterale main come ultimo fallback.
Elimina la dipendenza dagli ~11 hardcode origin/main sparsi nei gate
(REQ-DF-03)."
```

## Criteri di accettazione

- [ ] `lib/pr-base-resolver.sh` esiste, è eseguibile, ed espone `devforge_resolve_pr_base` sourceable senza errori.
- [ ] AC1 design (base = merge-base del target, non main hardcoded): Scenario2/Scenario3 del test dimostrano che branch derivati da `sviluppo`/`release/*` risolvono al branch reale, non a `main`.
- [ ] Precedenza (1) rispettata: Scenario4 dimostra che una PR esistente (`gh pr view`) vince sul merge-base voting anche quando quest'ultimo suggerirebbe un candidato diverso.
- [ ] Precedenza (4) rispettata: Scenario1 dimostra che in assenza di PR/candidati release/sviluppo il fallback finale è `main` (via symbolic-ref se configurato su main, altrimenti letterale).
- [ ] Nessuna dipendenza da rete reale nel test: tutti gli scenari usano repo git locali temporanei (bare + clone), `gh` è stubbato via `PATH` fake, mai chiamato realmente.
- [ ] `bash tests/lib/test_pr_base_resolver.sh` esce con `0` e stampa `PASS=4 FAIL=0`.
- [ ] `tests/run-all.sh` invoca il nuovo test nello stesso stile del blocco `test_net_timeout.sh` adiacente (contatori coerenti con lo scope reale del file).
- [ ] Zero regressioni: la suite esistente `tests/run-all.sh` resta verde (nessun test preesistente rotto dall'aggiunta).
